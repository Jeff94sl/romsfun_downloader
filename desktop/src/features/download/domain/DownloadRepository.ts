import type { DownloadProgressEvent, DownloadResultItem, RomGame } from "@/shared/types/rom";

export interface DownloadRequest {
  items?: RomGame[];
  url?: string;
  output: string;
  unzip: boolean;
  singleVersion: boolean;
  cleanTags: boolean;
}

export interface DownloadRepository {
  start(request: DownloadRequest): Promise<string>;
  subscribe(
    jobId: string,
    onEvent: (event: DownloadProgressEvent) => void,
    onError?: (error: Error) => void
  ): () => void;
  cancel(jobId: string): Promise<void>;
  getResult(jobId: string): Promise<{
    done: boolean;
    error?: string;
    result?: { items: DownloadResultItem[]; elapsed: number };
  }>;
}
