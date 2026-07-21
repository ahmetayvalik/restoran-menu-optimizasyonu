from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")


def parse_csv_env(name: str, default: list[str]) -> list[str]:
    raw_value = os.getenv(name, "")
    if not raw_value.strip():
        return default
    return [item.strip() for item in raw_value.split(",") if item.strip()]


@dataclass(frozen=True)
class Settings:
    service_name: str = os.getenv("BACKEND_SERVICE_NAME", "backend")
    service_port: int = int(os.getenv("BACKEND_PORT", "8000"))
    min_support: float = float(os.getenv("BACKEND_MIN_SUPPORT", "0.01"))
    min_lift: float = float(os.getenv("BACKEND_MIN_LIFT", "1.05"))
    allowed_origins: list[str] = field(
        default_factory=lambda: parse_csv_env(
            "BACKEND_ALLOWED_ORIGINS",
            ["http://localhost:5173", "http://127.0.0.1:5173"],
        )
    )
    allowed_category_filters: set[str] = field(
        default_factory=lambda: {"Asian", "Italian", "Mexican", "American"}
    )


settings = Settings()
