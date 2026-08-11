# 📅 Calendário Acadêmico UNINASSAU

> Agrega horários de aula e prazos do portal acadêmico da UNINASSAU numa única agenda no Google Calendar.
> Aggregates UNINASSAU's academic schedule and deadlines into a single Google Calendar.

Ferramenta pessoal em **Python + Flask** que resolve um problema real do portal acadêmico da **UNINASSAU** (grupo Ser Educacional): horários e prazos de trabalho ficam descentralizados — cada matéria na sua própria aba. Este app **loga no portal**, **extrai as atividades de todas as matérias** e **espelha tudo no seu Google Agenda**, numa agenda **UNINASSAU** criada automaticamente.

A versão em inglês está logo abaixo / *English version below.*

---

## ✨ Funcionalidades

- **Login por link mágico** do portal (sem senha) — o app segue o link recebido no Gmail e captura o token de acesso
- **Sincronização por matéria**: percorre o calendário de cada disciplina (aulas, provas, trabalhos, prazos)
- **Espelha tudo no Google Agenda** via Calendar API, numa agenda **UNINASSAU** com uma cor por matéria
- **Sem duplicar**: eventos alterados são atualizados; eventos que sumiram do portal são removidos da agenda
- **Preserva o que você cria à mão** no Google — eventos não criados pelo app não são apagados
- **Lista de próximos eventos** na página + atalho para abrir o Google Agenda
- **Seguro por padrão**: credenciais e tokens em arquivos locais fora do git; servidor roda apenas em `127.0.0.1`

## 🛠️ Stack

- **Python 3** + **Flask** — servidor local
- **requests** — cliente da API do portal (serconnect / Ser Educacional)
- **google-api-python-client** + **google-auth-oauthlib** — Google Calendar API (OAuth 2.0)
- **SQLite** — banco local, fonte da verdade com *upsert* idempotente

## 🧠 Como funciona

O portal acadêmico não expõe um calendário agregado: cada matéria é acessada por um cookie `ubiqua-discipline` (UUID). O app:

1. Captura o **token de acesso** pelo link mágico (SSO)
2. Para cada disciplina configurada, busca os calendários `bookings`, `assessments`, `academic` e `terms` mês a mês
3. Normaliza os eventos (nome curto da disciplina, datas *all-day* corrigidas) e grava no SQLite **sem duplicar**
4. Espelha tudo no **Google Agenda** com *id* determinístico — o mesmo dado gera o mesmo evento, então a sincronização é idempotente

## 📸 Screenshot

<!-- Adicione um print da aplicação (página com a lista de próximos eventos) em `docs/screenshot.png` e descomente:
<p align="center"><img src="docs/screenshot.png" width="720" alt="Calendário Acadêmico UNINASSAU"/></p>
-->

## 🚀 Como rodar

Pré-requisito: [Python 3](https://www.python.org/) instalado.

```bash
# 1. Instale as dependências (uma vez só)
pip install -r requirements.txt

# 2. Suba o servidor
python run.py

# 3. Abra no navegador
http://127.0.0.1:5000/
```

Ou use o **`iniciar.bat`** (duplo clique): sobe o servidor e abre o navegador sozinho.

### Primeiro uso

1. **Acesso ao portal** — em *Configurações*, peça o link mágico no portal, copie o link recebido no Gmail (**sem clicar**) e cole no app
2. **Disciplinas** — adicione o UUID de cada matéria (F12 → Application → Cookies → `ubiqua-discipline`, trocando de matéria pelo seletor do portal)
3. **Google Agenda** — siga o guia abaixo para criar o `credentials.json` (uma vez) e clique em *Conectar Google Agenda*
4. **Sincronizar** — os eventos aparecem na agenda **UNINASSAU** do seu Google

### Configurar o Google Agenda (uma única vez, ~10 min)

1. [Google Cloud Console](https://console.cloud.google.com/) → crie um projeto
2. **APIs e serviços → Biblioteca** → ative a **Google Calendar API**
3. **Tela de consentimento OAuth** → tipo **Externo** → nome do app + seu e-mail (adicione seu e-mail em *usuários de teste*)
4. **Credenciais → ID do cliente OAuth** → tipo **Aplicativo para desktop** → baixe o JSON
5. Renomeie o arquivo para `credentials.json` e coloque na raiz do projeto
6. No app: **Configurações → Conectar Google Agenda** e autorize no navegador (uma única vez)

> 🔒 `credentials.json` e o token gerado (`token.google.json`) ficam **fora do git**.

## 📁 Estrutura

```
Calendario-Academico/
├── run.py               # Entrada: cria o app e sobe o servidor local
├── app/                 # Pacote da aplicação
│   ├── __init__.py      #   Fábrica create_app()
│   ├── routes.py        #   Rotas web (página, config, sincronizar, Google)
│   ├── portal_client.py #   Cliente da API do portal UNINASSAU (login + extração)
│   ├── google_agenda.py #   Integração com o Google Agenda (Calendar API)
│   ├── db.py            #   Banco SQLite (matérias e atividades)
│   ├── config_manager.py#   Configuração local (config.local.json)
│   ├── templates/       #   Páginas HTML (base, index, config, google_setup)
│   └── static/          #   CSS
├── requirements.txt    # Dependências
├── iniciar.bat         # Atalho do Windows (sobe o servidor + abre o navegador)
├── .gitignore          # Arquivos sensíveis fora do git
├── .gitattributes      # Normalização de fim de linha
└── dados/              # calendario.db (gerado em runtime, fora do git)
```

## 🔒 Segurança

- `config.local.json`, `credentials.json` e `token.google.json` estão no `.gitignore` e **nunca** devem ser enviados ao GitHub
- O servidor roda **somente** em `127.0.0.1` (sua máquina) — não expõe na rede
- O link mágico do portal é de **uso único** e fica consumido depois de usado

## ⚖️ Direitos

Projeto pessoal de estudo. **Todos os direitos reservados** — sem licença de uso ou reprodução por terceiros.

---

# 🇬🇧 English

> Aggregates UNINASSAU's academic schedule and deadlines into a single Google Calendar.

A personal **Python + Flask** tool that solves a real problem with the **UNINASSAU** academic portal (Ser Educacional group): schedules and assignment deadlines are scattered — each subject lives in its own tab. This app **logs into the portal**, **extracts activities from every subject**, and **mirrors everything into your Google Calendar** in a **UNINASSAU** calendar created automatically.

## ✨ Features

- **Magic-link login** to the portal (no password) — the app follows the email link and captures the access token
- **Per-subject sync**: walks each discipline's calendar (classes, exams, assignments, deadlines)
- **Mirrors everything to Google Calendar** via the Calendar API, in a **UNINASSAU** calendar with one color per subject
- **No duplicates**: changed events are updated; events that vanish from the portal are removed
- **Keeps your manual Google events** — anything not created by the app is left alone
- **Upcoming-events list** on the page + a shortcut to open Google Calendar
- **Secure by default**: credentials and tokens live in local files outside git; the server runs only on `127.0.0.1`

## 🛠️ Tech stack

- **Python 3** + **Flask** — local server
- **requests** — UNINASSAU portal API client (serconnect / Ser Educacional)
- **google-api-python-client** + **google-auth-oauthlib** — Google Calendar API (OAuth 2.0)
- **SQLite** — local database, source of truth with idempotent upserts

## 🧠 How it works

The portal exposes no aggregated calendar: each subject is accessed through a `ubiqua-discipline` cookie (UUID). The app:

1. Captures the **access token** through the magic-link SSO flow
2. For each configured subject, fetches the `bookings`, `assessments`, `academic` and `terms` calendars month by month
3. Normalizes events (short subject name, fixed all-day dates) and stores them in SQLite **without duplicating**
4. Mirrors everything into **Google Calendar** using a deterministic id — the same data yields the same event, so sync is idempotent

## 🚀 Getting started

Prerequisite: [Python 3](https://www.python.org/) installed.

```bash
pip install -r requirements.txt
python run.py
# open http://127.0.0.1:5000/
```

### First run

1. **Portal access** — in *Settings*, request the magic link on the portal, copy the email link (**don't click it**) and paste it into the app
2. **Subjects** — add each subject's UUID (F12 → Application → Cookies → `ubiqua-discipline`, switching subjects via the portal selector)
3. **Google Calendar** — follow the one-time setup below to create `credentials.json`, then click *Connect Google Calendar*
4. **Sync** — events appear in your **UNINASSAU** Google calendar

### One-time Google Calendar setup (~10 min)

1. [Google Cloud Console](https://console.cloud.google.com/) → create a project
2. **APIs & Services → Library** → enable the **Google Calendar API**
3. **OAuth consent screen** → type **External** → app name + your email (add your email under *test users*)
4. **Credentials → Create OAuth client ID** → type **Desktop app** → download the JSON
5. Rename it to `credentials.json` and place it in the project root
6. In the app: **Settings → Connect Google Calendar** and authorize once

> 🔒 `credentials.json` and the generated token (`token.google.json`) stay **out of git**.

## 📁 Structure

```
Calendario-Academico/
├── run.py               # Entry point: creates the app and runs the local server
├── app/                 # Application package
│   ├── __init__.py      #   create_app() factory
│   ├── routes.py        #   Web routes (page, settings, sync, Google)
│   ├── portal_client.py #   UNINASSAU portal API client (login + extraction)
│   ├── google_agenda.py #   Google Calendar API integration
│   ├── db.py            #   SQLite database (subjects and activities)
│   ├── config_manager.py#   Local configuration (config.local.json)
│   ├── templates/       #   HTML pages (base, index, config, google_setup)
│   └── static/          #   CSS
├── requirements.txt    # Dependencies
├── iniciar.bat         # Windows launcher (starts server + opens browser)
├── .gitignore          # Sensitive files kept out of git
├── .gitattributes      # Line-ending normalization
└── dados/              # calendario.db (generated at runtime, out of git)
```

## 🔒 Security

- `config.local.json`, `credentials.json` and `token.google.json` are in `.gitignore` and must **never** be pushed to GitHub
- The server runs **only** on `127.0.0.1` (your machine)
- The portal magic link is **single-use** and gets consumed after it's used

## ⚖️ Rights

Personal study project. **All rights reserved** — no license granted for use or reproduction by third parties.
