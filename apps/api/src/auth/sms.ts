import { Logger, ServiceUnavailableException } from '@nestjs/common';

/**
 * SMS delivery for one-time passwords.
 *  - SMS_PROVIDER unset   → OTP requests fail with 503 (no silent success).
 *  - SMS_PROVIDER=dev     → development only: the code is returned in the API response as `dev_code`
 *                           and never logged. Refused when NODE_ENV=production.
 * A real gateway (e.g. a Bangladeshi SMS aggregator) is not configured in this repository.
 */
export interface SmsSender {
  readonly name: string;
  send(phone: string, text: string): Promise<{ devCode?: string }>;
}

class DevSender implements SmsSender {
  readonly name = 'dev';
  async send(_phone: string, text: string) {
    return { devCode: /\d{6}/.exec(text)?.[0] };
  }
}

class MissingSender implements SmsSender {
  readonly name = 'none';
  async send(): Promise<never> {
    throw new ServiceUnavailableException('SMS delivery is not configured on this server');
  }
}

export function smsFromEnv(): SmsSender {
  const p = process.env.SMS_PROVIDER;
  if (p === 'dev') {
    if (process.env.NODE_ENV === 'production') throw new Error('SMS_PROVIDER=dev is not allowed in production');
    new Logger('Auth').warn('SMS_PROVIDER=dev: OTP codes are returned in API responses (development only).');
    return new DevSender();
  }
  return new MissingSender();
}
