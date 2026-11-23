import type { Metadata } from 'next';
import { getTranslations, setRequestLocale } from 'next-intl/server';
import { nameOf, titleOf } from '@elaka360/shared';
import type { Geometry, Position } from 'geojson';
import { api } from '@/lib/api';
import { asLocale } from '@/lib/locale';
import { localeAlternates } from '@/lib/meta';
import { Wizard, type Type } from './Wizard';

export const dynamic = 'force-dynamic';

type Props = { params: Promise<{ locale: string }>; searchParams: Promise<{ type?: string; place?: string; area?: string }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const locale = asLocale((await params).locale);
  const t = await getTranslations({ locale, namespace: 'Wizard' });
  return { title: t('title'), robots: { index: false }, alternates: localeAlternates(locale, '/contribute/new') };
}

const TYPES: Type[] = ['new_place', 'correction', 'report', 'request', 'village_location'];
/** Levels whose boundary frames the map for a pin (closest first). */
const FRAME = ['union', 'pourashava', 'ward', 'upazila', 'city_corporation', 'district'];

function bboxOf(g: Geometry): [[number, number], [number, number]] | undefined {
  const pts: Position[] = g.type === 'Polygon' ? g.coordinates.flat() : g.type === 'MultiPolygon' ? g.coordinates.flat(2) : [];
  if (!pts.length) return undefined;
  const xs = pts.map((p) => p[0]!), ys = pts.map((p) => p[1]!);
  return [[Math.min(...xs), Math.min(...ys)], [Math.max(...xs), Math.max(...ys)]];
}

export default async function NewContribution({ params, searchParams }: Props) {
  const locale = asLocale((await params).locale);
  setRequestLocale(locale);
  const t = await getTranslations('Wizard');
  const sp = await searchParams;
  const categories = await api.categories();
  let type: Type = TYPES.includes(sp.type as Type) ? (sp.type as Type) : 'new_place';
  const place = sp.place && /^[a-z0-9-]{1,120}$/.test(sp.place) ? sp.place : undefined;
  const area = sp.area && /^[a-z0-9-]+(\/[a-z0-9-]+)*$/.test(sp.area) ? sp.area : undefined;
  // name the target area and frame the location map on the nearest area with a boundary
  let targetName: string | undefined, bounds: [[number, number], [number, number]] | undefined, outline: Geometry | undefined;
  if (area) {
    const d = await api.areaByPath(area).catch(() => null);
    if (d) {
      targetName = titleOf(d.area, locale);
      if (type === 'village_location' && d.area.level !== 'village' && d.area.level !== 'mouza') type = 'request';
      const frames = [...d.breadcrumb].reverse().filter((b) => FRAME.includes(b.level));
      for (const f of frames.slice(0, 3)) {
        const b = await api.boundary(f.id).catch(() => null);
        if (b?.geometry) { outline = b.geometry; bounds = bboxOf(b.geometry); break; }
      }
    }
  }
  if (type === 'village_location' && !area) type = 'request';
  return (
    <div className="mx-auto max-w-xl pt-6">
      <h1 className="text-2xl font-bold">{t('title')}</h1>
      <Wizard categories={categories.map((c) => ({ key: c.key, name: nameOf(c, locale), subs: (c.children ?? []).map((s) => ({ key: s.key, name: nameOf(s, locale) })) }))}
        initialType={type} targetPlace={place} targetArea={area} targetName={targetName} bounds={bounds} outline={outline} />
    </div>
  );
}
