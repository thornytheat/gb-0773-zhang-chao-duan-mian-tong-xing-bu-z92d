from flask import Blueprint, current_app, jsonify, request

from app.errors import TideError
from app.flow import STEPS, calculate
from app.modules.journal.service import record
from app.modules.proof.service import issue
from app.modules.roundtrip.confirm import confirm
from app.modules.roundtrip.service import pair_roundtrip
from app.source import load_sources

api = Blueprint('api', __name__, url_prefix='/api')


def journal():
    return current_app.extensions['tide_journal']


def _unloading(payload):
    value = payload.get('unloading_s', 900) if isinstance(payload, dict) else 900
    return value


def _roundtrip_context(payload, run_arg):
    """统一处理留档模式与临时计算模式的输入，返回 (sources, run_id, reports)。"""
    if run_arg:
        _, sources, reports = journal().get(run_arg)
        return sources, run_arg, reports
    if 'sources' in payload:
        sources = load_sources({'sources': payload['sources']})
    else:
        sources = load_sources({'sample': payload.get('sample', 'dirty')})
    return sources, None, calculate(sources)


@api.route('/stage/<stage>', methods=['GET', 'POST'])
def stage_result(stage):
    if stage not in STEPS:
        raise TideError('NO_STAGE', '找不到潮窗模块', 404)
    if 'run' in request.args and request.method == 'GET':
        _, _, reports = journal().get(request.args['run'])
    else:
        payload = request.get_json(silent=True) if request.method == 'POST' else {'sample': request.args.get('sample', 'dirty')}
        reports = calculate(load_sources(payload), stage)
    return jsonify(reports[stage])


@api.get('/journal')
def list_journal():
    return jsonify(runs=journal().list())


@api.post('/journal')
def publish_journal():
    result = record(journal(), load_sources(request.get_json(silent=True)))
    return jsonify(result), 200 if result['reused'] else 201


@api.get('/journal/<key>')
def inspect_journal(key):
    receipt, _, reports = journal().get(key)
    return jsonify(run_id=key, manifest=receipt, coverage=reports['coverage'])


@api.post('/journal/<key>/rerun')
def repeat_journal(key):
    manifest, sources, _ = journal().get(key)
    return jsonify(record(journal(), sources, manifest))


@api.get('/export/<key>')
def download(key):
    response = jsonify(issue(*journal().get(key)))
    response.headers['Content-Disposition'] = f'attachment; filename="tide-{key[:12]}.json"'
    return response


@api.route('/roundtrip/<vessel>', methods=['GET', 'POST'])
def roundtrip(vessel):
    payload = request.get_json(silent=True) if request.method == 'POST' else {}
    payload = payload if isinstance(payload, dict) else {}
    if 'unloading_s' not in payload and request.args.get('unloading_s') is not None:
        payload['unloading_s'] = request.args.get('unloading_s')
    run_arg = request.args.get('run') or payload.get('run')
    unloading_s = _unloading(payload)
    sources, run_id, reports = _roundtrip_context(payload, run_arg)
    paired = pair_roundtrip(reports['crossings'], reports['windows'], vessel, unloading_s)
    if request.method == 'GET':
        stored = journal().get_roundtrip(run_id, vessel) if run_id else None
        return jsonify(run_id=run_id, pairing=paired, confirmation=stored)
    plan_name = payload.get('plan', 'early')
    if plan_name not in ('early', 'late'):
        raise TideError('BAD_PLAN', '往返安排只能是 early 或 late')
    result = confirm(journal(), sources, vessel, unloading_s, plan_name, run_id)
    status = 200 if result['reused'] else 201
    return jsonify(result), status


@api.get('/journal/<key>/roundtrips')
def roundtrip_archive(key):
    journal().get(key)
    return jsonify(run_id=key, confirmations=journal().list_roundtrips(key))
