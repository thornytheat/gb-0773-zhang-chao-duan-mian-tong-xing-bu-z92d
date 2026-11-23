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

    @contextmanager
    def connection(self):
        with closing(sqlite3.connect(self.path, timeout=10)) as connection, connection:
            yield connection

    def publish(self, receipt, sources, reports):
        with self.connection() as connection:
            cursor = connection.execute('INSERT INTO journals VALUES (?, ?, ?, ?, ?) ON CONFLICT(id) DO NOTHING', (
                receipt['run_id'], receipt['started_at'], canonical(receipt), canonical(sources), canonical(reports)))
            return cursor.rowcount == 1

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
