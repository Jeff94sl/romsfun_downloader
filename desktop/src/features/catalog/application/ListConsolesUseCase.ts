import type { ConsoleOption } from "@/shared/types/rom";
import type { CatalogRepository } from "../domain/CatalogRepository";

export class ListConsolesUseCase {
  constructor(private readonly repo: CatalogRepository) {}

  execute(): Promise<ConsoleOption[]> {
    return this.repo.listConsoles();
  }
}
