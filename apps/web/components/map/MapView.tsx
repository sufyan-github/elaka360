'use client';

import { useEffect, useRef, useState } from 'react';
import type { Map as MlMap, GeoJSONSource, LngLatBoundsLike } from 'maplibre-gl';
import type { FeatureCollection, MultiPolygon } from 'geojson';
import 'maplibre-gl/dist/maplibre-gl.css';

/** Default basemap: OpenFreeMap (free, no key). Override with NEXT_PUBLIC_MAP_STYLE_URL (e.g. self-hosted PMTiles style). */
const STYLE_URL = process.env.NEXT_PUBLIC_MAP_STYLE_URL ?? 'https://tiles.openfreemap.org/styles/positron';
const BD_BOUNDS: LngLatBoundsLike = [[88.0, 20.6], [92.7, 26.7]];

const CATEGORY_COLORS: [string, string][] = [
  ['education', '#16865b'], ['health', '#e5383b'], ['government', '#1e5bd8'], ['religious', '#7b3fc6'],
  ['emergency', '#f2994a'], ['tourism', '#0f9d7a'], ['business', '#f2994a'], ['transport', '#5b4fd6'],
  ['agriculture', '#2f9e44'], ['finance', '#1e5bd8'],
];

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

export function MapView({ districtIds, divisionId, areaId, category, className = 'h-80', linkDistricts = true }: MapViewProps) {
  const el = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MlMap | null>(null);
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
        const map = new maplibregl.Map({
          container: el.current,
          style: STYLE_URL,
          bounds: bboxOf(focus) ?? BD_BOUNDS,
          fitBoundsOptions: { padding: 24 },
          attributionControl: { compact: true },
          cooperativeGestures: true,
        });
        mapRef.current = map;
        map.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'top-right');
        map.addControl(new maplibregl.GeolocateControl({ trackUserLocation: false }), 'top-right');

        map.on('load', () => {
          const focusIds = focus.map((f) => f.properties.district_id);
          map.addSource('districts', { type: 'geojson', data: districts, promoteId: 'district_id' });
          map.addLayer({
            id: 'district-fill', type: 'fill', source: 'districts',
            paint: {
              'fill-color': ['case', ['in', ['get', 'district_id'], ['literal', focusIds]], '#16865b', '#a8d5ba'],
              'fill-opacity': focusIds.length ? ['case', ['in', ['get', 'district_id'], ['literal', focusIds]], 0.28, 0.08] : 0.18,
            },
          });
          map.addLayer({ id: 'district-line', type: 'line', source: 'districts', paint: { 'line-color': '#075b3b', 'line-width': 0.8, 'line-opacity': 0.7 } });

          map.addSource('places', { type: 'geojson', data: placesUrl(areaId, category), cluster: true, clusterRadius: 40, clusterMaxZoom: 13 });
          map.addLayer({
            id: 'clusters', type: 'circle', source: 'places', filter: ['has', 'point_count'],
            paint: { 'circle-color': '#075b3b', 'circle-radius': ['step', ['get', 'point_count'], 14, 20, 18, 100, 24], 'circle-stroke-width': 2, 'circle-stroke-color': '#fff' },
          });
          map.addLayer({
            id: 'cluster-count', type: 'symbol', source: 'places', filter: ['has', 'point_count'],
            layout: { 'text-field': ['get', 'point_count_abbreviated'], 'text-size': 12 },
            paint: { 'text-color': '#fff' },
          });
          map.addLayer({
            id: 'pins', type: 'circle', source: 'places', filter: ['!', ['has', 'point_count']],
            paint: {
              'circle-radius': 7,
              'circle-color': ['match', ['get', 'category_key'], ...CATEGORY_COLORS.flat(), '#6b7a75'] as never,
              'circle-stroke-width': 2, 'circle-stroke-color': '#fff',
            },
          });

          map.on('click', 'pins', (e) => {
            const f = e.features?.[0];
            if (!f || f.geometry.type !== 'Point') return;
            const p = f.properties as { slug: string; name_bn: string; area_label_bn?: string };
            const box = document.createElement('div');
            const a = document.createElement('a');
            a.href = `/p/${p.slug}`;
            a.textContent = p.name_bn;
            a.style.cssText = 'font-weight:600;color:#075b3b;text-decoration:underline';
            box.append(a);
            if (p.area_label_bn) {
              const s = document.createElement('div');
              s.textContent = p.area_label_bn;
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
              if (path) window.location.href = `/${path}`;
            });
          }
          for (const layer of ['pins', 'clusters', ...(linkDistricts ? ['district-fill'] : [])]) {
            map.on('mouseenter', layer, () => (map.getCanvas().style.cursor = 'pointer'));
            map.on('mouseleave', layer, () => (map.getCanvas().style.cursor = ''));
          }
        });
        map.on('error', (e) => console.warn('map error', e.error?.message));
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
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [divisionId, areaId, districtIds?.join(',')]);

  useEffect(() => {
    const src = mapRef.current?.getSource('places') as GeoJSONSource | undefined;
    src?.setData(placesUrl(areaId, category));
  }, [areaId, category]);

  return (
    <div className={`relative overflow-hidden rounded-card border border-line bg-tint ${className}`}>
      <div ref={el} className="absolute inset-0" role="region" aria-label="মানচিত্র" />
      {failed && <div className="absolute inset-0 grid place-items-center p-4 text-center text-sm text-muted">মানচিত্র লোড করা যায়নি।</div>}
    </div>
  );
}
