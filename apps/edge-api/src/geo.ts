/** Geometry helpers for the edge API (no PostGIS on D1). */

type Ring = number[][];
type Polygon = Ring[];
export interface Geometry { type: string; coordinates: unknown }

function inRing(x: number, y: number, ring: Ring): boolean {
  let inside = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const [xi, yi] = ring[i] as [number, number];
    const [xj, yj] = ring[j] as [number, number];
    if ((yi > y) !== (yj > y) && x < ((xj - xi) * (y - yi)) / (yj - yi || 1e-12) + xi) inside = !inside;
  }
  return inside;
}

/** Point-in-polygon (even-odd rule, holes respected) for GeoJSON Polygon / MultiPolygon. */
export function covers(g: Geometry, lon: number, lat: number): boolean {
  const polys: Polygon[] = g.type === 'Polygon' ? [g.coordinates as Polygon] : g.type === 'MultiPolygon' ? (g.coordinates as Polygon[]) : [];
  return polys.some((p) => p[0] !== undefined && inRing(lon, lat, p[0]) && !p.slice(1).some((h) => inRing(lon, lat, h)));
}

/**
 * Distance in metres on the WGS84 ellipsoid (Vincenty's inverse formula), matching PostGIS ST_Distance on geography.
 * Falls back to the great-circle distance in the rare case the iteration does not converge (near-antipodal points).
 */
export function distanceM(lat1: number, lon1: number, lat2: number, lon2: number): number {
  const a = 6378137, f = 1 / 298.257223563, b = a * (1 - f), r = Math.PI / 180;
  const L = (lon2 - lon1) * r;
  const U1 = Math.atan((1 - f) * Math.tan(lat1 * r)), U2 = Math.atan((1 - f) * Math.tan(lat2 * r));
  const sinU1 = Math.sin(U1), cosU1 = Math.cos(U1), sinU2 = Math.sin(U2), cosU2 = Math.cos(U2);
  let lambda = L;
  for (let i = 0; i < 100; i++) {
    const sinL = Math.sin(lambda), cosL = Math.cos(lambda);
    const sinSigma = Math.sqrt((cosU2 * sinL) ** 2 + (cosU1 * sinU2 - sinU1 * cosU2 * cosL) ** 2);
    if (sinSigma === 0) return 0;
    const cosSigma = sinU1 * sinU2 + cosU1 * cosU2 * cosL;
    const sigma = Math.atan2(sinSigma, cosSigma);
    const sinAlpha = (cosU1 * cosU2 * sinL) / sinSigma;
    const cos2Alpha = 1 - sinAlpha ** 2;
    const cos2SigmaM = cos2Alpha ? cosSigma - (2 * sinU1 * sinU2) / cos2Alpha : 0;
    const C = (f / 16) * cos2Alpha * (4 + f * (4 - 3 * cos2Alpha));
    const prev = lambda;
    lambda = L + (1 - C) * f * sinAlpha * (sigma + C * sinSigma * (cos2SigmaM + C * cosSigma * (-1 + 2 * cos2SigmaM ** 2)));
    if (Math.abs(lambda - prev) < 1e-12) {
      const u2 = (cos2Alpha * (a * a - b * b)) / (b * b);
      const A = 1 + (u2 / 16384) * (4096 + u2 * (-768 + u2 * (320 - 175 * u2)));
      const B = (u2 / 1024) * (256 + u2 * (-128 + u2 * (74 - 47 * u2)));
      const dSigma = B * sinSigma * (cos2SigmaM + (B / 4) * (cosSigma * (-1 + 2 * cos2SigmaM ** 2)
        - (B / 6) * cos2SigmaM * (-3 + 4 * sinSigma ** 2) * (-3 + 4 * cos2SigmaM ** 2)));
      return b * A * (sigma - dSigma);
    }
  }
  const h = Math.sin(((lat2 - lat1) * r) / 2) ** 2 + Math.cos(lat1 * r) * Math.cos(lat2 * r) * Math.sin(((lon2 - lon1) * r) / 2) ** 2;
  return 2 * 6371008.8 * Math.asin(Math.sqrt(h));
}
