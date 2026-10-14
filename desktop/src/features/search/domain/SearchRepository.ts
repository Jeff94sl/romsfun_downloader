import type { RomGame } from "@/shared/types/rom";

export interface SearchRepository {
  search(query: string): Promise<RomGame[]>;
}
