'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { useLocale, useTranslations } from 'next-intl';
import type { GeoJSONSource, Map as MlMap, MapLayerMouseEvent, Popup } from 'maplibre-gl';
import type { Feature, FeatureCollection, Geometry, Point } from 'geojson';
import { LEVEL_LABEL, formatNumber, type AdminLevel, type EvidenceLevel, type Locale, type PlaceSummary } from '@elaka360/shared';
import { Link, useRouter } from '@/i18n/navigation';
import { localePath } from '@/lib/links';
import { areaLabel, evidenceText, localName } from '@/lib/locale';
import 'maplibre-gl/dist/maplibre-gl.css';

const STYLE_URL = process.env.NEXT_PUBLIC_MAP_STYLE_URL ?? 'https://tiles.openfreemap.org/styles/positron';
const CATEGORIES = ['education', 'health', 'government', 'emergency', 'tourism', 'religious', 'transport', 'finance', 'agriculture', 'business', 'other'];
const REFRESH_MS = 60_000;      // live refresh while the tab is visible
const PIN_LIMIT = 5000;         // the API's per-request cap

/** Rajshahi District first, then the whole division (more areas follow as their data is collected). */
export const SCOPES = {
  district: { id: 20015, divisionId: 10002, coarse: 'upazila,city_corporation', fine: 'union,pourashava', fineZoom: 0 },
  division: { id: 10002, divisionId: 10002, coarse: 'upazila,city_corporation', fine: 'union,pourashava', fineZoom: 9.6 },
} as const;
export type ScopeKey = keyof typeof SCOPES;

type AreaProps = {
  id: number; level: AdminLevel; name_bn: string; name_en: string | null; path: string;
  evidence_level: EvidenceLevel; population_2022: number | null; place_count: number | null;
};
type AreaFC = FeatureCollection<Geometry, AreaProps>;
type PinProps = Omit<PlaceSummary, 'lat' | 'lon'>;

function tokenColors() {
  const cs = getComputedStyle(document.documentElement);
  const v = (name: string, fb: string) => cs.getPropertyValue(name).trim() || fb;
  return {
    pins: CATEGORIES.flatMap((c) => [c, v(`--e360-cat-${c}`, '#6b7a75')]),
    primary: v('--e360-primary', '#075b3b'),
    secondary: v('--e360-secondary', '#137a52'),
    accent: v('--e360-accent', '#f2994a'),
  };
}

function boundsOf(fc: FeatureCollection): [[number, number], [number, number]] | null {
  let minX = 180, minY = 90, maxX = -180, maxY = -90;
  const visit = (c: unknown): void => {
    if (Array.isArray(c) && typeof c[0] === 'number') {
      const [x, y] = c as number[];
      minX = Math.min(minX, x!); minY = Math.min(minY, y!); maxX = Math.max(maxX, x!); maxY = Math.max(maxY, y!);
    } else if (Array.isArray(c)) c.forEach(visit);
  };
  for (const f of fc.features) if (f.geometry && 'coordinates' in f.geometry) visit(f.geometry.coordinates);
  return minX <= maxX ? [[minX, minY], [maxX, maxY]] : null;
}

const empty: FeatureCollection = { type: 'FeatureCollection', features: [] };

export function LiveMap({ scope, category, layers }: {
  scope: ScopeKey;
  category: string;
  layers: { coarse: boolean; fine: boolean; places: boolean };
}) {
  const locale = useLocale() as Locale;
  const t = useTranslations('LiveMap');
  const router = useRouter();
  const el = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MlMap | null>(null);
  const popupRef = useRef<Popup | null>(null);
  const hoverRef = useRef<Popup | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const fineLoaded = useRef<string | null>(null);
  const stateRef = useRef({ scope, category, layers });
  stateRef.current = { scope, category, layers };

  const [ready, setReady] = useState(false);
  const [failed, setFailed] = useState(false);
  const [loading, setLoading] = useState(false);
  const [updated, setUpdated] = useState<Date | null>(null);
  const [inView, setInView] = useState<{ total: number; byCat: Record<string, number>; truncated: boolean }>({ total: 0, byCat: {}, truncated: false });
  const [selected, setSelected] = useState<AreaProps | null>(null);
  const [areaPlaces, setAreaPlaces] = useState<{ items: PlaceSummary[]; total: number } | null>(null);

  /** Load the pins inside the current view (plus a margin) for the active scope and category. */
  const loadPins = useCallback(async () => {
    const map = mapRef.current;
    if (!map || !map.getSource('places')) return;
    const { scope: s, category: c, layers: l } = stateRef.current;
    if (!l.places) {
      (map.getSource('places') as GeoJSONSource).setData(empty);
      setInView({ total: 0, byCat: {}, truncated: false });
      return;
    }
    const b = map.getBounds();
    const padX = (b.getEast() - b.getWest()) * 0.2, padY = (b.getNorth() - b.getSouth()) * 0.2;
    const bbox = [b.getWest() - padX, b.getSouth() - padY, b.getEast() + padX, b.getNorth() + padY].map((n) => n.toFixed(4)).join(',');
    const params = new URLSearchParams({ area_id: String(SCOPES[s].id), bbox });
    if (c) params.set('category', c);
    abortRef.current?.abort();
    const ctl = new AbortController();
    abortRef.current = ctl;
    setLoading(true);
    try {
      const res = await fetch(`/api/places-geo?${params}`, { signal: ctl.signal });
      if (!res.ok) throw new Error(String(res.status));
      const fc = (await res.json()) as FeatureCollection<Point, PinProps>;
      (map.getSource('places') as GeoJSONSource | undefined)?.setData(fc);
      const byCat: Record<string, number> = {};
      const view = map.getBounds();
      let total = 0;
      for (const f of fc.features) {
        const [x, y] = f.geometry.coordinates as [number, number];
        if (!view.contains([x, y])) continue;
        total++;
        byCat[f.properties.category_key] = (byCat[f.properties.category_key] ?? 0) + 1;
      }
      setInView({ total, byCat, truncated: fc.features.length >= PIN_LIMIT });
      setUpdated(new Date());
    } catch (e) {
      if ((e as Error).name !== 'AbortError') console.warn('pins failed', e);
    } finally {
      if (abortRef.current === ctl) setLoading(false);
    }
  }, []);

  /** Union / pourashava outlines are heavy for the whole division: fetch them once the user zooms in. */
  const loadFine = useCallback(async () => {
    const map = mapRef.current;
    if (!map || !map.getSource('fine')) return;
    const { scope: s, layers: l } = stateRef.current;
    const cfg = SCOPES[s];
    const key = `${cfg.id}:${cfg.fine}`;
    if (!l.fine || map.getZoom() < cfg.fineZoom || fineLoaded.current === key) return;
    fineLoaded.current = key;
    const res = await fetch(`/api/boundaries?area_id=${cfg.id}&levels=${cfg.fine}`);
    if (res.ok) (map.getSource('fine') as GeoJSONSource).setData((await res.json()) as AreaFC);
    else fineLoaded.current = null;
  }, []);

  // Create the map once.
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const { default: maplibregl } = await import('maplibre-gl');
        if (cancelled || !el.current) return;
        const colors = tokenColors();
        const map = new maplibregl.Map({
          container: el.current, style: STYLE_URL, center: [88.6, 24.4], zoom: 8.5,
          attributionControl: { compact: true }, cooperativeGestures: true,
        });
        mapRef.current = map;
        map.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'top-right');
        map.addControl(new maplibregl.GeolocateControl({ trackUserLocation: true }), 'top-right');
        map.addControl(new maplibregl.ScaleControl({ unit: 'metric' }), 'bottom-left');
        map.on('error', (e) => {
          if (!map.isStyleLoaded()) setFailed(true);
          console.warn('map error', e.error?.message);
        });
        map.on('load', () => {
          // outlines: coarse (upazila + city corporation), fine (union + pourashava), selected area on top
          for (const id of ['coarse', 'fine']) map.addSource(id, { type: 'geojson', data: empty, promoteId: 'id' });
          map.addLayer({
            id: 'fine-fill', type: 'fill', source: 'fine',
            paint: { 'fill-color': colors.secondary, 'fill-opacity': ['case', ['boolean', ['feature-state', 'hover'], false], 0.18, 0.03] },
          });
          map.addLayer({ id: 'fine-line', type: 'line', source: 'fine', paint: { 'line-color': colors.secondary, 'line-width': 0.7, 'line-opacity': 0.7, 'line-dasharray': [2, 1] } });
          map.addLayer({
            id: 'coarse-fill', type: 'fill', source: 'coarse',
            paint: { 'fill-color': colors.primary, 'fill-opacity': ['case', ['boolean', ['feature-state', 'hover'], false], 0.14, 0.04] },
          });
          map.addLayer({ id: 'coarse-line', type: 'line', source: 'coarse', paint: { 'line-color': colors.primary, 'line-width': 1.4, 'line-opacity': 0.85 } });
          map.addLayer({
            id: 'selected-line', type: 'line', source: 'fine',
            filter: ['==', ['id'], -1], paint: { 'line-color': colors.accent, 'line-width': 3 },
          });
          map.addLayer({
            id: 'selected-coarse-line', type: 'line', source: 'coarse',
            filter: ['==', ['id'], -1], paint: { 'line-color': colors.accent, 'line-width': 3 },
          });

          map.addSource('places', { type: 'geojson', data: empty, cluster: true, clusterRadius: 44, clusterMaxZoom: 14 });
          map.addLayer({
            id: 'clusters', type: 'circle', source: 'places', filter: ['has', 'point_count'],
            paint: {
              'circle-color': colors.primary, 'circle-opacity': 0.9,
              'circle-radius': ['step', ['get', 'point_count'], 13, 25, 17, 100, 22, 500, 28],
              'circle-stroke-width': 2, 'circle-stroke-color': '#fff',
            },
          });
          map.addLayer({
            id: 'cluster-count', type: 'symbol', source: 'places', filter: ['has', 'point_count'],
            // the basemap only serves Noto Sans; the MapLibre default font 404s
            layout: { 'text-field': ['get', 'point_count_abbreviated'], 'text-size': 12, 'text-font': ['Noto Sans Bold'] },
            paint: { 'text-color': '#fff' },
          });
          map.addLayer({
            id: 'pins', type: 'circle', source: 'places', filter: ['!', ['has', 'point_count']],
            paint: {
              'circle-radius': ['interpolate', ['linear'], ['zoom'], 9, 4, 14, 7],
              'circle-color': ['match', ['get', 'category_key'], ...colors.pins, '#6b7a75'] as never,
              'circle-stroke-width': 1.5, 'circle-stroke-color': '#fff',
            },
          });

          // hover: outline highlight + name tooltip (desktop)
          hoverRef.current = new maplibregl.Popup({ closeButton: false, closeOnClick: false, offset: 8, className: 'e360-tip' });
          let hovered: { source: string; id: number } | null = null;
          const setHover = (next: typeof hovered) => {
            if (hovered) map.setFeatureState(hovered, { hover: false });
            hovered = next;
            if (hovered) map.setFeatureState(hovered, { hover: true });
          };
          for (const layer of ['fine-fill', 'coarse-fill']) {
            map.on('mousemove', layer, (e: MapLayerMouseEvent) => {
              if (map.queryRenderedFeatures(e.point, { layers: ['pins', 'clusters'] }).length) return;
              const f = e.features?.[0];
              if (!f || f.id === undefined) return;
              // prefer the finer area when both layers are under the cursor
              if (layer === 'coarse-fill' && map.queryRenderedFeatures(e.point, { layers: ['fine-fill'] }).length) return;
              setHover({ source: layer === 'fine-fill' ? 'fine' : 'coarse', id: Number(f.id) });
              const p = f.properties as unknown as AreaProps;
              map.getCanvas().style.cursor = 'pointer';
              hoverRef.current?.setLngLat(e.lngLat).setText(localName({ name_bn: p.name_bn, name_en: p.name_en }, locale)).addTo(map);
            });
            map.on('mouseleave', layer, () => {
              setHover(null);
              map.getCanvas().style.cursor = '';
              hoverRef.current?.remove();
            });
          }

          // click an area: select it (side panel); pins and clusters win over areas
          map.on('click', (e) => {
            if (map.queryRenderedFeatures(e.point, { layers: ['pins', 'clusters'] }).length) return;
            // the finest visible area wins (a union over its upazila)
            const hit = map.queryRenderedFeatures(e.point, { layers: ['fine-fill'] })[0]
              ?? map.queryRenderedFeatures(e.point, { layers: ['coarse-fill'] })[0];
            if (!hit) return;
            const p = hit.properties as unknown as AreaProps;
            selectArea({ ...p, id: Number(hit.id) }, hit.source === 'fine' ? 'fine' : 'coarse');
          });
          map.on('click', 'clusters', async (e) => {
            const f = e.features?.[0];
            if (!f || f.geometry.type !== 'Point') return;
            const zoom = await (map.getSource('places') as GeoJSONSource).getClusterExpansionZoom(f.properties.cluster_id as number);
            map.easeTo({ center: f.geometry.coordinates as [number, number], zoom });
          });
          map.on('click', 'pins', (e) => {
            const f = e.features?.[0] as Feature<Point, PinProps> | undefined;
            if (!f) return;
            const p = f.properties;
            const box = document.createElement('div');
            const a = document.createElement('a');
            a.href = localePath(locale, `/p/${p.slug}`);
            a.textContent = localName({ name_bn: p.name_bn, name_en: p.name_en ?? null }, locale);
            a.style.cssText = 'font-weight:600;color:#075b3b;text-decoration:underline';
            a.addEventListener('click', (ev) => { ev.preventDefault(); router.push(`/p/${p.slug}`); });
            box.append(a);
            for (const text of [areaLabel({ area_label_bn: p.area_label_bn ?? null, area_label_en: p.area_label_en ?? null }, locale), evidenceText(p.evidence_level, locale).label]) {
              if (!text) continue;
              const s = document.createElement('div');
              s.textContent = text;
              s.style.cssText = 'font-size:12px;color:#5c6b65';
              box.append(s);
            }
            popupRef.current?.remove();
            popupRef.current = new maplibregl.Popup({ offset: 10 }).setLngLat(f.geometry.coordinates as [number, number]).setDOMContent(box).addTo(map);
          });
          for (const layer of ['pins', 'clusters']) {
            map.on('mouseenter', layer, () => (map.getCanvas().style.cursor = 'pointer'));
            map.on('mouseleave', layer, () => (map.getCanvas().style.cursor = ''));
          }

          let timer: ReturnType<typeof setTimeout> | undefined;
          map.on('moveend', () => {
            clearTimeout(timer);
            timer = setTimeout(() => { void loadPins(); void loadFine(); }, 250);
          });
          setReady(true);
        });

        function selectArea(p: AreaProps, source: 'fine' | 'coarse') {
          map.setFilter('selected-line', ['==', ['id'], source === 'fine' ? p.id : -1]);
          map.setFilter('selected-coarse-line', ['==', ['id'], source === 'coarse' ? p.id : -1]);
          setSelected(p);
        }
      } catch (e) {
        console.warn('map failed to load', e);
        if (!cancelled) setFailed(true);
      }
    })();
    return () => {
      cancelled = true;
      abortRef.current?.abort();
      mapRef.current?.remove();
      mapRef.current = null;
    };
    // the map is created once per locale; scope, category and layers are applied by the effects below
  }, [locale, router, loadPins, loadFine]);

  // Scope: load outlines and fit the view.
  useEffect(() => {
    const map = mapRef.current;
    if (!ready || !map) return;
    const cfg = SCOPES[scope];
    let cancelled = false;
    fineLoaded.current = null;
    (map.getSource('fine') as GeoJSONSource).setData(empty);
    setSelected(null);
    (async () => {
      const res = await fetch(`/api/boundaries?area_id=${cfg.id}&levels=${cfg.coarse}`);
      if (cancelled || !res.ok) return;
      const fc = (await res.json()) as AreaFC;
      (map.getSource('coarse') as GeoJSONSource).setData(fc);
      const b = boundsOf(fc);
      if (b) map.fitBounds(b, { padding: 24, duration: 600 });
      void loadFine();
      void loadPins();
    })();
    return () => { cancelled = true; };
  }, [ready, scope, loadPins, loadFine]);

  // Category or layer toggles: reload pins, show/hide outlines.
  useEffect(() => {
    const map = mapRef.current;
    if (!ready || !map) return;
    const vis = (on: boolean) => (on ? 'visible' : 'none');
    for (const id of ['coarse-fill', 'coarse-line', 'selected-coarse-line']) map.setLayoutProperty(id, 'visibility', vis(layers.coarse));
    for (const id of ['fine-fill', 'fine-line', 'selected-line']) map.setLayoutProperty(id, 'visibility', vis(layers.fine));
    void loadFine();
    void loadPins();
  }, [ready, category, layers.coarse, layers.fine, layers.places, loadPins, loadFine]);

  // Live: refresh pins every minute while visible, and when the tab comes back.
  useEffect(() => {
    if (!ready) return;
    const tick = () => { if (document.visibilityState === 'visible') void loadPins(); };
    const id = setInterval(tick, REFRESH_MS);
    document.addEventListener('visibilitychange', tick);
    return () => { clearInterval(id); document.removeEventListener('visibilitychange', tick); };
  }, [ready, loadPins]);

  // Closing the panel (or switching scope) also clears the highlighted outline.
  useEffect(() => {
    const map = mapRef.current;
    if (!ready || !map || selected) return;
    for (const id of ['selected-line', 'selected-coarse-line']) map.setFilter(id, ['==', ['id'], -1]);
  }, [ready, selected]);

  // Side panel: the selected area's places, including ones without a map location.
  useEffect(() => {
    if (!selected) { setAreaPlaces(null); return; }
    let cancelled = false;
    const params = new URLSearchParams({ area_id: String(selected.id), limit: '8' });
    if (category) params.set('category', category);
    fetch(`/api/area-places?${params}`)
      .then((r) => (r.ok ? r.json() : null))
      .then((d: { items: PlaceSummary[]; total: number } | null) => { if (!cancelled) setAreaPlaces(d); })
      .catch(() => { if (!cancelled) setAreaPlaces(null); });
    return () => { cancelled = true; };
  }, [selected, category]);

  const fmt = (n: number) => formatNumber(n, locale);
  const time = updated?.toLocaleTimeString(locale === 'bn' ? 'bn-BD' : 'en-GB', { hour: '2-digit', minute: '2-digit' });
  const lvl = (l: AdminLevel) => LEVEL_LABEL[l]?.[locale === 'bn' ? 'bn' : 'en'] ?? l;

  return (
    <div className="mt-3 grid gap-3 lg:grid-cols-[1fr_320px]">
      <div className="relative h-[68dvh] min-h-[360px] overflow-hidden rounded-card border border-line bg-tint">
        {/* maplibre's CSS makes the container position:relative, so size it with h-full rather than absolute inset-0 */}
        <div ref={el} className="h-full w-full" role="region" aria-label={t('label')} />
        <div className="pointer-events-none absolute left-2 top-2 flex flex-wrap gap-1.5 text-xs">
          <span className="flex items-center gap-1.5 rounded-full bg-surface/95 px-2.5 py-1 font-medium shadow-sm" aria-live="polite">
            <span className={`h-2 w-2 rounded-full ${loading ? 'animate-pulse bg-accent' : 'bg-primary'}`} aria-hidden />
            {loading ? t('loading') : time ? t('live', { time }) : t('starting')}
          </span>
          {layers.places && (
            <span className="rounded-full bg-surface/95 px-2.5 py-1 shadow-sm">{t('inView', { n: fmt(inView.total) })}</span>
          )}
        </div>
        {inView.truncated && (
          <div className="absolute inset-x-2 bottom-8 rounded-chip bg-surface/95 px-3 py-2 text-xs shadow-sm">{t('zoomIn')}</div>
        )}
        {failed && <div className="absolute inset-0 grid place-items-center bg-tint p-4 text-center text-sm text-muted">{t('failed')}</div>}
      </div>

      <aside className="min-w-0 rounded-card border border-line bg-surface p-4 text-sm" aria-label={t('panel')}>
        {selected ? (
          <div>
            <div className="flex items-start justify-between gap-2">
              <div className="min-w-0">
                <div className="text-xs text-muted">{lvl(selected.level)}</div>
                <h2 className="text-lg font-bold">{localName({ name_bn: selected.name_bn, name_en: selected.name_en }, locale)}</h2>
              </div>
              <button type="button" onClick={() => setSelected(null)} className="rounded-chip border border-line px-2 py-1 text-xs">{t('close')}</button>
            </div>
            <div className="mt-1 text-xs text-muted">{evidenceText(selected.evidence_level, locale).label}</div>
            <dl className="mt-3 grid grid-cols-2 gap-2">
              {selected.population_2022 !== null && (
                <div className="rounded-chip bg-tint p-2"><dt className="text-xs text-muted">{t('population')}</dt><dd className="font-semibold">{fmt(selected.population_2022)}</dd></div>
              )}
              {areaPlaces && (
                <div className="rounded-chip bg-tint p-2"><dt className="text-xs text-muted">{t('places')}</dt><dd className="font-semibold">{fmt(areaPlaces.total)}</dd></div>
              )}
            </dl>
            {areaPlaces && areaPlaces.items.length > 0 && (
              <ul className="mt-3 divide-y divide-line">
                {areaPlaces.items.map((p) => (
                  <li key={p.slug} className="py-1.5">
                    <Link href={`/p/${p.slug}`} className="font-medium text-secondary underline">{localName(p, locale)}</Link>
                    {p.lat === null && <span className="ml-1 text-xs text-muted">· {t('noPin')}</span>}
                  </li>
                ))}
              </ul>
            )}
            <Link href={`/${selected.path}`} className="mt-3 inline-block font-medium text-secondary underline">{t('openArea')}</Link>
          </div>
        ) : (
          <div>
            <h2 className="font-bold">{t('inViewTitle')}</h2>
            {layers.places ? (
              <ul className="mt-2 space-y-1">
                {Object.entries(inView.byCat).sort((a, b) => b[1] - a[1]).map(([k, n]) => (
                  <li key={k} className="flex items-center justify-between gap-2">
                    <span className="flex items-center gap-2"><span className="h-2.5 w-2.5 rounded-full" style={{ background: `var(--e360-cat-${k})` }} aria-hidden />{t(`cat.${CATEGORIES.includes(k) ? k : 'other'}` as never)}</span>
                    <span className="font-medium">{fmt(n)}</span>
                  </li>
                ))}
                {inView.total === 0 && <li className="text-muted">{t('noneInView')}</li>}
              </ul>
            ) : (
              <p className="mt-2 text-muted">{t('placesOff')}</p>
            )}
            <p className="mt-3 text-xs text-muted">{t('hint')}</p>
          </div>
        )}
      </aside>
    </div>
  );
}
