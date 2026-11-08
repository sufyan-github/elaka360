import { Controller, Get, ServiceUnavailableException } from '@nestjs/common';
import { Db } from '../db/db.service';

@Controller('health')
export class HealthController {
  constructor(private readonly db: Db) {}

  @Get()
  async check() {
    try {
      await this.db.one('SELECT 1');
      return { status: 'ok' };
    } catch {
      throw new ServiceUnavailableException({ status: 'db_unavailable' });
    }
  }
}
