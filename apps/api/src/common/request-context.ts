import { randomUUID } from 'node:crypto';
import type { NextFunction, Request, Response } from 'express';

const ID_RE = /^[A-Za-z0-9._-]{8,64}$/;

/**
 * Gives every request an id (X-Request-Id, echoed back) and writes one structured access-log line.
 * The query string is never logged: it can hold coordinates (near-me) or search terms.
 */
export function requestContext(req: Request & { id?: string }, res: Response, next: NextFunction) {
  const incoming = req.header('x-request-id');
  req.id = incoming && ID_RE.test(incoming) ? incoming : randomUUID();
  res.setHeader('X-Request-Id', req.id);
  const started = process.hrtime.bigint();
  res.on('finish', () => {
    if (process.env.ACCESS_LOG === 'off') return;
    const ms = Number(process.hrtime.bigint() - started) / 1e6;
    process.stdout.write(
      JSON.stringify({ t: new Date().toISOString(), level: 'info', msg: 'request', request_id: req.id, method: req.method, path: req.path, status: res.statusCode, ms: Math.round(ms) }) + '\n',
    );
  });
  next();
}
