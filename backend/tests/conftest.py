import os
from pathlib import Path
import pytest

@pytest.fixture(scope='session',autouse=True)
def isolated_storage(tmp_path_factory):
    os.environ['ATMOS_DISABLE_SCHEDULER']='true'
    os.environ['ATMOS_AGENT_PROVIDER']='local_rules'
    from backend import config, storage, forecast
    directory = tmp_path_factory.mktemp('atmos')
    storage.DATA_DIR = directory
    forecast.DATA_DIR = directory
    config.DATA_DIR = directory
    storage.init_db()
    from backend import platform_store
    platform_store.initialize()
    from backend.demo import seed_demo
    seed_demo()
    return directory

@pytest.fixture
def client(isolated_storage):
    from fastapi.testclient import TestClient
    from backend.app import app
    with TestClient(app) as client:
        yield client
