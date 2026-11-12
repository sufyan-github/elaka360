import { timingSafeEqual } from 'node:crypto';
import type { NextFunction, Request, Response } from 'express';

const IP_RE = /^[0-9a-fA-F:.]{2,45}$/;

/**
 * Visitor IP from the web/admin servers. On Cloudflare Workers every API call comes from Cloudflare's addresses, so
 * per-IP limits would lump all visitors together. When EDGE_SHARED_SECRET is set, the web and admin servers send the
 * visitor's IP in X-Edge-Client-IP together with the secret in X-Edge-Key; only then does it replace req.ip (which the
 * rate limiter and audit log use). Without a matching key the header is ignored, so callers cannot forge their IP.
 */
export function edgeClientIp(secret: string | undefined) {
  const key = secret && secret.length >= 32 ? Buffer.from(secret) : null;
  return (req: Request, _res: Response, next: NextFunction) => {
    const sent = req.headers['x-edge-key'];
    const ip = req.headers['x-edge-client-ip'];
    delete req.headers['x-edge-key'];
    if (key && typeof sent === 'string' && typeof ip === 'string' && IP_RE.test(ip)) {
      const b = Buffer.from(sent);
      if (b.length === key.length && timingSafeEqual(b, key)) {
        Object.defineProperty(req, 'ip', { value: ip, configurable: true, enumerable: true });
      }
    }
    next();
  };
}
