import { getApiBase } from "@/shared/config/apiBase";
import type { ConsoleOption, RomGame } from "@/shared/types/rom";
import type { CatalogRepository } from "../domain/CatalogRepository";

export class HttpCatalogRepository implements CatalogRepository {
  async listConsoles(): Promise<ConsoleOption[]> {
    const base = await getApiBase();
    const res = await fetch(`${base}/api/consoles`);
    if (!res.ok) throw new Error("No se pudieron cargar las consolas");
    const data = await res.json();
    return data.consoles as ConsoleOption[];
  }

  async listByConsole(slug: string, limit: number): Promise<RomGame[]> {
    const base = await getApiBase();
    const res = await fetch(`${base}/api/console/${encodeURIComponent(slug)}?limit=${limit}`);
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error || "Error al listar juegos");
    }
    const data = await res.json();
    return data.results as RomGame[];
  }
}
