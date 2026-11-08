import { Controller, Get, NotFoundException, Param } from '@nestjs/common';
import type { Category } from '@elaka360/shared';
import { Db } from '../db/db.service';

export const CATEGORIES_SQL = `
SELECT id, key, parent_id, name_bn, name_en, icon, color, sort_order
FROM categories ORDER BY parent_id NULLS FIRST, sort_order`;

@Controller('v1/categories')
export class CategoriesController {
  constructor(private readonly db: Db) {}

  /** GET /v1/categories — two-level tree. */
  @Get()
  async tree(): Promise<Category[]> {
    const rows = await this.db.many<Category>(CATEGORIES_SQL);
    const top = rows.filter((c) => c.parent_id === null).map((c) => ({ ...c, children: [] as Category[] }));
    const byId = new Map(top.map((c) => [c.id, c]));
    for (const c of rows) if (c.parent_id !== null) byId.get(c.parent_id)?.children.push(c);
    return top;
  }

  @Get(':key')
  async one(@Param('key') key: string): Promise<Category> {
    const all = await this.tree();
    const found = all.find((c) => c.key === key) ?? all.flatMap((c) => c.children ?? []).find((c) => c.key === key);
    if (!found) throw new NotFoundException(`category not found: ${key}`);
    return found;
  }
}
