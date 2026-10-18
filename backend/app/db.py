"""Banco SQLite: usuários, sessões, registros de serviço e km informados pelos clientes."""
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
