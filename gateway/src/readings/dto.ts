import { ApiProperty, ApiPropertyOptional } from '@nestjs/swagger';
import { IsBoolean, IsISO8601, IsNumber, IsOptional, IsInt, Min } from 'class-validator';
import { Type } from 'class-transformer';

export class CreateReadingDto {
  @ApiPropertyOptional({ description: 'Original dataset id (optional)' })
  @IsOptional()
  @Type(() => Number)
  @IsInt()
  source_id?: number;

  @ApiProperty({ example: '2023-11-14T22:13:20.000Z' })
  @IsISO8601()
  ts!: string;

  @ApiProperty()
  @Type(() => Number)
  @IsNumber()
  temperature_c!: number;

  @ApiProperty()
  @Type(() => Number)
  @IsNumber()
  humidity_percent!: number;

  @ApiProperty()
  @Type(() => Number)
  @IsNumber()
  light_lux!: number;

  @ApiProperty()
  @Type(() => Number)
  @IsNumber()
  co2_ppm!: number;

  @ApiProperty()
  @Type(() => Number)
  @IsNumber()
  humidity_ratio!: number;

  @ApiProperty()
  @IsBoolean()
  occupancy!: boolean;
}

export class UpdateReadingDto extends CreateReadingDto {}

export class ListQueryDto {
  @ApiPropertyOptional({ description: 'ISO8601 from timestamp' })
  @IsOptional()
  @IsISO8601()
  from?: string;

  @ApiPropertyOptional({ description: 'ISO8601 to timestamp' })
  @IsOptional()
  @IsISO8601()
  to?: string;

  @ApiPropertyOptional({ default: 50, minimum: 1, maximum: 1000 })
  @IsOptional()
  @Type(() => Number)
  @IsInt()
  @Min(1)
  limit?: number = 50;

  @ApiPropertyOptional({ default: 0 })
  @IsOptional()
  @Type(() => Number)
  @IsInt()
  @Min(0)
  offset?: number = 0;

  @ApiPropertyOptional({ enum: ['asc', 'desc'], default: 'asc' })
  @IsOptional()
  order?: 'asc' | 'desc' = 'asc';
}

export class AggregateQueryDto {
  @ApiProperty({ description: 'ISO8601 from timestamp' })
  @IsISO8601()
  from!: string;

  @ApiProperty({ description: 'ISO8601 to timestamp' })
  @IsISO8601()
  to!: string;

  @ApiPropertyOptional({
    description: 'Comma separated list, e.g. temperature_c,co2_ppm',
    example: 'temperature_c,co2_ppm',
  })
  @IsOptional()
  fields?: string;
}
