from app.flow import calculate
from app.modules.schedule.service import reconcile
from app.source import load_sources


def test_dirty_ship_total(case):
    assert case['coverage']['ships']['海棠17']['seconds']=={'open':'1500','blocked':'900','unknown':'600'}


def test_clean_ship_total():
    clean = calculate(load_sources({'sample':'clean'}))
    assert clean['coverage']['ships']['海棠17']['seconds']=={'open':'3000','blocked':'0','unknown':'0'}


def test_three_ships(case):
    assert len(case['coverage']['ships']) == 3
    assert case['coverage']['ships']['江桐62']['window_s'] == 2100


def test_requested_source_line(case):
    row = case['coverage']['ships']['甬航05']
    assert row['order_line'] == 3 and row['requested']['status']=='blocked'


def test_no_measured_deficit_imputed(case):
    row = case['coverage']['ships']['海棠17']
    assert row['delta_s']=='0' and row['balanced']


def test_discrepancy_surfaces(case):
    del case['windows']['海棠17']['pieces'][0]
    result = reconcile(case['windows'])
    assert not result['balanced'] and result['ships']['海棠17']['delta_s']=='300'
