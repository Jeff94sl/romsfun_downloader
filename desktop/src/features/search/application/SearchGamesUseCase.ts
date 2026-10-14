import type { RomGame } from "@/shared/types/rom";
import type { SearchRepository } from "../domain/SearchRepository";

export class SearchGamesUseCase {
  constructor(private readonly repo: SearchRepository) {}

  execute(query: string): Promise<RomGame[]> {
    const trimmed = query.trim();
    if (!trimmed) return Promise.resolve([]);
    return this.repo.search(trimmed);
  }
}
