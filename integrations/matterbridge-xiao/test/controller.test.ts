import { describe, expect, it, vi } from 'vitest';

import { XiaoRvcController } from '../src/controller.js';
import { buildAreas, CLEAN_MODE_QUIET, CLEAN_MODE_TURBO, OperationalState, ZONE_AREA_ID_BASE } from '../src/mapping.js';

function setup() {
  const client = {
    status: vi.fn().mockResolvedValue({ state: 'Sweeping', battery: 90, charging: 'Not charging' }),
    start: vi.fn().mockResolvedValue({ ok: true }),
    stop: vi.fn().mockResolvedValue({ ok: true }),
    dock: vi.fn().mockResolvedValue({ ok: true }),
    find: vi.fn().mockResolvedValue({ ok: true }),
    setFan: vi.fn().mockResolvedValue({ ok: true }),
    cleanRooms: vi.fn().mockResolvedValue({ ok: true, warning: null }),
    cleanZones: vi.fn().mockResolvedValue({ ok: true }),
  };
  const sink = { apply: vi.fn().mockResolvedValue(undefined) };
  const log = { info: vi.fn(), warn: vi.fn(), error: vi.fn() };
  const areas = buildAreas([{ id: 2, name: 'Cocina' }, { id: 3, name: 'Sala' }], [{ name: 'Comedor', coords: '0,0,1000,1000' }]);
  const controller = new XiaoRvcController(client, areas, sink, log);
  return { client, sink, log, controller };
}

describe('XiaoRvcController', () => {
  it('"Oye Siri, limpia la cocina": selected room → room clean with the current fan', async () => {
    const { client, controller } = setup();
    controller.selectAreas([2]);
    await controller.startCleaning();
    expect(client.cleanRooms).toHaveBeenCalledWith([2], 'standard');
    expect(client.start).not.toHaveBeenCalled();
  });

  it('cleans the whole house when nothing is selected, setting the fan first', async () => {
    const { client, controller } = setup();
    controller.setCleanMode(CLEAN_MODE_QUIET);
    await controller.startCleaning();
    expect(client.setFan).toHaveBeenCalledWith('silent');
    expect(client.start).toHaveBeenCalledOnce();
  });

  it('still starts a full clean if the fan cannot be set while docked', async () => {
    const { client, controller, log } = setup();
    client.setFan.mockRejectedValue(new Error('code -4001'));
    await controller.startCleaning();
    expect(client.start).toHaveBeenCalledOnce();
    expect(log.warn).toHaveBeenCalled();
  });

  it('cleans configured zones with the selected fan', async () => {
    const { client, controller } = setup();
    controller.setCleanMode(CLEAN_MODE_TURBO);
    controller.selectAreas([ZONE_AREA_ID_BASE + 1]);
    await controller.startCleaning();
    expect(client.cleanZones).toHaveBeenCalledWith([[0, 0, 1000, 1000]], 'turbo');
  });

  it('warns when zones are dropped from a mixed selection', async () => {
    const { client, controller, log } = setup();
    controller.selectAreas([3, ZONE_AREA_ID_BASE + 1]);
    await controller.startCleaning();
    expect(client.cleanRooms).toHaveBeenCalledWith([3], 'standard');
    expect(log.warn).toHaveBeenCalledWith(expect.stringContaining('Comedor'));
  });

  it('propagates vacuum rejections so Siri reports the failure', async () => {
    const { client, controller } = setup();
    client.cleanRooms.mockRejectedValue(new Error('rejected'));
    controller.selectAreas([2]);
    await expect(controller.startCleaning()).rejects.toThrow('rejected');
  });

  it('ignores unknown clean modes', async () => {
    const { client, controller } = setup();
    controller.setCleanMode(42);
    await controller.startCleaning();
    expect(client.setFan).toHaveBeenCalledWith('standard');
  });

  it('pause stops the job and goHome docks', async () => {
    const { client, controller } = setup();
    await controller.stop();
    await controller.goHome();
    expect(client.stop).toHaveBeenCalledOnce();
    expect(client.dock).toHaveBeenCalledOnce();
  });

  it('refresh pushes mapped state to Matter and never throws', async () => {
    const { client, controller, sink, log } = setup();
    await controller.refresh();
    expect(sink.apply).toHaveBeenCalledWith(expect.objectContaining({ operationalState: OperationalState.Running, batPercentRemaining: 180 }));
    expect(controller.state?.operationalState).toBe(OperationalState.Running);

    client.status.mockRejectedValue(new Error('offline'));
    await expect(controller.refresh()).resolves.toBeUndefined();
    expect(log.error).toHaveBeenCalled();
  });
});
