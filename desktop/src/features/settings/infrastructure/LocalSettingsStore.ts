import type { AppSettings } from "@/shared/types/rom";
import type { SettingsStore } from "../domain/SettingsStore";

const KEY = "romsfun.settings.v1";

const defaults: AppSettings = {
  outputDir: "",
  unzip: true,
  singleVersion: true,
  cleanTags: false,
  limit: 10,
};

export class LocalSettingsStore implements SettingsStore {
  async load(): Promise<AppSettings> {
    let outputDir = "";
    if (window.romsfunDesktop) {
      outputDir = await window.romsfunDesktop.getDefaultOutput();
    }
    try {
      const raw = localStorage.getItem(KEY);
      if (!raw) return { ...defaults, outputDir };
      return { ...defaults, outputDir, ...JSON.parse(raw) };
    } catch {
      return { ...defaults, outputDir };
    }
  }

  async save(settings: AppSettings): Promise<void> {
    localStorage.setItem(KEY, JSON.stringify(settings));
  }
}
