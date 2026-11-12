import { afterEach, describe, expect, it, vi } from 'vitest';

import { readConfig } from '../src/config.js';

describe('readConfig', () => {
  afterEach(() => vi.unstubAllEnvs());

  it('applies defaults suitable for a local xiao web', () => {
    vi.stubEnv('XIAO_WEB_TOKEN', '');
    expect(readConfig({ name: 'matterbridge-xiao' })).toEqual({
      deviceName: 'Aspiradora',
      serial: 'xiao-c102gl',
      url: 'http://127.0.0.1:8120',
      token: '',
      serverMode: true,
      pollIntervalSeconds: 30,
      roomNames: {},
      zones: [],
    });
  });

  it('reads room names from the UI array or a plain object', () => {
    expect(readConfig({ roomNames: [{ id: 7, name: ' Cocina nueva ' }, { id: 8 }] }).roomNames).toEqual({ '7': 'Cocina nueva' });
    expect(readConfig({ roomNames: { '3': 'Sala' } }).roomNames).toEqual({ '3': 'Sala' });
  });

  it('keeps only complete zones and clamps the poll interval', () => {
    const config = readConfig({ zones: [{ name: 'Comedor', coords: '0,0,1,1' }, { name: 'x' }], pollIntervalSeconds: 1, serverMode: false });
    expect(config.zones).toEqual([{ name: 'Comedor', coords: '0,0,1,1' }]);
    expect(config.pollIntervalSeconds).toBe(30);
    expect(config.serverMode).toBe(false);
  });

  it('falls back to XIAO_WEB_TOKEN', () => {
    vi.stubEnv('XIAO_WEB_TOKEN', 'abc');
    expect(readConfig({}).token).toBe('abc');
  });
});
