import { Controller, Get } from '@nestjs/common';
import type { EmergencyNumber } from '@elaka360/shared';
import { Db } from '../db/db.service';

export const EMERGENCY_SQL = `
SELECT number, name_bn, name_en, category, verified, notes FROM emergency_numbers ORDER BY sort_order`;

@Controller('v1/emergency-numbers')
export class EmergencyController {
  constructor(private readonly db: Db) {}

  @Get()
  list(): Promise<EmergencyNumber[]> {
    return this.db.many<EmergencyNumber>(EMERGENCY_SQL);
  }
}
