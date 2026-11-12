/** Plugin configuration (matterbridge-xiao.config.json), with defaults. */

import type { ZoneConfig } from './mapping.js';

export interface XiaoPluginConfig {
  deviceName: string;
  serial: string;
  url: string;
  token: string;
  serverMode: boolean;
  pollIntervalSeconds: number;
  roomNames: Record<string, string>;
  zones: ZoneConfig[];
}

export function readConfig(config: object): XiaoPluginConfig {
  const c = config as Record<string, unknown>;
  const str = (key: string, fallback: string) => (typeof c[key] === 'string' && (c[key] as string).trim() ? (c[key] as string).trim() : fallback);
  const roomNames: Record<string, string> = {};
  // Accept either {"3": "Cocina"} or [{"id": 3, "name": "Cocina"}] (the Matterbridge UI edits arrays more easily).
  if (Array.isArray(c.roomNames)) {
    for (const entry of c.roomNames as { id?: unknown; name?: unknown }[]) {
      if (entry && entry.id !== undefined && typeof entry.name === 'string' && entry.name.trim()) roomNames[String(entry.id)] = entry.name.trim();
    }
  } else if (c.roomNames && typeof c.roomNames === 'object') {
    for (const [id, name] of Object.entries(c.roomNames as Record<string, unknown>)) {
      if (typeof name === 'string' && name.trim()) roomNames[id] = name.trim();
    }
  }
  const zones = Array.isArray(c.zones)
    ? (c.zones as { name?: unknown; coords?: unknown }[])
        .filter((z) => z && typeof z.name === 'string' && typeof z.coords === 'string')
        .map((z) => ({ name: z.name as string, coords: z.coords as string }))
    : [];
  const poll = Number(c.pollIntervalSeconds);
  return {
    deviceName: str('deviceName', 'Aspiradora'),
    serial: str('serial', 'xiao-c102gl'),
    url: str('url', 'http://127.0.0.1:8120'),
    token: str('token', process.env.XIAO_WEB_TOKEN ?? ''),
    serverMode: c.serverMode !== false,
    pollIntervalSeconds: Number.isFinite(poll) && poll >= 5 ? poll : 30,
    roomNames,
    zones,
  };
}
