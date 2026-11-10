import { Body, Controller, HttpCode, Post, Req } from '@nestjs/common';
import { ApiOperation, ApiTags } from '@nestjs/swagger';
import { Throttle } from '@nestjs/throttler';
import { AuthService } from './auth.service';
import { CurrentUser, RequireAuth, type AuthUser, type AuthedRequest } from '../common/auth/auth.guard';
import { body } from '../common/params';

/** Per-IP limits for sign-in. Raise OTP_RATE_PER_MIN only in test environments. */
const OTP_PER_MIN = Number(process.env.OTP_RATE_PER_MIN ?? 5);

@ApiTags('auth')
@Controller('v1/auth')
export class AuthController {
  constructor(private readonly auth: AuthService) {}

  @Post('otp/request')
  @HttpCode(200)
  @Throttle({ default: { limit: OTP_PER_MIN, ttl: 60_000 } })
  @ApiOperation({ summary: 'Send a 6-digit sign-in code by SMS (3 per number per 15 minutes)' })
  request(@Body() raw: unknown, @Req() req: AuthedRequest) {
    return this.auth.requestOtp(body(raw).phone, req.ip ?? null);
  }

  @Post('otp/verify')
  @HttpCode(200)
  @Throttle({ default: { limit: OTP_PER_MIN * 2, ttl: 60_000 } })
  @ApiOperation({ summary: 'Exchange phone + code for access and refresh tokens (creates the account on first sign-in)' })
  verify(@Body() raw: unknown, @Req() req: AuthedRequest) {
    const b = body(raw);
    return this.auth.verifyOtp(b.phone, b.code, b.name, req.header('user-agent'));
  }

  @Post('refresh')
  @HttpCode(200)
  @Throttle({ default: { limit: 30, ttl: 60_000 } })
  @ApiOperation({ summary: 'Rotate the refresh token and get a new access token' })
  refresh(@Body() raw: unknown) {
    return this.auth.refresh(body(raw).refresh_token);
  }

  @Post('logout')
  @HttpCode(200)
  @RequireAuth()
  logout(@CurrentUser() user: AuthUser, @Body() raw: unknown) {
    const all = !!(raw && typeof raw === 'object' && (raw as { all?: unknown }).all === true);
    return this.auth.logout(user.session_id, all, user.id);
  }
}
