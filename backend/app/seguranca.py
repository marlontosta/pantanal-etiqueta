"""Senhas (scrypt, da biblioteca padrão) e sessões por cookie."""
import base64
import hashlib
import hmac
import secrets
import time
from datetime import datetime, timedelta, timezone

from . import config, db

COOKIE = "pantanal_sessao"
# Senha errada: depois de 5 tentativas em 15 minutos, o usuário fica bloqueado até a janela passar.
_falhas: dict[str, list[float]] = {}
MAX_FALHAS, JANELA = 5, 15 * 60


def gerar_hash(senha: str) -> str:
    sal = secrets.token_bytes(16)
    h = hashlib.scrypt(senha.encode(), salt=sal, n=2**14, r=8, p=1)
    return "scrypt$" + base64.b64encode(sal).decode() + "$" + base64.b64encode(h).decode()


def conferir(senha: str, guardado: str) -> bool:
    try:
        _, sal, h = guardado.split("$")
        novo = hashlib.scrypt(senha.encode(), salt=base64.b64decode(sal), n=2**14, r=8, p=1)
        return hmac.compare_digest(novo, base64.b64decode(h))
    except ValueError:
        return False


def bloqueado(usuario: str) -> bool:
    agora = time.monotonic()
    tent = [t for t in _falhas.get(usuario.lower(), []) if agora - t < JANELA]
    _falhas[usuario.lower()] = tent
    return len(tent) >= MAX_FALHAS


def registrar_falha(usuario: str) -> None:
    _falhas.setdefault(usuario.lower(), []).append(time.monotonic())


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def autenticar(usuario: str, senha: str):
    """Devolve o usuário se a senha confere; None caso contrário."""
    with db.transacao() as con:
        u = con.execute("SELECT * FROM usuarios WHERE usuario = ?", (usuario,)).fetchone()
    if u is None:
        gerar_hash(senha)  # gasta o mesmo tempo, para não revelar quais usuários existem
        return None
    return u if conferir(senha, u["senha_hash"]) else None


def criar_sessao(usuario_id: int) -> str:
    token = secrets.token_urlsafe(32)
    expira = datetime.now(timezone.utc) + timedelta(days=config.SESSAO_DIAS)
    with db.transacao() as con:
        con.execute("DELETE FROM sessoes WHERE expira_em < ?", (datetime.now(timezone.utc).isoformat(),))
        con.execute("INSERT INTO sessoes VALUES (?, ?, ?)", (_hash_token(token), usuario_id, expira.isoformat()))
    return token


def usuario_da_sessao(token: str | None):
    if not token:
        return None
    with db.transacao() as con:
        return con.execute(
            "SELECT u.id, u.usuario, u.nome FROM sessoes s JOIN usuarios u ON u.id = s.usuario_id"
            " WHERE s.token_hash = ? AND s.expira_em > ?",
            (_hash_token(token), datetime.now(timezone.utc).isoformat()),
        ).fetchone()


def encerrar_sessao(token: str | None) -> None:
    if token:
        with db.transacao() as con:
            con.execute("DELETE FROM sessoes WHERE token_hash = ?", (_hash_token(token),))
