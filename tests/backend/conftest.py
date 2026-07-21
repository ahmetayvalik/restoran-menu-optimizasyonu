from __future__ import annotations

import io
import sys
from pathlib import Path
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient


ROOT_DIR = Path(__file__).resolve().parents[2]
REAL_DATASET_PATH = ROOT_DIR / "data" / "raw" / "restaurant_orders.csv"

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.app.main import app


@pytest.fixture
def client() -> TestClient:
    original_init = httpx.Client.__init__

    def patched_init(self, *args, **kwargs):
        kwargs.pop("app", None)
        return original_init(self, *args, **kwargs)

    httpx.Client.__init__ = patched_init
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        httpx.Client.__init__ = original_init


@pytest.fixture
def real_csv_path() -> Path:
    return REAL_DATASET_PATH


@pytest.fixture
def real_csv(real_csv_path: Path):
    with real_csv_path.open("rb") as file_obj:
        yield file_obj


@pytest.fixture
def post_csv(client: TestClient):
    def _post(
        file_source: Any,
        filename: str = "test.csv",
        params: dict[str, Any] | None = None,
        content_type: str = "text/csv",
    ):
        if hasattr(file_source, "seek"):
            file_source.seek(0)
            files = {"file": (filename, file_source, content_type)}
            return client.post("/upload-and-analyze", params=params, files=files)

        if isinstance(file_source, str):
            buffer = io.BytesIO(file_source.encode("utf-8"))
        else:
            buffer = io.BytesIO(file_source)

        files = {"file": (filename, buffer, content_type)}
        return client.post("/upload-and-analyze", params=params, files=files)

    return _post
