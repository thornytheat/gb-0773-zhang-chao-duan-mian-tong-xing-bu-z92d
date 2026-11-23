from fractions import Fraction

from flask import Blueprint, render_template, request

from app.api import journal
from app.clock import instant
from app.config import RULES
from app.errors import TideError
from app.flow import calculate
from app.modules.journal.service import record
from app.modules.proof.service import issue
from app.modules.roundtrip.service import pair_roundtrip
from app.reasons import REASONS
from app.source import load_sources

web = Blueprint('tide_desk', __name__)
CHAPTERS = {'coverage': '船期覆盖勾稽', 'readings': '潮尺读数采信', 'datum': '站点基准统一',
            'crossings': '水位阈值交点', 'windows': '全程可行潮窗', 'journal': '运行留档', 'proof': '潮窗证据签发'}
STATES = {'open': '可行', 'blocked': '不可行', 'unknown': '缺证'}
DEFAULT_UNLOAD_S = 900


@web.get('/')
@web.get('/desk/<chapter>')
def desk(chapter='coverage'):
    if chapter not in CHAPTERS:
        raise TideError('NO_STAGE', '找不到潮窗模块', 404)
    sample = request.args.get('sample', 'dirty')
    key = request.args.get('run')
    if key or chapter in ('journal', 'proof'):
        key = key or record(journal(), load_sources({'sample': sample}))['run_id']
        receipt, sources, reports = journal().get(key)
    else:
        sources = load_sources({'sample': sample})
        reports = calculate(sources)
        receipt = None
    vessel = request.args.get('vessel', next(iter(reports['coverage']['ships'])))
    if vessel not in reports['coverage']['ships']:
        raise TideError('NO_VESSEL', '找不到该船期', 404)
    proof = issue(receipt, sources, reports) if chapter == 'proof' else None
    try:
        unloading_s = int(request.args.get('unloading_s', DEFAULT_UNLOAD_S))
        if unloading_s < 0:
            raise ValueError
    except (TypeError, ValueError):
        unloading_s = DEFAULT_UNLOAD_S
    pairing = pair_roundtrip(reports['crossings'], reports['windows'], vessel, unloading_s)
    confirmation = journal().get_roundtrip(key, vessel) if key else None
    return render_template('base.html', chapter=chapter, chapters=CHAPTERS, states=STATES, sample=sample,
                           receipt=receipt, key=key, reports=reports, vessel=vessel, reason=REASONS,
                           gauge_fill=min(100, float(Fraction(reports['windows'][vessel]['order']['threshold_m'])) * 25),
                           seal=proof['seal_sha256'] if proof else None, time=instant, rule=RULES,
                           pairing=pairing, confirmation=confirmation, unloading_s=unloading_s,
                           history=journal().list() if chapter == 'journal' else [])
