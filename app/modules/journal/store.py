import json
import sqlite3
from contextlib import closing, contextmanager
from pathlib import Path

from app.errors import TideError

from .manifest import canonical


class Journal:
    def __init__(self, path):
        self.path = path
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as connection:
            connection.execute('''CREATE TABLE IF NOT EXISTS journals (
                id TEXT PRIMARY KEY, created TEXT NOT NULL, receipt TEXT NOT NULL,
                inputs TEXT NOT NULL, reports TEXT NOT NULL)''')
            connection.execute('''CREATE TABLE IF NOT EXISTS roundtrips (
                run_id TEXT NOT NULL, vessel TEXT NOT NULL, plan_key TEXT NOT NULL,
                created TEXT NOT NULL, detail TEXT NOT NULL,
                PRIMARY KEY (run_id, vessel))''')

    @contextmanager
    def connection(self):
        with closing(sqlite3.connect(self.path, timeout=10)) as connection, connection:
            connection.execute('PRAGMA busy_timeout=10000')
            yield connection

    def publish(self, receipt, sources, reports):
        with self.connection() as connection:
            cursor = connection.execute('INSERT INTO journals VALUES (?, ?, ?, ?, ?) ON CONFLICT(id) DO NOTHING', (
                receipt['run_id'], receipt['started_at'], canonical(receipt), canonical(sources), canonical(reports)))
            return cursor.rowcount == 1

    def confirm_roundtrip(self, run_id, vessel, plan_key, created, detail):
        """同一船期只能确认一份；同安排重试幂等，异安排冲突 409。"""
        with self.connection() as connection:
            row = connection.execute(
                'SELECT plan_key, detail FROM roundtrips WHERE run_id=? AND vessel=?', (run_id, vessel)).fetchone()
            if row is not None:
                return dict(reused=True, conflict=row[0] != plan_key, plan_key=row[0],
                            detail=json.loads(row[1]))
            try:
                connection.execute(
                    'INSERT INTO roundtrips VALUES (?, ?, ?, ?, ?)',
                    (run_id, vessel, plan_key, created, canonical(detail)))
            except sqlite3.IntegrityError as exc:
                row = connection.execute(
                    'SELECT plan_key, detail FROM roundtrips WHERE run_id=? AND vessel=?',
                    (run_id, vessel)).fetchone()
                if row is None:
                    raise
                return dict(reused=True, conflict=row[0] != plan_key, plan_key=row[0],
                            detail=json.loads(row[1]))
            return dict(reused=False, conflict=False, plan_key=plan_key, detail=detail)

    def get_roundtrip(self, run_id, vessel):
        with self.connection() as connection:
            row = connection.execute(
                'SELECT plan_key, detail FROM roundtrips WHERE run_id=? AND vessel=?',
                (run_id, vessel)).fetchone()
        if row is None:
            return None
        return dict(plan_key=row[0], detail=json.loads(row[1]))

    def list_roundtrips(self, run_id):
        with self.connection() as connection:
            rows = connection.execute(
                'SELECT vessel, plan_key, detail FROM roundtrips WHERE run_id=? ORDER BY vessel',
                (run_id,)).fetchall()
        return [dict(vessel=row[0], plan_key=row[1], detail=json.loads(row[2])) for row in rows]

    def get(self, key):
        with self.connection() as connection:
            row = connection.execute('SELECT receipt, inputs, reports FROM journals WHERE id=?', (key,)).fetchone()
        if row is None:
            raise TideError('NO_RUN', '未找到这份运行簿', 404)
        return tuple(json.loads(value) for value in row)

    def list(self):
        with self.connection() as connection:
            rows = connection.execute('SELECT receipt FROM journals ORDER BY created DESC, id LIMIT 40').fetchall()
        return [json.loads(row[0]) for row in rows]
