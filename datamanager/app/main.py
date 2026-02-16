from __future__ import annotations

import asyncio
import grpc
from grpc_reflection.v1alpha import reflection

from .config import GRPC_HOST, GRPC_PORT
from .db import engine
from .models import Base

from pathlib import Path
import sys

GEN_DIR = Path(__file__).resolve().parent / "generated"
if str(GEN_DIR) not in sys.path:
    sys.path.insert(0, str(GEN_DIR))

from .service import ReadingService
from .generated import iot_readings_pb2 as pb2
from .generated import iot_readings_pb2_grpc as pb2_grpc

from .mqtt_publisher import MqttPublisher
from .service import ReadingService

publisher = MqttPublisher()
service = ReadingService(publisher=publisher)



async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def serve() -> None:
    await init_db()

    server = grpc.aio.server(options=[
        ("grpc.max_receive_message_length", 50 * 1024 * 1024),
        ("grpc.max_send_message_length", 50 * 1024 * 1024),
    ])

    pb2_grpc.add_ReadingServiceServicer_to_server(ReadingService(), server)

    # Reflection (super za Postman/grpcurl)
    service_names = (
        pb2.DESCRIPTOR.services_by_name["ReadingService"].full_name,
        reflection.SERVICE_NAME,
    )
    reflection.enable_server_reflection(service_names, server)


    listen_addr = f"{GRPC_HOST}:{GRPC_PORT}"
    server.add_insecure_port(listen_addr)
    print(f"[datamanager] gRPC listening on {listen_addr}")

    await server.start()
    await server.wait_for_termination()

def main() -> None:
    asyncio.run(serve())

if __name__ == "__main__":
    main()