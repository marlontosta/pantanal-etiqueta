"""Cálculos da frota: km por dia, km atual estimado e próxima manutenção de cada placa."""
import calendar
from datetime import date, timedelta

from . import config

RANK = {"bad": 0, "warn": 1, "ok": 2}
# Visitas muito próximas dão médias absurdas com qualquer erro de digitação no km.
DIAS_MINIMOS_MEDIA = 7
# Km do cliente que exige rodar mais que isso por dia desde o km anterior é erro de digitação.
KM_DIA_MAXIMO = 1500


def somar_meses(d: date, meses: int) -> date:
    m = d.month - 1 + meses
    ano, mes = d.year + m // 12, m % 12 + 1
    return date(ano, mes, min(d.day, calendar.monthrange(ano, mes)[1]))


def km_por_dia(registros: list[dict]) -> float | None:
    """Média entre o km mais antigo e o mais recente (visitas e km do cliente). None se não dá para calcular."""
    por_dia: dict[date, int] = {}
    for r in registros:
        if r["km"] is not None:
            d = date.fromisoformat(r["data"])
            por_dia[d] = max(por_dia.get(d, 0), r["km"])
    if len(por_dia) < 2:
        return None
    primeiro, ultimo = min(por_dia), max(por_dia)
    if (ultimo - primeiro).days < DIAS_MINIMOS_MEDIA:
        return None
    media = (por_dia[ultimo] - por_dia[primeiro]) / (ultimo - primeiro).days
    # Km menor numa visita mais nova é erro de digitação ou troca de painel: melhor não estimar.
    return media if media >= 0 else None


def leituras_validas(registros: list[dict], leituras: list[dict]) -> list[dict]:
    """Km do cliente que fazem sentido com as visitas da oficina: nem menor que o km de uma
    visita anterior, nem maior que o de uma posterior, nem com mais de KM_DIA_MAXIMO por dia.
    Cada leitura é conferida só com as visitas, para um erro de digitação não derrubar as seguintes.
    Cada leitura volta com "usada"."""
    pontos = [(date.fromisoformat(r["data"]), r["km"]) for r in registros if r["km"] is not None]
    saida = []
    for lt in sorted(leituras, key=lambda x: x["data"]):
        d = date.fromisoformat(lt["data"])
        antes = [p for p in pontos if p[0] <= d]
        ok = True
        if antes:
            d0, k0 = max(antes, key=lambda p: (p[0], p[1]))
            ok = lt["km"] >= max(k for _, k in antes) and lt["km"] - k0 <= KM_DIA_MAXIMO * max(1, (d - d0).days)
        # Uma visita depois com km menor também desmente a leitura.
        ok = ok and all(k >= lt["km"] for dd, k in pontos if dd > d)
        saida.append({**lt, "usada": ok})
    return saida


# Km do cliente comparado com o último km conhecido: até MEDIA_VEZES a média da placa, mais uma folga.
MEDIA_VEZES, FOLGA_KM = 4, 300


def motivo_descarte(registros: list[dict], leituras: list[dict], km: int, data: date) -> str | None:
    """Por que um km do cliente não deve ser guardado (None: pode guardar).
    registros: visitas da placa. leituras: km já guardados (cliente e oficina), sem o do cliente no
    mesmo dia, que este substitui."""
    if not leituras_validas(registros, [{"km": km, "data": data.isoformat()}])[0]["usada"]:
        return "não confere com as visitas"
    aceitas = [lt for lt in leituras_validas(registros, leituras) if lt["usada"] and lt["data"] <= data.isoformat()]
    pontos = [r for r in registros if r["km"] is not None and r["data"] <= data.isoformat()] + aceitas
    if not pontos:
        return None
    ref = max(pontos, key=lambda r: (r["data"], r["km"]))
    if km == ref["km"]:
        return "igual ao último km"
    if aceitas and km < max(lt["km"] for lt in aceitas):
        return "menor que um km já informado"
    if km < ref["km"]:
        return "menor que o último km"
    dias = max(1, (data - date.fromisoformat(ref["data"])).days)
    media = km_por_dia(pontos)
    limite = KM_DIA_MAXIMO * dias
    if media:
        limite = min(limite, MEDIA_VEZES * media * dias + FOLGA_KM)
    if km - ref["km"] > limite:
        return f"{(km - ref['km']) / dias:.0f} km/dia desde o último km"
    return None


def resumo_veiculo(placa: str, registros: list[dict], hoje: date, leituras: list[dict] = ()) -> dict:
    """registros: [{servico, km, data}] de uma placa, em qualquer ordem.
    leituras: [{km, data}] que o cliente digitou na página da etiqueta."""
    m = config.MARGEM
    datas = [date.fromisoformat(r["data"]) for r in registros]
    ult_visita = max(datas)
    com_km = [r for r in registros if r["km"] is not None]
    # O km da visita fica separado; o do cliente só entra na estimativa.
    ref_visita = max(com_km, key=lambda r: (r["data"], r["km"])) if com_km else None
    do_cliente = [{**lt, "cliente": True} for lt in leituras_validas(registros, list(leituras)) if lt["usada"]]
    pontos = com_km + do_cliente
    # Último km conhecido: o maior km do dia mais recente que tem km (visita ou cliente).
    ref = max(pontos, key=lambda r: (r["data"], r["km"])) if pontos else None
    km_ult = ref["km"] if ref else None
    data_km = date.fromisoformat(ref["data"]) if ref else None

    media = km_por_dia(pontos)
    km_atual = None
    if km_ult is not None:
        km_atual = round(km_ult + (media or 0) * max(0, (hoje - data_km).days))

    servicos = []
    for s in config.SERVICOS:
        doS = [r for r in registros if r["servico"] == s["id"]]
        if not doS:
            continue
        ult = max(doS, key=lambda r: r["data"])
        d = date.fromisoformat(ult["data"])
        it = {"servico": s["id"], "nome": s["nome"], "ultima_data": ult["data"], "ultimo_km": ult["km"],
              "proximo_km": None, "falta_km": None, "proxima_data": None, "falta_dias": None}
        status = "ok"
        candidatas = [somar_meses(d, s["intervalo_meses"])]
        if ult["km"] is not None and km_atual is not None:
            it["proximo_km"] = ult["km"] + s["intervalo_km"]
            it["falta_km"] = it["proximo_km"] - km_atual
            margem = min(s["intervalo_km"] * m["fracao"], m["km"])
            status = "bad" if it["falta_km"] <= 0 else "warn" if it["falta_km"] <= margem else "ok"
            if media:
                # Dia em que o km estimado chega no próximo km (pode já ter passado).
                candidatas.append(data_km + timedelta(days=round((it["proximo_km"] - km_ult) / media)))
        prox = min(candidatas)
        it["proxima_data"] = prox.isoformat()
        it["falta_dias"] = (prox - hoje).days
        st = "bad" if it["falta_dias"] < 0 else "warn" if it["falta_dias"] <= m["dias"] else "ok"
        it["status"] = st if RANK[st] < RANK[status] else status
        servicos.append(it)

    servicos.sort(key=lambda i: (RANK[i["status"]], i["falta_dias"]))
    proxima = servicos[0] if servicos else None
    return {
        "placa": placa,
        "ultima_visita": ult_visita.isoformat(),
        "ultimo_km": ref_visita["km"] if ref_visita else None,
        "km_referencia": km_ult,
        "km_referencia_data": ref["data"] if ref else None,
        "km_do_cliente": bool(ref and ref.get("cliente") and ref.get("origem") != "oficina"),
        "km_da_oficina": bool(ref and ref.get("origem") == "oficina"),
        "leituras_cliente": len(do_cliente),
        "km_por_dia": round(media, 1) if media is not None else None,
        "km_atual": km_atual,
        "km_estimado": bool(media) and km_ult is not None and data_km < hoje,
        "status": proxima["status"] if proxima else "ok",
        "proxima": proxima,
        "servicos": servicos,
        "visitas": len(set(datas)),
    }


def resumo_frota(registros: list[dict], hoje: date, leituras: list[dict] = ()) -> list[dict]:
    """Só aparecem placas com visita; km do cliente sem visita fica guardado para depois."""
    por_placa: dict[str, list[dict]] = {}
    for r in registros:
        por_placa.setdefault(r["placa"], []).append(r)
    lt_placa: dict[str, list[dict]] = {}
    for lt in leituras:
        lt_placa.setdefault(lt["placa"], []).append(lt)
    return [resumo_veiculo(p, rs, hoje, lt_placa.get(p, [])) for p, rs in sorted(por_placa.items())]
