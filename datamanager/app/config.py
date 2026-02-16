from __future__ import annotations
import os

def env(name: str, default: str | None = None) -> str:
    v = os.getenv(name, default)
    if v is None or v == "":
        raise RuntimeError(f"Missing required env var: {name}")
    return v

DATABASE_URL = env(
    "DATABASE_URL",
    "postgresql+asyncpg://iot:iot@localhost:5432/iot"
)
GRPC_HOST = os.getenv("GRPC_HOST", "0.0.0.0")
GRPC_PORT = int(os.getenv("GRPC_PORT", "50051"))