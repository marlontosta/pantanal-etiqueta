import pytest
from fastapi.testclient import TestClient

from app import config, db, main, seguranca


@pytest.fixture
def cliente(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "BANCO", tmp_path / "teste.db")
    monkeypatch.setattr(config, "ARQUIVOS_OS", tmp_path / "os")
    monkeypatch.setattr(config, "COOKIE_SEGURO", False)
    seguranca._falhas.clear()
    main._envios.clear()
    db.criar_tabelas()
    with db.transacao() as con:
        con.execute("INSERT INTO usuarios (usuario, nome, senha_hash) VALUES ('marlon', 'Marlon', ?)",
                    (seguranca.gerar_hash("senha-boa-123"),))
    with TestClient(main.app) as c:
        yield c


@pytest.fixture
def logado(cliente):
    r = cliente.post("/api/entrar", json={"usuario": "marlon", "senha": "senha-boa-123"})
    assert r.status_code == 200
    return cliente
