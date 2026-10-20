"""Banco SQLite: usuários, sessões, registros de serviço, clientes, ordens de serviço e km informados pelos clientes."""
import sqlite3
from contextlib import contextmanager

from . import config

ESQUEMA = """
CREATE TABLE IF NOT EXISTS usuarios (
  id INTEGER PRIMARY KEY,
  usuario TEXT NOT NULL UNIQUE COLLATE NOCASE,
  nome TEXT NOT NULL DEFAULT '',
  senha_hash TEXT NOT NULL,
  criado_em TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS sessoes (
  token_hash TEXT PRIMARY KEY,
  usuario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
  expira_em TEXT NOT NULL
);
-- Um serviço feito numa placa, num dia. Gravar a mesma etiqueta de novo não duplica.
CREATE TABLE IF NOT EXISTS registros (
  id INTEGER PRIMARY KEY,
  placa TEXT NOT NULL,
  servico TEXT NOT NULL,
  km INTEGER,
  data TEXT NOT NULL,
  usuario_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
  criado_em TEXT NOT NULL DEFAULT (datetime('now')),
  UNIQUE (placa, servico, data)
);
CREATE INDEX IF NOT EXISTS registros_placa ON registros (placa, data);
-- Km que o cliente digitou na página da etiqueta. Um por placa e dia; vale o último digitado.
CREATE TABLE IF NOT EXISTS leituras_cliente (
  id INTEGER PRIMARY KEY,
  placa TEXT NOT NULL,
  km INTEGER NOT NULL,
  data TEXT NOT NULL,
  criado_em TEXT NOT NULL DEFAULT (datetime('now')),
  UNIQUE (placa, data)
);
-- Nome e telefone do dono de cada placa. Vale o último informado na tela de visita.
CREATE TABLE IF NOT EXISTS clientes (
  placa TEXT PRIMARY KEY,
  nome TEXT NOT NULL DEFAULT '',
  telefone TEXT NOT NULL DEFAULT '',
  atualizado_em TEXT NOT NULL DEFAULT (datetime('now'))
);
-- PDF da OS de uma visita. O arquivo fica em config.ARQUIVOS_OS com o nome igual ao sha256 do conteúdo.
CREATE TABLE IF NOT EXISTS ordens (
  id INTEGER PRIMARY KEY,
  placa TEXT NOT NULL,
  data TEXT NOT NULL,
  km INTEGER,
  arquivo TEXT NOT NULL,
  nome_arquivo TEXT NOT NULL DEFAULT '',
  tamanho INTEGER NOT NULL,
  usuario_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
  criado_em TEXT NOT NULL DEFAULT (datetime('now')),
  UNIQUE (placa, arquivo)
);
CREATE INDEX IF NOT EXISTS ordens_placa ON ordens (placa, data);
"""


def conectar() -> sqlite3.Connection:
    config.BANCO.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(config.BANCO)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con


@contextmanager
def transacao():
    con = conectar()
    try:
        with con:
            yield con
    finally:
        con.close()


def criar_tabelas() -> None:
    with transacao() as con:
        con.executescript(ESQUEMA)
