import pytest
import os

@pytest.fixture(autouse=False)
def client(tmp_path, monkeypatch):
    """
    Provides a Flask test client with DATA_DIR and VERSIONS_FILE pointed to a tmp location
    so tests run isolated without touching repo files.
    """
    tmpdata = tmp_path / "data"
    tmpdata.mkdir()
    # Patch paths in backend.app module
    import backend.app as mod
    mod.DATA_DIR = str(tmpdata)
    mod.VERSIONS_FILE = str(tmp_path / "versions.json")
    from backend.app import app
    return app.test_client()