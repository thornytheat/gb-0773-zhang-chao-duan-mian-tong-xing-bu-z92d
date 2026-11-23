from collections import Counter

from .contract import HEADERS, SENTINELS
from .readings import scan


def intake(inputs):
    tables, rejected, files = {}, [], []
    for name, header in HEADERS.items():
        rows, malformed, segments, blanks = scan(inputs[name], header, name)
        clean = []
        for record in rows:
            raw = record['raw']
            if any(value.strip().upper() in SENTINELS for value in raw.values()):
                malformed.append({**record, 'source': name, 'code': 'EMPTY_FIELD'})
            else:
                clean.append(record)
        rejected.extend(sorted(malformed, key=lambda row: row['line']))
        tables[name] = clean
        files.append(dict(source=name, records=len(rows) + len([r for r in malformed if r['code'] == 'COLUMN_COUNT']),
                          accepted=len(clean), rejected=len(malformed), segments=segments, blanks=blanks))
    return {'files': files, 'tables': tables, 'rejected': rejected,
            'reasons': dict(Counter(row['code'] for row in rejected))}
