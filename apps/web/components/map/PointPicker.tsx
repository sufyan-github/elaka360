'use client';

import { useEffect, useRef, useState } from 'react';
import { useLocale, useTranslations } from 'next-intl';
import type { Map as MlMap, Marker, LngLatBoundsLike } from 'maplibre-gl';
import type { Geometry } from 'geojson';
import 'maplibre-gl/dist/maplibre-gl.css';
import { STYLE_URL, enableBanglaText, localizeBasemap, transformRequest } from './basemap';

const BD_BOUNDS: LngLatBoundsLike = [[88.0, 20.6], [92.7, 26.7]];

export interface PointPickerProps {
  value: { lat: number; lon: number } | null;
  onChange: (p: { lat: number; lon: number }) => void;
  /** Start here (the union or upazila around the place), else all of Bangladesh. */
  bounds?: [[number, number], [number, number]];
  /** Outline of that area, drawn for orientation. */
  outline?: Geometry;
  className?: string;
}

/** Tap the map (or drag the pin) to choose a point. The basemap shows roads, rivers and building outlines. */
export function PointPicker({ value, onChange, bounds, outline, className = 'h-72' }: PointPickerProps) {
  const t = useTranslations('Wizard');
  const locale = useLocale();
  const box = useRef<HTMLDivElement>(null);
  const map = useRef<MlMap | null>(null);
  const marker = useRef<Marker | null>(null);
  const change = useRef(onChange);
  change.current = onChange;
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const maplibregl = (await import('maplibre-gl')).default;
        if (cancelled || !box.current) return;
        enableBanglaText(maplibregl);
        const m = new maplibregl.Map({
          container: box.current, style: STYLE_URL, transformRequest, attributionControl: { compact: true },
          ...(value ? { center: [value.lon, value.lat] as [number, number], zoom: 15 } : { bounds: bounds ?? BD_BOUNDS, fitBoundsOptions: { padding: 16 } }),
        });
        m.on('error', (e) => { if (String((e as { error?: Error }).error?.message ?? '').toLowerCase().includes('webgl')) setFailed(true); });
        map.current = m;
        m.once('style.load', () => localizeBasemap(m, locale));
        m.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'top-right');
        m.addControl(new maplibregl.GeolocateControl({ trackUserLocation: false }), 'top-right');
        const color = getComputedStyle(document.documentElement).getPropertyValue('--e360-primary').trim() || '#075b3b';
        const place = (lon: number, lat: number) => {
          const p = { lat: Math.round(lat * 1e6) / 1e6, lon: Math.round(lon * 1e6) / 1e6 };
          if (!marker.current) {
            marker.current = new maplibregl.Marker({ color, draggable: true }).setLngLat([p.lon, p.lat]).addTo(m);
            marker.current.on('dragend', () => { const ll = marker.current!.getLngLat(); place(ll.lng, ll.lat); });
          } else marker.current.setLngLat([p.lon, p.lat]);
          change.current(p);
        };
        if (value) place(value.lon, value.lat);
        m.on('click', (e) => place(e.lngLat.lng, e.lngLat.lat));
        m.on('load', () => {
          if (!outline) return;
          m.addSource('outline', { type: 'geojson', data: { type: 'Feature', properties: {}, geometry: outline } });
          m.addLayer({ id: 'outline', type: 'line', source: 'outline', paint: { 'line-color': color, 'line-width': 2, 'line-dasharray': [2, 1] } });
        });
      } catch {
        setFailed(true);
      }
    })();
    return () => { cancelled = true; map.current?.remove(); map.current = null; marker.current = null; };
    // the map is created once; later value changes come from the map itself
  }, []);

  const [lat, setLat] = useState(value ? String(value.lat) : '');
  const [lon, setLon] = useState(value ? String(value.lon) : '');
  const typed = { lat: Number(lat), lon: Number(lon) };
  const typedOk = lat !== '' && lon !== '' && typed.lat >= 20.3 && typed.lat <= 26.8 && typed.lon >= 87.9 && typed.lon <= 92.8;
  const applyTyped = () => {
    if (!typedOk) return;
    const p = { lat: Math.round(typed.lat * 1e6) / 1e6, lon: Math.round(typed.lon * 1e6) / 1e6 };
    onChange(p);
    map.current?.easeTo({ center: [p.lon, p.lat], zoom: 15 });
    marker.current?.setLngLat([p.lon, p.lat]);
  };
  const coords = (
    <div className="flex flex-wrap items-end gap-2 text-sm">
      <label className="block">{t('latitude')}<input value={lat} onChange={(e) => setLat(e.target.value.trim())} inputMode="decimal" placeholder="24.3745" className="mt-1 w-32 rounded-chip border border-line bg-surface px-2 py-1.5 font-en" /></label>
      <label className="block">{t('longitude')}<input value={lon} onChange={(e) => setLon(e.target.value.trim())} inputMode="decimal" placeholder="88.6042" className="mt-1 w-32 rounded-chip border border-line bg-surface px-2 py-1.5 font-en" /></label>
      <button type="button" disabled={!typedOk} onClick={applyTyped} className="rounded-chip border border-line px-3 py-1.5 font-medium text-secondary disabled:opacity-40">{t('useCoordinates')}</button>
    </div>
  );
  return (
    <div className="space-y-2">
      <div className={`relative overflow-hidden rounded-card border border-line ${className}`}>
        <div ref={box} className="absolute inset-0" role="application" aria-label={t('pickOnMap')} />
        {failed && <div className="absolute inset-0 grid place-items-center bg-tint p-4 text-center text-sm text-muted">{t('mapFailed')}</div>}
      </div>
      {failed ? coords : (
        <details className="text-sm">
          <summary className="cursor-pointer text-secondary">{t('typeCoordinates')}</summary>
          <div className="mt-2">{coords}</div>
        </details>
      )}
      <p className="text-xs text-muted">{t('coordinatesHint')}</p>
    </div>
  );
}
