from fractions import Fraction
from itertools import pairwise


def interpolate(points, gap, threshold):
    bands = []
    for left, right in pairwise(points):
        start, end = left['time'], right['time']
        a, b = Fraction(left['depth_m']), Fraction(right['depth_m'])
        band = dict(start=start, end=end, lines=[left['line'], right['line']], depths_m=[str(a), str(b)])
        if end - start > gap:
            bands.append({**band, 'code': 'OVER_GAP', 'crossing': None})
            continue
        crossing = start + (end - start) * (threshold - a) / (b - a) if min(a, b) < threshold < max(a, b) else None
        bands.append({**band, 'code': 'LINEAR', 'crossing': str(crossing) if crossing is not None else None})
    return bands
