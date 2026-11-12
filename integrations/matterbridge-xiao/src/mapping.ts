/**
 * Pure translation between xiao's vocabulary and the Matter RVC clusters.
 * Kept free of Matterbridge imports so it can be unit-tested in isolation.
 */

import type { FanLevel, XiaoRoom, XiaoStatus, ZoneRect } from './xiaoClient.js';

// ── Matter enum values (RVC Operational State / Power Source, Matter 1.4) ──
// Duplicated as plain numbers on purpose: the mapping stays testable without
// loading matter.js, and these values are fixed by the Matter spec.
export const OperationalState = {
  Stopped: 0x00,
  Running: 0x01,
  Paused: 0x02,
  Error: 0x03,
  SeekingCharger: 0x40,
  Charging: 0x41,
  Docked: 0x42,
  EmptyingDustBin: 0x43,
  CleaningMop: 0x44,
  UpdatingMaps: 0x46,
} as const;

export const ErrorState = {
  NoError: 0x00,
  UnableToCompleteOperation: 0x02,
  Stuck: 0x41,
  WaterTankEmpty: 0x44,
} as const;

export const BatChargeState = { Unknown: 0, IsCharging: 1, IsAtFullCharge: 2, IsNotCharging: 3 } as const;

// ── Run modes (RVC Run Mode) ──
export const RUN_MODE_IDLE = 1;
export const RUN_MODE_CLEANING = 2;

// ── Clean modes (RVC Clean Mode) → xiao fan level ──
// The X20+ always vacuums and mops together (`xiao start` washes the mop
// first), so every mode carries both Vacuum and Mop tags and only the suction
// changes. Apple Home renders the Quiet / Auto / Max tags.
export const CLEAN_MODE_STANDARD = 1;
export const CLEAN_MODE_QUIET = 2;
export const CLEAN_MODE_TURBO = 3;

export const CLEAN_MODE_FAN: Record<number, FanLevel> = {
  [CLEAN_MODE_STANDARD]: 'standard',
  [CLEAN_MODE_QUIET]: 'silent',
  [CLEAN_MODE_TURBO]: 'turbo',
};

/** Zone area IDs live above this offset so they never collide with device room IDs. */
export const ZONE_AREA_ID_BASE = 100_000;

export interface ZoneConfig {
  name: string;
  /** "x1,y1,x2,y2" in millimetres, same format as `xiao clean -z`. */
  coords: string;
}

export interface AreaEntry {
  areaId: number;
  name: string;
  kind: 'room' | 'zone';
  roomId?: number;
  zone?: ZoneRect;
}

export function parseZoneCoords(raw: string): ZoneRect {
  const parts = raw.split(',').map((p) => p.trim());
  if (parts.length !== 4 || parts.some((p) => !/^-?\d+$/.test(p))) {
    throw new Error(`Zone coords must be "x1,y1,x2,y2" integers in mm (got "${raw}")`);
  }
  const [x1, y1, x2, y2] = parts.map(Number) as ZoneRect;
  if (x1 === x2 || y1 === y2) throw new Error(`Zone "${raw}" has zero width or height`);
  return [Math.min(x1, x2), Math.min(y1, y2), Math.max(x1, x2), Math.max(y1, y2)];
}

/**
 * Build the Service Area list: device rooms first (areaId = xiao room id),
 * then the user's named zones. `roomNames` lets the plugin config rename a
 * room for Siri without touching xiao's aliases.
 */
export function buildAreas(rooms: XiaoRoom[], zones: ZoneConfig[] = [], roomNames: Record<string, string> = {}): AreaEntry[] {
  const areas: AreaEntry[] = [];
  const seenNames = new Set<string>();
  const addName = (name: string) => {
    const key = name.trim().toLocaleLowerCase();
    if (seenNames.has(key)) throw new Error(`Duplicate area name "${name}": Siri could not tell them apart`);
    seenNames.add(key);
  };

  for (const room of rooms) {
    if (!Number.isInteger(room.id) || room.id < 0 || room.id >= ZONE_AREA_ID_BASE) continue;
    const name = (roomNames[String(room.id)] ?? room.name ?? `Room ${room.id}`).trim();
    addName(name);
    areas.push({ areaId: room.id, name, kind: 'room', roomId: room.id });
  }
  zones.forEach((zone, index) => {
    const name = zone.name.trim();
    if (!name) throw new Error(`Zone #${index + 1} has no name`);
    addName(name);
    areas.push({ areaId: ZONE_AREA_ID_BASE + index + 1, name, kind: 'zone', zone: parseZoneCoords(zone.coords) });
  });
  return areas;
}

/** Matter ServiceArea.Area structs for the RoboticVacuumCleaner constructor. */
export function toMatterAreas(areas: AreaEntry[]) {
  return areas.map((area) => ({
    areaId: area.areaId,
    mapId: null,
    areaInfo: {
      locationInfo: { locationName: area.name.slice(0, 128), floorNumber: null, areaType: null },
      landmarkInfo: null,
    },
  }));
}

export type CleanPlan =
  | { kind: 'full' }
  | { kind: 'rooms'; roomIds: number[]; ignoredZones: string[] }
  | { kind: 'zones'; zones: ZoneRect[] };

/**
 * Decide which xiao call satisfies the areas Apple Home selected.
 * The X20+ cannot mix room and zone cleaning in one job, so rooms win and the
 * zones are reported back as ignored.
 */
export function planClean(selectedAreaIds: number[], areas: AreaEntry[]): CleanPlan {
  const byId = new Map(areas.map((a) => [a.areaId, a]));
  const selected = [...new Set(selectedAreaIds)].map((id) => byId.get(id)).filter((a): a is AreaEntry => a !== undefined);
  if (selected.length === 0) return { kind: 'full' };

  const rooms = selected.filter((a) => a.kind === 'room');
  const zones = selected.filter((a) => a.kind === 'zone');
  if (rooms.length > 0) {
    return { kind: 'rooms', roomIds: rooms.map((a) => a.roomId as number), ignoredZones: zones.map((z) => z.name) };
  }
  return { kind: 'zones', zones: zones.map((z) => z.zone as ZoneRect) };
}

export interface MatterRvcState {
  operationalState: number;
  errorStateId: number;
  errorDetails: string;
  runMode: number;
  /** Matter battery percentage is in half-percent units (0-200). */
  batPercentRemaining: number | null;
  batChargeState: number;
}

const CLEANING_STATES = new Set(['Sweeping', 'Mopping', 'Sweeping And Mopping', 'Remote Clean', 'Water Inspecting']);

/** Translate `GET /api/status` into Matter RVC attribute values. */
export function mapStatus(status: XiaoStatus): MatterRvcState {
  const state = status.state ?? 'Unknown';
  let operationalState: number = OperationalState.Stopped;
  let runMode = RUN_MODE_IDLE;
  let errorStateId: number = ErrorState.NoError;
  let errorDetails = 'Fully operational';

  if (CLEANING_STATES.has(state)) {
    operationalState = OperationalState.Running;
    runMode = RUN_MODE_CLEANING;
  } else if (state === 'Go Washing' || state === 'Washing mop') {
    // Mid-job mop washes: keep the job "cleaning" so Home doesn't show it as finished.
    operationalState = OperationalState.CleaningMop;
    runMode = RUN_MODE_CLEANING;
  } else if (state === 'Building map') {
    operationalState = OperationalState.UpdatingMaps;
    runMode = RUN_MODE_CLEANING;
  } else if (state === 'Paused') {
    operationalState = OperationalState.Paused;
    runMode = RUN_MODE_CLEANING;
  } else if (state === 'Go Charging') {
    operationalState = OperationalState.SeekingCharger;
  } else if (state === 'Charging') {
    operationalState = OperationalState.Charging;
  } else if (state === 'Charging Completed' || state === 'Drying' || state === 'Upgrading') {
    operationalState = OperationalState.Docked;
  } else if (state === 'Dust Collecting') {
    operationalState = OperationalState.EmptyingDustBin;
  } else if (state === 'WashingMopPause') {
    operationalState = OperationalState.Error;
    errorStateId = ErrorState.WaterTankEmpty;
    // Matter caps errorStateDetails at 64 characters; xiao's alert text is longer.
    errorDetails = 'Refill the clean-water tank / empty the dirty-water tank';
  } else if (state === 'Error') {
    operationalState = OperationalState.Error;
    errorStateId = ErrorState.UnableToCompleteOperation;
    errorDetails = status.fault_code !== undefined ? `Vacuum fault ${status.fault_code}` : 'Vacuum reported an error';
  } else if (state === 'Idle') {
    operationalState = status.charging === 'Charging' ? OperationalState.Charging : OperationalState.Stopped;
  }

  let batChargeState: number = BatChargeState.Unknown;
  if (status.charging === 'Charging') batChargeState = BatChargeState.IsCharging;
  else if (status.charging === 'Charged' || state === 'Charging Completed') batChargeState = BatChargeState.IsAtFullCharge;
  else if (status.charging === 'Not charging' || status.charging === 'Go Charging') batChargeState = BatChargeState.IsNotCharging;

  if (batChargeState === BatChargeState.IsCharging && operationalState === OperationalState.Stopped) {
    operationalState = OperationalState.Charging;
  }

  const battery = typeof status.battery === 'number' ? Math.max(0, Math.min(100, status.battery)) : null;
  return {
    operationalState,
    errorStateId,
    errorDetails: errorDetails.slice(0, 64),
    runMode,
    batPercentRemaining: battery === null ? null : battery * 2,
    batChargeState,
  };
}
