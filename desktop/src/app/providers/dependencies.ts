import { ListConsoleGamesUseCase } from "@/features/catalog/application/ListConsoleGamesUseCase";
import { ListConsolesUseCase } from "@/features/catalog/application/ListConsolesUseCase";
import { HttpCatalogRepository } from "@/features/catalog/infrastructure/HttpCatalogRepository";
import { StartDownloadUseCase } from "@/features/download/application/StartDownloadUseCase";
import { HttpDownloadRepository } from "@/features/download/infrastructure/HttpDownloadRepository";
import { SearchGamesUseCase } from "@/features/search/application/SearchGamesUseCase";
import { HttpSearchRepository } from "@/features/search/infrastructure/HttpSearchRepository";
import { LocalSettingsStore } from "@/features/settings/infrastructure/LocalSettingsStore";

const searchRepo = new HttpSearchRepository();
const catalogRepo = new HttpCatalogRepository();
const downloadRepo = new HttpDownloadRepository();
const settingsStore = new LocalSettingsStore();

export const deps = {
  searchGames: new SearchGamesUseCase(searchRepo),
  listConsoles: new ListConsolesUseCase(catalogRepo),
  listConsoleGames: new ListConsoleGamesUseCase(catalogRepo),
  startDownload: new StartDownloadUseCase(downloadRepo),
  downloadRepo,
  settingsStore,
};
