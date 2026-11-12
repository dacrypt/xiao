/**
 * Minimal client for the `xiao web` REST API (see the xiao README, "REST API").
 *
 * The plugin never talks to the Xiaomi cloud directly: `xiao web` owns the
 * credentials, token refresh and MIoT mapping, and this client only issues
 * the same calls the Mission Control dashboard does.
 */

export interface XiaoStatus {
  state?: string;
  battery?: number;
  charging?: string;
  fault_code?: number;
  alert?: string;
}

export interface XiaoRoom {
  id: number;
  name: string;
  sources?: string[];
}

export type FanLevel = 'silent' | 'standard' | 'medium' | 'turbo';

/** [x1, y1, x2, y2] in millimetres, as accepted by `xiao clean -z`. */
export type ZoneRect = [number, number, number, number];

interface ActionResponse {
  ok?: boolean;
  code?: number;
  warning?: string | null;
}

export type FetchLike = (input: string, init?: RequestInit) => Promise<Response>;

export class XiaoApiError extends Error {
  override name = 'XiaoApiError';
}

export interface XiaoClientOptions {
  baseUrl: string;
  token?: string;
  timeoutMs?: number;
  fetchImpl?: FetchLike;
}

export class XiaoClient {
  private readonly baseUrl: string;
  private readonly token?: string;
  private readonly timeoutMs: number;
  private readonly fetchImpl: FetchLike;

  constructor(options: XiaoClientOptions) {
    this.baseUrl = options.baseUrl.replace(/\/+$/, '');
    this.token = options.token || undefined;
    // Cloud actions on the X20+ can take several seconds (room cleans verify the robot left the dock).
    this.timeoutMs = options.timeoutMs ?? 45_000;
    this.fetchImpl = options.fetchImpl ?? ((input, init) => fetch(input, init));
  }

  status(): Promise<XiaoStatus> {
    return this.request<XiaoStatus>('GET', '/api/status');
  }

  rooms(): Promise<XiaoRoom[]> {
    return this.request<XiaoRoom[]>('GET', '/api/rooms');
  }

  start(): Promise<ActionResponse> {
    return this.action('/api/start');
  }

  stop(): Promise<ActionResponse> {
    return this.action('/api/stop');
  }

  dock(): Promise<ActionResponse> {
    return this.action('/api/dock');
  }

  find(): Promise<ActionResponse> {
    return this.action('/api/find');
  }

  setFan(fan: FanLevel): Promise<ActionResponse> {
    const level = { silent: 0, standard: 1, medium: 2, turbo: 3 }[fan];
    return this.action('/api/settings/speed', { level });
  }

  cleanRooms(roomIds: number[], fan?: FanLevel): Promise<ActionResponse> {
    return this.action('/api/clean/rooms', { room_ids: roomIds, fan: fan ?? null });
  }

  cleanZones(zones: ZoneRect[], fan?: FanLevel): Promise<ActionResponse> {
    return this.action('/api/clean/zone', { zones, fan: fan ?? null });
  }

  private async action(path: string, body?: unknown): Promise<ActionResponse> {
    const result = await this.request<ActionResponse>('POST', path, body);
    if (result.ok === false) {
      throw new XiaoApiError(`${path} was rejected by the vacuum (code ${result.code ?? '?'})`);
    }
    return result;
  }

  private async request<T>(method: 'GET' | 'POST', path: string, body?: unknown): Promise<T> {
    const headers: Record<string, string> = { 'X-Xiao-Client': 'dashboard', Accept: 'application/json' };
    if (this.token) headers['X-Xiao-Token'] = this.token;
    if (body !== undefined) headers['Content-Type'] = 'application/json';

    let response: Response;
    try {
      response = await this.fetchImpl(`${this.baseUrl}${path}`, {
        method,
        headers,
        body: body === undefined ? undefined : JSON.stringify(body),
        signal: AbortSignal.timeout(this.timeoutMs),
      });
    } catch (error) {
      throw new XiaoApiError(`${method} ${path} failed: is \`xiao web\` running at ${this.baseUrl}? (${String(error)})`);
    }

    if (!response.ok) {
      let detail = '';
      try {
        const payload = (await response.json()) as { detail?: unknown; error?: unknown };
        detail = String(payload.detail ?? payload.error ?? '');
      } catch {
        // body was not JSON
      }
      throw new XiaoApiError(`${method} ${path} → HTTP ${response.status}${detail ? `: ${detail}` : ''}`);
    }
    return (await response.json()) as T;
  }
}
