import { getApiBase } from "@/shared/config/apiBase";
import type { RomGame } from "@/shared/types/rom";
import type { SearchRepository } from "../domain/SearchRepository";

export class HttpSearchRepository implements SearchRepository {
  async search(query: string): Promise<RomGame[]> {
    const base = await getApiBase();
    const res = await fetch(`${base}/api/search?q=${encodeURIComponent(query)}`);
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error || "Error al buscar juegos");
    }
    const data = await res.json();
    return data.results as RomGame[];
  }
}
