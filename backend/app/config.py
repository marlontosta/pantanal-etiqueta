"""Configuração do backend. Valores de ambiente sobrescrevem os padrões."""
import os
import pathlib
from datetime import date, datetime, timedelta, timezone

RAIZ = pathlib.Path(__file__).resolve().parents[2]
FRONTEND = RAIZ / "frontend"

# Banco SQLite. Em hospedagem, aponte para um disco que não se apaga a cada deploy.
BANCO = pathlib.Path(os.environ.get("PANTANAL_BANCO", RAIZ / "backend" / "dados" / "pantanal.db"))
# PDFs das ordens de serviço: por padrão numa pasta "os" ao lado do banco, no mesmo disco.
ARQUIVOS_OS = pathlib.Path(os.environ.get("PANTANAL_ARQUIVOS_OS", BANCO.parent / "os"))
OS_TAMANHO_MAXIMO = 10 * 1024 * 1024
# Cookie só por https em produção; em http local precisa ser 0.
COOKIE_SEGURO = os.environ.get("PANTANAL_COOKIE_SEGURO", "1") != "0"
SESSAO_DIAS = int(os.environ.get("PANTANAL_SESSAO_DIAS", "30"))
# Sites que podem ler a resposta de "minha frota" (a página do cliente no GitHub Pages), separados por vírgula.
ORIGENS_CLIENTE = [o.strip() for o in os.environ.get("PANTANAL_ORIGENS_CLIENTE", "https://marlontosta.github.io").split(",") if o.strip()]
# Primeiro acesso em hospedagens sem terminal: cria este usuário se o banco não tiver nenhum.
USUARIO_INICIAL = os.environ.get("PANTANAL_USUARIO")
SENHA_INICIAL = os.environ.get("PANTANAL_SENHA")

# Os mesmos serviços, letras e intervalos de frontend/cliente/config.js (um teste confere).
SERVICOS = [
    {"id": "oleo", "c": "o", "nome": "Troca de óleo e filtro", "intervalo_km": 10000, "intervalo_meses": 12},
    {"id": "rev", "c": "r", "nome": "Revisão mecânica", "intervalo_km": 10000, "intervalo_meses": 12},
    {"id": "geo", "c": "g", "nome": "Geometria (alinhamento e balanceamento)", "intervalo_km": 10000, "intervalo_meses": 6},
    {"id": "hig", "c": "h", "nome": "Higienização do ar-condicionado", "intervalo_km": 10000, "intervalo_meses": 12},
]
SERVICO_POR_ID = {s["id"]: s for s in SERVICOS}
# Amarelo: faltam até 10% do intervalo ou 3.000 km (o menor), ou até 30 dias.
MARGEM = {"fracao": 0.1, "km": 3000, "dias": 30}


def hoje() -> date:
    # Horário de Mato Grosso do Sul (UTC-4, sem horário de verão).
    return datetime.now(timezone(timedelta(hours=-4))).date()
