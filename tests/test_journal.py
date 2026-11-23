from concurrent.futures import ThreadPoolExecutor

from app.main import create_app
from app.modules.journal.service import record
from app.modules.journal.store import Journal


def test_receipt(client):
    response = client.post('/api/journal',json={'sample':'dirty'})
    assert response.status_code == 201 and response.json['manifest']['rule_version']=='tide-1.0'


def test_replay(client):
    first=client.post('/api/journal',json={'sample':'dirty'}).json
    second=client.post(f"/api/journal/{first['run_id']}/rerun").json
    assert second == {**first,'reused':True}
    assert len(client.get('/api/journal').json['runs'])==1


def test_rollback(client,sources):
    sources['stations'] += 'duplicate\n'
    assert client.post('/api/journal',json={'sources':sources}).status_code==422
    assert client.get('/api/journal').json['runs']==[]


def test_concurrent(tmp_path,sources):
    journal=Journal(tmp_path/'overlap.db')
    with ThreadPoolExecutor(max_workers=4) as pool:
        results=list(pool.map(lambda _: record(journal,sources),range(4)))
    assert sum(not row['reused'] for row in results)==1
    assert len({r['run_id'] for r in results})==1


def test_reopen(tmp_path):
    path=tmp_path/'saved.db'
    first=create_app(path).test_client().post('/api/journal',json={'sample':'dirty'}).json
    second=create_app(path).test_client().get(f"/api/journal/{first['run_id']}").json
    assert second['manifest']==first['manifest']
    assert second['coverage']['ships']['海棠17']['seconds']['unknown']=='600'


def test_missing_run(client):
    result=client.post('/api/journal/absent/rerun')
    assert (result.status_code,result.json['code'])==(404,'NO_RUN')
