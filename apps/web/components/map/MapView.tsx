'use client';

import { useEffect, useRef, useState } from 'react';
import { useLocale, useTranslations } from 'next-intl';
import { useRouter } from '@/i18n/navigation';
import { localePath } from '@/lib/links';
import { areaLabel, localName } from '@/lib/locale';
import type { Map as MlMap, GeoJSONSource, LngLatBoundsLike } from 'maplibre-gl';
import type { FeatureCollection, MultiPolygon } from 'geojson';
import 'maplibre-gl/dist/maplibre-gl.css';

/** Default basemap: OpenFreeMap (free, no key). Override with NEXT_PUBLIC_MAP_STYLE_URL (e.g. self-hosted PMTiles style). */
const STYLE_URL = process.env.NEXT_PUBLIC_MAP_STYLE_URL ?? 'https://tiles.openfreemap.org/styles/positron';
const BD_BOUNDS: LngLatBoundsLike = [[88.0, 20.6], [92.7, 26.7]];

const CATEGORIES = ['education', 'health', 'government', 'religious', 'emergency', 'tourism', 'business', 'transport', 'agriculture', 'finance', 'other'];

/** Pin colours come from the design tokens (packages/ui/tokens.css), so map and UI never drift apart. */
function tokenColors(): { pins: string[]; primary: string; secondary: string } {
  const cs = getComputedStyle(document.documentElement);
  const v = (name: string, fb: string) => cs.getPropertyValue(name).trim() || fb;
  return {
    pins: CATEGORIES.flatMap((c) => [c, v(`--e360-cat-${c}`, '#6b7a75')]),
    primary: v('--e360-primary', '#075b3b'),
    secondary: v('--e360-secondary', '#137a52'),
  };
}

type DistrictFC = FeatureCollection<MultiPolygon, { district_id: number; division_id: number; name_bn: string; name_en: string; path: string }>;

export interface MapViewProps {
  /** Highlight + fit these districts. */
  districtIds?: number[];
  /** Highlight + fit all districts of this division. */
  divisionId?: number;
  /** Load pins for this area id (all of Bangladesh when omitted). */
  areaId?: number;
  category?: string;
  className?: string;
  /** Click a district to open its page. */
  linkDistricts?: boolean;
  /** Single-place mode: centre on this [lon, lat] with a marker (no pins layer). */
  point?: [number, number];
}

function bboxOf(features: DistrictFC['features']): LngLatBoundsLike | null {
  let minX = 180, minY = 90, maxX = -180, maxY = -90;
  for (const f of features)
    for (const poly of f.geometry.coordinates)
      for (const [x, y] of poly[0] ?? []) {
        if (x === undefined || y === undefined) continue;
        minX = Math.min(minX, x); minY = Math.min(minY, y); maxX = Math.max(maxX, x); maxY = Math.max(maxY, y);
      }
  return minX <= maxX ? [[minX, minY], [maxX, maxY]] : null;
}

function placesUrl(areaId?: number, category?: string) {
  const p = new URLSearchParams();
  if (areaId) p.set('area_id', String(areaId));
  if (category) p.set('category', category);
  return `/api/places-geo?${p}`;
}

export function MapView({ districtIds, divisionId, areaId, category, className = 'h-80', linkDistricts = true, point }: MapViewProps) {
  const el = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MlMap | null>(null);
  const categoryRef = useRef(category);
  categoryRef.current = category;
  const router = useRouter(); // locale-aware: '/p/x' opens '/en/p/x' on English pages
  const locale = useLocale();
  const t = useTranslations('Map');
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [{ default: maplibregl }, districts] = await Promise.all([
          import('maplibre-gl'),
          fetch('/geo/districts.json').then((r) => r.json() as Promise<DistrictFC>),
        ]);
        if (cancelled || !el.current) return;
        const focus = districts.features.filter(
          (f) => (districtIds?.includes(f.properties.district_id) ?? false) || f.properties.division_id === divisionId,
        );
        const colors = tokenColors();
        const map = new maplibregl.Map({
          container: el.current,
          style: STYLE_URL,
          ...(point ? { center: point, zoom: 14 } : { bounds: bboxOf(focus) ?? BD_BOUNDS, fitBoundsOptions: { padding: 24 } }),
          attributionControl: { compact: true },
          cooperativeGestures: true,
        });
        mapRef.current = map;
        map.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'top-right');
        map.addControl(new maplibregl.GeolocateControl({ trackUserLocation: false }), 'top-right');

        if (point) {
          new maplibregl.Marker({ color: colors.primary }).setLngLat(point).addTo(map);
          map.on('error', () => setFailed(true));
          return;
        }
        map.on('load', () => {
          const focusIds = focus.map((f) => f.properties.district_id);
          map.addSource('districts', { type: 'geojson', data: districts, promoteId: 'district_id' });
          map.addLayer({
            id: 'district-fill', type: 'fill', source: 'districts',
            paint: {
              'fill-color': ['case', ['in', ['get', 'district_id'], ['literal', focusIds]], colors.secondary, '#a8d5ba'],
              'fill-opacity': focusIds.length ? ['case', ['in', ['get', 'district_id'], ['literal', focusIds]], 0.28, 0.08] : 0.18,
            },
          });
          map.addLayer({ id: 'district-line', type: 'line', source: 'districts', paint: { 'line-color': colors.primary, 'line-width': 0.8, 'line-opacity': 0.7 } });

          // Read the latest category on load: a chip picked before the map finished loading is not lost (finding C17).
          map.addSource('places', { type: 'geojson', data: placesUrl(areaId, categoryRef.current), cluster: true, clusterRadius: 40, clusterMaxZoom: 13 });
          map.addLayer({
            id: 'clusters', type: 'circle', source: 'places', filter: ['has', 'point_count'],
            paint: { 'circle-color': colors.primary, 'circle-radius': ['step', ['get', 'point_count'], 14, 20, 18, 100, 24], 'circle-stroke-width': 2, 'circle-stroke-color': '#fff' },
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
              'circle-radius': 7,
              'circle-color': ['match', ['get', 'category_key'], ...colors.pins, '#6b7a75'] as never,
              'circle-stroke-width': 2, 'circle-stroke-color': '#fff',
            },
          });

          map.on('click', 'pins', (e) => {
            const f = e.features?.[0];
            if (!f || f.geometry.type !== 'Point') return;
            const p = f.properties as { slug: string; name_bn: string; name_en?: string | null; area_label_bn?: string | null; area_label_en?: string | null };
            const box = document.createElement('div');
            const a = document.createElement('a');
            a.href = localePath(locale, `/p/${p.slug}`);
            a.textContent = localName({ name_bn: p.name_bn, name_en: p.name_en ?? null }, locale);
            a.style.cssText = 'font-weight:600;color:#075b3b;text-decoration:underline';
            a.addEventListener('click', (ev) => { ev.preventDefault(); router.push(`/p/${p.slug}`); });
            box.append(a);
            const label = areaLabel({ area_label_bn: p.area_label_bn ?? null, area_label_en: p.area_label_en ?? null }, locale);
            if (label) {
              const s = document.createElement('div');
              s.textContent = label;
              s.style.cssText = 'font-size:12px;color:#5c6b65';
              box.append(s);
            }
            new maplibregl.Popup({ offset: 10 }).setLngLat(f.geometry.coordinates as [number, number]).setDOMContent(box).addTo(map);
          });
          map.on('click', 'clusters', async (e) => {
            const f = e.features?.[0];
            if (!f || f.geometry.type !== 'Point') return;
            const zoom = await (map.getSource('places') as GeoJSONSource).getClusterExpansionZoom(f.properties.cluster_id as number);
            map.easeTo({ center: f.geometry.coordinates as [number, number], zoom });
          });
          if (linkDistricts) {
            map.on('click', 'district-fill', (e) => {
              if (map.queryRenderedFeatures(e.point, { layers: ['pins', 'clusters'] }).length) return;
              const path = e.features?.[0]?.properties?.path as string | undefined;
              if (path) router.push(`/${path}`);
            });
          }
          for (const layer of ['pins', 'clusters', ...(linkDistricts ? ['district-fill'] : [])]) {
            map.on('mouseenter', layer, () => (map.getCanvas().style.cursor = 'pointer'));
            map.on('mouseleave', layer, () => (map.getCanvas().style.cursor = ''));
          }
        });
        // A broken style or tile server should say so instead of leaving a blank box.
        map.on('error', (e) => {
          if (!map.isStyleLoaded()) setFailed(true);
          console.warn('map error', e.error?.message);
        });
      } catch (e) {
        console.warn('map failed to load', e);
        if (!cancelled) setFailed(true);
      }
    })();
    return () => {
      cancelled = true;
      mapRef.current?.remove();
      mapRef.current = null;
    };
    // Re-create only when the focus changes; category updates are handled below.
  }, [divisionId, areaId, districtIds?.join(','), point?.join(','), locale]);

  useEffect(() => {
    const src = mapRef.current?.getSource('places') as GeoJSONSource | undefined;
    src?.setData(placesUrl(areaId, category));
  }, [areaId, category]);

  return (
    <div className={`relative overflow-hidden rounded-card border border-line bg-tint ${className}`}>
      {/* maplibre's CSS makes the container position:relative, so size it with h-full rather than absolute inset-0 */}
      <div ref={el} className="h-full w-full" role="region" aria-label={t('label')} />
      {failed && <div className="absolute inset-0 grid place-items-center bg-tint p-4 text-center text-sm text-muted">{t('failed')}</div>}
    </div>
  );
}
