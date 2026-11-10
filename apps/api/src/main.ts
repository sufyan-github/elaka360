import 'reflect-metadata';
import { NestFactory } from '@nestjs/core';
import { DocumentBuilder, SwaggerModule } from '@nestjs/swagger';
import type { NestExpressApplication } from '@nestjs/platform-express';
import helmet from 'helmet';
import { AppModule } from './app.module';
import { requestContext } from './common/request-context';
import { jwtSecret } from './common/auth/tokens';

async function bootstrap() {
  jwtSecret(); // fail fast in production without a secret
  const app = await NestFactory.create<NestExpressApplication>(AppModule, { logger: ['log', 'warn', 'error'] });
  app.disable('x-powered-by');
  app.set('trust proxy', Number(process.env.TRUST_PROXY_HOPS ?? 1));
  app.use(requestContext);
  app.use(helmet({ contentSecurityPolicy: { directives: { defaultSrc: ["'self'"], scriptSrc: ["'self'", "'unsafe-inline'"], styleSrc: ["'self'", "'unsafe-inline'"], imgSrc: ["'self'", 'data:'] } } }));
  app.useBodyParser('json', { limit: '100kb' });
  const origins = (process.env.CORS_ORIGINS ?? 'http://localhost:3000').split(',').map((s) => s.trim());
  app.enableCors({ origin: origins, credentials: false, exposedHeaders: ['X-Request-Id'] });
  app.enableShutdownHooks();

  const doc = SwaggerModule.createDocument(app, new DocumentBuilder()
    .setTitle('Elaka360 API').setVersion('1')
    .setDescription('Public reads return only production-eligible records (see docs/data/DATA_TRUST_POLICY.md). Errors are RFC 9457 problem details.')
    .addBearerAuth().build());
  SwaggerModule.setup('docs', app, doc, { jsonDocumentUrl: 'openapi.json' });

  const port = Number(process.env.API_PORT ?? process.env.PORT ?? 4000);
  await app.listen(port);
  console.log(JSON.stringify({ t: new Date().toISOString(), level: 'info', msg: `Elaka360 API listening on :${port}` }));
}

void bootstrap();
