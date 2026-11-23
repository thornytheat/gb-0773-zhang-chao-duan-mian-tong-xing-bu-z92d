from datetime import UTC, datetime
from time import perf_counter_ns

from app.errors import TideError
from app.flow import calculate

from .manifest import manifest


def record(journal, sources, previous=None):
    started = datetime.now(UTC).isoformat(timespec='seconds')
    clock = perf_counter_ns()
    reports = calculate(sources)
    receipt = manifest(sources, reports, started, (perf_counter_ns() - clock) // 1_000_000)
    if previous is not None and (receipt['run_id'] != previous['run_id'] or
                                 receipt['result_sha256'] != previous['result_sha256']):
        raise TideError('REPLAY_CHANGED', '规则或结论变化，原簿保留', 409)
    created = journal.publish(receipt, sources, reports)
    stored, _, _ = journal.get(receipt['run_id'])
    if stored['result_sha256'] != receipt['result_sha256']:
        raise TideError('REPLAY_CHANGED', '同一输入复算不一致', 409)
    return {'run_id': stored['run_id'], 'manifest': stored, 'reused': not created}
