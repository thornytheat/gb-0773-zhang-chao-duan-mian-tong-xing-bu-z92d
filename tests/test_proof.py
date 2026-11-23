import pytest

from app.errors import TideError
from app.modules.journal.manifest import manifest
from app.modules.proof.service import issue
from app.modules.proof.signature import verifies


@pytest.fixture
def receipt(case,sources):
    return manifest(sources,case,'2026-11-22T00:00:00Z',1)


def test_signoff(case,sources,receipt):
    output=issue(receipt,sources,case)
    digest=output.pop('seal_sha256')
    output.pop('verified')
    assert verifies(output,digest)


def test_corrupt_source(case,sources,receipt):
    sources['vessels']+='\n'
    with pytest.raises(TideError) as error:
        issue(receipt,sources,case)
    assert error.value.code=='INVALID_PROOF'


def test_corrupt_report(case,sources,receipt):
    case['coverage']['balanced']=False
    with pytest.raises(TideError) as error:
        issue(receipt,sources,case)
    assert error.value.status==409


def test_originals_preserved(case,sources,receipt):
    assert issue(receipt,sources,case)['originals']['observations'].startswith('\ufeffstation')


def test_attached_evidence(client):
    key=client.post('/api/journal',json={'sample':'dirty'}).json['run_id']
    response=client.get(f'/api/export/{key}')
    assert response.headers['Content-Disposition'].startswith('attachment;')
    assert response.json['reports']['datum']['reasons']['CONFLICT']==2


def test_missing_export(client):
    response=client.get('/api/export/missing')
    assert (response.status_code,response.json['code'])==(404,'NO_RUN')
