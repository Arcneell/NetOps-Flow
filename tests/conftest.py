import pytest
from fastapi.testclient import TestClient
import sys
import os

# Ensure backend is in python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app import app

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c
