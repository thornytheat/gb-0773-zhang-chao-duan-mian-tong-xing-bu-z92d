from datetime import UTC, datetime

from app.errors import TideError
from app.modules.journal.manifest import canonical, digest
from app.modules.journal.service import publish_run

from .service import pair_roundtrip


def plan_key(run_id, vessel, unloading_s, plan):
    """同一安排的确定性指纹：同源、同船、同卸货时长、同两程时刻。"""
    payload = [run_id, vessel, unloading_s, plan['outbound']['departure'],
               plan['return_leg']['departure']]
    return digest(canonical(payload))


def confirm(journal, sources, vessel, unloading_s, plan_name, previous_run_id=None):
    run_id, _, _, reports = publish_run(journal, sources)
    if previous_run_id is not None and previous_run_id != run_id:
        raise TideError('RUN_MISMATCH', '原件与该运行簿不一致', 422)
    paired = pair_roundtrip(reports['crossings'], reports['windows'], vessel, unloading_s)
    if not paired['feasible']:
        raise TideError('NO_RETURN_WINDOW', '回程无可行潮窗，不确认往返', 422)
    if plan_name not in paired['plans']:
        raise TideError('BAD_PLAN', '该往返安排不可行，无法确认', 422)
    plan = paired['plans'][plan_name]
    key = plan_key(run_id, vessel, paired['unloading_s'], plan)
    detail = dict(run_id=run_id, vessel=vessel, plan=plan_name, plan_key=key,
                  unloading_s=paired['unloading_s'],
                  confirmed_at=datetime.now(UTC).isoformat(timespec='seconds'),
                  outbound=plan['outbound'], return_leg=plan['return_leg'],
                  unload_ready=plan['unload_ready'], buffer_s=plan['buffer_s'])
    outcome = journal.confirm_roundtrip(run_id, vessel, key, detail['confirmed_at'], detail)
    if outcome['conflict']:
        raise TideError('SCHEDULE_TAKEN', '该船期已确认另一份往返安排', 409)
    return dict(run_id=run_id, vessel=vessel, plan=plan_name, plan_key=outcome['plan_key'],
                reused=outcome['reused'], detail=outcome['detail'], pairing=paired)
