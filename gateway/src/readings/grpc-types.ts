export type Timestamp = { seconds: number; nanos?: number };

export type Reading = {
  id?: string;
  source_id?: number;
  ts?: Timestamp;
  temperature_c?: number;
  humidity_percent?: number;
  light_lux?: number;
  co2_ppm?: number;
  humidity_ratio?: number;
  occupancy?: boolean;
};

export type CreateReadingRequest = { reading: Reading };
export type GetReadingRequest = { id: string };
export type UpdateReadingRequest = { id: string; reading: Reading };
export type DeleteReadingRequest = { id: string };

export type ReadingResponse = { reading: Required<Reading> };
export type DeleteReadingResponse = { deleted: boolean };

export type ListReadingsRequest = {
  from_ts?: Timestamp;
  to_ts?: Timestamp;
  limit?: number;
  offset?: number;
  order?: string;
};

export type ListReadingsResponse = {
  readings: Required<Reading>[];
  total: number;
};

export enum AggFunc {
  AGG_FUNC_UNSPECIFIED = 0,
  MIN = 1,
  MAX = 2,
  AVG = 3,
  SUM = 4,
}

export type AggregateRequest = {
  from_ts: Timestamp;
  to_ts: Timestamp;
  fields?: string[];
  funcs?: AggFunc[];
};

export type AggValue = { field: string; func: AggFunc; value: number };
export type AggregateResponse = { values: AggValue[] };

export interface ReadingServiceGrpc {
  CreateReading(req: CreateReadingRequest): any;
  GetReading(req: GetReadingRequest): any;
  UpdateReading(req: UpdateReadingRequest): any;
  DeleteReading(req: DeleteReadingRequest): any;
  ListReadings(req: ListReadingsRequest): any;
  Aggregate(req: AggregateRequest): any;
}