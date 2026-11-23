from app.clock import moment
from app.modules.passage.service import route_windows


def test_midnight_window(case):
    window = case['windows']['海棠17']['windows'][0]
    assert window == dict(start='1795362300',end='1795363200',start_included=True,end_included=True)
    assert window['end'] == str(moment('2026-11-23T00:00:00+08:00'))


def test_half_open_end(case):  # TRAP-23
    final = case['windows']['海棠17']['windows'][1]
    assert final['end'] == str(moment('2026-11-23T00:30:00+08:00'))
    assert final['end_included'] is False


def test_equal_threshold(case):
    request = case['windows']['海棠17']['requested']
    assert request['status']=='open' and request['evidence'][0]['depth_m']=='5/2'


def test_no_interpolation_across_gap(case):
    pieces = case['windows']['海棠17']['pieces']
    assert sum(int(p['seconds']) for p in pieces if p['status']=='unknown') == 600


def test_blocked_precedence(case):
    evidence = case['windows']['江桐62']['requested']['evidence']
    assert {row['status'] for row in evidence} == {'unknown','blocked'}
    assert case['windows']['江桐62']['requested']['status']=='blocked'


def test_single_instant():
    points = [dict(time=t,depth_m=str(v),line=t+2) for t,v in [(0,1),(1,2),(2,1)]]
    bands = [dict(start=t,end=t+1,depths_m=[points[t]['depth_m'],points[t+1]['depth_m']],code='LINEAR',crossing=None,lines=[t+2,t+3]) for t in (0,1)]
    out = route_windows({'one':dict(order=dict(start=0,end=2,requested=1,threshold_m='2'),sections={'闸':dict(offset_s=0,points=points,bands=bands)})})['one']
    assert out['windows']==[] and [p['at'] for p in out['isolated_points']]==['1']
