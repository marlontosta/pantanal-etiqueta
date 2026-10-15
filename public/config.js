// Configuração da etiqueta Pantanal Pneus.
// Para mudar intervalos ou contato, edite só este arquivo.
// "km" e "dt" são os nomes dos parâmetros no link gravado na etiqueta NFC.
window.ETIQUETA = {
  oficina: {
    nome: "Pantanal Pneus",
    whatsapp: "5567999367507",
    instagram: "pantanalpneus.ms"
  },
  // Plataforma com o histórico detalhado: link direto para o login/cadastro do cliente.
  sobreRodas: { nome: "Sobre Rodas", url: "https://sobrerodas.club/client/login" },
  // "os": trechos que identificam o serviço na descrição dos itens da OS (sem acento, maiúsculas).
  servicos: [
    { id: "oleo", nome: "Troca de óleo e filtro", grupo: "Óleo e filtros", km: "oleo-km", dt: "oleo-dt", intervalo_km: 10000, intervalo_meses: 12, os: ["TROCA DE OLEO"] },
    { id: "alinhamento", nome: "Alinhamento", grupo: "Pneus e rodas", km: "alinhamento-km", dt: "alinhamento-dt", intervalo_km: 10000, intervalo_meses: 6, os: ["ALINHAMENTO"] },
    { id: "balanceamento", nome: "Balanceamento", grupo: "Pneus e rodas", km: "balanceamento-km", dt: "balanceamento-dt", intervalo_km: 10000, intervalo_meses: 6, os: ["BALANCEAMENTO"] },
    { id: "hig", nome: "Higienização do ar-condicionado", grupo: "Ar-condicionado", km: "hig-km", dt: "hig-ar-dt", intervalo_km: 10000, intervalo_meses: 12, os: ["HIGIENIZ"] }
  ],
  // Amarelo: faltam até 10% do intervalo ou 3.000 km (o menor), ou até 30 dias.
  margem: { fracao: 0.1, km: 3000, dias: 30 }
};

// Funções usadas pelas duas páginas.
window.ETQ = {
  // Aceita 2026-04-22, 22/04/2026, 22-04-2026 ou 20260422.
  data(s) {
    if (!s) return null;
    s = String(s).trim();
    let m;
    if ((m = s.match(/^(\d{4})-(\d{2})-(\d{2})$/))) return new Date(+m[1], m[2] - 1, +m[3]);
    if ((m = s.match(/^(\d{2})[\/.-](\d{2})[\/.-](\d{4})$/))) return new Date(+m[3], m[2] - 1, +m[1]);
    if ((m = s.match(/^(\d{4})(\d{2})(\d{2})$/))) return new Date(+m[1], m[2] - 1, +m[3]);
    return null;
  },
  iso(d) { return d.getFullYear() + "-" + String(d.getMonth() + 1).padStart(2, "0") + "-" + String(d.getDate()).padStart(2, "0"); },
  km(s) { const n = parseInt(String(s || "").replace(/\D/g, ""), 10); return isNaN(n) ? null : n; },
  placa(s) { return String(s || "").toUpperCase().replace(/[^A-Z0-9]/g, "").slice(0, 7); },
  fone(n) {
    const d = String(n).replace(/\D/g, "").replace(/^55/, "");
    return d.length === 11 ? "(" + d.slice(0, 2) + ") " + d.slice(2, 7) + "-" + d.slice(7) : n;
  }
};
