import { BadRequestException, Body, Controller, HttpCode, Post } from '@nestjs/common';
import { ApiOperation, ApiTags } from '@nestjs/swagger';
import { Throttle } from '@nestjs/throttler';
import { Db } from '../db/db.service';
import { CurrentUser, type AuthUser } from '../common/auth/auth.guard';
import { body, textField } from '../common/params';
import { scaled } from '../common/throttle';

@ApiTags('content')
@Controller('v1/contact')
export class ContactController {
  constructor(private readonly db: Db) {}

  @Post()
  @HttpCode(201)
  @Throttle({ default: { limit: scaled(3), ttl: 60_000 } })
  @ApiOperation({ summary: 'Send a message to the Elaka360 team (subject ≤ 120, message ≤ 1,000 characters)' })
  async send(@Body() raw: unknown, @CurrentUser() u?: AuthUser) {
    const b = body(raw);
    if (typeof b.website === 'string' && b.website) return { received: true }; // honeypot: bots fill hidden fields
    const subject = textField(b, 'subject', { max: 120, min: 3, required: true });
    const message = textField(b, 'message', { max: 1000, min: 10, required: true });
    const email = textField(b, 'email', { max: 120 });
    if (email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) throw new BadRequestException('email looks invalid');
    await this.db.many('INSERT INTO contact_messages(user_id, email, subject, message) VALUES ($1,$2,$3,$4)', [u?.id ?? null, email, subject, message]);
    return { received: true };
  }
}
