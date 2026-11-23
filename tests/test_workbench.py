def test_all_chapters(client):
    expected={'/':'断面水位刻线','/desk/readings':'潮尺隔离记录','/desk/datum':'孪站裁决',
              '/desk/crossings':'阈值交点','/desk/windows':'连续放行区间',
              '/desk/journal':'归档目录','/desk/proof':'潮窗验签'}
    for path,text in expected.items():
        result=client.get(path)
        assert result.status_code==200 and text in result.get_data(as_text=True)


def test_clean_scope(client):
    response=client.get('/desk/coverage?sample=clean')
    assert '3000 s' in response.get_data(as_text=True)


def test_source_error(client):
    response=client.get('/api/stage/windows?sample=missing')
    assert (response.status_code,response.json['code']) == (404,'NO_SAMPLE')


def test_roundtrip_panel_and_confirmation_state(client):
    page = client.get('/?vessel=海棠17&unloading_s=1200').get_data(as_text=True)
    assert '往返成对出发时刻' in page and '早走腾位' in page
    assert '2026-11-22T15:45:00Z' in page
    confirmed = client.post('/api/roundtrip/海棠17',
                            json={'sample': 'dirty', 'unloading_s': 0, 'plan': 'early'}).json
    url = f"/?run={confirmed['run_id']}&vessel=海棠17&unloading_s=0"
    html = client.get(url).get_data(as_text=True)
    assert '本船期已确认' in html and '已确认' in html
    assert 'disabled' in html  # 另一套安排不可再确认


def test_roundtrip_no_window_banner(client):
    html = client.get('/?vessel=江桐62&unloading_s=1000').get_data(as_text=True)
    assert '往返不予确认' in html
