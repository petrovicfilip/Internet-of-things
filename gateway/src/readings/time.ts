import { Timestamp } from './grpc-types';

export function toTimestamp(iso: string): Timestamp {
  const ms = Date.parse(iso);
  if (Number.isNaN(ms)) {
    throw new Error('Invalid ISO date-time');
  }
  const seconds = Math.floor(ms / 1000);
  const nanos = (ms % 1000) * 1_000_000;
  return { seconds, nanos };
}

export function fromTimestamp(ts: Timestamp): string {
  const ms = ts.seconds * 1000 + Math.floor((ts.nanos || 0) / 1_000_000);
  return new Date(ms).toISOString();
}