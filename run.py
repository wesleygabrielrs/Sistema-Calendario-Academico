"""Entrada do Calendario Academico UNINASSAU.

Cria a aplicacao Flask (app/create_app) e sobe o servidor local.

Rodar com: python run.py
Abre em:    http://127.0.0.1:5000/
"""

from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False, threaded=True)
