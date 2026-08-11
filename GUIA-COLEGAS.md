# 📅 Calendário Acadêmico UNINASSAU — guia para rodar na sua máquina

Ferramenta pessoal que pega **aulas, prazos e AOLs do portal da UNINASSAU** e joga tudo no **seu Google Agenda**. Roda 100% na sua máquina — suas credenciais e seu Google ficam só com você.

> Repositório: **[LINK DO GITHUB]**

---

## ✅ Antes de começar (5 min)

1. Instale o [Python 3](https://www.python.org/downloads/). Na instalação, **marque a opção "Add Python to PATH"** (importante!).
2. Baixe o projeto no GitHub: botão verde **Code → Download ZIP**.
3. Descompacte a pasta em qualquer lugar (ex.: `Documentos`).

## 🚀 Rodar (3 passos)

### 1. Instalar as dependências (uma única vez)
Abra um terminal **dentro da pasta do projeto** e rode:

```
pip install -r requirements.txt
```

### 2. Subir a ferramenta
Dê **duplo clique no `iniciar.bat`**. O navegador abre em `http://127.0.0.1:5000/`.

### 3. Configurar (primeira vez, ~15 min)

1. **Acesso ao portal** — na tela do app, em *Configurações*, clique no link do portal e peça o **link mágico** com seu e-mail. No Gmail, **copie o link sem clicar** e cole no app.
2. **Disciplinas** — para cada matéria: abra a matéria no portal → `F12` → aba **Application** → **Cookies** → copie o valor de `ubiqua-discipline` → cole no app (o nome da matéria é preenchido sozinho).
3. **Google Agenda** — siga o guia do `README.md` para criar o `credentials.json` (uma vez, ~10 min). Depois, no app: *Configurações → Conectar Google Agenda*.
4. **Sincronizar** — clique em **↻ Sincronizar com o Google Agenda**. Seus eventos aparecem na agenda **UNINASSAU** do seu Google.

## ✅ Deu certo?
- A lista de **Próximos eventos** na página fica preenchida.
- **Aulas, AOLs e prazos** aparecem no Google Agenda.
- Clicar em *Sincronizar* de novo **não duplica** nada.

## 🆘 Problemas comuns
- **"python não é reconhecido"** → reinstale o Python marcando *Add to PATH*, ou use `py` em vez de `python`.
- **Porta 5000 em uso** → feche outro servidor Flask e rode de novo.
- **Link mágico "expirado"** → o link é de uso único; gere outro no portal.
- **Sincronização dá erro de token** → gere um novo link mágico e cole de novo.
