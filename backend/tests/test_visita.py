from datetime import timedelta

from app import config

PDF = b"%PDF-1.4\n% OS de teste\n%%EOF\n"


def test_cliente_e_visita_sem_etiqueta(logado):
    hoje = config.hoje().isoformat()
    r = logado.post("/api/registros", json={"placa": "LMV4G22", "nome": "  João   da Silva ", "telefone": "+55 (67) 99123-4567",
                                             "servicos": [{"servico": "oleo", "km": 95000, "data": hoje}]})
    assert r.status_code == 200
    carro = logado.get("/api/frota").json()["veiculos"][0]
    assert carro["cliente"] == {"nome": "João da Silva", "telefone": "67991234567"}
    # Sem nome e telefone (por exemplo, ao ler uma etiqueta) não apaga o que já está salvo.
    logado.post("/api/registros", json={"placa": "LMV4G22", "servicos": [{"servico": "geo", "km": 95000, "data": hoje}]})
    logado.post("/api/registros", json={"placa": "LMV4G22", "nome": "", "telefone": "", "servicos": []})
    assert logado.get("/api/veiculos/LMV4G22").json()["cliente"]["nome"] == "João da Silva"
    logado.post("/api/registros", json={"placa": "LMV4G22", "telefone": "67 3321-0000", "servicos": []})
    assert logado.get("/api/veiculos/LMV4G22").json()["cliente"] == {"nome": "João da Silva", "telefone": "6733210000"}


def test_telefone_invalido(logado):
    r = logado.post("/api/registros", json={"placa": "LMV4G22", "telefone": "1234", "servicos": []})
    assert r.status_code == 422


def test_placa_so_com_cliente(logado):
    assert logado.post("/api/registros", json={"placa": "QWE1R23", "nome": "Ana", "servicos": []}).status_code == 200
    # Não entra na frota (não tem serviço), mas a tela de visita encontra o nome.
    assert logado.get("/api/frota").json()["veiculos"] == []
    d = logado.get("/api/veiculos/QWE1R23").json()
    assert d["cliente"]["nome"] == "Ana" and d["servicos"] == [] and d["historico"] == []


def test_pdf_da_os(logado):
    hoje = config.hoje().isoformat()
    envio = lambda corpo, **q: logado.post("/api/ordens", params={"placa": "lmv4g22", "data": hoje, **q},
                                           content=corpo, headers={"content-type": "application/pdf"})
    r = envio(PDF, km=95000, nome="OS 1234.pdf")
    assert r.status_code == 200
    id_ = r.json()["id"]
    # O mesmo arquivo de novo não duplica.
    assert envio(PDF).json()["id"] == id_
    assert envio(b"nao sou pdf").status_code == 422
    assert envio(PDF, placa="XX").status_code == 422
    futuro = (config.hoje() + timedelta(days=3)).isoformat()
    assert envio(PDF, data=futuro).status_code == 422
    assert envio(b"%PDF-" + b"0" * config.OS_TAMANHO_MAXIMO).status_code == 413

    arquivo = logado.get(f"/api/ordens/{id_}")
    assert arquivo.status_code == 200 and arquivo.content == PDF
    assert arquivo.headers["content-type"] == "application/pdf"
    assert arquivo.headers["content-disposition"].startswith("inline")
    assert len(list(config.ARQUIVOS_OS.iterdir())) == 1

    d = logado.get("/api/veiculos/LMV4G22").json()
    assert d["ordens"] == [{"id": id_, "data": hoje, "km": 95000, "nome_arquivo": "OS 1234.pdf", "tamanho": len(PDF)}]
    assert logado.get("/api/ordens/999").status_code == 404


def test_pdf_exige_login(cliente):
    r = cliente.post("/api/ordens", params={"placa": "LMV4G22", "data": config.hoje().isoformat()}, content=PDF)
    assert r.status_code == 401
    assert cliente.get("/api/ordens/1").status_code == 401
