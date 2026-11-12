import { describe, expect, it } from 'vitest';

import {
  AreaType,
  BatChargeState,
  buildAreas,
  inferAreaType,
  ErrorState,
  mapStatus,
  OperationalState,
  parseZoneCoords,
  planClean,
  RUN_MODE_CLEANING,
  RUN_MODE_IDLE,
  toMatterAreas,
  ZONE_AREA_ID_BASE,
} from '../src/mapping.js';

const rooms = [
  { id: 2, name: 'Cocina', sources: ['device'] },
  { id: 3, name: 'Sala', sources: ['device'] },
];

describe('parseZoneCoords', () => {
  it('normalizes corners like `xiao clean -z`', () => {
    expect(parseZoneCoords(' 3000, 2000,1000 ,500')).toEqual([1000, 500, 3000, 2000]);
  });

  it.each(['1,2,3', '1,2,3,x', '0,0,0,100', '1.5,2,3,4'])('rejects %s', (raw) => {
    expect(() => parseZoneCoords(raw)).toThrow();
  });
});

describe('buildAreas', () => {
  it('exposes rooms with their xiao id and zones above the offset', () => {
    const areas = buildAreas(rooms, [{ name: 'Debajo del comedor', coords: '0,0,1000,1000' }]);
    expect(areas.map((a) => [a.areaId, a.name, a.kind])).toEqual([
      [2, 'Cocina', 'room'],
      [3, 'Sala', 'room'],
      [ZONE_AREA_ID_BASE + 1, 'Debajo del comedor', 'zone'],
    ]);
  });

  it('lets the plugin config rename rooms for Siri', () => {
    expect(buildAreas(rooms, [], { '3': 'Sala de estar' })[1].name).toBe('Sala de estar');
  });

  it('rejects duplicate names, which Siri could not disambiguate', () => {
    expect(() => buildAreas(rooms, [{ name: 'cocina', coords: '0,0,10,10' }])).toThrow(/Duplicate/);
  });

  it('builds Matter Service Area structs', () => {
    const [area] = toMatterAreas(buildAreas(rooms));
    expect(area).toEqual({
      areaId: 2,
      mapId: null,
      areaInfo: { locationInfo: { locationName: 'Cocina', floorNumber: null, areaType: AreaType.Kitchen }, landmarkInfo: null },
    });
  });
});

describe('planClean', () => {
  const areas = buildAreas(rooms, [{ name: 'Comedor', coords: '0,0,1000,1000' }]);

  it('cleans the whole house when nothing is selected', () => {
    expect(planClean([], areas)).toEqual({ kind: 'full' });
  });

  it('maps selected rooms to xiao room ids', () => {
    expect(planClean([3, 2, 3], areas)).toEqual({ kind: 'rooms', roomIds: [3, 2], ignoredZones: [] });
  });

  it('cleans zones when only zones are selected', () => {
    expect(planClean([ZONE_AREA_ID_BASE + 1], areas)).toEqual({ kind: 'zones', zones: [[0, 0, 1000, 1000]] });
  });

  it('prefers rooms and reports zones it had to drop', () => {
    expect(planClean([2, ZONE_AREA_ID_BASE + 1], areas)).toEqual({ kind: 'rooms', roomIds: [2], ignoredZones: ['Comedor'] });
  });

  it('ignores unknown area ids', () => {
    expect(planClean([999], areas)).toEqual({ kind: 'full' });
  });
});

describe('mapStatus', () => {
  it.each([
    ['Sweeping', OperationalState.Running, RUN_MODE_CLEANING],
    ['Sweeping And Mopping', OperationalState.Running, RUN_MODE_CLEANING],
    ['Go Washing', OperationalState.CleaningMop, RUN_MODE_CLEANING],
    ['Go Charging', OperationalState.SeekingCharger, RUN_MODE_IDLE],
    ['Charging', OperationalState.Charging, RUN_MODE_IDLE],
    ['Charging Completed', OperationalState.Docked, RUN_MODE_IDLE],
    ['Dust Collecting', OperationalState.EmptyingDustBin, RUN_MODE_IDLE],
    ['Paused', OperationalState.Paused, RUN_MODE_CLEANING],
    ['Idle', OperationalState.Stopped, RUN_MODE_IDLE],
  ])('%s → operational state %i', (state, operationalState, runMode) => {
    const mapped = mapStatus({ state, battery: 80, charging: 'Not charging' });
    expect(mapped.operationalState).toBe(operationalState);
    expect(mapped.runMode).toBe(runMode);
  });

  it('reports the state-21 tank alert as a water-tank error', () => {
    const mapped = mapStatus({ state: 'WashingMopPause', alert: '⚠️ Washing mop paused. Check clean water (refill) and dirty water (empty), then press Resume after fixing.' });
    expect(mapped.operationalState).toBe(OperationalState.Error);
    expect(mapped.errorStateId).toBe(ErrorState.WaterTankEmpty);
    expect(mapped.errorDetails.length).toBeLessThanOrEqual(64);
    expect(mapped.errorDetails).toMatch(/water/);
  });

  it('keeps fault details within the Matter 64-character limit', () => {
    expect(mapStatus({ state: 'Error', fault_code: 123456789 }).errorDetails.length).toBeLessThanOrEqual(64);
  });

  it('converts battery to Matter half-percent units and charge state', () => {
    expect(mapStatus({ state: 'Charging', battery: 57, charging: 'Charging' })).toMatchObject({
      batPercentRemaining: 114,
      batChargeState: BatChargeState.IsCharging,
    });
    expect(mapStatus({ state: 'Idle' }).batPercentRemaining).toBeNull();
  });

  it('treats an idle robot that is charging as Charging', () => {
    expect(mapStatus({ state: 'Idle', charging: 'Charging' }).operationalState).toBe(OperationalState.Charging);
  });
});

describe('inferAreaType', () => {
  it.each([
    ['Cocina', AreaType.Kitchen],
    ['New Kitchen', AreaType.Kitchen],
    ['Baño', AreaType.Bathroom],
    ['Baño principal', AreaType.PrimaryBathroom],
    ['Habitación Principal', AreaType.PrimaryBedroom],
    ['Habitación de huéspedes', AreaType.Bedroom],
    ['Sala', AreaType.LivingRoom],
    ['Pasillo', AreaType.Hallway],
    ['Lavandería', AreaType.LaundryRoom],
    ['Balcón', AreaType.Balcony],
    ['Estudio', AreaType.Study],
    ['Comedor', AreaType.Dining],
    ['Living room', AreaType.LivingRoom],
  ])('%s → %i', (name, type) => {
    expect(inferAreaType(name)).toBe(type);
  });

  it('returns null for names it cannot classify', () => {
    expect(inferAreaType('Room 5')).toBeNull();
    expect(inferAreaType('Saladero')).toBeNull();
  });
});
