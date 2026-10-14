import { getApiBase } from "@/shared/config/apiBase";
import type { DownloadProgressEvent, DownloadResultItem } from "@/shared/types/rom";
import type { DownloadRepository, DownloadRequest } from "../domain/DownloadRepository";

export class HttpDownloadRepository implements DownloadRepository {
  async start(request: DownloadRequest): Promise<string> {
    const base = await getApiBase();
    const res = await fetch(`${base}/api/download`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error || "No se pudo iniciar la descarga");
    }
    const data = await res.json();
    return data.jobId as string;
  }

  subscribe(
    jobId: string,
    onEvent: (event: DownloadProgressEvent) => void,
    onError?: (error: Error) => void
  ): () => void {
    let source: EventSource | null = null;
    let closed = false;

    getApiBase().then((base) => {
      if (closed) return;
      source = new EventSource(`${base}/api/jobs/${jobId}/events`);
      source.onmessage = (msg) => {
        try {
          const event = JSON.parse(msg.data) as DownloadProgressEvent;
          onEvent(event);
          if (event.type === "done" || event.type === "cancelled" || event.type === "error") {
            source?.close();
          }
        } catch (e) {
          onError?.(e instanceof Error ? e : new Error(String(e)));
        }
      };
      source.onerror = () => {
        onError?.(new Error("Conexión de progreso interrumpida"));
        source?.close();
      };
    });

    return () => {
      closed = true;
      source?.close();
    };
  }

  async cancel(jobId: string): Promise<void> {
    const base = await getApiBase();
    await fetch(`${base}/api/jobs/${jobId}/cancel`, { method: "POST" });
  }

  async getResult(jobId: string): Promise<{
    done: boolean;
    error?: string;
    result?: { items: DownloadResultItem[]; elapsed: number };
  }> {
    const base = await getApiBase();
    const res = await fetch(`${base}/api/jobs/${jobId}`);
    if (!res.ok) throw new Error("Job no encontrado");
    return res.json();
  }
}
