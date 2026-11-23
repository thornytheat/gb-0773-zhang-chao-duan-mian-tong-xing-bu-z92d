from app.clock import depth
from app.errors import TideError


def catalog(rows, rejected):
    if any(row['source'] == 'stations' for row in rejected):
        raise TideError('BAD_STATIONS', '测站定义有隔离行')
    stations, sections = {}, {}
    for row in rows:
        raw = row['raw']
        key, section = raw['station'].strip(), raw['section'].strip()
        try:
            datum, bed = depth(raw['datum_m']), depth(raw['bed_m'])
            priority, offset, gap = (int(raw[name]) for name in ('priority', 'offset_s', 'gap_s'))
            if key in stations or priority < 1 or not 0 <= offset <= 86400 or not 0 < gap <= 86400:
                raise ValueError()
            spec = (bed, offset, gap)
            if section in sections and sections[section] != spec:
                raise ValueError()
        except ValueError as exc:
            raise TideError('BAD_STATIONS', f'测站定义第 {row["line"]} 行冲突或越界') from exc
        sections[section] = spec
        stations[key] = {'section': section, 'datum_m': str(datum), 'bed_m': str(bed),
                         'priority': priority, 'offset_s': offset, 'gap_s': gap, 'line': row['line']}
    return stations
