import type { DownloadProgressEvent, DownloadResultItem } from "@/shared/types/rom";

interface Props {
  event: DownloadProgressEvent | null;
  results: DownloadResultItem[];
  busy: boolean;
  onCancel?: () => void;
}

function statusClass(status: string) {
  if (status === "success") return "status-ok";
  if (status === "already_exists") return "status-warn";
  return "status-err";
}

function statusLabel(status: string) {
  if (status === "success") return "Éxito";
  if (status === "already_exists") return "Ya existía";
  return "Error";
}

export function DownloadProgress({ event, results, busy, onCancel }: Props) {
  const current = event?.current ?? 0;
  const total = event?.total ?? 0;
  const pct = total > 0 ? Math.min(100, Math.round((current / total) * 100)) : busy ? 8 : 0;
  const filePct =
    event?.type === "file" && event.total
      ? Math.min(100, Math.round(((event.downloaded ?? 0) / event.total) * 100))
      : null;

  return (
    <div className="progress-box">
      <div className="progress-label">
        <strong>{event?.message || (busy ? "Preparando descarga..." : "Listo")}</strong>
        <span>
          {total > 0 ? `${current}/${total}` : ""} {busy && onCancel ? "" : ""}
        </span>
      </div>
      <div className="bar">
        <span style={{ width: `${pct}%` }} />
      </div>
      {filePct !== null && (
        <>
          <div className="progress-label" style={{ marginTop: 12 }}>
            <span>{event?.filename || "Archivo"}</span>
            <span>{filePct}%</span>
          </div>
          <div className="bar">
            <span style={{ width: `${filePct}%` }} />
          </div>
        </>
      )}
      {busy && onCancel && (
        <div style={{ marginTop: 12 }}>
          <button className="btn btn-danger" type="button" onClick={onCancel}>
            Cancelar
          </button>
        </div>
      )}
      {results.length > 0 && (
        <table className="summary-table">
          <thead>
            <tr>
              <th>Juego</th>
              <th>ROM</th>
              <th>Tamaño</th>
              <th>Estado</th>
            </tr>
          </thead>
          <tbody>
            {results.map((item, idx) =>
              item.roms.map((rom, ridx) => (
                <tr key={`${idx}-${ridx}`}>
                  <td>
                    [{item.console}] {item.title}
                  </td>
                  <td>{rom.name}</td>
                  <td>{rom.size}</td>
                  <td className={statusClass(item.status)}>{statusLabel(item.status)}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      )}
    </div>
  );
}
