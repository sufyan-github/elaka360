import { ArgumentsHost, Catch, ExceptionFilter, HttpException, HttpStatus, Logger } from '@nestjs/common';
import type { Request, Response } from 'express';
import type { Problem } from '@elaka360/shared';

/** Every error leaves the API as RFC 9457 problem details (application/problem+json). */
@Catch()
export class ProblemFilter implements ExceptionFilter {
  private readonly log = new Logger('Error');

  catch(exception: unknown, host: ArgumentsHost) {
    const ctx = host.switchToHttp();
    const req = ctx.getRequest<Request & { id?: string }>();
    const res = ctx.getResponse<Response>();
    let status = HttpStatus.INTERNAL_SERVER_ERROR;
    let detail: string | undefined;
    let errors: Record<string, string> | undefined;
    let type = 'about:blank';

    if (exception instanceof HttpException) {
      status = exception.getStatus();
      const body = exception.getResponse();
      if (typeof body === 'string') detail = body;
      else if (body && typeof body === 'object') {
        const b = body as Record<string, unknown>;
        const msg = b.message;
        detail = Array.isArray(msg) ? msg.join('; ') : typeof msg === 'string' ? msg : typeof b.detail === 'string' ? b.detail : undefined;
        if (b.errors && typeof b.errors === 'object') errors = b.errors as Record<string, string>;
        if (typeof b.type === 'string') type = b.type;
      }
    } else if (isPgError(exception) && exception.code === '23505') {
      status = HttpStatus.CONFLICT;
      detail = 'already exists';
    } else if (isPgError(exception) && (exception.code === '23514' || exception.code === '23503' || exception.code === '22P02')) {
      status = HttpStatus.BAD_REQUEST;
      detail = 'value rejected by a data rule';
    } else {
      this.log.error(JSON.stringify({ request_id: req.id, error: (exception as Error)?.message, stack: (exception as Error)?.stack?.split('\n').slice(0, 4) }));
    }

    const problem: Problem = {
      type,
      title: HTTP_TITLES[status] ?? 'Error',
      status,
      ...(detail && status < 500 ? { detail } : {}),
      instance: req.path,
      request_id: req.id,
      ...(errors ? { errors } : {}),
    };
    res.status(status).type('application/problem+json').setHeader('Cache-Control', 'no-store');
    res.send(JSON.stringify(problem));
  }
}

function isPgError(e: unknown): e is { code: string } {
  return typeof e === 'object' && e !== null && typeof (e as { code?: unknown }).code === 'string' && /^[0-9A-Z]{5}$/.test((e as { code: string }).code);
}

const HTTP_TITLES: Record<number, string> = {
  400: 'Bad Request', 401: 'Unauthorized', 403: 'Forbidden', 404: 'Not Found', 409: 'Conflict',
  422: 'Unprocessable Content', 429: 'Too Many Requests', 500: 'Internal Server Error', 503: 'Service Unavailable',
};
