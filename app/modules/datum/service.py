from collections import Counter

from .catalog import catalog
from .resolve import choose, translate


def normalize(intake):
    stations = catalog(intake['tables']['stations'], intake['rejected'])
    rejected, candidates = [], []

    def reject(row, code):
        rejected.append(dict(source='observations', line=row['line'], raw=row['raw'], code=code))

    for row in intake['tables']['observations']:
        error, point = translate(row, stations)
        if error:
            reject(row, error)
        else:
            candidates.append(point)
    chosen = choose(candidates, reject)
    sections = {}
    for station in stations.values():
        name = station['section']
        sections[name] = dict(offset_s=station['offset_s'], gap_s=station['gap_s'], points=chosen.get(name, []))
    return {'stations': stations, 'sections': sections, 'rejected': sorted(rejected, key=lambda r: r['line']),
            'reasons': dict(Counter(row['code'] for row in rejected)),
            'accepted': sum(len(section['points']) for section in sections.values())}
