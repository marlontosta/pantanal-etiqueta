"""API da Pantanal Pneus e páginas da área da oficina.

Rodar: uvicorn app.main:app --reload  (dentro de backend/)
"""
import json
import re
import time
from contextlib import asynccontextmanager
from datetime import date

from fastapi import Cookie, Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, ValidationError, field_validator

from . import config, db, frota, seguranca

OFICINA = config.FRONTEND / "oficina"
PLACA = re.compile(r"^[A-Z]{3}\d[A-Z0-9]\d{2}$")


@asynccontextmanager
async def iniciar(_app):
    db.criar_tabelas()
    if config.USUARIO_INICIAL and config.SENHA_INICIAL:
        with db.transacao() as con:
            if not con.execute("SELECT 1 FROM usuarios").fetchone():
                con.execute("INSERT INTO usuarios (usuario, senha_hash) VALUES (?, ?)",
                            (config.USUARIO_INICIAL, seguranca.gerar_hash(config.SENHA_INICIAL)))
    yield


app = FastAPI(title="Pantanal Pneus", docs_url=None, redoc_url=None, openapi_url=None, lifespan=iniciar)


def usuario_logado(pantanal_sessao: str | None = Cookie(None)):
    u = seguranca.usuario_da_sessao(pantanal_sessao)
    if u is None:
        raise HTTPException(401, "Entre com usuário e senha.")
    return u


# Login

class Login(BaseModel):
    usuario: str = Field(min_length=1, max_length=60)
    senha: str = Field(min_length=1, max_length=200)


@app.post("/api/entrar")
def entrar(dados: Login, resposta: Response):
    if seguranca.bloqueado(dados.usuario):
        raise HTTPException(429, "Muitas tentativas. Espere 15 minutos.")
    u = seguranca.autenticar(dados.usuario.strip(), dados.senha)
    if u is None:
        seguranca.registrar_falha(dados.usuario)
        raise HTTPException(401, "Usuário ou senha incorretos.")
    token = seguranca.criar_sessao(u["id"])
    resposta.set_cookie(seguranca.COOKIE, token, max_age=config.SESSAO_DIAS * 86400, httponly=True,
                        secure=config.COOKIE_SEGURO, samesite="lax", path="/")
    return {"usuario": u["usuario"], "nome": u["nome"]}


@app.post("/api/sair")
def sair(resposta: Response, pantanal_sessao: str | None = Cookie(None)):
    seguranca.encerrar_sessao(pantanal_sessao)
    resposta.delete_cookie(seguranca.COOKIE, path="/")
    return {"ok": True}


@app.get("/api/eu")
def eu(u=Depends(usuario_logado)):
    return {"usuario": u["usuario"], "nome": u["nome"]}


# Registros de serviço (enviados pela tela de gravar etiqueta)

def placa_valida(v: str) -> str:
    v = re.sub(r"[^A-Z0-9]", "", v.upper())
    if not PLACA.match(v):
        raise ValueError("placa inválida")
    return v


class Servico(BaseModel):
    servico: str
    km: int | None = Field(None, ge=0, le=9_999_999)
    data: date

    @field_validator("servico")
    @classmethod
    def servico_conhecido(cls, v: str) -> str:
        if v not in config.SERVICO_POR_ID:
            raise ValueError("serviço desconhecido")
        return v


class Visita(BaseModel):
    placa: str
    servicos: list[Servico] = Field(max_length=20)

    _placa = field_validator("placa")(placa_valida)


@app.post("/api/registros")
def salvar_registros(visita: Visita, u=Depends(usuario_logado)):
    """Guarda o que está na etiqueta. Serviço já salvo no mesmo dia só atualiza o km."""
    with db.transacao() as con:
        for s in visita.servicos:
            if s.data > config.hoje():
                raise HTTPException(422, "Data no futuro: " + s.data.strftime("%d/%m/%Y"))
            cur = con.execute(
                "INSERT INTO registros (placa, servico, km, data, usuario_id) VALUES (?, ?, ?, ?, ?)"
                " ON CONFLICT (placa, servico, data) DO UPDATE SET km = COALESCE(excluded.km, km)",
                (visita.placa, s.servico, s.km, s.data.isoformat(), u["id"]),
            )
    return {"placa": visita.placa, "recebidos": len(visita.servicos)}


# Km que o cliente digita na página da etiqueta. Público: a página do cliente não tem login.
# Vem também da página antiga no GitHub Pages, que manda sem CORS (texto puro, sem ler a resposta).

class Leitura(BaseModel):
    placa: str
    km: int = Field(ge=1, le=9_999_999)

    _placa = field_validator("placa")(placa_valida)


# Por IP: no máximo 30 envios por hora, para ninguém encher o banco.
_envios: dict[str, list[float]] = {}
MAX_ENVIOS, JANELA_ENVIOS = 30, 3600


def _ip(req: Request) -> str:
    fwd = req.headers.get("x-real-ip") or req.headers.get("x-forwarded-for", "").split(",")[0].strip()
    return fwd or (req.client.host if req.client else "")


@app.post("/api/leituras")
async def salvar_leitura(req: Request):
    agora, ip = time.monotonic(), _ip(req)
    tent = [t for t in _envios.get(ip, []) if agora - t < JANELA_ENVIOS]
    if len(tent) >= MAX_ENVIOS:
        raise HTTPException(429, "Muitos envios.")
    _envios[ip] = tent + [agora]
    try:
        lt = Leitura.model_validate(json.loads(await req.body()))
    except (ValueError, ValidationError):
        raise HTTPException(422, "Placa ou km inválidos.")
    hoje = config.hoje()
    leituras = frota.leituras_validas(_registros(lt.placa), [{"km": lt.km, "data": hoje.isoformat()}])
    if not leituras[0]["usada"]:
        raise HTTPException(422, "Km não confere com as visitas.")
    with db.transacao() as con:
        con.execute("INSERT INTO leituras_cliente (placa, km, data) VALUES (?, ?, ?)"
                    " ON CONFLICT (placa, data) DO UPDATE SET km = excluded.km, criado_em = datetime('now')",
                    (lt.placa, lt.km, hoje.isoformat()))
    return {"ok": True}


def _registros(placa: str | None = None) -> list[dict]:
    sql, args = "SELECT placa, servico, km, data FROM registros", ()
    if placa:
        sql, args = sql + " WHERE placa = ?", (placa,)
    with db.transacao() as con:
        return [dict(r) for r in con.execute(sql + " ORDER BY placa, data", args)]


def _leituras(placa: str | None = None) -> list[dict]:
    sql, args = "SELECT placa, km, data FROM leituras_cliente", ()
    if placa:
        sql, args = sql + " WHERE placa = ?", (placa,)
    with db.transacao() as con:
        return [dict(r) for r in con.execute(sql + " ORDER BY placa, data", args)]


@app.get("/api/frota")
def ver_frota(u=Depends(usuario_logado)):
    return {"hoje": config.hoje().isoformat(), "servicos": config.SERVICOS,
            "veiculos": frota.resumo_frota(_registros(), config.hoje(), _leituras())}


@app.get("/api/veiculos/{placa}")
def ver_veiculo(placa: str, u=Depends(usuario_logado)):
    placa = re.sub(r"[^A-Z0-9]", "", placa.upper())
    regs = _registros(placa)
    if not regs:
        raise HTTPException(404, "Placa sem registros.")
    leituras = _leituras(placa)
    return {**frota.resumo_veiculo(placa, regs, config.hoje(), leituras), "historico": regs[::-1],
            "leituras": frota.leituras_validas(regs, leituras)[::-1]}


# Páginas da oficina: tudo menos a tela de login exige sessão.

@app.get("/oficina/")
def oficina_inicio():
    return RedirectResponse("/oficina/frota.html", 303)


@app.get("/oficina/{arquivo}")
def oficina(arquivo: str, pantanal_sessao: str | None = Cookie(None)):
    caminho = (OFICINA / arquivo).resolve()
    if caminho.parent != OFICINA.resolve() or not caminho.is_file():
        raise HTTPException(404)
    if caminho.suffix == ".html" and arquivo != "entrar.html" and not seguranca.usuario_da_sessao(pantanal_sessao):
        return RedirectResponse("/oficina/entrar.html?volta=" + arquivo, 303)
    return FileResponse(caminho, headers={"Cache-Control": "no-store"} if caminho.suffix == ".html" else None)


# Página do cliente e arquivos comuns (config.js, estilo.css, logo.png).
app.mount("/", StaticFiles(directory=config.FRONTEND / "cliente", html=True), name="cliente")
