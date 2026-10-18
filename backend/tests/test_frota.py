import json
import re
from datetime import date

from app import config
from app.frota import km_por_dia, leituras_validas, resumo_veiculo, somar_meses

HOJE = date(2026, 10, 18)


def reg(servico, km, data):
    return {"servico": servico, "km": km, "data": data}


def test_somar_meses():
    assert somar_meses(date(2026, 1, 31), 1) == date(2026, 2, 28)
    assert somar_meses(date(2026, 10, 15), 12) == date(2027, 10, 15)
    assert somar_meses(date(2026, 8, 1), 6) == date(2027, 2, 1)


def test_km_por_dia():
    assert km_por_dia([reg("oleo", 10000, "2026-01-01")]) is None
    assert km_por_dia([reg("oleo", 10000, "2026-01-01"), reg("geo", 12000, "2026-01-21")]) == 100
    # Menos de uma semana entre as visitas: não estima.
    assert km_por_dia([reg("oleo", 10000, "2026-01-01"), reg("geo", 14000, "2026-01-04")]) is None
    # Km menor depois: não estima.
    assert km_por_dia([reg("oleo", 10000, "2026-01-01"), reg("oleo", 9000, "2026-02-01")]) is None
    # Sem km não entra na conta.
    assert km_por_dia([reg("hig", None, "2025-01-01"), reg("oleo", 1000, "2026-01-01")]) is None


def test_km_atual_estimado_e_vencido():
    r = resumo_veiculo("ABC1D23", [reg("oleo", 20000, "2026-01-01"), reg("oleo", 30000, "2026-05-31")], HOJE)
    assert r["km_por_dia"] == round(10000 / 150, 1)
    # 140 dias depois da última visita.
    assert r["km_atual"] == round(30000 + 10000 / 150 * 140)
    assert r["km_estimado"] is True
    oleo = r["servicos"][0]
    assert oleo["proximo_km"] == 40000
    assert oleo["status"] == "warn"  # faltam ~667 km


def test_so_data():
    r = resumo_veiculo("ABC1D23", [reg("hig", None, "2025-09-01")], HOJE)
    assert r["km_atual"] is None and r["km_por_dia"] is None
    assert r["proxima"]["proxima_data"] == "2026-09-01"
    assert r["status"] == "bad"


def test_intervalos_iguais_ao_config_js():
    js = (config.FRONTEND / "cliente" / "config.js").read_text()
    for s in config.SERVICOS:
        linha = re.search(r'\{ id: "%s",.*?intervalo_meses: \d+' % s["id"], js, re.S).group(0)
        assert f'c: "{s["c"]}"' in linha
        assert f'intervalo_km: {s["intervalo_km"]}' in linha
        assert f'intervalo_meses: {s["intervalo_meses"]}' in linha
    assert re.search(r"margem: \{ fracao: ([\d.]+), km: (\d+), dias: (\d+) \}", js).groups() == \
        (str(config.MARGEM["fracao"]), str(config.MARGEM["km"]), str(config.MARGEM["dias"]))


def test_km_do_cliente_entra_na_estimativa():
    regs = [reg("oleo", 30000, "2026-05-31")]
    # Sozinha, a visita não dá média; com o km do cliente 100 dias depois, dá 30 km/dia.
    r = resumo_veiculo("ABC1D23", regs, HOJE, [{"km": 33000, "data": "2026-09-08"}])
    assert r["ultimo_km"] == 30000
    assert r["km_referencia"] == 33000 and r["km_do_cliente"] is True
    assert r["km_por_dia"] == 30.0
    assert r["km_atual"] == 33000 + 30 * 40
    assert r["leituras_cliente"] == 1


def test_km_do_cliente_absurdo_e_ignorado():
    regs = [reg("oleo", 30000, "2026-05-31"), reg("geo", 36000, "2026-09-01")]
    leituras = [{"km": 29000, "data": "2026-06-10"},   # menor que a visita anterior
                {"km": 40000, "data": "2026-08-01"},   # maior que a visita seguinte
                {"km": 900000, "data": "2026-10-01"},  # mais de 1.500 km por dia
                {"km": 37000, "data": "2026-10-10"}]
    v = leituras_validas(regs, leituras)
    assert [x["usada"] for x in v] == [False, False, False, True]
    r = resumo_veiculo("ABC1D23", regs, HOJE, leituras)
    assert r["km_referencia"] == 37000 and r["leituras_cliente"] == 1
