from __future__ import annotations

import uuid
from datetime import datetime
from typing import Sequence

from sqlalchemy import select, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession

from .models import SensorReading

NUMERIC_FIELDS = {
    "temperature_c": SensorReading.temperature_c,
    "humidity_percent": SensorReading.humidity_percent,
    "light_lux": SensorReading.light_lux,
    "co2_ppm": SensorReading.co2_ppm,
    "humidity_ratio": SensorReading.humidity_ratio,
}

def _apply_time_filter(stmt, from_ts: datetime | None, to_ts: datetime | None):
    if from_ts is not None:
        stmt = stmt.where(SensorReading.ts >= from_ts)
    if to_ts is not None:
        stmt = stmt.where(SensorReading.ts <= to_ts)
    return stmt

async def create_reading(session: AsyncSession, r: SensorReading) -> SensorReading:
    session.add(r)
    await session.flush()
    return r

async def get_reading(session: AsyncSession, reading_id: uuid.UUID) -> SensorReading | None:
    res = await session.execute(select(SensorReading).where(SensorReading.id == reading_id))
    return res.scalar_one_or_none()

async def update_reading(session: AsyncSession, reading_id: uuid.UUID, patch: dict) -> SensorReading | None:
    stmt = (
        update(SensorReading)
        .where(SensorReading.id == reading_id)
        .values(**patch)
        .returning(SensorReading)
    )
    res = await session.execute(stmt)
    return res.scalar_one_or_none()

async def delete_reading(session: AsyncSession, reading_id: uuid.UUID) -> bool:
    stmt = delete(SensorReading).where(SensorReading.id == reading_id).returning(SensorReading.id)
    res = await session.execute(stmt)
    return res.scalar_one_or_none() is not None

async def list_readings(
    session: AsyncSession,
    from_ts: datetime | None,
    to_ts: datetime | None,
    limit: int,
    offset: int,
    order: str,
) -> tuple[Sequence[SensorReading], int]:
    base = select(SensorReading)
    base = _apply_time_filter(base, from_ts, to_ts)

    order = (order or "asc").lower()
    if order not in ("asc", "desc"):
        order = "asc"

    if order == "asc":
        base = base.order_by(SensorReading.ts.asc())
    else:
        base = base.order_by(SensorReading.ts.desc())

    # total count
    count_stmt = select(func.count()).select_from(
        _apply_time_filter(select(SensorReading.id), from_ts, to_ts).subquery()
    )
    total = (await session.execute(count_stmt)).scalar_one()

    # items
    items_stmt = base.limit(limit).offset(offset)
    items = (await session.execute(items_stmt)).scalars().all()

    return items, int(total)

async def aggregate(
    session: AsyncSession,
    from_ts: datetime,
    to_ts: datetime,
    fields: list[str],
    funcs_list: list[str],  # "min"|"max"|"avg"|"sum"
) -> list[tuple[str, str, float]]:
    """
    Returns list of (field, func, value)
    """
    if not fields:
        fields = list(NUMERIC_FIELDS.keys())

    results: list[tuple[str, str, float]] = []
    for f in fields:
        col = NUMERIC_FIELDS.get(f)
        if col is None:
            continue

        for fn in funcs_list:
            if fn == "min":
                expr = func.min(col)
            elif fn == "max":
                expr = func.max(col)
            elif fn == "avg":
                expr = func.avg(col)
            elif fn == "sum":
                expr = func.sum(col)
            else:
                continue

            stmt = select(expr).where(SensorReading.ts >= from_ts, SensorReading.ts <= to_ts)
            val = (await session.execute(stmt)).scalar_one()
            # ako nema redova u opsegu -> val može biti None
            results.append((f, fn, float(val) if val is not None else float("nan")))

    return results
