import type { ConsoleOption, RomGame } from "@/shared/types/rom";

export interface CatalogRepository {
  listConsoles(): Promise<ConsoleOption[]>;
  listByConsole(slug: string, limit: number): Promise<RomGame[]>;
}
