# Etiqueta digital de manutenção — Pantanal Pneus

Página estática que o cliente abre ao encostar o celular na etiqueta NFC do veículo
(ou ler o QR code). Os dados da última visita ficam no próprio link gravado na etiqueta,
então a página do cliente não depende de servidor.

A área da oficina (gravar etiqueta e tela de frota) fica atrás de login e roda num backend
em Python, que guarda cada visita num banco SQLite.

## Estrutura

```
etiqueta/
├── frontend/
│   ├── cliente/         ← página do cliente, publicada no GitHub Pages
│   │   ├── index.html   lê os parâmetros do link da etiqueta
│   │   ├── config.js    oficina, serviços, intervalos e margens (edite só aqui)
│   │   ├── estilo.css   visual de todas as páginas
│   │   └── logo.png
│   └── oficina/         ← área da oficina, servida pelo backend, exige login
│       ├── entrar.html  login
│       ├── frota.html   veículos por placa: km atual, km/dia, próxima manutenção
│       ├── gravar.html  registra a visita (cliente, serviços, PDF da OS) e grava a etiqueta
│       └── oficina.js   chamadas à API e menu
├── backend/             ← API em Python (FastAPI + SQLite)
│   ├── app/
│   │   ├── main.py      rotas da API e páginas da oficina
│   │   ├── frota.py     cálculos de km/dia, km atual e previsões
│   │   ├── seguranca.py senhas e sessões
│   │   ├── db.py        banco SQLite
│   │   ├── config.py    intervalos (iguais ao config.js; um teste confere)
│   │   └── usuarios.py  criar, listar e remover usuários
│   └── tests/
└── servidor.py          serve só a página do cliente, sem backend
```

## Parâmetros do link

Formato compacto, para caber nas etiquetas menores. Os nomes e valores são estes:

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

As letras, intervalos (km e meses) e margens de aviso ficam em `frontend/cliente/config.js`.
Se mudar um intervalo, mude também em `backend/app/config.py` (um teste avisa se ficarem diferentes).
Mudar a letra de um serviço invalida as etiquetas já gravadas com a letra antiga.

## Área da oficina (backend)

### Rodar

```bash
cd backend
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
python -m app.usuarios criar marlon "Marlon"     # pede a senha
PANTANAL_COOKIE_SEGURO=0 uvicorn app.main:app --port 8000
```

Abra `http://localhost:8000/oficina/`. Sem login, qualquer página da oficina volta para a tela
de entrar. `PANTANAL_COOKIE_SEGURO=0` só vale para testar em http; publicado em https, deixe sem.

Testes: `pip install -r requirements-dev.txt && python -m pytest`.

### Configuração (variáveis de ambiente)

| Variável                  | Padrão                       | Para que serve                                    |
|---------------------------|------------------------------|---------------------------------------------------|
| `PANTANAL_BANCO`          | `backend/dados/pantanal.db`  | arquivo do banco; precisa ficar num disco que não se apaga |
| `PANTANAL_COOKIE_SEGURO`  | `1`                          | cookie só por https                               |
| `PANTANAL_SESSAO_DIAS`    | `30`                         | quantos dias o login dura                         |
| `PANTANAL_ARQUIVOS_OS`    | pasta `os` ao lado do banco  | onde ficam os PDFs das OS                         |
| `PANTANAL_USUARIO` / `PANTANAL_SENHA` | –                | cria esse usuário na primeira vez, se o banco não tiver nenhum (para hospedagens sem terminal) |

### Usuários

```bash
python -m app.usuarios listar
python -m app.usuarios criar joao "João da Silva"
python -m app.usuarios senha joao      # troca a senha e derruba os logins dele
python -m app.usuarios remover joao
```

As senhas ficam guardadas com hash (scrypt). Cinco senhas erradas em 15 minutos bloqueiam o
usuário até a janela passar.

### O que é salvo

A tela "Registrar visita" (`gravar.html`) salva a visita com o botão "Salvar visita no sistema",
sem depender da etiqueta: placa, nome e telefone do cliente, todos os serviços que estão na tela
(serviço, km e data) e o PDF da OS. Gravar a etiqueta ou copiar o link também salva, se a visita
ainda não foi salva. Ler uma etiqueta salva os serviços que ela tem, para carros que ainda não
estão no sistema. O mesmo serviço na mesma placa e no mesmo dia não duplica.

- **Cliente**: um nome e um telefone por placa (tabela `clientes`); vale o último informado, e
  campo vazio não apaga o que já estava salvo. Ao digitar uma placa que já está no sistema, a
  tela completa cliente, telefone e, se ainda estiverem em branco, os últimos serviços.
- **PDF da OS**: até 10 MB, guardado na pasta `PANTANAL_ARQUIVOS_OS` (por padrão
  `backend/dados/os/`, no mesmo disco do banco) com o nome igual ao hash do conteúdo; o mesmo
  PDF de novo não duplica. Na tela de frota, o detalhe da placa lista as OS e abre o PDF.
- **Leitura do PDF**: se o PDF tiver texto (não for imagem escaneada), o navegador extrai o
  texto com pdf.js e preenche placa, cliente (`Cliente:`, `Proprietário:` ou `Nome:`), telefone
  (`Telefone`, `Celular`, `Fone`… ou o primeiro número que não seja o da oficina), km, data da
  OS e serviços, igual ao texto colado. Os campos podem ser corrigidos antes de salvar. A placa
  vem depois de "Placa" ou, se não tiver rótulo, é a primeira no formato `ABC-1234`/`ABC1D23`.
- **Gravar pelo celular**: no computador não dá para gravar NFC. Depois de salvar, a tela mostra
  um QR code (e a frota tem o botão "QR para gravar pelo celular") que abre a mesma placa no
  celular, com os dados do sistema, direto na gravação. Se o celular não estiver logado, o login
  volta para a placa.

Na página do cliente, o km que ele digita em "Quilometragem atual" é enviado ao backend
(`envioKm` no `config.js`) uns segundos depois que ele para de digitar, só se for maior que o
km da etiqueta. Fica numa tabela separada (`leituras_cliente`), um valor por placa e dia, sem
login. A página no GitHub Pages também envia, então etiquetas antigas contam. Para não poluir a
estimativa, o km do cliente é ignorado se for menor que o de uma visita anterior, maior que o de
uma visita posterior ou se exigir mais de 1.500 km por dia; e cada endereço IP pode enviar até
30 vezes por hora. Km de placa que ainda não tem visita fica guardado e entra quando ela tiver.

### Tela de frota

Uma linha por placa, com última visita, km na visita, km/dia, km atual, próxima manutenção,
previsão, dias e km que faltam e situação. Clique em qualquer coluna para ordenar (de novo
inverte). Filtros: placa ou nome do cliente, situação, serviço, prazo da previsão e data da última
visita. Clicar numa linha mostra cliente e telefone (link para o WhatsApp), todos os serviços do
carro, o histórico de visitas, os PDFs das OS e os botões "Gravar etiqueta com estes dados" (abre
a tela de visita com o carro carregado, direto na gravação) e "Registrar nova visita".

- **Km/dia**: (último km conhecido − primeiro) ÷ dias entre eles, contando as visitas e o km
  digitado pelo cliente. Precisa de pelo menos dois dias com km e 7 dias entre eles; km que
  diminui não gera média.
- **Km atual**: último km conhecido + km/dia × dias desde então (marcado "est." quando
  estimado, e "cliente" quando o último km veio do cliente). "Km na visita" é sempre o da oficina.
- O detalhe da placa lista os km informados pelo cliente, marcando os ignorados.
- **Km atual hoje**: no lápis ✎ da coluna "Km atual", a oficina pode informar o km do dia (cliente ligou ou
  passou na loja). Entra na estimativa como o km do cliente, com a marca "oficina", e precisa bater
  com as visitas. O km que o cliente digitar no mesmo dia não troca o da oficina.
- **Previsão** de cada serviço: a data mais próxima entre o prazo em meses e o dia em que o km
  estimado chega no km da próxima troca. A situação segue as mesmas regras da página do cliente.
- Com "Serviço" escolhido, as colunas de previsão mostram aquele serviço em vez do mais urgente.

### API

| Rota                       | O que faz                                  |
|----------------------------|--------------------------------------------|
| `POST /api/entrar`         | `{usuario, senha}` → cookie de sessão      |
| `POST /api/sair`           | encerra a sessão                           |
| `GET /api/eu`              | usuário logado                             |
| `POST /api/registros`      | `{placa, nome?, telefone?, servicos: [{servico, km, data}]}` |
| `POST /api/ordens?placa=&data=&km=&nome=` | corpo = o PDF da OS (`application/pdf`) |
| `GET /api/ordens/{id}`     | abre o PDF de uma OS                        |
| `POST /api/leituras`       | `{placa, km}` do cliente, sem login         |
| `GET /api/frota`           | resumo de todas as placas                  |
| `GET /api/veiculos/{placa}`| resumo e histórico de uma placa            |

## Montar o link a partir da OS

Em `frontend/oficina/gravar.html`, escolha o PDF da OS ou cole no campo "Colar itens da OS" a placa, o km e os itens da ordem de serviço.
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
enviado. O endereço fica em `sobreRodas.url` no `config.js`. O link "Área da oficina" no rodapé só aparece
quando `areaOficina` estiver preenchido com o endereço do backend.

## Tamanho da etiqueta

O link do exemplo acima tem 77 bytes na etiqueta; com os quatro serviços em datas diferentes,
cerca de 100. Os dois cabem na **NTAG213** (137 bytes), a etiqueta mais barata. A maior parte
é o endereço `marlontosta.github.io/pantanal-etiqueta/` (40 caracteres); um domínio próprio
curto encurtaria ainda mais. A tela de gravar mostra o tamanho e em quais chips cabe.

## Hospedagem (precisa ser https)

A gravação NFC pelo navegador (Web NFC) só funciona no **Chrome para Android** e só em páginas
servidas por **https**.

- **Página do cliente**: o GitHub Pages publica `frontend/cliente/` a cada push na main
  (`.github/workflows/pages.yml`). As etiquetas apontam para esse endereço (`paginaCliente`
  no `config.js`), que não muda.
- **Backend e área da oficina**: o GitHub Pages não roda Python. É preciso uma hospedagem com
  Python e um disco que guarde o arquivo do banco entre reinícios (`PANTANAL_BANCO`). Depois de
  publicado, abra `https://<endereço-do-backend>/oficina/gravar.html` no Chrome Android.

Sem Chrome Android, copie o link gerado e grave com um app como NFC Tools, ou imprima o QR code.

## Testar localmente

```bash
cd etiqueta && python3 servidor.py
```

O script serve só a página do cliente (`frontend/cliente/`) na porta 8080 (outra porta:
`python3 servidor.py 9000`) e mostra o endereço local e o endereço pelo IP da máquina, para abrir
no celular conectado à mesma rede Wi-Fi. Para a área da oficina, rode o backend (acima).
NFC não funciona em http local; para testar a gravação, use a versão publicada em https.
