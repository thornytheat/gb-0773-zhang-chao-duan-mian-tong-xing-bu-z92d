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
