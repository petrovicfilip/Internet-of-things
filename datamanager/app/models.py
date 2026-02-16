from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Boolean, Double, Integer, DateTime, func, Index
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

class Base(DeclarativeBase):
    pass

class SensorReading(Base):
    __tablename__ = "sensor_readings"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    temperature_c: Mapped[float] = mapped_column(Double, nullable=False)
    humidity_percent: Mapped[float] = mapped_column(Double, nullable=False)
    light_lux: Mapped[float] = mapped_column(Double, nullable=False)
    co2_ppm: Mapped[float] = mapped_column(Double, nullable=False)
    humidity_ratio: Mapped[float] = mapped_column(Double, nullable=False)
    occupancy: Mapped[bool] = mapped_column(Boolean, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

Index("idx_sensor_readings_ts", SensorReading.ts)
Index("idx_sensor_readings_ts_occupancy", SensorReading.ts, SensorReading.occupancy)
