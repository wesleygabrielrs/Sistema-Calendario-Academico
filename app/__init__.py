"""Pacote do Calendario Academico UNINASSAU.

``create_app()`` monta a aplicacao Flask, garante o banco de dados e
registra as rotas (definidas em ``routes.py``).
"""

from flask import Flask

from . import db, routes


def create_app():
    """Cria a aplicacao, garante o banco e registra as rotas."""
    app = Flask(__name__)
    db.init_db()
    routes.init_app(app)
    return app
