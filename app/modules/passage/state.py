from bisect import bisect_left
from fractions import Fraction


class SectionClock:
    def __init__(self, name, section):
        self.name, self.offset = name, section['offset_s']
        self.points, self.bands = section['points'], section['bands']
        self.times = [point['time'] for point in self.points]

    def boundaries(self):
        yield from (time - self.offset for time in self.times)
        yield from (Fraction(band['crossing']) - self.offset for band in self.bands if band['crossing'] is not None)

    def at(self, departure, threshold):
        time = departure + self.offset
        index = bisect_left(self.times, time)
        detail = {'section': self.name, 'at': str(time), 'depth_m': None, 'lines': []}
        if index < len(self.times) and self.times[index] == time:
            point = self.points[index]
            value = Fraction(point['depth_m'])
            detail['lines'] = [point['line']]
        elif not 0 < index < len(self.times):
            return {**detail, 'code': 'NO_BRACKET', 'status': 'unknown'}
        else:
            band = self.bands[index - 1]
            detail['lines'] = band['lines']
            if band['code'] == 'OVER_GAP':
                return {**detail, 'code': 'OVER_GAP', 'status': 'unknown'}
            start, end = band['start'], band['end']
            left, right = map(Fraction, band['depths_m'])
            value = left + (right - left) * Fraction(time - start, end - start)
        status = 'open' if value >= threshold else 'blocked'
        return {**detail, 'depth_m': str(value), 'status': status,
                'code': 'DEPTH_OK' if status == 'open' else 'UNDER_DEPTH'}


def judgement(clocks, when, threshold):
    evidence = [clock.at(when, threshold) for clock in clocks]
    states = {row['status'] for row in evidence}
    status = next((state for state in ('blocked', 'unknown') if state in states), 'open')
    return {'at': str(when), 'status': status, 'evidence': evidence}
