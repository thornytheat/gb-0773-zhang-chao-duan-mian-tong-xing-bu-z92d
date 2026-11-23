import pytest

from app.errors import TideError
from app.modules.intake.contract import OBSERVATION
from app.modules.intake.readings import scan


def test_bom(case):  # TRAP-02
    assert case['readings']['tables']['observations'][0]['raw']['station'] == 'U1'


def test_repeated_header(case):  # TRAP-04
    assert case['readings']['files'][0]['segments'] == 2
    assert case['readings']['files'][0]['blanks'] == 1


def test_wrong_width(case):  # TRAP-05
    issue = next(row for row in case['readings']['rejected'] if row['code'] == 'COLUMN_COUNT')
    assert issue['line'] == 20 and issue['raw'][-1] == '多余'


def test_sentinel(case):  # TRAP-07
    assert case['readings']['rejected'][0]['raw']['level'] == 'N/A'
    assert case['readings']['rejected'][0]['code'] == 'EMPTY_FIELD'


def test_counts(case):
    assert case['readings']['files'][0]['records'] == 20
    assert case['readings']['files'][0]['accepted'] == 18


def test_empty_state():
    for text, code in (('', 'EMPTY_FILE'), ('\n\n', 'BLANK_FILE'), (','.join(OBSERVATION), 'HEADER_ONLY')):
        with pytest.raises(TideError) as error:
            scan(text, OBSERVATION, '潮尺')
        assert error.value.code == code


def test_unclosed_field():
    with pytest.raises(TideError) as error:
        scan(','.join(OBSERVATION) + '\n"unterminated', OBSERVATION, '潮尺')
    assert error.value.code == 'BAD_CSV'
