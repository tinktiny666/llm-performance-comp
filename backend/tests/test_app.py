import io
import json
import os
import tempfile
import shutil
import pytest
from backend import app as app_module
from backend.app import app

@pytest.fixture(autouse=True)
def isolate_env(tmp_path, monkeypatch):
    # point DATA_DIR and VERSIONS_FILE to tmp dir
    tmpdata = tmp_path / "data"
    tmpdata.mkdir()
    # patch paths in module
    import backend.app as mod
    mod.DATA_DIR = str(tmpdata)
    mod.VERSIONS_FILE = str(tmp_path / "versions.json")
    yield

def make_csv(content: str):
    return io.BytesIO(content.encode('utf-8'))

def test_upload_and_versions_and_compare():
    # use test client
    cli = app.test_client()
    csv1 = "test_case,value\nA,1\nB,2\n"
    csv2 = "test_case,value\nA,1.5\nB,1.8\nC,3\n"
    # upload v1
    rv = cli.post('/api/upload', data={
        'version': 'v1',
        'file': (make_csv(csv1), 'r1.csv')
    }, content_type='multipart/form-data')
    assert rv.status_code == 200
    d = rv.get_json()
    assert d['ok'] is True and d['version'] == 'v1'
    # upload v2
    rv = cli.post('/api/upload', data={
        'version': 'v2',
        'file': (make_csv(csv2), 'r2.csv')
    }, content_type='multipart/form-data')
    assert rv.status_code == 200
    # list versions
    rv = cli.get('/api/versions')
    assert rv.status_code == 200
    versions = rv.get_json()
    assert any(v['version']=='v1' for v in versions)
    assert any(v['version']=='v2' for v in versions)
    # compare
    rv = cli.get('/api/compare', query_string={'v1':'v1','v2':'v2'})
    assert rv.status_code == 200
    payload = rv.get_json()
    assert 'table' in payload and 'chart' in payload
    # check some values
    table = {r['test_case']: r for r in payload['table']}
    assert table['A']['v1'] == 1.0
    assert table['A']['v2'] == 1.5
    assert table['C']['v1'] is None
    assert table['C']['v2'] == 3.0
