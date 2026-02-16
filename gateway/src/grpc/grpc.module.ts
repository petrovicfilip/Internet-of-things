import { Module } from '@nestjs/common';
import { ClientsModule, Transport } from '@nestjs/microservices';
import { join } from 'path';

@Module({
  imports: [
    ClientsModule.register([
      {
        name: 'DATAMANAGER_GRPC',
        transport: Transport.GRPC,
        options: {
          url: process.env.DATAMANAGER_GRPC_URL || 'localhost:50051',
          package: 'iot',
          protoPath: join(process.cwd(), 'proto', 'iot_readings.proto'),
          loader: { keepCase: true },
        },
      },
    ]),
  ],
  exports: [ClientsModule], // <- ključna stvar
})
export class GrpcModule {}