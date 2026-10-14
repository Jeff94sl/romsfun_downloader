import type { DownloadProgressEvent } from "@/shared/types/rom";
import type { DownloadRepository, DownloadRequest } from "../domain/DownloadRepository";

export class StartDownloadUseCase {
  constructor(private readonly repo: DownloadRepository) {}

  async execute(
    request: DownloadRequest,
    onEvent: (event: DownloadProgressEvent) => void
  ): Promise<{ jobId: string; unsubscribe: () => void }> {
    const jobId = await this.repo.start(request);
    const unsubscribe = this.repo.subscribe(jobId, onEvent);
    return { jobId, unsubscribe };
  }
}
