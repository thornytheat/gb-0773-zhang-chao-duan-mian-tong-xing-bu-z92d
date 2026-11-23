from fractions import Fraction
from itertools import pairwise

from .state import SectionClock, judgement


def route_windows(crossings):
    result = {}
    for key, rec in crossings.items():
        order = rec['order']
        left, right = order['start'], order['end']
        threshold = Fraction(order['threshold_m'])
        clocks = [SectionClock(name, section) for name, section in rec['sections'].items()]
        cuts = {left, right}
        cuts.update(cut for clock in clocks for cut in clock.boundaries() if left < cut < right)
        knots = sorted(cuts)
        boundary = {t: judgement(clocks, t, threshold) for t in knots[:-1]}
        pieces, windows, covered_knots = [], [], set()
        for start, end in pairwise(knots):
            band = judgement(clocks, Fraction(start + end, 2), threshold)
            pieces.append({**band, 'start': str(start), 'end': str(end), 'seconds': str(end - start)})
            if band['status'] != 'open':
                continue
            covered_knots.update((start, end))
            start_open = boundary[start]['status'] == 'open'
            end_open = end in boundary and boundary[end]['status'] == 'open'
            if windows and windows[-1]['end'] == str(start) and start_open:
                windows[-1].update(end=str(end), end_included=end_open)
            else:
                windows.append(dict(start=str(start), end=str(end), start_included=start_open, end_included=end_open))
        points = [point for time, point in boundary.items()
                  if point['status'] == 'open' and time not in covered_knots]
        result[key] = dict(order=order, pieces=pieces, windows=windows, isolated_points=points,
                           requested=judgement(clocks, order['requested'], threshold))
    return result
