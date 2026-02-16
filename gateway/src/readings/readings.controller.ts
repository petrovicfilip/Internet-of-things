import {
  Body,
  Controller,
  Delete,
  Get,
  HttpCode,
  Param,
  ParseUUIDPipe,
  Post,
  Put,
  Query,
} from '@nestjs/common';
import { ApiOperation, ApiParam, ApiQuery, ApiResponse, ApiTags } from '@nestjs/swagger';
import { ReadingsService } from './readings.service';
import { AggregateQueryDto, CreateReadingDto, ListQueryDto, UpdateReadingDto } from './dto';

@ApiTags('readings')
@Controller('readings')
export class ReadingsController {
  constructor(private readonly svc: ReadingsService) {}

  @Post()
  @ApiOperation({ summary: 'Create a sensor reading' })
  @ApiResponse({ status: 201, description: 'Created' })
  async create(@Body() dto: CreateReadingDto) {
    return this.svc.create(dto);
  }

  @Get()
  @ApiOperation({ summary: 'List readings (time filter + paging)' })
  @ApiResponse({ status: 200, description: 'OK' })
  async list(@Query() q: ListQueryDto) {
    return this.svc.list(q);
  }

  @Get('aggregate')
  @ApiOperation({ summary: 'Aggregate numeric fields over time range' })
  @ApiResponse({ status: 200, description: 'OK' })
  async aggregate(@Query() q: AggregateQueryDto) {
    return this.svc.aggregate(q);
  }

  @Get(':id')
  @ApiOperation({ summary: 'Get reading by id' })
  @ApiParam({ name: 'id', format: 'uuid' })
  async get(@Param('id', new ParseUUIDPipe()) id: string) {
    return this.svc.get(id);
  }

  @Put(':id')
  @ApiOperation({ summary: 'Update reading' })
  @ApiParam({ name: 'id', format: 'uuid' })
  async update(
    @Param('id', new ParseUUIDPipe()) id: string,
    @Body() dto: UpdateReadingDto,
  ) {
    return this.svc.update(id, dto);
  }

  @Delete(':id')
  @HttpCode(204)
  @ApiOperation({ summary: 'Delete reading' })
  @ApiParam({ name: 'id', format: 'uuid' })
  async remove(@Param('id', new ParseUUIDPipe()) id: string) {
    await this.svc.remove(id);
  }
}