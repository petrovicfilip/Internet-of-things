from __future__ import annotations

import uuid
from datetime import timezone

import grpc
from google.protobuf.timestamp_pb2 import Timestamp

from .db import SessionLocal
from .models import SensorReading
from . import repository

from .generated import iot_readings_pb2 as pb2
from .generated import iot_readings_pb2_grpc as pb2_grpc
from .mqtt_publisher import MqttPublisher


def dt_from_ts(ts: Timestamp):
    # Timestamp je message => ima presence (HasField radi)
    return ts.ToDatetime(tzinfo=timezone.utc)

def ts_from_dt(dt):
    t = Timestamp()
    t.FromDatetime(dt)
    return t

def reading_to_proto(m: SensorReading) -> pb2.Reading:
    return pb2.Reading(
        id=str(m.id),
        source_id=int(m.source_id or 0),
        ts=ts_from_dt(m.ts),
        temperature_c=m.temperature_c,
        humidity_percent=m.humidity_percent,
        light_lux=m.light_lux,
        co2_ppm=m.co2_ppm,
        humidity_ratio=m.humidity_ratio,
        occupancy=m.occupancy,
    )

def reading_to_mqtt(m: SensorReading) -> dict:
    ts = m.ts.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    return {
        "id": str(m.id),
        "source_id": int(m.source_id or 0),
        "ts": ts,
        "temperature_c": m.temperature_c,
        "humidity_percent": m.humidity_percent,
        "light_lux": m.light_lux,
        "co2_ppm": m.co2_ppm,
        "humidity_ratio": m.humidity_ratio,
        "occupancy": m.occupancy,
        # "location": ...
    }


def parse_uuid(value: str) -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except Exception:
        raise ValueError("Invalid UUID")

class ReadingService(pb2_grpc.ReadingServiceServicer):
    def __init__(self, publisher: MqttPublisher | None = None):
        self.publisher = publisher


    async def CreateReading(self, request: pb2.CreateReadingRequest, context: grpc.aio.ServicerContext):
        if request is None or request.reading is None:
            await context.abort(grpc.StatusCode.INVALID_ARGUMENT, "Missing reading")

        r = request.reading

        # id opcionalno: ako prazno -> generiši
        rid = None
        if r.id:
            try:
                rid = parse_uuid(r.id)
            except ValueError:
                await context.abort(grpc.StatusCode.INVALID_ARGUMENT, "Invalid id UUID")

        if not r.HasField("ts"):
            await context.abort(grpc.StatusCode.INVALID_ARGUMENT, "Missing ts")

        model = SensorReading(
            id=rid or uuid.uuid4(),
            source_id=(r.source_id if r.source_id != 0 else None),
            ts=dt_from_ts(r.ts),
            temperature_c=r.temperature_c,
            humidity_percent=r.humidity_percent,
            light_lux=r.light_lux,
            co2_ppm=r.co2_ppm,
            humidity_ratio=r.humidity_ratio,
            occupancy=r.occupancy,
        )

        async with SessionLocal() as session:
            async with session.begin():
                created = await repository.create_reading(session, model)

        if self.publisher:
            self.publisher.publish_reading(reading_to_mqtt(created), action="created")

        return pb2.ReadingResponse(reading=reading_to_proto(created))

    async def GetReading(self, request: pb2.GetReadingRequest, context: grpc.aio.ServicerContext):
        try:
            rid = parse_uuid(request.id)
        except ValueError:
            await context.abort(grpc.StatusCode.INVALID_ARGUMENT, "Invalid id UUID")

        async with SessionLocal() as session:
            m = await repository.get_reading(session, rid)
            if m is None:
                await context.abort(grpc.StatusCode.NOT_FOUND, "Not found")
            return pb2.ReadingResponse(reading=reading_to_proto(m))

    async def UpdateReading(self, request: pb2.UpdateReadingRequest, context: grpc.aio.ServicerContext):
        try:
            rid = parse_uuid(request.id)
        except ValueError:
            await context.abort(grpc.StatusCode.INVALID_ARGUMENT, "Invalid id UUID")

        r = request.reading
        if r is None:
            await context.abort(grpc.StatusCode.INVALID_ARGUMENT, "Missing reading")

        patch = {
            "source_id": (r.source_id if r.source_id != 0 else None),
            "temperature_c": r.temperature_c,
            "humidity_percent": r.humidity_percent,
            "light_lux": r.light_lux,
            "co2_ppm": r.co2_ppm,
            "humidity_ratio": r.humidity_ratio,
            "occupancy": r.occupancy,
        }
        if r.HasField("ts"):
            patch["ts"] = dt_from_ts(r.ts)

        async with SessionLocal() as session:
            async with session.begin():
                updated = await repository.update_reading(session, rid, patch)

        if updated is None:
            await context.abort(grpc.StatusCode.NOT_FOUND, "Not found")

        if self.publisher:
            self.publisher.publish_reading(reading_to_mqtt(updated), action="updated")

        return pb2.ReadingResponse(reading=reading_to_proto(updated))

    async def DeleteReading(self, request: pb2.DeleteReadingRequest, context: grpc.aio.ServicerContext):
        try:
            rid = parse_uuid(request.id)
        except ValueError:
            await context.abort(grpc.StatusCode.INVALID_ARGUMENT, "Invalid id UUID")

        async with SessionLocal() as session:
            async with session.begin():
                m = await repository.get_reading(session, rid)
                if m is None:
                    await context.abort(grpc.StatusCode.NOT_FOUND, "Not found")

                ok = await repository.delete_reading(session, rid)
                if not ok:
                    await context.abort(grpc.StatusCode.NOT_FOUND, "Not found")

        # posle commita:
        if self.publisher:
            self.publisher.publish_reading(reading_to_mqtt(m), action="deleted")

        return pb2.DeleteReadingResponse(deleted=True)

    async def ListReadings(self, request: pb2.ListReadingsRequest, context: grpc.aio.ServicerContext):
        limit = int(request.limit or 50)
        offset = int(request.offset or 0)
        if limit < 1 or limit > 1000:
            await context.abort(grpc.StatusCode.INVALID_ARGUMENT, "limit must be 1..1000")
        if offset < 0:
            await context.abort(grpc.StatusCode.INVALID_ARGUMENT, "offset must be >= 0")

        from_ts = dt_from_ts(request.from_ts) if request.HasField("from_ts") else None
        to_ts = dt_from_ts(request.to_ts) if request.HasField("to_ts") else None

        async with SessionLocal() as session:
            items, total = await repository.list_readings(
                session=session,
                from_ts=from_ts,
                to_ts=to_ts,
                limit=limit,
                offset=offset,
                order=request.order or "asc",
            )
            return pb2.ListReadingsResponse(
                readings=[reading_to_proto(x) for x in items],
                total=total,
            )

    async def Aggregate(self, request: pb2.AggregateRequest, context: grpc.aio.ServicerContext):
        if not request.HasField("from_ts") or not request.HasField("to_ts"):
            await context.abort(grpc.StatusCode.INVALID_ARGUMENT, "from_ts and to_ts are required")

        from_dt = dt_from_ts(request.from_ts)
        to_dt = dt_from_ts(request.to_ts)
        if from_dt > to_dt:
            await context.abort(grpc.StatusCode.INVALID_ARGUMENT, "from_ts must be <= to_ts")

        fields = list(request.fields)
        funcs_map = {
            pb2.MIN: "min",
            pb2.MAX: "max",
            pb2.AVG: "avg",
            pb2.SUM: "sum",
        }
        funcs_list = []
        for f in request.funcs:
            if f in funcs_map:
                funcs_list.append(funcs_map[f])
        if not funcs_list:
            funcs_list = ["min", "max", "avg", "sum"]

        async with SessionLocal() as session:
            rows = await repository.aggregate(session, from_dt, to_dt, fields, funcs_list)

        out = []
        inv = {"min": pb2.MIN, "max": pb2.MAX, "avg": pb2.AVG, "sum": pb2.SUM}
        for field, fn, value in rows:
            out.append(pb2.AggValue(field=field, func=inv[fn], value=value))
        return pb2.AggregateResponse(values=out)