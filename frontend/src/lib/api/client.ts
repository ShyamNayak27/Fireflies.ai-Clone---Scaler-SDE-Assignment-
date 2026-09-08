/**
 * Thin fetch wrapper. Every backend error is problem+json (see
 * docs/ARCHITECTURE.md §6.2), so this is the one place that shape is parsed —
 * callers just get a typed value or a thrown ApiError.
 */
const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

/** Full URL for a link the browser navigates to directly rather than fetching
 * from JS — e.g. the export download, which relies on the server's own
 * Content-Disposition header rather than a client-side blob dance. */
export function apiUrl(path: string): string {
  return `${API_BASE}${path}`;
}

export class ApiError extends Error {
  constructor(
    public status: number,
    public title: string,
    detail: string,
  ) {
    super(detail);
  }
}

async function parseErrorAndThrow(res: Response): Promise<never> {
  const problem = await res.json().catch(() => null);
  throw new ApiError(
    res.status,
    problem?.title ?? "Request failed",
    problem?.detail ?? res.statusText,
  );
}

export async function apiGet<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, { cache: "no-store" });
  if (!res.ok) await parseErrorAndThrow(res);
  return res.json() as Promise<T>;
}

/** Like apiGet, but a 404 resolves to null instead of throwing — for data that
 * genuinely may not exist yet (e.g. a summary before its job has run) rather
 * than indicating something is wrong. */
export async function apiGetOptional<T>(path: string): Promise<T | null> {
  const res = await fetch(`${API_BASE}${path}`, { cache: "no-store" });
  if (res.status === 404) return null;
  if (!res.ok) await parseErrorAndThrow(res);
  return res.json() as Promise<T>;
}

export async function apiPost<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) await parseErrorAndThrow(res);
  return res.json() as Promise<T>;
}

export async function apiPatch<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) await parseErrorAndThrow(res);
  return res.json() as Promise<T>;
}

/** multipart/form-data POST — for the ingest upload endpoint, which accepts a
 * file or pasted text alongside a title. Browsers set the correct
 * multipart boundary automatically as long as Content-Type is left unset. */
export async function apiPostForm<T>(path: string, form: FormData): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, { method: "POST", body: form });
  if (!res.ok) await parseErrorAndThrow(res);
  return res.json() as Promise<T>;
}

export async function apiDelete(path: string): Promise<void> {
  const res = await fetch(`${API_BASE}${path}`, { method: "DELETE" });
  if (!res.ok) await parseErrorAndThrow(res);
}
