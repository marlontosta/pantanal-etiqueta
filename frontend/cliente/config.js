// Configuração da etiqueta Pantanal Pneus.
// Para mudar intervalos ou contato, edite só este arquivo.
// "km" e "dt" são os nomes dos parâmetros no link gravado na etiqueta NFC.
window.ETIQUETA = {
  oficina: {
    nome: "Pantanal Pneus",
    whatsapp: "5567999367507",
    instagram: "pantanalpneus.ms"
  },
  // Endereço publicado da página do cliente: é o começo do link gravado na etiqueta.
  paginaCliente: "https://marlao.pythonanywhere.com/",
  // Endereço da área da oficina (backend). Vazio esconde o link no rodapé da página do cliente.
  areaOficina: "https://marlao.pythonanywhere.com/oficina/",
  // Para onde vai o km que o cliente digita (estimativa de km/dia na frota). Vazio não envia.
  // Endereço completo, porque a página também é publicada no GitHub Pages (etiquetas antigas).
  envioKm: "https://marlao.pythonanywhere.com/api/leituras",
  // Outros veículos do mesmo cliente (telefone cadastrado para a placa), mostrados em abas. Vazio desliga.
  minhaFrota: "https://marlao.pythonanywhere.com/api/minha-frota",
  // Plataforma com o histórico detalhado: link direto para o login/cadastro do cliente.
  sobreRodas: { nome: "Sobre Rodas", url: "https://sobrerodas.club/client/login" },
  // "c": letra do serviço no link da etiqueta.
  // "os": trechos que identificam o serviço na descrição dos itens da OS (sem acento, maiúsculas).
  servicos: [
    { id: "oleo", c: "o", nome: "Troca de óleo e filtro", grupo: "Óleo e filtros", intervalo_km: 10000, intervalo_meses: 12, os: ["TROCA DE OLEO"] },
    { id: "rev", c: "r", nome: "Revisão mecânica", grupo: "Suspensão, freios e demais itens mecânicos", intervalo_km: 10000, intervalo_meses: 12,
      os: ["REVISAO", "SUSPENS", "FREIO", "AMORTECEDOR", "BIELETA", "TERMINAL", "BANDEJA", "PASTILHA", "AXIAL"] },
    { id: "geo", c: "g", nome: "Geometria (alinhamento e balanceamento)", grupo: "Pneus e rodas", intervalo_km: 10000, intervalo_meses: 6, os: ["ALINHAMENTO", "BALANCEAMENTO", "GEOMETRIA"] },
    { id: "hig", c: "h", nome: "Higienização do ar-condicionado", grupo: "Ar-condicionado", intervalo_km: 10000, intervalo_meses: 12, os: ["HIGIENIZ"] }
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
  // Último registro de um serviço no link: {km, dt} como texto.
  ler(p, s) { return this.decodificar(p, s.c) || { km: null, dt: null }; },
  // Link da etiqueta: ?p=PLACA&o=KM.DIA, com km e dias desde 01/01/2020 em base 36
  // ("21fu.1wv" = 95.178 km em 15/10/2026). "KM." só km, ".DIA" só data.
  // Um valor sem ponto repete outro serviço: r=o é "igual à troca de óleo".
  EPOCA: Date.UTC(2020, 0, 1),
  codificar(km, dt) {
    const d = this.data(dt);
    if (km == null && !d) return "";
    const dias = d ? Math.round((Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()) - this.EPOCA) / 864e5) : null;
    return (km != null ? km.toString(36) : "") + "." + (dias != null && dias >= 0 ? dias.toString(36) : "");
  },
  decodificar(p, c, prof = 0) {
    const v = c && p.get(c);
    if (!v) return null;
    if (!v.includes(".")) return prof < 5 ? this.decodificar(p, v, prof + 1) : null;
    const [k, d] = v.split(".");
    const km = k ? parseInt(k, 36) : NaN, dias = d ? parseInt(d, 36) : NaN;
    return { km: isNaN(km) ? null : String(km), dt: isNaN(dias) ? null : new Date(this.EPOCA + dias * 864e5).toISOString().slice(0, 10) };
  },
  placa(s) { return String(s || "").toUpperCase().replace(/[^A-Z0-9]/g, "").slice(0, 7); },
  // Endereço de uma rota da API: a página servida pelo próprio backend (PythonAnywhere ou um
  // servidor local) usa o mesmo endereço dela; só a do GitHub Pages usa o endereço completo do config.
  api(url) {
    if (!url || !/^https?:$/.test(location.protocol) || location.hostname.endsWith("github.io")) return url;
    try { return new URL(url).pathname; } catch (e) { return url; }
  },
  fone(n) {
    const d = String(n).replace(/\D/g, "").replace(/^55/, "");
    return d.length === 11 ? "(" + d.slice(0, 2) + ") " + d.slice(2, 7) + "-" + d.slice(7) : n;
  }
};
