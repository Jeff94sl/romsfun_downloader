import type { RomGame } from "@/shared/types/rom";
import type { CatalogRepository } from "../domain/CatalogRepository";

export class ListConsoleGamesUseCase {
  constructor(private readonly repo: CatalogRepository) {}

  execute(slug: string, limit: number): Promise<RomGame[]> {
    return this.repo.listByConsole(slug, limit);
  }
}
