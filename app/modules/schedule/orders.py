from app.clock import depth, moment
from app.errors import TideError


def orders(accepted):
    if any(row['source'] == 'vessels' for row in accepted['rejected']):
        raise TideError('BAD_VESSELS', '船期表有隔离行')
    planned = {}
    for record in accepted['tables']['vessels']:
        row = record['raw']
        vessel = row['vessel'].strip()
        try:
            draft, clearance = (depth(row[key]) for key in ('draft_m', 'clearance_m'))
            start, end, requested = (moment(row[key]) for key in ('start', 'end', 'requested'))
            if vessel in planned or draft <= 0 or clearance < 0 or end - start > 7 * 86400 or not start <= requested < end:
                raise ValueError()
        except (ValueError, OverflowError) as exc:
            raise TideError('BAD_VESSELS', f'船期第 {record["line"]} 行定义错误') from exc
        planned[vessel] = dict(vessel=vessel, line=record['line'], draft_m=str(draft), clearance_m=str(clearance),
                               threshold_m=str(draft + clearance), start=start, end=end, requested=requested)
    return planned
