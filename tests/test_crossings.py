from fractions import Fraction

from app.clock import moment
from app.modules.crossings.interpolate import interpolate


def test_exact_fraction():  # TRAP-10
    points = [{'time': 0, 'depth_m':'0.1', 'line':2}, {'time':1, 'depth_m':'0.4','line':3}]
    assert interpolate(points, 1, Fraction('0.2'))[0]['crossing']=='1/3'


def test_rising_crossing(case):
    band = case['crossings']['海棠17']['sections']['上游外闸']['bands'][0]
    assert band['crossing'] == str(moment('2026-11-22T23:45:00+08:00'))


def test_falling_crossing(case):
    band = case['crossings']['海棠17']['sections']['下游浅滩']['bands'][2]
    assert band['crossing'] == str(moment('2026-11-23T00:15:00+08:00'))


def test_maximum_gap(case):
    assert [b['code'] for b in case['crossings']['海棠17']['sections']['上游外闸']['bands']] == ['LINEAR','LINEAR','OVER_GAP','LINEAR']


def test_equal_endpoint(case):
    band = case['crossings']['甬航05']['sections']['下游浅滩']['bands'][0]
    assert band['depths_m'][1] == '13/5' and band['crossing'] is None


def test_rejected_vessel(client, sources):
    sources['vessels'] = sources['vessels'].replace('2.3,0.2','0,0.2',1)
    response = client.post('/api/stage/crossings', json={'sources':sources})
    assert (response.status_code, response.json['code']) == (422,'BAD_VESSELS')
