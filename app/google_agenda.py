"""Integracao com o Google Agenda (Google Calendar API).

O app cria (ou reutiliza) uma agenda "UNINASSAU" na conta Google do
usuario e mantem os eventos do portal sincronizados nela.

Setup unico (guia no README): criar um projeto no Google Cloud,
habilitar a Google Calendar API, criar um Client ID OAuth do tipo
"Aplicativo para desktop" e salvar o JSON baixado como credentials.json
na pasta do projeto. Depois de autorizar uma vez, o token fica salvo em
token.google.json (fora do git).
"""

import datetime
import hashlib
import json
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/calendar"]
TIMEZONE = "America/Sao_Paulo"
NOME_AGENDA = "UNINASSAU"

BASE_DIR = Path(__file__).resolve().parent.parent
CREDENTIALS_PATH = BASE_DIR / "credentials.json"
TOKEN_PATH = BASE_DIR / "token.google.json"


class GoogleAgenda:
    """Cliente para espelhar as atividades do banco numa agenda do Google."""

    def __init__(self):
        self.service = None
        self.calendario_id = None
        self.ultimo_erro = ""

    # ---------------------------------------------------------------
    # Autenticacao (OAuth 2.0)
    # ---------------------------------------------------------------
    def autenticar(self):
        """Carrega o token salvo ou faz o fluxo OAuth (abre o navegador).

        Devolve True se conseguiu conectar na API do Google.
        """
        creds = None
        if TOKEN_PATH.exists():
            try:
                creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
            except Exception as exc:
                self.ultimo_erro = f"Nao deu para ler token.google.json: {exc}"
                creds = None

        if creds and creds.valid:
            self.service = build("calendar", "v3", credentials=creds)
            return True

        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as exc:
                self.ultimo_erro = f"Token expirado e nao renovou: {exc}"
                creds = None

        if not creds or not creds.valid:
            if not CREDENTIALS_PATH.exists():
                self.ultimo_erro = (
                    "Falta o arquivo credentials.json na pasta do projeto."
                )
                return False
            flow = InstalledAppFlow.from_client_secrets_file(
                str(CREDENTIALS_PATH), SCOPES
            )
            creds = flow.run_local_server(port=0)

        TOKEN_PATH.write_text(creds.to_json(), encoding="utf-8")
        self.service = build("calendar", "v3", credentials=creds)
        return True

    # ---------------------------------------------------------------
    # Agenda "UNINASSAU"
    # ---------------------------------------------------------------
    def garantir_agenda(self):
        """Devolve o id da agenda 'UNINASSAU', procurando ou criando."""
        try:
            pagina = None
            while True:
                resultado = self.service.calendarList().list(pageToken=pagina).execute()
                for calendario in resultado.get("items", []):
                    if calendario.get("summary") == NOME_AGENDA:
                        self.calendario_id = calendario["id"]
                        return self.calendario_id
                pagina = resultado.get("nextPageToken")
                if not pagina:
                    break
            criado = (
                self.service.calendars()
                .insert(body={"summary": NOME_AGENDA, "timeZone": TIMEZONE})
                .execute()
            )
            self.calendario_id = criado["id"]
            return self.calendario_id
        except Exception as exc:
            self.ultimo_erro = f"Falha ao localizar/criar a agenda: {exc}"
            return None

    # ---------------------------------------------------------------
    # Eventos
    # ---------------------------------------------------------------
    def _id_evento(self, materia, titulo, data_fim):
        """Id determinístico no Google: o mesmo dado sempre gera o mesmo id.

        O Google só aceita letras a-v e dígitos 0-9 em id de evento
        (base32hex). O prefixo "uninassau" (todas letras válidas) identifica
        os eventos criados por este app e o restante é o sha1 em hex.
        """
        chave = f"{materia}|{titulo}|{data_fim}"
        return "uninassau" + hashlib.sha1(chave.encode("utf-8")).hexdigest()[:40]

    def _corpo_evento(self, atv):
        """Monta o corpo do evento do Google a partir de uma linha do banco."""
        gid = self._id_evento(atv["materia_nome"], atv["titulo"], atv["data_fim"])

        raw = {}
        try:
            raw = json.loads(atv.get("raw_json") or "{}")
        except (ValueError, TypeError):
            pass
        all_day = bool(raw.get("is_all_day"))

        inicio = atv["data_inicio"] or atv["data_fim"] or ""
        fim = atv["data_fim"] or inicio

        resumo = f"[{atv['materia_nome']}] {atv['titulo']}"
        descricao = [f"Disciplina: {atv['materia_nome']}"]
        if atv.get("tipo"):
            descricao.append(f"Tipo: {atv['tipo']}")
        if atv.get("link"):
            descricao.append(f"Link: {atv['link']}")

        corpo = {
            "id": gid,
            "summary": resumo,
            "description": "\n".join(descricao),
            # Google tem 11 cores pré-definidas (1-11); cada disciplina usa a sua.
            "colorId": str((atv["materia_id"] % 11) + 1),
        }

        if all_day:
            data = inicio[:10]
            corpo["start"] = {"date": data}
            corpo["end"] = {
                # O Google trata o fim como exclusivo -> soma 1 dia.
                "date": (
                    datetime.datetime.strptime(data, "%Y-%m-%d")
                    + datetime.timedelta(days=1)
                ).strftime("%Y-%m-%d")
            }
        else:
            corpo["start"] = {"dateTime": inicio, "timeZone": TIMEZONE}
            corpo["end"] = {"dateTime": fim or inicio, "timeZone": TIMEZONE}

        return corpo

    def sincronizar_eventos(self, atividades):
        
        if not self.service or not self.calendario_id:
            self.ultimo_erro = "Google Agenda nao conectado."
            return None

        # Eventos que ja estao na agenda.
        existentes = {}
        pagina = None
        while True:
            res = (
                self.service.events()
                .list(
                    calendarId=self.calendario_id,
                    maxResults=250,
                    pageToken=pagina,
                )
                .execute()
            )
            for ev in res.get("items", []):
                existentes[ev["id"]] = ev
            pagina = res.get("nextPageToken")
            if not pagina:
                break

        criados = atualizados = removidos = 0
        erros = []
        esperados = set()

        for atv in atividades:
            try:
                corpo = self._corpo_evento(atv)
                gid = corpo["id"]
                esperados.add(gid)
                if gid in existentes:
                    self.service.events().update(
                        calendarId=self.calendario_id, eventId=gid, body=corpo
                    ).execute()
                    atualizados += 1
                else:
                    try:
                        self.service.events().insert(
                            calendarId=self.calendario_id, body=corpo
                        ).execute()
                        criados += 1
                    except Exception as exc_insert:
                        # Evento recém-deletado pode estar na "lixeira" do Google
                        # por até 30 dias -> tenta update. Se falhar, reporta a
                        # causa original do insert (mais informativa).
                        try:
                            self.service.events().update(
                                calendarId=self.calendario_id, eventId=gid, body=corpo
                            ).execute()
                            atualizados += 1
                        except Exception:
                            erros.append(f"{atv['titulo']}: {exc_insert}")
            except Exception as exc:
                erros.append(f"{atv['titulo']}: {exc}")

        for gid in existentes:
            if gid not in esperados and gid.startswith("uninassau"):
                try:
                    self.service.events().delete(
                        calendarId=self.calendario_id, eventId=gid
                    ).execute()
                    removidos += 1
                except Exception:
                    pass  

        return {
            "criados": criados,
            "atualizados": atualizados,
            "removidos": removidos,
            "erros": erros,
        }
