import { Body, Controller, Get, HttpCode, Param, Patch, Post } from '@nestjs/common';
import { ApiOperation, ApiTags } from '@nestjs/swagger';
import { Throttle } from '@nestjs/throttler';
import { ContributionsService } from './contributions.service';
import { CurrentUser, RequireAuth, type AuthUser } from '../common/auth/auth.guard';
import { body, idParam } from '../common/params';
import { scaled } from '../common/throttle';

@ApiTags('contributions')
@Controller('v1')
@RequireAuth()
export class ContributionsController {
  constructor(private readonly svc: ContributionsService) {}

  @Post('contributions')
  @Throttle({ default: { limit: scaled(10), ttl: 60_000 } })
  @ApiOperation({ summary: 'Create a contribution as a draft, or submit it (submit: true + confirmed_accurate: true)' })
  create(@CurrentUser() u: AuthUser, @Body() raw: unknown) {
    return this.svc.create(u.id, body(raw));
  }

  @Get('contributions/:id')
  get(@CurrentUser() u: AuthUser, @Param('id') id: string) {
    return this.svc.get(idParam(id), u.id);
  }

  @Patch('contributions/:id')
  @ApiOperation({ summary: 'Edit your draft or a submission returned for changes' })
  update(@CurrentUser() u: AuthUser, @Param('id') id: string, @Body() raw: unknown) {
    return this.svc.update(idParam(id), u.id, body(raw));
  }

  @Post('contributions/:id/submit')
  @HttpCode(200)
  submit(@CurrentUser() u: AuthUser, @Param('id') id: string) {
    return this.svc.submit(idParam(id), u.id);
  }

  @Get('me/contributions')
  async mine(@CurrentUser() u: AuthUser) {
    return { items: await this.svc.mine(u.id) };
  }

  @Get('me/contributions/stats')
  stats(@CurrentUser() u: AuthUser) {
    return this.svc.stats(u.id);
  }
}
