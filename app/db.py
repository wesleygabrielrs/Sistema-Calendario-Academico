"""Banco de dados SQLite do Calendario Academico UNINASSAU.

Guarda as materias e atividades extraidas do portal.
Upsert idempotente: ao sincronizar de novo, NAO duplica registros.
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "dados" / "calendario.db"


def conectar():
    """Abre uma conexao com o banco, retornando linhas como dicts."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Cria as tabelas caso ainda nao existam."""
    with conectar() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS materias (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                codigo TEXT,
                professor TEXT,
                url TEXT,
                UNIQUE(nome)
            );

            CREATE TABLE IF NOT EXISTS atividades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                materia_id INTEGER NOT NULL,
                titulo TEXT NOT NULL,
                tipo TEXT,
                data_inicio TEXT,
                data_fim TEXT,
                status TEXT,
                link TEXT,
                raw_json TEXT,
                UNIQUE(materia_id, titulo, data_fim),
                FOREIGN KEY (materia_id) REFERENCES materias(id) ON DELETE CASCADE
            );
            """)


def upsert_materia(nome, codigo="", professor="", url=""):
    """Grava uma materia e devolve o id. Se ja existe pelo nome, atualiza."""
    with conectar() as conn:
        conn.execute(
            """
            INSERT INTO materias (nome, codigo, professor, url)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(nome) DO UPDATE SET
                codigo = excluded.codigo,
                professor = excluded.professor,
                url = excluded.url
            """,
            (nome, codigo, professor, url),
        )
        row = conn.execute("SELECT id FROM materias WHERE nome = ?", (nome,)).fetchone()
        return row["id"]


def upsert_atividade(
    materia_id,
    titulo,
    tipo="",
    data_inicio="",
    data_fim="",
    status="",
    link="",
    raw_json="",
):
    """Grava uma atividade sem duplicar (materia + titulo + data de fim)."""
    with conectar() as conn:
        conn.execute(
            """
            INSERT INTO atividades
                (materia_id, titulo, tipo, data_inicio, data_fim, status, link, raw_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(materia_id, titulo, data_fim) DO UPDATE SET
                tipo = excluded.tipo,
                data_inicio = excluded.data_inicio,
                status = excluded.status,
                link = excluded.link,
                raw_json = excluded.raw_json
            """,
            (materia_id, titulo, tipo, data_inicio, data_fim, status, link, raw_json),
        )


def listar_atividades():
    """Lista atividades com o nome da materia (para o calendario)."""
    with conectar() as conn:
        rows = conn.execute("""
            SELECT a.id, a.titulo, a.tipo, a.data_inicio, a.data_fim,
                   a.status, a.link, a.raw_json, a.materia_id,
                   m.nome AS materia_nome
            FROM atividades a
            JOIN materias m ON m.id = a.materia_id
            ORDER BY a.data_fim
            """).fetchall()
        return [dict(r) for r in rows]


def resumo():
    """Contagem de materias e atividades no banco."""
    with conectar() as conn:
        materias = conn.execute("SELECT COUNT(*) FROM materias").fetchone()[0]
        atividades = conn.execute("SELECT COUNT(*) FROM atividades").fetchone()[0]
    return {"materias": materias, "atividades": atividades}
