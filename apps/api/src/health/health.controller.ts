import { Controller, Get, ServiceUnavailableException } from '@nestjs/common';
import { Db } from '../db/db.service';
import { SearchService } from '../search/search.service';

@Controller('health')
export class HealthController {
  constructor(private readonly db: Db, private readonly search: SearchService) {}

  @Get()
  async check() {
    try {
      await this.db.one('SELECT 1');
      return { status: 'ok', search: this.search.engine };
    } catch {
      throw new ServiceUnavailableException({ status: 'db_unavailable' });
    }
  }
}
