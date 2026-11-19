import { Controller, Get, Header } from '@nestjs/common';
import { ApiOperation, ApiTags } from '@nestjs/swagger';
import type { EmergencyNumber } from '@elaka360/shared';
import { Db } from '../db/db.service';

/** Only hotlines backed by official or secondary evidence are public (unverified numbers are never shown as callable). */
export const EMERGENCY_SQL = `
SELECT number, name_bn, name_en, category, verified, evidence_level::text, notes FROM public_emergency_numbers ORDER BY sort_order`;

@ApiTags('emergency')
@Controller('v1/emergency-numbers')
export class EmergencyController {
  constructor(private readonly db: Db) {}

  @Get()
  @Header('Cache-Control', 'public, max-age=300, stale-while-revalidate=86400')
  @ApiOperation({ summary: 'National hotlines with official or secondary evidence' })
  list(): Promise<EmergencyNumber[]> {
    return this.db.many<EmergencyNumber>(EMERGENCY_SQL);
  }
}
