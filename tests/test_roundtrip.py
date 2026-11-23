import pytest

from app.clock import instant
from app.flow import calculate
from app.modules.roundtrip.confirm import confirm, plan_key
from app.modules.roundtrip.service import pair_roundtrip
from app.source import load_sources


@pytest.fixture
def dirty(sources):
    return calculate(sources)


def test_paired_departures_are_feasible_windows(dirty):
    paired = pair_roundtrip(dirty['crossings'], dirty['windows'], '海棠17', 1200)
    assert paired['feasible'] and set(paired['plans']) == {'early'}
    plan = paired['plans']['early']
    assert plan['outbound']['departure'] == '1795362300'
    assert plan['return_leg']['departure'] == '1795364400'
    # 回程出发不早于去程出发 + 卸货时长
    assert int(plan['unload_ready']) == 1795362300 + 1200
    assert int(plan['return_leg']['departure']) >= int(plan['unload_ready'])


def test_unloading_change_recomputes(dirty):
    short = pair_roundtrip(dirty['crossings'], dirty['windows'], '海棠17', 600)
    long = pair_roundtrip(dirty['crossings'], dirty['windows'], '海棠17', 1200)
    assert short['plans']['early']['return_leg']['departure'] == '1795362900'
    assert long['plans']['early']['return_leg']['departure'] == '1795364400'


def test_two_plans_when_both_fit(dirty):
    paired = pair_roundtrip(dirty['crossings'], dirty['windows'], '海棠17', 0)
    assert set(paired['plans']) == {'early', 'late'}
    early, late = paired['plans']['early'], paired['plans']['late']
    assert early['outbound']['departure'] == '1795362300'
    assert late['outbound']['departure'] == '1795364400'
    # 晚走给卸货留的时间不少于早走
    assert int(late['outbound']['departure']) > int(early['outbound']['departure'])


def test_no_return_window_not_feasible(dirty):
    paired = pair_roundtrip(dirty['crossings'], dirty['windows'], '江桐62', 1000)
    assert not paired['feasible'] and paired['reason'] == 'NO_RETURN_WINDOW'
    assert paired['plans'] == {}


def test_return_respects_schedule_half_open_end(dirty):
    # 卸货就绪恰落在船期右端时，右端不可用 -> 无回程
    route = dirty['windows']['甬航05']
    end = int(route['order']['end'])
    paired = pair_roundtrip(dirty['crossings'], dirty['windows'], '甬航05',
                            end - int(route['windows'][0]['start']))
    assert not paired['feasible'] and paired['reason'] == 'NO_RETURN_WINDOW'


def test_each_leg_keeps_tide_ruler_lines(dirty):
    plan = pair_roundtrip(dirty['crossings'], dirty['windows'], '海棠17', 1200)['plans']['early']
    for leg in (plan['outbound'], plan['return_leg']):
        assert leg['status'] == 'open'
        assert all(evidence['lines'] for evidence in leg['evidence'])
        assert {evidence['section'] for evidence in leg['evidence']} == {'上游外闸', '下游浅滩'}


def test_bad_unloading_rejected(dirty):
    from app.errors import TideError
    for value in (-1, '12.5', None, True, 12.5):
        with pytest.raises(TideError) as exc:
            pair_roundtrip(dirty['crossings'], dirty['windows'], '海棠17', value)
        assert exc.value.code == 'BAD_UNLOAD'


def test_clean_sample_single_window_pairing():
    reports = calculate(load_sources({'sample': 'clean'}))
    paired = pair_roundtrip(reports['crossings'], reports['windows'], '海棠17', 900)
    plan = paired['plans']['early']
    assert plan['outbound']['departure'] == str(reports['windows']['海棠17']['order']['start'])
    assert int(plan['return_leg']['departure']) == int(plan['outbound']['departure']) + 900
    assert plan['buffer_s'] == '0'


def test_unknown_vessel(dirty):
    from app.errors import TideError
    with pytest.raises(TideError) as exc:
        pair_roundtrip(dirty['crossings'], dirty['windows'], '幽灵船', 600)
    assert exc.value.status == 404


def test_isolated_point_roundtrip():
    points = [dict(time=t, depth_m=str(v), line=t + 2) for t, v in [(0, 1), (1, 2), (2, 1)]]
    bands = [dict(start=t, end=t + 1, depths_m=[points[t]['depth_m'], points[t + 1]['depth_m']],
                  code='LINEAR', crossing=None, lines=[t + 2, t + 3]) for t in (0, 1)]
    section = dict(offset_s=0, points=points, bands=bands)
    crossings = {'one': dict(order=dict(start=0, end=20, requested=10, threshold_m='2'),
                             sections={'闸': section})}
    windows = {'one': dict(order=crossings['one']['order'], windows=[],
                           isolated_points=[dict(at='10', status='open', evidence=[])],
                           pieces=[], requested={})}
    same = pair_roundtrip(crossings, windows, 'one', 0)
    assert same['feasible'] and list(same['plans']) == ['early']
    assert same['plans']['early']['outbound']['departure'] == '10'
    spaced = pair_roundtrip(crossings, windows, 'one', 1)
    assert not spaced['feasible'] and spaced['reason'] == 'NO_RETURN_WINDOW'


def test_iso_times_render():
    assert instant('1795362300').startswith('2026-11-22T15:45:00')
