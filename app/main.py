import os

from flask import Flask, jsonify

from app.api import api
from app.config import PORT
from app.errors import TideError
from app.modules.journal.store import Journal
from app.web import web


def create_app(database=None):
    app = Flask(__name__)
    app.config['MAX_CONTENT_LENGTH'] = 2_000_000
    app.extensions['tide_journal'] = Journal(database or os.environ.get('TIDE_DB', 'var/tide.sqlite3'))
    app.register_blueprint(api)
    app.register_blueprint(web)
    app.errorhandler(TideError)(lambda error: (jsonify(code=error.code, message=str(error)), error.status))
    app.errorhandler(413)(lambda _: (jsonify(code='TOO_LARGE', message='上传体积超限'), 413))
    app.add_url_rule('/health', view_func=lambda: jsonify(status='ok'))
    return app


if __name__ == '__main__':
    create_app().run(host='127.0.0.1', port=PORT)
