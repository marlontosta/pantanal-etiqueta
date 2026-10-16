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

Formato compacto, para caber nas etiquetas menores:

```
https://marlontosta.github.io/pantanal-etiqueta/?p=LMV4G22&o=21fu.1wv&r=o&g=o
```

| Parâmetro | Significado                                              |
|-----------|----------------------------------------------------------|
| `p`       | Placa do veículo (7 caracteres, sem hífen)               |
| `o`       | Troca de óleo e filtro                                   |
| `r`       | Revisão mecânica (suspensão, freios e demais itens)      |
| `g`       | Geometria (alinhamento e balanceamento)                  |
| `h`       | Higienização do ar-condicionado                          |

Cada serviço vale `KM.DIA`, os dois em base 36: km rodado e dias desde 01/01/2020.
`21fu.1wv` é 95.178 km em 15/10/2026. `KM.` guarda só o km e `.DIA` só a data.
Um valor sem ponto repete outro serviço: `r=o` quer dizer "mesmo km e data da troca de óleo",
que é o caso comum de vários serviços feitos na mesma visita.

- A área da oficina monta esse formato sozinha; não é preciso calcular à mão.
- Qualquer serviço pode faltar; ele aparece como "Sem registro".
- Sem nenhum parâmetro, `index.html` mostra um exemplo de demonstração.

**Formato longo antigo**, ainda lido para etiquetas já gravadas: `placa`, `oleo-km`, `oleo-dt`,
`rev-km`, `rev-dt`, `geo-km`, `geo-dt`, `hig-km`, `hig-ar-dt` (e, de antes da geometria,
`alinhamento-*` e `balanceamento-*`, usando o mais antigo dos dois). Ao regravar pela área
da oficina, a etiqueta passa para o formato compacto.

As letras, intervalos (km e meses) e margens de aviso ficam em `public/config.js`.
Mudar a letra de um serviço invalida as etiquetas já gravadas com a letra antiga.

## Montar o link a partir da OS

Em `gravar.html`, cole no campo "Colar itens da OS" a placa, o km e os itens da ordem de serviço.
A página reconhece `Placa: LMV4G22`, `KM do serviço: 95178` e marca como feitos hoje os
serviços cujas descrições contêm os trechos do campo `os` de cada serviço no `config.js`
(`TROCA DE OLEO`; `REVISAO`, `SUSPENS`, `FREIO`, `AMORTECEDOR`, `BIELETA`, `TERMINAL`, `BANDEJA`, `PASTILHA` ou `AXIAL`; `ALINHAMENTO`, `BALANCEAMENTO` ou `GEOMETRIA`; `HIGIENIZ`). Os demais itens da OS são ignorados.

Exemplo: uma OS com troca de óleo, peças de suspensão (revisão mecânica) e alinhamento (geometria) em 15/10/2026 com 95.178 km gera

```
?p=LMV4G22&o=21fu.1wv&r=o&g=o
```

## Link para o Sobre Rodas

No fim da página do cliente, o botão "Ver detalhes no Sobre Rodas" abre em nova aba a tela de
login/cadastro do cliente: `https://sobrerodas.club/client/login`. Nenhum dado da etiqueta é
enviado. O endereço fica em `sobreRodas.url` no `config.js`.

## Tamanho da etiqueta

O link do exemplo acima tem 77 bytes na etiqueta; com os quatro serviços em datas diferentes,
cerca de 100. Os dois cabem na **NTAG213** (137 bytes), a etiqueta mais barata. A maior parte
é o endereço `marlontosta.github.io/pantanal-etiqueta/` (40 caracteres); um domínio próprio
curto encurtaria ainda mais. A página `gravar.html` mostra o tamanho e em quais chips cabe.

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
