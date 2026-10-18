"""Cálculos da frota: km por dia, km atual estimado e próxima manutenção de cada placa."""
import calendar
from datetime import date, timedelta

from . import config

RANK = {"bad": 0, "warn": 1, "ok": 2}
# Visitas muito próximas dão médias absurdas com qualquer erro de digitação no km.
DIAS_MINIMOS_MEDIA = 7


def somar_meses(d: date, meses: int) -> date:
    m = d.month - 1 + meses
    ano, mes = d.year + m // 12, m % 12 + 1
    return date(ano, mes, min(d.day, calendar.monthrange(ano, mes)[1]))


def km_por_dia(registros: list[dict]) -> float | None:
    """Média entre a visita mais antiga e a mais recente com km. None se não dá para calcular."""
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


def resumo_veiculo(placa: str, registros: list[dict], hoje: date) -> dict:
    """registros: [{servico, km, data}] de uma placa, em qualquer ordem."""
    m = config.MARGEM
    datas = [date.fromisoformat(r["data"]) for r in registros]
    ult_visita = max(datas)
    com_km = [r for r in registros if r["km"] is not None]
    # Último km conhecido: o maior km da visita mais recente que tem km.
    ref = max(com_km, key=lambda r: (r["data"], r["km"])) if com_km else None
    km_ult = ref["km"] if ref else None
    data_km = date.fromisoformat(ref["data"]) if ref else None

    media = km_por_dia(registros)
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
        "ultimo_km": km_ult,
        "km_por_dia": round(media, 1) if media is not None else None,
        "km_atual": km_atual,
        "km_estimado": bool(media) and km_ult is not None and data_km < hoje,
        "status": proxima["status"] if proxima else "ok",
        "proxima": proxima,
        "servicos": servicos,
        "visitas": len(set(datas)),
    }


def resumo_frota(registros: list[dict], hoje: date) -> list[dict]:
    por_placa: dict[str, list[dict]] = {}
    for r in registros:
        por_placa.setdefault(r["placa"], []).append(r)
    return [resumo_veiculo(p, rs, hoje) for p, rs in sorted(por_placa.items())]
