from fractions import Fraction

from app.errors import TideError
from app.modules.passage.state import SectionClock, judgement


def _as_seconds(value):
    if isinstance(value, bool) or isinstance(value, float):
        raise TideError('BAD_UNLOAD', '卸货时长应为非负整数秒')
    try:
        seconds = int(value)
    except (TypeError, ValueError) as exc:
        raise TideError('BAD_UNLOAD', '卸货时长应为非负整数秒') from exc
    if seconds < 0 or str(seconds) != str(value).strip():
        raise TideError('BAD_UNLOAD', '卸货时长应为非负整数秒')
    return seconds


def _slots(route):
    """把连续区间和单点达标统一成按时刻排序的可行集合。"""
    slots = [dict(kind='window', start=Fraction(w['start']), end=Fraction(w['end']),
                  start_included=w['start_included'], end_included=w['end_included'])
             for w in route['windows']]
    slots.extend(dict(kind='point', start=point['at'], end=point['at'], at=point['at'])
                 for point in route['isolated_points'])
    return sorted(slots, key=lambda slot: Fraction(slot['start']))


def _contains(slot, when):
    if slot['kind'] == 'point':
        return when == Fraction(slot['at'])
    left_ok = when >= slot['start'] if slot['start_included'] else when > slot['start']
    right_ok = when < slot['end'] if not slot['end_included'] else when <= slot['end']
    return left_ok and right_ok


def _earliest_after(slots, not_before, hard_end):
    """不早于 not_before、且严格落在船期右端之前的最早可行出发时刻。"""
    if not_before >= hard_end:
        return None
    for slot in slots:
        if slot['kind'] == 'point':
            when = Fraction(slot['at'])
            if when >= not_before and when < hard_end:
                return when
            continue
        if slot['end'] < not_before or (slot['end'] == not_before and not slot['end_included']):
            continue
        if not_before <= slot['start'] or (not_before == slot['start'] and slot['start_included']):
            candidate = slot['start']
        elif _contains(slot, not_before):
            candidate = not_before
        else:
            continue
        if candidate < hard_end:
            return candidate
    return None


def _leg(clocks, when, threshold):
    verdict = judgement(clocks, when, threshold)
    return dict(departure=str(when), status=verdict['status'],
                evidence=[dict(section=row['section'], at=row['at'], depth_m=row['depth_m'],
                               code=row['code'], status=row['status'], lines=row['lines'])
                          for row in verdict['evidence']])


def pair_roundtrip(crossings, windows, vessel, unloading_s):
    """按卸货时长重算两程出发时刻；回程无窗则往返不成立。"""
    if vessel not in windows:
        raise TideError('NO_VESSEL', '找不到该船期', 404)
    unloading_s = _as_seconds(unloading_s)
    route = windows[vessel]
    order = route['order']
    start, end = Fraction(order['start']), Fraction(order['end'])
    threshold = Fraction(order['threshold_m'])
    clocks = [SectionClock(name, section) for name, section in crossings[vessel]['sections'].items()]
    slots = _slots(route)

    def build(outbound_when):
        return_when = _earliest_after(slots, outbound_when + unloading_s, end)
        if return_when is None:
            return None
        return dict(outbound=_leg(clocks, outbound_when, threshold),
                    return_leg=_leg(clocks, return_when, threshold),
                    unload_ready=str(outbound_when + unloading_s),
                    buffer_s=str(return_when - outbound_when - unloading_s))

    plans = {}
    early_when = _earliest_after(slots, start, end)
    if early_when is not None:
        early = build(early_when)
        if early is not None:
            plans['early'] = dict(plan='early', **early)
    for slot in reversed(slots):
        candidates = [Fraction(slot['at'])] if slot['kind'] == 'point' else [slot['start']]
        late = next((dict(plan='late', **candidate) for when in candidates
                     if (candidate := build(when)) is not None), None)
        if late is None:
            continue
        if 'early' not in plans or (late['outbound']['departure'] != plans['early']['outbound']['departure']
                                    or late['return_leg']['departure'] != plans['early']['return_leg']['departure']):
            plans['late'] = late
        break
    if not plans and early_when is None:
        reason = 'NO_OUTBOUND_WINDOW'
    else:
        reason = None if plans else 'NO_RETURN_WINDOW'
    return dict(vessel=vessel, unloading_s=unloading_s, feasible=bool(plans), reason=reason,
                plans=plans, schedule_start=str(start), schedule_end=str(end),
                threshold_m=str(threshold))
