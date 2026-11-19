import { Controller, Get, Header, ServiceUnavailableException } from '@nestjs/common';
import { SkipThrottle } from '@nestjs/throttler';
import { Db, INCLUDE_UNVERIFIED } from '../db/db.service';
import { SearchService } from '../search/search.service';
import { STAFF_REQUIRE_2FA } from '../common/auth/totp';

@Controller('health')
@SkipThrottle()
export class HealthController {
  constructor(private readonly db: Db, private readonly search: SearchService) {}

  @Get()
  @Header('Cache-Control', 'no-store')
  async check() {
    const started = Date.now();
    try {
      await this.db.one('SELECT 1');
    } catch {
      throw new ServiceUnavailableException({ status: 'db_unavailable' });
    }
    return {
      status: 'ok',
      db: { ok: true, ms: Date.now() - started },
      search: this.search.health(),
      public_include_unverified: INCLUDE_UNVERIFIED,
      staff_require_2fa: STAFF_REQUIRE_2FA,
      // the deploy pipeline waits until this matches the commit it just released
      version: process.env.APP_VERSION ?? process.env.RENDER_GIT_COMMIT ?? 'dev',
    };
  }
}
