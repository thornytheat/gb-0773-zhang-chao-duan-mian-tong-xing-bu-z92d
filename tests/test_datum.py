from app.clock import moment
from app.flow import calculate


def test_timezone_repeat(case):  # TRAP-11
    assert case['datum']['reasons']['DUPLICATE'] == 1
    assert moment('2026-11-22T23:50:00+08:00') == moment('2026-11-22T15:50:00Z')


def test_normalize_unit(case):  # TRAP-15
    fallback = next(p for p in case['datum']['sections']['上游外闸']['points'] if p['station'] == 'U2')
    assert (fallback['raw']['level'], fallback['raw']['unit'], fallback['water_m'], fallback['depth_m']) == ('180', 'cm', '2', '3')


def test_conflicting_station(case):  # TRAP-14
    assert [row['line'] for row in case['datum']['rejected'] if row['code']=='CONFLICT'] == [5, 16]


def test_station_priority(case, sources):  # TRAP-19
    lines = sources['stations'].splitlines()
    sources['stations'] = '\n'.join([lines[0], *reversed(lines[1:])])
    other = calculate(sources, 'datum')['datum']
    assert other['reasons'] == case['datum']['reasons']
    points = other['sections']['上游外闸']['points']
    assert [row['station'] for row in points] == ['U1','U1','U1','U2','U1']


def test_sensor_flags(case):
    assert case['datum']['accepted'] == 11
    assert case['datum']['reasons']['SENSOR_BAD'] == 2


def test_bad_catalog(client, sources):
    sources['stations'] += 'U1,上游外闸,0,-1,1,0,600\n'
    result = client.post('/api/stage/datum', json={'sources': sources})
    assert (result.status_code, result.json['code']) == (422, 'BAD_STATIONS')
