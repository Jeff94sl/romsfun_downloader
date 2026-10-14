import type { AppSettings } from "@/shared/types/rom";

export interface SettingsStore {
  load(): Promise<AppSettings>;
  save(settings: AppSettings): Promise<void>;
}
