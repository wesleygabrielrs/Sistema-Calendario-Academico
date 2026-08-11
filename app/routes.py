"""Rotas web do Calendario Academico UNINASSAU.

O portal usa login por SSO (link magico): o usuario pede o link no
portal, recebe no Gmail, cola aqui e o app captura o token de acesso.

Depois de sincronizar, os eventos vao para o Google Agenda (numa agenda
"UNINASSAU" criada automaticamente). A pagina mostra os proximos
eventos e um atalho para abrir o Google.
"""

import re
from datetime import date

from flask import jsonify, redirect, render_template, request, url_for

from . import config_manager, db
from .google_agenda import CREDENTIALS_PATH, GoogleAgenda
from .portal_client import BASE_URL, PortalClient

# Paleta de cores por materia.
CORES = [
    "#e74c3c",
    "#e67e22",
    "#f1c40f",
    "#2ecc71",
    "#1abc9c",
    "#3498db",
    "#9b59b6",
    "#e84393",
]

DIAS_SEMANA = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"]


def init_app(app):
    """Registra as rotas da aplicacao."""

    @app.route("/")
    def index():
        """Pagina principal: proximos eventos + atalho para o Google Agenda."""
        if not config_manager.configurado():
            return redirect(url_for("config"))
        google = google_status()
        return render_template(
            "index.html",
            google_conectado=google["conectado"],
            google_mensagem=google["mensagem"],
            url_google="https://calendar.google.com/calendar/r/week",
            proximos=listar_proximos(),
        )

    
    # Configuracao / acesso
    
    @app.route("/config", methods=["GET", "POST"])
    def config():
        """Tela de configuracao: e-mail + link magico + Google Agenda."""
        if request.method == "POST":
            email = request.form.get("email", "").strip()
            if email:
                config_manager.salvar(email=email)
            return redirect(url_for("config"))
        cfg = config_manager.carregar()
        google = google_status()
        return render_template(
            "config.html",
            email=cfg.get("email", ""),
            tem_token=bool(cfg.get("token")),
            url_portal=BASE_URL + "/auth/sso",
            disciplinas=config_manager.disciplinas(),
            google_conectado=google["conectado"],
            google_mensagem=google["mensagem"],
            tem_credentials=CREDENTIALS_PATH.exists(),
            google_msg=request.args.get("google", ""),
        )

    @app.route("/api/completar-link", methods=["POST"])
    def api_completar_link():
        """Recebe o link colado, segue ate o token e salva o acesso."""
        dados = request.get_json(silent=True) or {}
        link = (dados.get("link") or "").strip()
        if not link:
            return (
                jsonify({"ok": False, "erros": ["Cole o link recebido no Gmail"]}),
                400,
            )

        cfg = config_manager.carregar()
        cliente = PortalClient(email=cfg.get("email", ""))
        token = cliente.completar_link(link)
        if not token:
            return (
                jsonify(
                    {
                        "ok": False,
                        "erros": [cliente.ultimo_erro or "Nao foi possivel entrar"],
                    }
                ),
                400,
            )

        config_manager.salvar(token=token)
        return jsonify({"ok": True, "mensagem": "Acesso configurado com sucesso!"})

    
    # Disciplinas (uuid + nome)
    
    @app.route("/api/disciplinas", methods=["POST"])
    def api_adicionar_disciplina():
        """Adiciona uma disciplina pelo uuid (consulta o nome no portal)."""
        dados = request.get_json(silent=True) or {}
        uuid = (dados.get("uuid") or "").strip()
        if not uuid:
            return (
                jsonify({"ok": False, "erros": ["Informe o UUID da disciplina"]}),
                400,
            )

        cfg = config_manager.carregar()
        cliente = PortalClient(email=cfg.get("email", ""), token=cfg.get("token", ""))
        nome = cliente.nomear_disciplina(uuid)
        if not nome:
            return (
                jsonify(
                    {
                        "ok": False,
                        "erros": [
                            cliente.ultimo_erro
                            or "Nao foi possivel buscar o nome. Confira o token/UUID."
                        ],
                    }
                ),
                400,
            )

        config_manager.adicionar_disciplina(uuid, nome)
        return jsonify({"ok": True, "mensagem": f"Disciplina adicionada: {nome}"})

    @app.route("/api/disciplinas", methods=["DELETE"])
    def api_remover_disciplina():
        """Remove uma disciplina pelo uuid."""
        dados = request.get_json(silent=True) or {}
        uuid = (dados.get("uuid") or "").strip()
        if not uuid:
            return jsonify({"ok": False, "erros": ["Informe o UUID"]}), 400
        if config_manager.remover_disciplina(uuid):
            return jsonify({"ok": True, "mensagem": "Disciplina removida."})
        return jsonify({"ok": False, "erros": ["Disciplina nao encontrada."]}), 404

    
    # Google Agenda
    
    @app.route("/google/autorizar")
    def google_autorizar():
        """Conecta a conta Google (OAuth, abre o navegador) e prepara a agenda."""
        agenda = GoogleAgenda()
        if not CREDENTIALS_PATH.exists():
            return render_template("google_setup.html", erro=None)
        if not agenda.autenticar():
            return render_template("google_setup.html", erro=agenda.ultimo_erro)
        calendario_id = agenda.garantir_agenda()
        if not calendario_id:
            return render_template("google_setup.html", erro=agenda.ultimo_erro)
        config_manager.salvar(google_calendario_id=calendario_id)
        return redirect(url_for("config", google="conectado"))

    def google_status():
        """Diz se o Google Agenda esta pronto para receber eventos."""
        if not CREDENTIALS_PATH.exists():
            return {
                "conectado": False,
                "mensagem": "falta o credentials.json (guia no README)",
            }
        if not config_manager.carregar().get("google_calendario_id"):
            return {"conectado": False, "mensagem": "autorize o Google Agenda uma vez"}
        return {
            "conectado": True,
            "mensagem": "Conectado ao Google Agenda (agenda UNINASSAU)",
        }

    def sincronizar_google():
        """Manda as atividades do banco para a agenda 'UNINASSAU' do Google."""
        cfg = config_manager.carregar()
        if not cfg.get("google_calendario_id"):
            return {
                "ok": False,
                "mensagem": "Google Agenda nao conectado — autorize em Configurações.",
            }
        agenda = GoogleAgenda()
        agenda.calendario_id = cfg["google_calendario_id"]
        if not agenda.autenticar():
            return {"ok": False, "mensagem": agenda.ultimo_erro}
        try:
            detalhes = agenda.sincronizar_eventos(db.listar_atividades())
        except Exception as exc:
            return {"ok": False, "mensagem": str(exc)}
        if detalhes is None:
            return {
                "ok": False,
                "mensagem": agenda.ultimo_erro or "Falha ao sincronizar no Google.",
            }
        return {"ok": True, "detalhes": detalhes}

    
    # Sincronizacao
    
    @app.route("/api/sincronizar", methods=["POST"])
    def api_sincronizar():
        #Extrai do portal, grava no banco e manda tudo pro Google Agenda.
        cfg = config_manager.carregar()
        if not cfg.get("token"):
            return (
                jsonify(
                    {
                        "ok": False,
                        "erros": ["Acesso nao configurado. Gere o link magico."],
                    }
                ),
                400,
            )

        cliente = PortalClient(
            email=cfg.get("email", ""),
            token=cfg["token"],
            disciplinas=config_manager.disciplinas(),
        )
        resultado = cliente.sincronizar()

        if not cliente.logado:
            # Token expirou -> pedir novo link
            return jsonify(
                {"ok": False, "erros": [cliente.ultimo_erro], "resumo": db.resumo()}
            )

        google = None
        if resultado["ok"]:
            gravar_resultado(resultado)
            google = sincronizar_google()

        return jsonify(
            {
                "ok": resultado["ok"],
                "erros": resultado["erros"],
                "resumo": db.resumo(),
                "google": google,
            }
        )

    @app.route("/api/proximos")
    def api_proximos():
        #Proximos eventos (usado para atualizar a lista apos sincronizar).
        return jsonify(listar_proximos())

    def gravar_resultado(resultado):
        """Grava materias e atividades no banco, sem duplicar (upsert)."""
        for materia in resultado["materias"]:
            materia_id = db.upsert_materia(
                materia.get("nome", ""),
                codigo=materia.get("codigo", ""),
                professor=materia.get("professor", ""),
                url=materia.get("url", ""),
            )
            for atv in materia.get("atividades", []):
                db.upsert_atividade(
                    materia_id,
                    atv.get("titulo", ""),
                    tipo=atv.get("tipo", ""),
                    data_inicio=atv.get("data_inicio", ""),
                    data_fim=atv.get("data_fim", ""),
                    status=atv.get("status", ""),
                    link=atv.get("link", ""),
                    raw_json=atv.get("raw_json", ""),
                )

   
    # Lista de proximos eventos
    
    def _extrair_hora(data_iso):
        """Devolve 'HH:MM' quando a data tem horario com fuso local (-03:00)."""
        m = re.search(r"T(\d{2}:\d{2})[+-]\d{2}:\d{2}$", data_iso or "")
        return m.group(1) if m else ""

    def listar_proximos(limite=12):
        """Proximas atividades (a partir de hoje), formatadas para a pagina."""
        hoje = date.today()
        itens = []
        for atv in db.listar_atividades():
            inicio = atv["data_inicio"] or atv["data_fim"] or ""
            data_iso = inicio[:10]
            try:
                d = date.fromisoformat(data_iso)
            except ValueError:
                continue
            if d < hoje:
                continue
            itens.append(
                {
                    "data": data_iso,
                    "data_texto": formatar_data(d, _extrair_hora(inicio)),
                    "materia": atv["materia_nome"],
                    "materia_id": atv["materia_id"],
                    "cor": CORES[atv["materia_id"] % len(CORES)],
                    "titulo": atv["titulo"],
                    "tipo": atv["tipo"],
                    "link": atv["link"],
                }
            )
        itens.sort(key=lambda x: x["data"])
        return itens[:limite]

    def formatar_data(d, hora=""):
        """'14/08 (sex) 19:00' — sem o ano, com o dia da semana (e hora quando houver)."""
        texto = f"{d.day:02d}/{d.month:02d} ({DIAS_SEMANA[d.weekday()]})"
        if hora:
            texto += f" {hora}"
        return texto
