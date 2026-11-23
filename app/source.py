from app.config import SAMPLE_ROOT, SOURCE_LIMIT
from app.errors import TideError
from app.modules.intake.contract import HEADERS


def load_sources(payload):
    if not isinstance(payload, dict):
        raise TideError('BAD_SOURCE', '请选择样例或提交三份潮汐资料')
    if set(payload) == {'sample'}:
        sample = payload['sample']
        if sample not in ('dirty', 'clean'):
            raise TideError('NO_SAMPLE', '找不到样例簿', 404)
        return {name: (SAMPLE_ROOT / sample / f'{name}.csv').read_bytes().decode() for name in HEADERS}
    sources = payload.get('sources')
    if set(payload) != {'sources'} or not isinstance(sources, dict) or set(sources) != set(HEADERS):
        raise TideError('BAD_SOURCE', '请提交潮尺、站点及船期 CSV')
    if any(not isinstance(text, str) for text in sources.values()):
        raise TideError('BAD_SOURCE', 'CSV 内容应为字符串')
    try:
        if any(len(text.encode('utf-8')) > SOURCE_LIMIT for text in sources.values()):
            raise TideError('TOO_LARGE', '单份资料超过 256 KB', 413)
    except UnicodeEncodeError as exc:
        raise TideError('BAD_SOURCE', 'CSV 内容含非法字符') from exc
    return sources
