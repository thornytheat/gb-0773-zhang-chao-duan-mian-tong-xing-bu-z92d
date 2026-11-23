from collections import defaultdict
from fractions import Fraction

from app.clock import depth, moment

UNIT = {'m': Fraction(1), 'cm': Fraction(1, 100), 'mm': Fraction(1, 1000)}


def translate(row, stations):
    raw = row['raw']
    station = raw['station'].strip()
    if station not in stations:
        return 'NO_STATION', None
    definition = stations[station]
    try:
        at = moment(raw['observed_at'])
        ruler = depth(raw['level']) * UNIT[raw['unit'].strip()]
        quality = raw['quality'].strip().upper()
        if quality not in {'OK', 'BAD'}:
            raise ValueError()
    except (ValueError, KeyError, OverflowError):
        return 'BAD_READING', None
    if quality == 'BAD':
        return 'SENSOR_BAD', None
    water = ruler + Fraction(definition['datum_m'])
    return None, {**row, 'station': station, 'section': definition['section'], 'time': at,
                  'water_m': str(water), 'depth_m': str(water - Fraction(definition['bed_m'])),
                  'definition_line': definition['line'], 'priority': definition['priority']}


def choose(candidates, reject):
    by_station, by_section = defaultdict(list), defaultdict(list)
    for point in candidates:
        by_station[point['station'], point['time']].append(point)
    for points in by_station.values():
        if len({p['depth_m'] for p in points}) > 1:
            for point in points:
                reject(point, 'CONFLICT')
            continue
        first, *copies = sorted(points, key=lambda p: p['line'])
        for point in copies:
            reject(point, 'DUPLICATE')
        by_section[first['section'], first['time']].append(first)
    chosen = defaultdict(list)
    for (section, _), points in sorted(by_section.items()):
        ordered = sorted(points, key=lambda p: (p['priority'], p['station']))
        best_priority = ordered[0]['priority']
        best = [point for point in ordered if point['priority'] == best_priority]
        if len({point['depth_m'] for point in best}) > 1:
            for point in ordered:
                reject(point, 'CONFLICT')
            continue
        winner, *others = ordered
        chosen[section].append(winner)
        for point in others:
            reject(point, 'SHADOWED')
    return chosen
