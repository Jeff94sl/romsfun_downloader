export interface RomGame {
  title: string;
  console: string;
  console_slug?: string;
  url: string;
}

export interface ConsoleOption {
  alias: string;
  slug: string;
  label: string;
  folder: string;
}

export interface RomFileInfo {
  name: string;
  size: string;
}

export interface DownloadResultItem {
  title: string;
  console: string;
  status: string;
  roms: RomFileInfo[];
  error?: string;
}

export interface DownloadProgressEvent {
  type: string;
  current?: number;
  total?: number;
  downloaded?: number;
  title?: string;
  console?: string;
  filename?: string;
  message?: string;
  items?: DownloadResultItem[];
  elapsed?: number;
}

export interface AppSettings {
  outputDir: string;
  unzip: boolean;
  singleVersion: boolean;
  cleanTags: boolean;
  limit: number;
}
