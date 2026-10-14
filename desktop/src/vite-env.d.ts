/// <reference types="vite/client" />

interface RomsfunDesktopBridge {
  getApiBase: () => Promise<string>;
  pickDirectory: (defaultPath?: string) => Promise<string | null>;
  openPath: (targetPath: string) => Promise<boolean>;
  getDefaultOutput: () => Promise<string>;
}

interface Window {
  romsfunDesktop?: RomsfunDesktopBridge;
}
