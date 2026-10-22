from datetime import date, timedelta

from app import config
from app.frota import somar_meses


def test_sem_login_nao_ve_nada(cliente):
    assert cliente.get("/api/frota").status_code == 401
    assert cliente.post("/api/registros", json={"placa": "ABC1D23", "servicos": []}).status_code == 401
    r = cliente.get("/oficina/frota.html", follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/oficina/entrar.html?volta=frota.html"
    assert cliente.get("/oficina/gravar.html", follow_redirects=False).status_code == 303
    # O QR do celular traz a placa; depois do login volta para ela.
    r = cliente.get("/oficina/gravar.html?placa=LMV4G22&etiqueta=1", follow_redirects=False)
    assert r.headers["location"] == "/oficina/entrar.html?volta=gravar.html%3Fplaca%3DLMV4G22%26etiqueta%3D1"


def test_login_e_paginas_publicas(cliente):
    assert cliente.get("/oficina/entrar.html").status_code == 200
    assert cliente.get("/oficina/oficina.js").status_code == 200
    assert "Etiqueta digital" in cliente.get("/").text
    assert cliente.get("/config.js").status_code == 200
    assert cliente.get("/oficina/..%2fbackend%2fapp%2fconfig.py").status_code == 404


def test_senha_errada_e_bloqueio(cliente):
    for _ in range(5):
        assert cliente.post("/api/entrar", json={"usuario": "marlon", "senha": "errada"}).status_code == 401
    r = cliente.post("/api/entrar", json={"usuario": "marlon", "senha": "senha-boa-123"})
    assert r.status_code == 429


def test_cookie_httponly(cliente):
    r = cliente.post("/api/entrar", json={"usuario": "Marlon", "senha": "senha-boa-123"})
    assert r.status_code == 200
    cookie = r.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=lax" in cookie


def test_sair_encerra_sessao(logado):
    assert logado.get("/api/eu").json()["usuario"] == "marlon"
    logado.post("/api/sair")
    assert logado.get("/api/eu").status_code == 401


def test_salvar_e_ver_frota(logado):
    hoje = config.hoje()
    antes = (hoje - timedelta(days=100)).isoformat()
    visita1 = {"placa": "lmv-4g22", "servicos": [{"servico": "oleo", "km": 90000, "data": antes},
                                                  {"servico": "geo", "km": 90000, "data": antes}]}
    assert logado.post("/api/registros", json=visita1).status_code == 200
    # Gravar a mesma etiqueta de novo não duplica.
    assert logado.post("/api/registros", json=visita1).status_code == 200
    visita2 = {"placa": "LMV4G22", "servicos": [{"servico": "oleo", "km": 95000, "data": hoje.isoformat()}]}
    assert logado.post("/api/registros", json=visita2).status_code == 200

    v = logado.get("/api/frota").json()["veiculos"]
    assert len(v) == 1
    carro = v[0]
    assert carro["placa"] == "LMV4G22"
    assert carro["km_por_dia"] == 50.0
    assert carro["km_atual"] == 95000
    assert carro["visitas"] == 2
    # Geometria: 6 meses ou 10.000 km depois de 90.000; a 50 km/dia chega em 100.000 km em 200 dias.
    geo = next(s for s in carro["servicos"] if s["servico"] == "geo")
    assert geo["proximo_km"] == 100000 and geo["falta_km"] == 5000
    pelo_prazo = (somar_meses(date.fromisoformat(antes), 6) - hoje).days
    assert geo["falta_dias"] == min(100, pelo_prazo)
    assert carro["proxima"]["servico"] == "geo"

    det = logado.get("/api/veiculos/LMV4G22").json()
    assert len(det["historico"]) == 3


def test_validacao(logado):
    futuro = (config.hoje() + timedelta(days=2)).isoformat()
    assert logado.post("/api/registros", json={"placa": "XX", "servicos": []}).status_code == 422
    assert logado.post("/api/registros", json={"placa": "ABC1234", "servicos": [{"servico": "motor", "data": "2026-01-01"}]}).status_code == 422
    assert logado.post("/api/registros", json={"placa": "ABC1234", "servicos": [{"servico": "oleo", "data": futuro}]}).status_code == 422
    assert logado.get("/api/veiculos/ZZZ9Z99").status_code == 404


def test_km_do_cliente(cliente, logado):
    antes = (config.hoje() - timedelta(days=50)).isoformat()
    logado.post("/api/registros", json={"placa": "LMV4G22", "servicos": [{"servico": "oleo", "km": 90000, "data": antes}]})
    logado.post("/api/sair")
    # Sem login e em texto puro, como manda a página do cliente (também a do GitHub Pages).
    envio = lambda corpo: cliente.post("/api/leituras", content=corpo, headers={"content-type": "text/plain"})
    assert envio('{"placa":"lmv-4g22","km":92000}').status_code == 200
    assert envio('{"placa":"LMV4G22","km":92500}').status_code == 200  # mesmo dia: vale o último
    assert envio('{"placa":"LMV4G22","km":80000}').status_code == 422  # menor que a visita
    assert envio('{"placa":"XX","km":1}').status_code == 422
    assert envio("lixo").status_code == 422
    # Placa ainda sem visita fica guardada.
    assert envio('{"placa":"QWE1R23","km":5000}').status_code == 200

    logado.post("/api/entrar", json={"usuario": "marlon", "senha": "senha-boa-123"})
    v = logado.get("/api/frota").json()["veiculos"]
    assert [c["placa"] for c in v] == ["LMV4G22"]
    assert v[0]["km_referencia"] == 92500 and v[0]["km_do_cliente"] and v[0]["km_por_dia"] == 50.0
    det = logado.get("/api/veiculos/LMV4G22").json()
    assert det["leituras"] == [{"placa": "LMV4G22", "km": 92500, "data": config.hoje().isoformat(), "origem": "cliente", "usada": True}]


def test_limite_de_envios(cliente):
    for _ in range(30):
        cliente.post("/api/leituras", content='{"placa":"QWE1R23","km":5000}')
    assert cliente.post("/api/leituras", content='{"placa":"QWE1R23","km":5000}').status_code == 429


def test_km_atual_pela_oficina(cliente, logado):
    antes = (config.hoje() - timedelta(days=50)).isoformat()
    logado.post("/api/registros", json={"placa": "LMV4G22", "servicos": [{"servico": "oleo", "km": 90000, "data": antes}]})
    assert logado.post("/api/veiculos/LMV4G22/km", json={"km": 80000}).status_code == 422  # menor que a visita
    assert logado.post("/api/veiculos/ZZZ9Z99/km", json={"km": 1000}).status_code == 404
    assert logado.post("/api/veiculos/lmv-4g22/km", json={"km": 92500}).status_code == 200
    carro = logado.get("/api/frota").json()["veiculos"][0]
    assert carro["km_referencia"] == 92500 and carro["km_da_oficina"] and not carro["km_do_cliente"]
    assert carro["km_por_dia"] == 50.0
    # O cliente digitando no mesmo dia não troca o km da oficina.
    cliente.post("/api/leituras", content='{"placa":"LMV4G22","km":92600}')
    det = logado.get("/api/veiculos/LMV4G22").json()
    assert [(l["km"], l["origem"]) for l in det["leituras"]] == [(92500, "oficina")]
    logado.post("/api/sair")
    assert cliente.post("/api/veiculos/LMV4G22/km", json={"km": 93000}).status_code == 401
