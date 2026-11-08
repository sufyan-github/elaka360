import { BadRequestException, Controller, Get, Query } from '@nestjs/common';
import { SearchService, type SearchResult } from './search.service';

@Controller('v1/search')
export class SearchController {
  constructor(private readonly search: SearchService) {}

  /** GET /v1/search?q=রাজশাহী  or  ?q=rajshahi  (typo-tolerant when Typesense is on) */
  @Get()
  find(@Query('q') raw?: string): Promise<SearchResult> {
    const q = (raw ?? '').trim();
    if (q.length < 2) throw new BadRequestException('q must be at least 2 characters');
    if (q.length > 80) throw new BadRequestException('q is too long');
    return this.search.search(q);
  }
}
