import os
import tempfile
from pathlib import Path
TEST_DIR = tempfile.mkdtemp(prefix='mandatetrail-test-')
os.environ['DATA_DIR'] = TEST_DIR
os.environ['DATABASE_URL'] = 'sqlite:///' + (Path(TEST_DIR) / 'test.db').as_posix()
os.environ['DEMO_PASSWORD'] = 'Test-only-randomized-fixture-972!'
import pytest
from fastapi.testclient import TestClient
from alembic.config import Config
from alembic import command
from app.main import app

@pytest.fixture(scope='session')
def client():
    command.upgrade(Config('alembic.ini'), 'head')
    with TestClient(app) as client:
        yield client

@pytest.fixture
def admin(client):
    client.cookies.clear()
    result = client.post('/api/v1/auth/login', json={'email':'admin@mandatetrail.local','password':os.environ['DEMO_PASSWORD']})
    assert result.status_code == 200, result.text
    client.headers['X-CSRF-Token'] = result.json()['csrf']
    return client
