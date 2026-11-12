/**
 * Behaviour of the bridged vacuum, independent of Matterbridge so it can be
 * tested with a fake client and sink. The platform wires Matter commands to
 * these methods and pushes `MatterRvcState` updates back through the sink.
 */

import { CLEAN_MODE_FAN, CLEAN_MODE_STANDARD, mapStatus, planClean, type AreaEntry, type CleanPlan, type MatterRvcState } from './mapping.js';
import type { XiaoClient } from './xiaoClient.js';

export interface RvcSink {
  apply(state: MatterRvcState): Promise<void>;
}

export interface ControllerLog {
  info(message: string): void;
  warn(message: string): void;
  error(message: string): void;
}

type ClientLike = Pick<XiaoClient, 'status' | 'start' | 'stop' | 'dock' | 'find' | 'setFan' | 'cleanRooms' | 'cleanZones'>;

export class XiaoRvcController {
  private selectedAreas: number[] = [];
  private cleanMode = CLEAN_MODE_STANDARD;
  private lastState?: MatterRvcState;

  constructor(
    private readonly client: ClientLike,
    private readonly areas: AreaEntry[],
    private readonly sink: RvcSink,
    private readonly log: ControllerLog,
  ) {}

  get state(): MatterRvcState | undefined {
    return this.lastState;
  }

  selectAreas(areaIds: number[]): void {
    const names = areaIds.map((id) => this.areas.find((a) => a.areaId === id)?.name ?? `#${id}`);
    this.log.info(`Selected areas: ${names.length ? names.join(', ') : '(whole house)'}`);
    this.selectedAreas = [...areaIds];
  }

  setCleanMode(mode: number): void {
    if (CLEAN_MODE_FAN[mode] === undefined) {
      this.log.warn(`Ignoring unknown clean mode ${mode}`);
      return;
    }
    this.cleanMode = mode;
  }

  /** Start cleaning whatever Apple Home selected; nothing selected = whole house. */
  async startCleaning(): Promise<CleanPlan> {
    const fan = CLEAN_MODE_FAN[this.cleanMode];
    const plan = planClean(this.selectedAreas, this.areas);
    if (plan.kind === 'rooms') {
      if (plan.ignoredZones.length) {
        this.log.warn(`The X20+ cannot clean rooms and zones in one job; ignoring zones: ${plan.ignoredZones.join(', ')}`);
      }
      this.log.info(`Cleaning rooms ${plan.roomIds.join(', ')} (fan ${fan})`);
      const result = await this.client.cleanRooms(plan.roomIds, fan);
      if (result.warning) this.log.warn(result.warning);
    } else if (plan.kind === 'zones') {
      this.log.info(`Cleaning ${plan.zones.length} zone(s) (fan ${fan})`);
      await this.client.cleanZones(plan.zones, fan);
    } else {
      this.log.info(`Cleaning the whole house (fan ${fan})`);
      // Fan speed is best effort: some MIoT fields are only writable off-dock.
      try {
        await this.client.setFan(fan);
      } catch (error) {
        this.log.warn(`Could not set fan to ${fan} before starting: ${String(error)}`);
      }
      await this.client.start();
    }
    return plan;
  }

  /** The X20+ has no real pause in cloud mode, so Pause stops the job (same as `xiao pause`). */
  async stop(): Promise<void> {
    this.log.info('Stopping the current job (the X20+ has no pause)');
    await this.client.stop();
  }

  async goHome(): Promise<void> {
    this.log.info('Returning to the dock');
    await this.client.dock();
  }

  async identify(): Promise<void> {
    await this.client.find();
  }

  /** Poll `xiao web` and push the result into Matter. Never throws. */
  async refresh(): Promise<MatterRvcState | undefined> {
    try {
      const status = await this.client.status();
      const state = mapStatus(status);
      const previous = this.lastState;
      if (!previous || previous.operationalState !== state.operationalState || previous.runMode !== state.runMode) {
        this.log.info(`Vacuum is "${status.state ?? 'Unknown'}" (battery ${status.battery ?? '?'}%)`);
      }
      this.lastState = state;
      await this.sink.apply(state);
      return state;
    } catch (error) {
      this.log.error(`Status refresh failed: ${String(error)}`);
      return undefined;
    }
  }
}
