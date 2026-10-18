// Funções da área da oficina: chamadas à API e menu do topo.
window.OFICINA = {
  // Chama a API com o cookie de sessão. Sessão expirada volta para o login.
  async api(url, opcoes = {}) {
    const r = await fetch(url, {
      credentials: "same-origin",
      ...opcoes,
      headers: { "Content-Type": "application/json", ...(opcoes.headers || {}) }
    });
    if (r.status === 401 && !url.endsWith("/entrar")) {
      location.href = "entrar.html?volta=" + encodeURIComponent(location.pathname.split("/").pop());
      throw new Error("sessão expirada");
    }
    const dados = await r.json().catch(() => ({}));
    if (!r.ok) {
      const d = dados.detail;
      throw new Error(typeof d === "string" ? d : Array.isArray(d) ? d.map(e => e.msg).join("; ") : "Erro " + r.status);
    }
    return dados;
  },
  // Menu: Frota, Gravar etiqueta, nome do usuário e Sair.
  async menu() {
    const nav = document.querySelector(".menu");
    const atual = location.pathname.split("/").pop();
    for (const a of nav.querySelectorAll("a")) if (a.getAttribute("href") === atual) a.setAttribute("aria-current", "page");
    nav.querySelector("[data-sair]").addEventListener("click", async () => {
      await this.api("/api/sair", { method: "POST" }).catch(() => {});
      location.href = "entrar.html";
    });
    const eu = await this.api("/api/eu");
    nav.querySelector(".quem").textContent = eu.nome || eu.usuario;
  }
};
