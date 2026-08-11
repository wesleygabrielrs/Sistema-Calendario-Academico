"""Leitura e gravacao das configuracoes em config.local.json.

Guarda o e-mail do Wesley e o token de acesso do portal (gerado via
link magico). O arquivo fica FORA do versionamento (ver .gitignore)
para nada sensivel subir para o GitHub. Uso local apenas.
"""

import json
from pathlib import Path

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.local.json"


def carregar():
    """Retorna dict com email/token, ou {} se ainda nao configurado."""
    if CONFIG_PATH.exists():
        try:
            return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def salvar(email=None, token=None, google_calendario_id=None):
    """Atualiza os campos fornecidos em config.local.json (preserva o resto)."""
    cfg = carregar()
    if email:
        cfg["email"] = email
    if token:
        cfg["token"] = token
    if google_calendario_id:
        cfg["google_calendario_id"] = google_calendario_id
    CONFIG_PATH.write_text(
        json.dumps(cfg, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def adicionar_disciplina(uuid, nome=""):
    """Adiciona uma disciplina (uuid + nome) sem duplicar."""
    cfg = carregar()
    disciplinas = cfg.setdefault("disciplinas", [])
    if any(d.get("uuid") == uuid for d in disciplinas):
        return False
    disciplinas.append({"uuid": uuid, "nome": nome})
    CONFIG_PATH.write_text(
        json.dumps(cfg, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return True


def remover_disciplina(uuid):
    """Remove uma disciplina pelo uuid."""
    cfg = carregar()
    disciplinas = cfg.get("disciplinas", [])
    novas = [d for d in disciplinas if d.get("uuid") != uuid]
    if len(novas) == len(disciplinas):
        return False
    cfg["disciplinas"] = novas
    CONFIG_PATH.write_text(
        json.dumps(cfg, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return True


def disciplinas():
    """Lista de disciplinas configuradas (dicts com uuid/nome)."""
    cfg = carregar()
    return cfg.get("disciplinas", [])


def configurado():
    """True se ja existe email ou token salvos."""
    cfg = carregar()
    return bool(cfg.get("email") or cfg.get("token"))
