/** Minimal Typesense REST client (fetch-based, no extra dependency). */
export class TypesenseClient {
  constructor(private readonly url: string, private readonly apiKey: string, private readonly timeoutMs = 3000) {}

  static fromEnv(): TypesenseClient | null {
    const url = process.env.TYPESENSE_URL;
    const key = process.env.TYPESENSE_API_KEY;
    return url && key ? new TypesenseClient(url.replace(/\/+$/, ''), key) : null;
  }

  async request<T>(method: string, path: string, body?: unknown, raw = false): Promise<T> {
    const res = await fetch(`${this.url}${path}`, {
      method,
      headers: { 'X-TYPESENSE-API-KEY': this.apiKey, 'Content-Type': raw ? 'text/plain' : 'application/json' },
      body: body === undefined ? undefined : raw ? String(body) : JSON.stringify(body),
      signal: AbortSignal.timeout(path.includes('/import') ? 120000 : this.timeoutMs),
    });
    const text = await res.text();
    if (!res.ok) throw new TypesenseError(res.status, `${method} ${path} → ${res.status} ${text.slice(0, 300)}`);
    return (raw ? text : text ? JSON.parse(text) : null) as T;
  }

  health() {
    return this.request<{ ok: boolean }>('GET', '/health');
  }

  multiSearch<T>(searches: Record<string, unknown>[]) {
    return this.request<{ results: { hits?: { document: T }[]; error?: string }[] }>('POST', '/multi_search', { searches });
  }
}

export class TypesenseError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}
