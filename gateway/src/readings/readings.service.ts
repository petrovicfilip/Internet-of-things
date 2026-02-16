import {
  BadRequestException,
  Inject,
  Injectable,
  InternalServerErrorException,
  NotFoundException,
} from '@nestjs/common';
import type { ClientGrpc } from '@nestjs/microservices';
import { lastValueFrom } from 'rxjs';

import {
  AggFunc,
  AggregateResponse,
  ListReadingsResponse,
  ReadingResponse,
  ReadingServiceGrpc,
} from './grpc-types';
import { CreateReadingDto, UpdateReadingDto, ListQueryDto, AggregateQueryDto } from './dto';
import { toTimestamp, fromTimestamp } from './time';

function mapGrpcError(e: any): never {
  // gRPC status codes:
  // 3 INVALID_ARGUMENT, 5 NOT_FOUND, 13 INTERNAL, ...
  const code = e?.code;
  const message = e?.details || e?.message || 'gRPC error';

  if (code === 3) throw new BadRequestException(message);
  if (code === 5) throw new NotFoundException(message);

  throw new InternalServerErrorException(message);
}

@Injectable()
export class ReadingsService {
  private svc!: ReadingServiceGrpc;

  constructor(@Inject('DATAMANAGER_GRPC') private readonly client: ClientGrpc) {}

  onModuleInit() {
    this.svc = this.client.getService<ReadingServiceGrpc>('ReadingService');
  }

  async create(dto: CreateReadingDto) {
    try {
      const res: ReadingResponse = await lastValueFrom(
        this.svc.CreateReading({
          reading: {
            source_id: dto.source_id ?? 0,
            ts: toTimestamp(dto.ts),
            temperature_c: dto.temperature_c,
            humidity_percent: dto.humidity_percent,
            light_lux: dto.light_lux,
            co2_ppm: dto.co2_ppm,
            humidity_ratio: dto.humidity_ratio,
            occupancy: dto.occupancy,
          },
        }),
      );

      return this.normalizeReading(res);
    } catch (e) {
      mapGrpcError(e);
    }
  }

  async get(id: string) {
    try {
      const res: ReadingResponse = await lastValueFrom(this.svc.GetReading({ id }));
      return this.normalizeReading(res);
    } catch (e) {
      mapGrpcError(e);
    }
  }

  async update(id: string, dto: UpdateReadingDto) {
    try {
      const res: ReadingResponse = await lastValueFrom(
        this.svc.UpdateReading({
          id,
          reading: {
            source_id: dto.source_id ?? 0,
            ts: toTimestamp(dto.ts),
            temperature_c: dto.temperature_c,
            humidity_percent: dto.humidity_percent,
            light_lux: dto.light_lux,
            co2_ppm: dto.co2_ppm,
            humidity_ratio: dto.humidity_ratio,
            occupancy: dto.occupancy,
          },
        }),
      );
      return this.normalizeReading(res);
    } catch (e) {
      mapGrpcError(e);
    }
  }

  async remove(id: string) {
    try {
      await lastValueFrom(this.svc.DeleteReading({ id }));
      return;
    } catch (e) {
      mapGrpcError(e);
    }
  }

  async list(q: ListQueryDto) {
    try {
      const res: ListReadingsResponse = await lastValueFrom(
        this.svc.ListReadings({
          from_ts: q.from ? toTimestamp(q.from) : undefined,
          to_ts: q.to ? toTimestamp(q.to) : undefined,
          limit: q.limit ?? 50,
          offset: q.offset ?? 0,
          order: q.order ?? 'asc',
        }),
      );

      return {
        items: res.readings.map((r) => this.normalizeReading({ reading: r }).reading),
        total: res.total,
      };
    } catch (e) {
      mapGrpcError(e);
    }
  }

  async aggregate(q: AggregateQueryDto) {
    // fields query: "a,b,c"
    const fieldsArr = q.fields
      ? q.fields.split(',').map((s) => s.trim()).filter(Boolean)
      : [];

    try {
      const res: AggregateResponse = await lastValueFrom(
        this.svc.Aggregate({
          from_ts: toTimestamp(q.from),
          to_ts: toTimestamp(q.to),
          fields: fieldsArr,
          funcs: [AggFunc.MIN, AggFunc.MAX, AggFunc.AVG, AggFunc.SUM],
        }),
      );

      // Transform list -> object grouped by field
      const grouped: Record<string, any> = {};
      for (const v of res.values) {
        grouped[v.field] ??= {};
        const key =
          v.func === AggFunc.MIN ? 'min' :
          v.func === AggFunc.MAX ? 'max' :
          v.func === AggFunc.AVG ? 'avg' :
          v.func === AggFunc.SUM ? 'sum' : 'unknown';
        grouped[v.field][key] = v.value;
      }

      return {
        from: q.from,
        to: q.to,
        values: grouped,
      };
    } catch (e) {
      mapGrpcError(e);
    }
  }

  private normalizeReading(res: ReadingResponse) {
    const r = res.reading;
    // Convert Timestamp -> ISO for REST output
    return {
      reading: {
        ...r,
        ts: r.ts ? fromTimestamp(r.ts) : null,
      },
    };
  }
}