from concurrent.futures import ThreadPoolExecutor

from app.main import create_app
from app.modules.journal.service import publish_run
from app.modules.roundtrip.confirm import confirm
from app.source import load_sources


def _post(client, plan, unloading_s=0, sample='dirty'):
    return client.post('/api/roundtrip/海棠17',
                       json={'sample': sample, 'unloading_s': unloading_s, 'plan': plan})


def test_confirm_creates_then_reuses_same_arrangement(client):
    first = _post(client, 'early', 1200)
    assert first.status_code == 201 and first.json['reused'] is False
    second = _post(client, 'early', 1200)
    assert second.status_code == 200 and second.json['reused'] is True
    assert second.json['plan_key'] == first.json['plan_key']
    assert second.json['run_id'] == first.json['run_id']


def test_different_arrangement_conflicts(client):
    _post(client, 'early', 0)
    clash = _post(client, 'late', 0)
    assert clash.status_code == 409 and clash.json['code'] == 'SCHEDULE_TAKEN'
    # 原确认仍然是 early
    run = client.get('/api/journal').json['runs'][0]['run_id']
    stored = client.get(f'/api/roundtrip/海棠17?run={run}').json['confirmation']
    assert stored['detail']['plan'] == 'early'


def test_no_return_window_refuses_confirmation(client):
    response = client.post('/api/roundtrip/江桐62',
                           json={'sample': 'dirty', 'unloading_s': 1000, 'plan': 'early'})
    assert response.status_code == 422 and response.json['code'] == 'NO_RETURN_WINDOW'
    # 被驳回的往返不产生确认留档；输入本身仍会幂等留运行簿
    run_id = client.get('/api/journal').json['runs'][0]['run_id']
    assert client.get(f'/api/journal/{run_id}/roundtrips').json['confirmations'] == []


def test_concurrent_different_arrangements_single_winner(tmp_path, sources):
    journal = create_app(tmp_path / 'race.db').extensions['tide_journal']

    def submit(plan):
        return confirm(journal, sources, '海棠17', 0, plan)

    with ThreadPoolExecutor(max_workers=4) as pool:
        outcomes = []
        futures = [pool.submit(submit, plan) for plan in ('early', 'late', 'early', 'late')]
        for future in futures:
            try:
                outcomes.append(('ok', future.result()))
            except Exception as exc:  # noqa: BLE001 - 冲突也是预期结果
                outcomes.append(('conflict', exc))
    winners = [out for kind, out in outcomes if kind == 'ok']
    conflicts = [kind for kind, _ in outcomes if kind == 'conflict']
    assert len(winners) == 2 and len(conflicts) == 2
    assert {row['plan'] for row in winners} == {'early'} or {row['plan'] for row in winners} == {'late'}
    assert len({row['plan_key'] for row in winners}) == 1
    archived = journal.list_roundtrips(winners[0]['run_id'])
    assert len(archived) == 1 and archived[0]['vessel'] == '海棠17'


def test_archive_holds_both_legs_evidence(client):
    response = _post(client, 'early', 1200)
    run_id = response.json['run_id']
    detail = response.json['detail']
    for leg_name in ('outbound', 'return_leg'):
        leg = detail[leg_name]
        assert leg['evidence'] and all(row['lines'] for row in leg['evidence'])
    listing = client.get(f'/api/journal/{run_id}/roundtrips')
    assert listing.status_code == 200
    assert listing.json['confirmations'][0]['plan_key'] == response.json['plan_key']


def test_confirmation_pairs_other_vessels_independently(client):
    first = _post(client, 'early', 0)
    second = client.post('/api/roundtrip/甬航05',
                         json={'sample': 'dirty', 'unloading_s': 0, 'plan': 'early'})
    assert second.status_code == 201
    assert first.json['run_id'] == second.json['run_id']
    listing = client.get(f'/api/journal/{first.json["run_id"]}/roundtrips').json['confirmations']
    assert {row['vessel'] for row in listing} == {'海棠17', '甬航05'}


def test_get_pairing_preview_requires_no_archive(client):
    response = client.get('/api/roundtrip/海棠17?unloading_s=1200')
    assert response.status_code == 200
    assert response.json['run_id'] is None and response.json['confirmation'] is None
    assert response.json['pairing']['plans']['early']['return_leg']['departure'] == '1795364400'
    assert client.get('/api/journal').json['runs'] == []


def test_rerun_same_sources_keeps_archive(client, sources):
    created = _post(client, 'early', 1200).json
    run_id, _, _, _ = publish_run(client.application.extensions['tide_journal'], sources)
    assert run_id == created['run_id']
    again = confirm(client.application.extensions['tide_journal'], sources, '海棠17', 1200, 'early')
    assert again['reused'] is True and again['plan_key'] == created['plan_key']


def test_plan_key_changes_with_times(client):
    from app.modules.roundtrip.confirm import plan_key
    first = _post(client, 'early', 600).json
    detail = first['detail']
    key_a = plan_key(first['run_id'], '海棠17', 600,
                     {'outbound': {'departure': detail['outbound']['departure']},
                      'return_leg': {'departure': detail['return_leg']['departure']}})
    key_b = plan_key(first['run_id'], '海棠17', 1200,
                     {'outbound': {'departure': detail['outbound']['departure']},
                      'return_leg': {'departure': '999'}})
    assert key_a == first['plan_key'] and key_b != key_a


def test_roundtrip_panel_renders_on_schedule_page(client):
    html = client.get('/?unloading_s=1200').get_data(as_text=True)
    assert '往返成对出发时刻' in html and '确认往返' in html
    assert '1795364400' not in html  # 页面显示 ISO 时刻而非裸秒
    assert '2026-11-22' in html
