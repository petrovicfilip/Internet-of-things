import { ValidationPipe } from '@nestjs/common';
import { NestFactory } from '@nestjs/core';
import { SwaggerModule, DocumentBuilder } from '@nestjs/swagger';
import * as fs from 'fs';
import * as path from 'path';
import * as yaml from 'js-yaml';
import { AppModule } from './app.module';

async function bootstrap() {
  const app = await NestFactory.create(AppModule);

  app.setGlobalPrefix('api/v1');
  app.useGlobalPipes(
    new ValidationPipe({
      whitelist: true,
      transform: true,
      forbidNonWhitelisted: true,
    }),
  );

  const config = new DocumentBuilder()
    .setTitle('IoT Gateway API')
    .setDescription('REST Gateway that forwards CRUD + aggregations to DataManager (gRPC)')
    .setVersion('1.0.0')
    .build();

  const document = SwaggerModule.createDocument(app, config);
  SwaggerModule.setup('docs', app, document);

  // Export OpenAPI to files
  const outDir = path.resolve(process.cwd(), '..', 'openapi');
  fs.mkdirSync(outDir, { recursive: true });
  fs.writeFileSync(path.join(outDir, 'gateway.json'), JSON.stringify(document, null, 2), 'utf-8');
  fs.writeFileSync(path.join(outDir, 'gateway.yaml'), yaml.dump(document as any), 'utf-8');

  const port = process.env.PORT ? Number(process.env.PORT) : 3000;
  await app.listen(port);
  console.log(`[gateway] REST listening on http://localhost:${port}/api/v1`);
  console.log(`[gateway] Swagger on http://localhost:${port}/docs`);
}

bootstrap();