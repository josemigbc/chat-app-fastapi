import pytest
from fastapi.testclient import TestClient
from tortoise.models import Model
from tortoise.exceptions import DoesNotExist
from app import app
from unittest.mock import patch
from models import User
from datetime import datetime
from typing import Any


client = TestClient(app)

payload_ok = payload = {
        "first_name": "test_first_name",
        "last_name": "test_last_name",
        "username": "test",
        "email": "test@test.com",
        "password": "test1234",
    }

def model_creation_mock(model: type[Model]):
    return lambda *args, **kwargs: model(id=1, **kwargs, joined=datetime.now())

def model_get_mock(model: type[Model], in_db: bool = True, **fields):
    if in_db:
        return lambda *args, **kwargs: model(**kwargs,**fields)
    def not_found(*args, **kwargs):
        raise DoesNotExist()
    return not_found

@patch.object(User, 'create', side_effect=model_creation_mock(User))
def test_create_user(mock):
    response = client.post("/user", json=payload)
    assert response.status_code == 201
    assert response.json()["username"] == "test"