let cachedBase: string | null = null;

export async function getApiBase(): Promise<string> {
  if (cachedBase) return cachedBase;
  if (window.romsfunDesktop) {
    cachedBase = await window.romsfunDesktop.getApiBase();
  } else {
    cachedBase = "http://127.0.0.1:8765";
  }
  return cachedBase;
}
