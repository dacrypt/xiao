import { describe, expect, it, vi } from 'vitest';

import { XiaoApiError, XiaoClient } from '../src/xiaoClient.js';

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });
}

describe('XiaoClient', () => {
  it('sends the dashboard CSRF header, the token and a JSON body', async () => {
    const fetchImpl = vi.fn().mockResolvedValue(jsonResponse({ ok: true, code: 0 }));
    const client = new XiaoClient({ baseUrl: 'http://127.0.0.1:8120/', token: 'secret', fetchImpl });

    await client.cleanRooms([2, 3], 'turbo');

    const [url, init] = fetchImpl.mock.calls[0];
    expect(url).toBe('http://127.0.0.1:8120/api/clean/rooms');
    expect(init.method).toBe('POST');
    expect(init.headers).toMatchObject({ 'X-Xiao-Client': 'dashboard', 'X-Xiao-Token': 'secret', 'Content-Type': 'application/json' });
    expect(JSON.parse(init.body)).toEqual({ room_ids: [2, 3], fan: 'turbo' });
  });

  it('omits the token header when none is configured', async () => {
    const fetchImpl = vi.fn().mockResolvedValue(jsonResponse({ state: 'Charging' }));
    await new XiaoClient({ baseUrl: 'http://x', fetchImpl }).status();
    expect(fetchImpl.mock.calls[0][1].headers).not.toHaveProperty('X-Xiao-Token');
  });

  it('posts zones to the zone endpoint', async () => {
    const fetchImpl = vi.fn().mockResolvedValue(jsonResponse({ ok: true, code: 0 }));
    await new XiaoClient({ baseUrl: 'http://x', fetchImpl }).cleanZones([[0, 0, 100, 100]]);
    expect(fetchImpl.mock.calls[0][0]).toBe('http://x/api/clean/zone');
    expect(JSON.parse(fetchImpl.mock.calls[0][1].body)).toEqual({ zones: [[0, 0, 100, 100]], fan: null });
  });

  it('maps fan names to the speed levels xiao web expects', async () => {
    const fetchImpl = vi.fn().mockResolvedValue(jsonResponse({ ok: true, code: 0 }));
    await new XiaoClient({ baseUrl: 'http://x', fetchImpl }).setFan('silent');
    expect(JSON.parse(fetchImpl.mock.calls[0][1].body)).toEqual({ level: 0 });
  });

  it('throws when xiao saw the robot stay docked after a room clean', async () => {
    const fetchImpl = vi.fn().mockResolvedValue(jsonResponse({ ok: true, code: 0, verified_started: false, warning: 'still docked' }));
    await expect(new XiaoClient({ baseUrl: 'http://x', fetchImpl }).cleanRooms([8])).rejects.toThrow('still docked');
  });

  it('throws when the vacuum rejects an action', async () => {
    const fetchImpl = vi.fn().mockResolvedValue(jsonResponse({ ok: false, code: -9999 }));
    await expect(new XiaoClient({ baseUrl: 'http://x', fetchImpl }).start()).rejects.toThrow(/rejected by the vacuum \(code -9999\)/);
  });

  it('surfaces HTTP errors with the server detail', async () => {
    const fetchImpl = vi.fn().mockResolvedValue(jsonResponse({ detail: 'Unauthorized' }, 401));
    await expect(new XiaoClient({ baseUrl: 'http://x', fetchImpl }).status()).rejects.toThrow('GET /api/status → HTTP 401: Unauthorized');
  });

  it('explains connection failures', async () => {
    const fetchImpl = vi.fn().mockRejectedValue(new TypeError('fetch failed'));
    const promise = new XiaoClient({ baseUrl: 'http://x', fetchImpl }).status();
    await expect(promise).rejects.toBeInstanceOf(XiaoApiError);
    await expect(promise).rejects.toThrow(/is `xiao web` running/);
  });
});
