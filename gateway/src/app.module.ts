import { Module } from '@nestjs/common';
import { ReadingsModule } from './readings/readings.module';
import { GrpcModule } from './grpc/grpc.module';

@Module({
  imports: [GrpcModule, ReadingsModule],
})
export class AppModule {}