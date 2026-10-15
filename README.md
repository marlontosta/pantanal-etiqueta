# Etiqueta digital de manutenção — Pantanal Pneus

Página estática que o cliente abre ao encostar o celular na etiqueta NFC do veículo
(ou ler o QR code). Os dados da última visita ficam no próprio link gravado na etiqueta,
então não há servidor nem banco de dados.

## Estrutura

```
etiqueta/
├── README.md
└── public/            ← tudo que vai para a hospedagem
    ├── index.html     página do cliente (lê os parâmetros do link)
    ├── gravar.html    área da oficina (lê, monta e grava o link na etiqueta)
    ├── config.js      oficina, serviços, intervalos e margens (edite só aqui)
    ├── estilo.css     visual das duas páginas
    └── logo.png
```

## Parâmetros do link

Exemplo: `https://seusite.com.br/etiqueta/?placa=ABC1D23&oleo-km=27350&oleo-dt=2026-04-22`

| Parâmetro          | Significado                                   |
|--------------------|-----------------------------------------------|
| `placa`            | Placa do veículo (7 caracteres, sem hífen)    |
| `oleo-km`          | Km da última troca de óleo e filtro           |
| `oleo-dt`          | Data da última troca de óleo e filtro         |
| `alinhamento-km`   | Km do último alinhamento                      |
| `alinhamento-dt`   | Data do último alinhamento                    |
| `balanceamento-km` | Km do último balanceamento                    |
| `balanceamento-dt` | Data do último balanceamento                  |
| `hig-km`           | Km da última higienização do ar-condicionado  |
| `hig-ar-dt`        | Data da última higienização do ar-condicionado|

- Datas aceitas: `2026-04-22`, `22/04/2026`, `22-04-2026` ou `20260422`. A página da oficina grava sempre `AAAA-MM-DD`.
- Km aceita só números (pontos são ignorados).
- Qualquer parâmetro pode faltar; o serviço aparece como "Sem registro".
- Sem nenhum parâmetro, `index.html` mostra um exemplo de demonstração.

Os nomes dos parâmetros, intervalos (km e meses) e margens de aviso ficam em `public/config.js`.
Mudar um nome de parâmetro ali invalida as etiquetas já gravadas com o nome antigo.

## Montar o link a partir da OS

Em `gravar.html`, cole no campo "Colar itens da OS" a placa, o km e os itens da ordem de serviço.
A página reconhece `Placa: LMV4G22`, `KM do serviço: 95178` e marca como feitos hoje os
serviços cujas descrições contêm os trechos do campo `os` de cada serviço no `config.js`
(`TROCA DE OLEO`, `ALINHAMENTO`, `BALANCEAMENTO`, `HIGIENIZ`). Os demais itens da OS são ignorados.

Exemplo: uma OS com troca de óleo e alinhamento em 15/10/2026 com 95.178 km gera

```
?placa=LMV4G22&oleo-km=95178&oleo-dt=2026-10-15&alinhamento-km=95178&alinhamento-dt=2026-10-15
```

## Link para o Sobre Rodas

No fim da página do cliente, o botão "Ver detalhes no Sobre Rodas" abre em nova aba a tela de
login/cadastro do cliente: `https://sobrerodas.club/client/login`. Nenhum dado da etiqueta é
enviado. O endereço fica em `sobreRodas.url` no `config.js`.

## Tamanho da etiqueta

Um link com os quatro serviços tem cerca de 210 bytes (varia com o domínio). Use **NTAG215** ou **NTAG216**; a NTAG213 (137 bytes)
só comporta links curtos. A página `gravar.html` mostra o tamanho e em quais chips cabe.

## Hospedagem (precisa ser https)

A gravação NFC pelo navegador (Web NFC) só funciona no **Chrome para Android** e só em páginas
servidas por **https**. Qualquer hospedagem estática serve; publique o conteúdo de `public/`:

- **GitHub Pages**: crie um repositório, envie o conteúdo de `public/` e ative Pages.
- **Netlify** ou **Cloudflare Pages**: arraste a pasta `public/` no painel.

Depois de publicado, abra `https://<seu-endereço>/gravar.html` no Chrome Android. O campo
"Endereço da página do cliente" é preenchido sozinho com o endereço publicado.

Sem Chrome Android, copie o link gerado e grave com um app como NFC Tools, ou imprima o QR code.

## Testar localmente

```bash
cd etiqueta && python3 servidor.py
```

O script serve a pasta `public/` na porta 8080 (outra porta: `python3 servidor.py 9000`) e mostra
os endereços: `http://localhost:8080/` (página do cliente), `http://localhost:8080/gravar.html`
e o endereço pelo IP da máquina, para abrir no celular conectado à mesma rede Wi-Fi.
NFC não funciona em http local; para testar a gravação, use a versão publicada em https.
