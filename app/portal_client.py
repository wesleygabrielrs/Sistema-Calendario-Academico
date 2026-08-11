"""Cliente da API do portal academico UNINASSAU (serconnect.sereducacional.com).

O login e por SSO com link magico (email -> link no Gmail -> clique).
Este cliente:
  1. Segue o link colado e captura o cookie ubiqua-access-token
  2. Usa esse token (cookie) nas chamadas da API de recursos
  3. Busca os eventos do calendario (aulas, avaliacoes, termos) por periodo

API descoberta no HAR (Etapa 0):
  GET /api/resources/auth/me                                  -> sessao
  GET /api/resources/student/content/calendar/{tipo}?start_date=...&end_date=...
      onde tipo em: bookings, assessments, academic, terms
"""

import datetime
import json
import re
import time
import urllib.parse

import requests

BASE_URL = "https://serconnect.sereducacional.com"
API_URL = BASE_URL + "/api/resources"
AUTH_ME_URL = API_URL + "/auth/me"
CALENDAR_URL = API_URL + "/student/content/calendar/{tipo}"

# AOLs (avaliacoes online, nota 0-10 por unidade) ficam na plataforma
# "Prova Facil". O portal so fornece o nome/uuid e o SSO; a lista com os
# prazos reais (end_date) mora na API da Prova Facil (descoberto na Etapa 0).
PROVAFACIL_ASSESSMENTS_URL = API_URL + "/student/content/sso/prova-facil/assessments"
PROVAFACIL_SSO_URL = API_URL + "/student/content/sso/prova-facil"
PROVAFACIL_ONLINE_TESTS = "api/v2/ot/online-tests/"

# Endpoints de calendario que agregam a agenda do periodo.
TIPOS_CALENDARIO = ("bookings", "assessments", "academic", "terms")

# Nome amigavel por tipo de evento do calendario.
ROTULO_TIPO = {
    "BOOKING": "Aula",
    "ASSESSMENT": "Avaliação",
    "ACADEMIC": "Evento acadêmico",
    "DISCIPLINE_TERM": "Início de disciplina",
}

# Pausa entre chamadas ao portal.
PAUSA_SEGUNDOS = 0.4

# Quantos meses a frente (a partir do mes atual) considerar no calendario.
# O portal limita a janela de datas (bookings) a ~1 mes por chamada.
MESES_JANELA = 4

# Headers de navegador: o portal rejeita pedidos sem cara de navegador.
HEADERS_NAVEGADOR = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": BASE_URL + "/home/my-calendar",
}


class PortalClient:
    #Sessao de acesso ao portal via token (gerado pelo link magico)."""

    def __init__(self, email="", token="", disciplinas=None):
        """disciplinas: lista de dicts {"uuid": ..., "nome": ...}."""
        self.email = email
        self.disciplinas = disciplinas or []
        self.session = requests.Session()
        self.session.headers.update(HEADERS_NAVEGADOR)
        self.logado = False
        self.ultimo_erro = ""
        if token:
            self.usar_token(token)

    def _set_disciplina(self, uuid):
        """Troca o cookie ubiqua-discipline para a disciplina do uuid."""
        self.session.cookies.set(
            "ubiqua-discipline",
            uuid,
            domain="serconnect.sereducacional.com",
        )

    @staticmethod
    def nome_curto(nome):
        """Encurta 'Módulo A - 5064 . 7 - Fundamentos de Banco de Dados - D.20262.A'
        para 'Fundamentos de Banco de Dados' (sem o prefixo de modulo e o codigo)."""
        if not nome:
            return nome
        m = re.match(r"^M[oó]dulo[^-]*-\s*[^-]+-\s*(.+?)\s*-\s*D\.\d", nome.strip())
        if m:
            return m.group(1).strip()
        return nome.strip()

    def nomear_disciplina(self, uuid):
        """Consulta o nome da disciplina via /discipline?light=true (ja encurtado)."""
        self._set_disciplina(uuid)
        resp = self.session.get(
            API_URL + "/student/content/discipline",
            params={"light": "true"},
            timeout=30,
        )
        if resp.status_code != 200:
            return ""
        result = resp.json().get("result") or {}
        return self.nome_curto(result.get("name") or "")

    
    # Token / sessao
    
    def usar_token(self, token):
        """Configura a sessao com um ubiqua-access-token conhecido."""
        if token:
            self.session.cookies.set(
                "ubiqua-access-token",
                token,
                domain="serconnect.sereducacional.com",
            )
            self.session.cookies.set(
                "ubiqua-origin",
                "serconnect.sereducacional.com",
                domain="serconnect.sereducacional.com",
            )
            self.logado = True

    def enviar_link(self, email):
        """Dispara o link magico para o e-mail.

        Ainda nao descobri a chamada exata que o portal faz ao pedir
        o link (a tela /auth/sso nao estava no HAR, que foi exportado ja
        logado). Por isso oriento o usuario a pedir o link no proprio
        navegador e colar aqui embaixo. Quando capturarmos o POST real,
        este metodo passa a enviar sozinho.
        """
        self.ultimo_erro = (
            "O app ainda nao consegue pedir o link sozinho. "
            "Abra serconnect.sereducacional.com/auth/sso no navegador, "
            "digite seu e-mail, e cole o link recebido no Gmail na etapa 2."
        )
        return False

    def completar_link(self, link):
        """Segue o link magico colado e devolve o token obtido.

        O link do Gmail passa por um rastreador (awstrack.me) que
        redireciona para /api/sso?token=...; ao seguir, o servidor
        emite o cookie ubiqua-access-token.
        """
        resp = self.session.get(link, timeout=30, allow_redirects=True)
        if resp.status_code >= 400:
            self.ultimo_erro = f"Link rejeitado pelo portal (status {resp.status_code})"
            self.logado = False
            return ""

        token = self.session.cookies.get("ubiqua-access-token", "")
        if not token:
            self.ultimo_erro = "Link seguido, mas o portal nao emitiu token de acesso"
            self.logado = False
            return ""
        self.usar_token(token)
        return token

    def autenticado(self):
        """True se o token ainda e aceito pelo portal (GET /auth/me)."""
        resp = self.session.get(AUTH_ME_URL, timeout=30)
        if resp.status_code in (401, 403):
            self.logado = False
            self.ultimo_erro = "Token expirado. Gere um novo link magico."
            return False
        return resp.status_code == 200

    
    # Extracao do calendario
   
    @staticmethod
    def _periodos():
        """Pares (inicio, fim) de mes a mes, do mes atual em diante."""
        hoje = datetime.date.today()
        mes = hoje.replace(day=1)
        periodos = []
        for _ in range(MESES_JANELA):
            primeiro = mes
            ultimo = (mes + datetime.timedelta(days=32)).replace(
                day=1
            ) - datetime.timedelta(days=1)
            periodos.append((primeiro.isoformat(), ultimo.isoformat()))
            mes = ultimo + datetime.timedelta(days=1)
        return periodos

    def _buscar_calendario(self, tipo):
        """Chama o endpoint de calendario (mes a mes) e devolve os eventos."""
        url = CALENDAR_URL.format(tipo=tipo)
        eventos = []
        for inicio, fim in self._periodos():
            resp = self.session.get(
                url, params={"start_date": inicio, "end_date": fim}, timeout=30
            )
            if resp.status_code != 200:
                if resp.status_code in (401, 403):
                    self.logado = False
                    self.ultimo_erro = "Token expirado. Gere um novo link magico."
                return eventos
            dados = resp.json()
            eventos.extend(dados.get("result") or [])
            time.sleep(PAUSA_SEGUNDOS)
        return eventos

    @staticmethod
    def _normalizar_evento(evento):
        """Converte um evento do calendario no formato do banco."""
        tipo = evento.get("type", "")
        subject = (evento.get("subject") or "").strip()
        conteudo = evento.get("content") or {}
        disciplina = conteudo.get("discipline") or {}

        nome_disciplina = (
            disciplina.get("name")
            or subject
            or conteudo.get("name")
            or "Sem disciplina"
        ).strip()

        titulo = subject or nome_disciplina or "Evento"

        
        # O nome da disciplina fica no prefixo do evento no calendario, entao
        # reduzim o titulo para "Inicio/Encerramento da disciplina".
        rotulo = ROTULO_TIPO.get(tipo, tipo)
        if tipo == "DISCIPLINE_TERM":
            if titulo.lower().startswith("encerramento"):
                rotulo = "Fim de disciplina"
                titulo = "Encerramento da disciplina"
            else:
                titulo = "Início da disciplina"

        return {
            "titulo": titulo,
            "tipo": rotulo,
            "data_inicio": (evento.get("event_start_date") or ""),
            "data_fim": (evento.get("event_end_date") or ""),
            "status": "",
            "link": conteudo.get("meeting_url") or "",
            "raw_json": json.dumps(evento, ensure_ascii=False),
        }


    # AOLs (avaliacoes online) - Prova Facil

    def _primeiro_item_aol(self):
        """Devolve o uuid de uma AOL qualquer (para gerar o SSO da Prova Facil)."""
        for disciplina in self.disciplinas:
            uuid = (disciplina.get("uuid") or "").strip()
            if not uuid:
                continue
            self._set_disciplina(uuid)
            try:
                resp = self.session.get(PROVAFACIL_ASSESSMENTS_URL, timeout=30)
            except requests.RequestException:
                continue
            if resp.status_code != 200:
                continue
            for aol in resp.json().get("result") or []:
                if aol.get("uuid"):
                    return aol["uuid"]
            time.sleep(PAUSA_SEGUNDOS)
        return ""

    def _candidate_token(self, item_uuid):
        """Gera o candidate_token da Prova Facil via SSO de uma AOL.

        Devolve (token, origin). O token e do candidato (nao da materia),
        entao uma chamada cobre as AOLs de todas as materias.
        """
        try:
            resp = self.session.get(
                PROVAFACIL_SSO_URL, params={"item_uuid": item_uuid}, timeout=30
            )
            if resp.status_code != 200:
                return "", ""
            url = (resp.json().get("result") or {}).get("url") or ""
            if not url:
                return "", ""
            final = self.session.get(url, timeout=30, allow_redirects=True)
            tok = re.search(r"candidate_token=([A-Za-z0-9]+)", final.url)
            orig = re.search(r"origin=([^&]+)", final.url)
            if not tok or not orig:
                return "", ""
            origin = urllib.parse.unquote(orig.group(1))
            origin = origin.replace("\\", "/").replace("//", "/").rstrip("/")
            return tok.group(1), origin
        except requests.RequestException:
            return "", ""

    @staticmethod
    def _normalizar_aol(item):
        """Converte uma AOL da Prova Facil no formato de atividade do banco.

        Agendamos o evento no DIA DO PRAZO (end_date) como dia inteiro.
        """
        agendamento = item.get("schedule") or {}
        tipo_assessment = (agendamento.get("type_assessment") or {}).get("name") or ""
        if not tipo_assessment:
            return None
        nome_materia = PortalClient.nome_curto(
            item.get("module_name") or item.get("academic") or ""
        )
        if not nome_materia:
            return None
        prazo = item.get("end_date") or ""
        if not prazo:
            return None
        raw = dict(item)
        raw["is_all_day"] = True
        return {
            "materia": nome_materia,
            "titulo": tipo_assessment,  # ex.: "AOL1"
            "tipo": "AOL",
            "data_inicio": prazo,
            "data_fim": prazo,
            "status": "",
            "link": "",
            "raw_json": json.dumps(raw, ensure_ascii=False),
        }

    def _buscar_aols(self):
        """Busca as AOLs disponiveis (com prazo) na plataforma Prova Facil."""
        if not self.disciplinas:
            return []
        item_uuid = self._primeiro_item_aol()
        if not item_uuid:
            return []
        token, origin = self._candidate_token(item_uuid)
        if not token or not origin:
            return []
        base = f"https://{origin}/"
        try:
            resp = self.session.get(
                base + PROVAFACIL_ONLINE_TESTS,
                headers={
                    "Authorization": f"Token {token}",
                    "Content-Type": "application/json",
                },
                timeout=30,
            )
        except requests.RequestException:
            return []
        if resp.status_code != 200:
            self.ultimo_erro = (
                f"Prova Facil nao listou as AOLs (status {resp.status_code})"
            )
            return []
        dados = resp.json()
        if not isinstance(dados, list):
            return []
        return [
            atv
            for atv in (self._normalizar_aol(item) for item in dados)
            if atv is not None
        ]

    def sincronizar(self):
        """Busca o calendario de cada disciplina e agrupa por materia.

        Devolve:
            {
              "ok": bool,
              "erros": [str, ...],
              "materias": [ {"nome", "codigo", "professor", "url", "atividades":[...]}, ... ]
            }
        """
        if not self.logado:
            return {
                "ok": False,
                "erros": ["Nao ha token de acesso. Use o link magico."],
                "materias": [],
            }
        if not self.autenticado():
            return {"ok": False, "erros": [self.ultimo_erro], "materias": []}
        if not self.disciplinas:
            return {
                "ok": False,
                "erros": [
                    "Nenhuma disciplina configurada. Adicione no menu Configuracoes."
                ],
                "materias": [],
            }

        resultado = {"ok": True, "erros": [], "materias": []}

        for disciplina in self.disciplinas:
            uuid = disciplina.get("uuid", "").strip()
            if not uuid:
                continue
            nome_config = (disciplina.get("nome") or "").strip() or uuid[:8]
            self._set_disciplina(uuid)

           
            atividades = []
            vistos = set()
            for tipo in TIPOS_CALENDARIO:
                try:
                    eventos = self._buscar_calendario(tipo)
                except Exception as exc:  # noqa: BLE001
                    resultado["erros"].append(f"{nome_config} / {tipo}: {exc}")
                    continue

                for evento in eventos:
                    atividade = self._normalizar_evento(evento)
                   
                    chave = (atividade["titulo"], atividade["data_fim"])
                    if chave in vistos:
                        continue
                    vistos.add(chave)
                    atividades.append(atividade)

            resultado["materias"].append(
                {
                    "nome": nome_config,
                    "codigo": "",
                    "professor": "",
                    "url": "",
                    "atividades": atividades,
                }
            )

        # AOLs (avaliacoes online): o candidate_token cobre todas as materias,
        # entao uma chamada basta. Filtra apenas as disciplinas configuradas.
        try:
            aols = self._buscar_aols()
        except Exception as exc:  # noqa: BLE001
            resultado["erros"].append(f"AOLs: {exc}")
            aols = []
        materias_por_nome = {m["nome"]: m for m in resultado["materias"]}
        for atv_aol in aols:
            materia = materias_por_nome.get(atv_aol.pop("materia", ""))
            if materia is not None:
                materia["atividades"].append(atv_aol)

        return resultado
