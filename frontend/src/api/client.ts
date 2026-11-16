/**
 * Typed fetch wrappers for the AccessAstana API (see docs/api.md and docs/openapi.json).
 *
 * The TypeScript types below mirror the JSON shapes of the contract one-to-one,
 * so a contract change shows up as a compile error in the components.
 */
import type { FeatureCollection, Point, Polygon, MultiPolygon } from 'geojson';

/** Base URL, e.g. "/api" (default) or "http://localhost:8000" via VITE_API_BASE. */
export const API_BASE: string = (import.meta.env.VITE_API_BASE ?? '/api').replace(/\/+$/, '');

// ---------------------------------------------------------------- enumerations
export const SEASONS = ['summer', 'winter', 'winter_severe'] as const;
export type Season = (typeof SEASONS)[number];

export const CATEGORIES = [
  'school',
  'kindergarten',
  'clinic',
  'pharmacy',
  'transit_stop',
  'grocery',
  'park',
] as const;
export type Category = (typeof CATEGORIES)[number];

/** `/accessibility` additionally accepts the composite 15-minute index. */
export type AccessCategory = Category | 'index';

export type Lang = 'en' | 'ru' | 'kk';

// ---------------------------------------------------------------- responses
export interface City {
  slug: string;
  name: Record<Lang, string>;
  /** [lon, lat] */
  center: [number, number];
  h3_resolution: number;
  population_total: number;
  attribution: string[];
}

export interface CategoryInfo {
  key: Category;
  label: string;
}

export interface SeasonInfo {
  key: Season;
  label: string;
  speed_mps: number;
  max_minutes: number;
  share_of_days: number | null;
}

export interface AccessibilityCell {
  h3: string;
  /** minutes to nearest facility (null = unreachable within 60 min) or index in [0, 1] */
  value: number | null;
  reachable: boolean;
  population: number;
}

export interface AccessibilityResponse {
  city: string;
  category: AccessCategory;
  season: Season;
  metric: 'minutes' | 'index';
  max_minutes: number;
  cells: AccessibilityCell[];
}

export interface DistrictCategoryStats {
  /** keys are thresholds in minutes as strings: "5", "10", "15" */
  share_within: Record<string, number>;
  share_reachable: number;
  mean_minutes: number | null;
}

export interface DistrictSummary {
  id: number | null;
  name: string;
  population: number;
  index: number | null;
  categories: Partial<Record<Category, DistrictCategoryStats>>;
}

export interface DistrictsSummaryResponse {
  city: string;
  season: Season;
  thresholds: number[];
  districts: DistrictSummary[];
  city_total: DistrictSummary;
}

export type DistrictsGeoJSON = FeatureCollection<
  Polygon | MultiPolygon,
  { id: number; name: string; name_en: string | null }
>;

export type PoisGeoJSON = FeatureCollection<
  Point,
  { id: number; name: string | null; category: Category }
>;

/** Aggregate metrics shared by /scenarios and /optimize. */
export interface Metrics {
  population_reachable: number;
  share_reachable: number;
  mean_minutes: number | null;
}

export interface ScenarioRequest {
  city: string;
  category: Category;
  season: Season;
  add: { lon: number; lat: number; name: string }[];
  remove: number[];
  save: boolean;
  name: string | null;
}

export interface ChangedCell {
  h3: string;
  before: number | null;
  after: number | null;
  reachable_after: boolean;
}

export interface ScenarioResponse {
  scenario_id: number | null;
  before: Metrics;
  after: Metrics;
  changed_cells: ChangedCell[];
}

export type OptimizeMethod = 'max_covering' | 'p_median';

export interface OptimizeRequest {
  city: string;
  category: Category;
  season: Season;
  k: number;
  method: OptimizeMethod;
}

export interface OptimizeLocation {
  h3: string;
  lon: number;
  lat: number;
  population_gain: number;
}

export interface OptimizeResponse {
  method: OptimizeMethod;
  k: number;
  status: string;
  solve_seconds: number;
  locations: OptimizeLocation[];
  before: Metrics;
  after: Metrics;
}

// ---------------------------------------------------------------- transport
/** Error carrying the HTTP status (0 = network error / backend unreachable). */
export class ApiError extends Error {
  readonly status: number;
  constructor(status: number, message: string) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

type Query = Record<string, string | number | undefined>;

function buildUrl(path: string, query?: Query): string {
  const params = new URLSearchParams();
  for (const [k, v] of Object.entries(query ?? {})) {
    if (v !== undefined) params.set(k, String(v));
  }
  const qs = params.toString();
  return `${API_BASE}${path}${qs ? `?${qs}` : ''}`;
}

async function request<T>(path: string, init: RequestInit & { query?: Query } = {}): Promise<T> {
  const { query, ...rest } = init;
  let res: Response;
  try {
    res = await fetch(buildUrl(path, query), {
      ...rest,
      headers: { Accept: 'application/json', ...(rest.headers ?? {}) },
    });
  } catch (e) {
    // Aborts must propagate unchanged so callers can ignore them.
    if (e instanceof DOMException && e.name === 'AbortError') throw e;
    throw new ApiError(0, 'Network error: API is unreachable');
  }
  if (!res.ok) {
    // FastAPI reports errors as {"detail": "..."} (or a list for validation errors).
    let detail = res.statusText;
    try {
      const body: unknown = await res.json();
      if (body && typeof body === 'object' && 'detail' in body) {
        const d = (body as { detail: unknown }).detail;
        detail = typeof d === 'string' ? d : JSON.stringify(d);
      }
    } catch {
      /* non-JSON error body: keep statusText */
    }
    throw new ApiError(res.status, `HTTP ${res.status}: ${detail}`);
  }
  return (await res.json()) as T;
}

function postJson<T>(path: string, body: unknown, signal?: AbortSignal): Promise<T> {
  return request<T>(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    signal,
  });
}

// ---------------------------------------------------------------- endpoints
export const api = {
  cities: (signal?: AbortSignal) => request<City[]>('/cities', { signal }),

  categories: (signal?: AbortSignal) => request<CategoryInfo[]>('/categories', { signal }),

  seasons: (city: string, signal?: AbortSignal) =>
    request<SeasonInfo[]>('/seasons', { query: { city }, signal }),

  accessibility: (city: string, category: AccessCategory, season: Season, signal?: AbortSignal) =>
    request<AccessibilityResponse>('/accessibility', {
      query: { city, category, season, format: 'json' },
      signal,
    }),

  districtsSummary: (city: string, season: Season, signal?: AbortSignal) =>
    request<DistrictsSummaryResponse>('/districts/summary', { query: { city, season }, signal }),

  districts: (city: string, signal?: AbortSignal) =>
    request<DistrictsGeoJSON>('/districts', { query: { city }, signal }),

  pois: (city: string, category: Category, signal?: AbortSignal) =>
    request<PoisGeoJSON>('/pois', { query: { city, category }, signal }),

  scenario: (body: ScenarioRequest, signal?: AbortSignal) =>
    postJson<ScenarioResponse>('/scenarios', body, signal),

  optimize: (body: OptimizeRequest, signal?: AbortSignal) =>
    postJson<OptimizeResponse>('/optimize', body, signal),
};

/** Direct link (not fetched by JS): the browser downloads the PDF itself. */
export const reportUrl = (city: string): string =>
  `${API_BASE}/reports/${encodeURIComponent(city)}.pdf`;

export function errorMessage(e: unknown): string {
  return e instanceof Error ? e.message : String(e);
}
