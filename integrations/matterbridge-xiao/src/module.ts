/**
 * matterbridge-xiao — exposes a Xiaomi Robot Vacuum X20+ to Matter (Apple Home,
 * Siri) by driving the `xiao web` REST API.
 *
 * Apple Home only supports robot vacuums that are standalone Matter nodes, so
 * the device is created in Matterbridge "server" mode by default: it gets its
 * own pairing code instead of living behind the Matterbridge bridge.
 */

import { MatterbridgeDynamicPlatform, type PlatformConfig, type PlatformMatterbridge } from 'matterbridge';
import { RoboticVacuumCleaner } from 'matterbridge/devices';
import { RvcCleanMode, RvcOperationalState, RvcRunMode } from 'matterbridge/matter/clusters';
import type { AnsiLogger } from 'matterbridge/logger';

import { XiaoRvcController, type RvcSink } from './controller.js';
import {
  buildAreas,
  CLEAN_MODE_QUIET,
  CLEAN_MODE_STANDARD,
  CLEAN_MODE_TURBO,
  OperationalState,
  RUN_MODE_CLEANING,
  RUN_MODE_IDLE,
  toMatterAreas,
  type AreaEntry,
  type MatterRvcState,
} from './mapping.js';
import { readConfig, type XiaoPluginConfig } from './config.js';
import { XiaoClient, type XiaoRoom } from './xiaoClient.js';

export default function initializePlugin(matterbridge: PlatformMatterbridge, log: AnsiLogger, config: PlatformConfig): XiaoPlatform {
  return new XiaoPlatform(matterbridge, log, config);
}

export class XiaoPlatform extends MatterbridgeDynamicPlatform {
  private readonly settings: XiaoPluginConfig;
  private readonly client: XiaoClient;
  private device?: RoboticVacuumCleaner;
  private controller?: XiaoRvcController;
  private pollTimer?: NodeJS.Timeout;
  private followUpTimer?: NodeJS.Timeout;

  constructor(matterbridge: PlatformMatterbridge, log: AnsiLogger, config: PlatformConfig) {
    super(matterbridge, log, config);
    if (typeof this.verifyMatterbridgeVersion !== 'function' || !this.verifyMatterbridgeVersion('3.4.0')) {
      throw new Error(`matterbridge-xiao requires Matterbridge >= 3.4.0 (found ${this.matterbridge.matterbridgeVersion})`);
    }
    this.settings = readConfig(config);
    this.client = new XiaoClient({ baseUrl: this.settings.url, token: this.settings.token });
  }

  override async onStart(reason?: string): Promise<void> {
    this.log.info(`Starting matterbridge-xiao (${reason ?? 'no reason'}) against ${this.settings.url}`);
    await this.ready;
    await this.clearSelect();

    const rooms = await this.loadRooms();
    const areas = buildAreas(rooms, this.settings.zones, this.settings.roomNames);
    for (const area of areas) {
      if (area.kind === 'room' && /^Room \d+$/.test(area.name)) {
        this.log.warn(`Room ${area.roomId} has no name; Siri will call it "${area.name}". Name it with \`xiao rooms alias ${area.roomId} "<nombre>"\` or the plugin's roomNames.`);
      }
    }
    this.log.info(`Exposing ${areas.length} area(s) to Matter: ${areas.map((a) => a.name).join(', ')}`);

    const device = this.createDevice(areas);
    const controller = new XiaoRvcController(this.client, areas, this.createSink(device), this.log);
    this.wireCommands(device, controller);
    this.device = device;
    this.controller = controller;
    await this.registerDevice(device);
  }

  override async onConfigure(): Promise<void> {
    await super.onConfigure();
    await this.controller?.refresh();
    this.pollTimer = setInterval(() => void this.controller?.refresh(), this.settings.pollIntervalSeconds * 1000);
  }

  override async onShutdown(reason?: string): Promise<void> {
    await super.onShutdown(reason);
    if (this.pollTimer) clearInterval(this.pollTimer);
    if (this.followUpTimer) clearTimeout(this.followUpTimer);
    this.pollTimer = undefined;
    this.followUpTimer = undefined;
    if (this.config.unregisterOnShutdown === true) await this.unregisterAllDevices();
  }

  private async loadRooms(): Promise<XiaoRoom[]> {
    // xiao web may still be booting when Matterbridge starts at login.
    for (let attempt = 1; attempt <= 6; attempt++) {
      try {
        return await this.client.rooms();
      } catch (error) {
        this.log.warn(`Could not read rooms from xiao web (attempt ${attempt}/6): ${String(error)}`);
        if (attempt < 6) await new Promise((resolve) => setTimeout(resolve, 5_000));
      }
    }
    this.log.error('xiao web is unreachable: exposing only the configured zones. Restart the plugin once `xiao web` is running.');
    return [];
  }

  private createDevice(areas: AreaEntry[]): RoboticVacuumCleaner {
    return new RoboticVacuumCleaner(this.settings.deviceName, this.settings.serial, {
      mode: this.settings.serverMode ? 'server' : undefined,
      currentRunMode: RUN_MODE_IDLE,
      supportedRunModes: [
        { label: 'Idle', mode: RUN_MODE_IDLE, modeTags: [{ value: RvcRunMode.ModeTag.Idle }] },
        { label: 'Cleaning', mode: RUN_MODE_CLEANING, modeTags: [{ value: RvcRunMode.ModeTag.Cleaning }] },
      ],
      currentCleanMode: CLEAN_MODE_STANDARD,
      supportedCleanModes: [
        {
          label: 'Vacuum & Mop',
          mode: CLEAN_MODE_STANDARD,
          modeTags: [{ value: RvcCleanMode.ModeTag.Vacuum }, { value: RvcCleanMode.ModeTag.Mop }, { value: RvcCleanMode.ModeTag.Auto }],
        },
        {
          label: 'Quiet',
          mode: CLEAN_MODE_QUIET,
          modeTags: [{ value: RvcCleanMode.ModeTag.Vacuum }, { value: RvcCleanMode.ModeTag.Mop }, { value: RvcCleanMode.ModeTag.Quiet }],
        },
        {
          label: 'Turbo',
          mode: CLEAN_MODE_TURBO,
          modeTags: [{ value: RvcCleanMode.ModeTag.Vacuum }, { value: RvcCleanMode.ModeTag.Mop }, { value: RvcCleanMode.ModeTag.Max }],
        },
      ],
      operationalStateList: [
        OperationalState.Stopped,
        OperationalState.Running,
        OperationalState.Paused,
        OperationalState.Error,
        OperationalState.SeekingCharger,
        OperationalState.Charging,
        OperationalState.Docked,
        OperationalState.EmptyingDustBin,
        OperationalState.CleaningMop,
        OperationalState.UpdatingMaps,
      ].map((operationalStateId) => ({ operationalStateId })),
      operationalState: RvcOperationalState.OperationalState.Docked,
      supportedAreas: toMatterAreas(areas),
      selectedAreas: [],
      currentArea: null,
      supportedMaps: [],
    });
  }

  private createSink(device: RoboticVacuumCleaner): RvcSink {
    return {
      apply: async (state: MatterRvcState) => {
        await device.setAttribute('rvcOperationalState', 'operationalState', state.operationalState, this.log);
        await device.setAttribute('rvcOperationalState', 'operationalError', { errorStateId: state.errorStateId, errorStateDetails: state.errorDetails }, this.log);
        await device.setAttribute('rvcRunMode', 'currentMode', state.runMode, this.log);
        if (state.batPercentRemaining !== null) {
          await device.setAttribute('powerSource', 'batPercentRemaining', state.batPercentRemaining, this.log);
        }
        await device.setAttribute('powerSource', 'batChargeState', state.batChargeState, this.log);
      },
    };
  }

  /** Re-read the real state shortly after a command so Home reflects what the robot actually did. */
  private scheduleFollowUp(): void {
    if (this.followUpTimer) clearTimeout(this.followUpTimer);
    this.followUpTimer = setTimeout(() => void this.controller?.refresh(), 15_000);
  }

  private wireCommands(device: RoboticVacuumCleaner, controller: XiaoRvcController): void {
    // Handlers run before Matterbridge updates the cluster state: throwing makes
    // the Matter command fail (Home/Siri report the error) and leaves state untouched.
    const run = async (label: string, action: () => Promise<unknown>) => {
      try {
        await action();
      } catch (error) {
        this.log.error(`${label} failed: ${String(error)}`);
        throw error;
      } finally {
        this.scheduleFollowUp();
      }
    };

    device
      .addCommandHandler('ServiceArea.selectAreas', ({ request }) => {
        controller.selectAreas([...request.newAreas]);
      })
      .addCommandHandler('RvcCleanMode.changeToMode', ({ request }) => {
        controller.setCleanMode(request.newMode);
      })
      .addCommandHandler('RvcRunMode.changeToMode', async ({ request }) => {
        if (request.newMode === RUN_MODE_CLEANING) {
          await run('Start cleaning', () => controller.startCleaning());
        } else if (request.newMode === RUN_MODE_IDLE && controller.state?.runMode === RUN_MODE_CLEANING) {
          await run('Return to dock', () => controller.goHome());
        }
      })
      .addCommandHandler('RvcOperationalState.pause', async () => {
        await run('Pause', () => controller.stop());
      })
      .addCommandHandler('RvcOperationalState.resume', async () => {
        await run('Resume', () => controller.startCleaning());
      })
      .addCommandHandler('RvcOperationalState.goHome', async () => {
        await run('Go home', () => controller.goHome());
      })
      .addCommandHandler('Identify.identify', async () => {
        await run('Identify', () => controller.identify());
      });
  }
}
