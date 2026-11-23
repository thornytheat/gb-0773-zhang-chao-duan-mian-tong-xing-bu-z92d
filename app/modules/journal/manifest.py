import hashlib
import json

from app.config import RULES


def canonical(data):
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


def manifest(sources, reports, started, elapsed_ms):
    inputs = {name: digest(content) for name, content in sources.items()}
    run_id = digest(canonical([RULES, inputs]))
    return dict(run_id=run_id, inputs=inputs, rule_version=RULES, result_sha256=digest(canonical(reports)),
                started_at=started, elapsed_ms=elapsed_ms)
