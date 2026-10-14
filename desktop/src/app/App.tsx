import { useEffect, useMemo, useState, startTransition } from "react";
import { deps } from "@/app/providers/dependencies";
import { DownloadProgress } from "@/features/download/ui/DownloadProgress";
import type {
  AppSettings,
  ConsoleOption,
  DownloadProgressEvent,
  DownloadResultItem,
  RomGame,
} from "@/shared/types/rom";

type Tab = "search" | "console" | "url" | "settings";

export function App() {
  const [tab, setTab] = useState<Tab>("search");
  const [settings, setSettings] = useState<AppSettings | null>(null);
  const [consoles, setConsoles] = useState<ConsoleOption[]>([]);
  const [query, setQuery] = useState("");
  const [consoleQuery, setConsoleQuery] = useState("");
  const [url, setUrl] = useState("");
  const [selectedConsole, setSelectedConsole] = useState("game-boy-advance");
  const [games, setGames] = useState<RomGame[]>([]);
  const [selected, setSelected] = useState<Record<string, boolean>>({});
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [progress, setProgress] = useState<DownloadProgressEvent | null>(null);
  const [results, setResults] = useState<DownloadResultItem[]>([]);
  const [jobId, setJobId] = useState<string | null>(null);
  const [unsubscribe, setUnsubscribe] = useState<(() => void) | null>(null);

  useEffect(() => {
    void (async () => {
      const loaded = await deps.settingsStore.load();
      setSettings(loaded);
      try {
        const list = await deps.listConsoles.execute();
        setConsoles(list);
        if (list[0]) setSelectedConsole(list[0].slug);
      } catch (e) {
        setError(e instanceof Error ? e.message : String(e));
      }
    })();
  }, []);

  const selectedGames = useMemo(
    () => games.filter((g) => selected[g.url]),
    [games, selected]
  );

  async function persistSettings(next: AppSettings) {
    setSettings(next);
    await deps.settingsStore.save(next);
  }

  async function runSearch() {
    if (!query.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const found = await deps.searchGames.execute(query);
      startTransition(() => {
        setGames(found);
        setSelected({});
        setResults([]);
        setProgress(null);
      });
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }

  async function runConsoleList() {
    if (!settings) return;
    setLoading(true);
    setError(null);
    try {
      const name = consoleQuery.trim();
      let found: RomGame[];

      if (name) {
        const selectedMeta = consoles.find((c) => c.slug === selectedConsole);
        const results = await deps.searchGames.execute(name);
        found = results
          .filter((g) => {
            const slug = g.console_slug || "";
            return (
              slug === selectedConsole ||
              g.console === selectedMeta?.folder ||
              g.console === selectedMeta?.label
            );
          })
          .slice(0, settings.limit);

        // Si el buscador global no devolvió matches de esa consola,
        // caemos al listado de la consola y filtramos por nombre localmente.
        if (found.length === 0) {
          const listed = await deps.listConsoleGames.execute(
            selectedConsole,
            Math.max(settings.limit * 3, 40)
          );
          const needle = name.toLowerCase();
          found = listed
            .filter((g) => g.title.toLowerCase().includes(needle))
            .slice(0, settings.limit);
        }
      } else {
        found = await deps.listConsoleGames.execute(selectedConsole, settings.limit);
      }

      startTransition(() => {
        setGames(found);
        const all: Record<string, boolean> = {};
        found.forEach((g) => {
          all[g.url] = true;
        });
        setSelected(all);
        setResults([]);
        setProgress(null);
      });
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }

  function toggleAll(value: boolean) {
    const next: Record<string, boolean> = {};
    games.forEach((g) => {
      next[g.url] = value;
    });
    setSelected(next);
  }

  async function startDownload(items?: RomGame[], directUrl?: string) {
    if (!settings) return;
    if (!directUrl && (!items || items.length === 0)) {
      setError("Selecciona al menos un juego");
      return;
    }

    unsubscribe?.();
    setBusy(true);
    setError(null);
    setResults([]);
    setProgress({ type: "batch", current: 0, total: items?.length || 1, message: "Iniciando..." });

    try {
      const session = await deps.startDownload.execute(
        {
          items,
          url: directUrl,
          output: settings.outputDir,
          unzip: settings.unzip,
          singleVersion: settings.singleVersion,
          cleanTags: settings.cleanTags,
        },
        (event) => {
          setProgress(event);
          if (event.type === "done" && event.items) {
            setResults(event.items);
            setBusy(false);
            setJobId(null);
          }
          if (event.type === "cancelled" && event.items) {
            setResults(event.items);
            setBusy(false);
            setJobId(null);
          }
          if (event.type === "error") {
            setError(event.message || "Error en la descarga");
            setBusy(false);
            setJobId(null);
          }
        }
      );
      setJobId(session.jobId);
      setUnsubscribe(() => session.unsubscribe);
    } catch (e) {
      setBusy(false);
      setError(e instanceof Error ? e.message : String(e));
    }
  }

  async function cancelDownload() {
    if (!jobId) return;
    await deps.downloadRepo.cancel(jobId);
  }

  async function pickOutput() {
    if (!settings || !window.romsfunDesktop) return;
    const dir = await window.romsfunDesktop.pickDirectory(settings.outputDir);
    if (dir) await persistSettings({ ...settings, outputDir: dir });
  }

  async function openOutput() {
    if (!settings?.outputDir || !window.romsfunDesktop) return;
    await window.romsfunDesktop.openPath(settings.outputDir);
  }

  const titles: Record<Tab, { title: string; subtitle: string }> = {
    search: {
      title: "Buscar juegos",
      subtitle: "Encuentra ROMs por nombre y descarga la mejor versión",
    },
    console: {
      title: "Por consola",
      subtitle: "Busca por nombre dentro de una consola o lista un lote completo",
    },
    url: {
      title: "URL directa",
      subtitle: "Pega el enlace de la ficha o descarga en RomsFun",
    },
    settings: {
      title: "Ajustes",
      subtitle: "Carpeta de salida, idioma y limpieza FAT32",
    },
  };

  if (!settings) {
    return <div className="empty">Cargando RomsFun Desktop...</div>;
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">RF</div>
          <h1>RomsFun</h1>
          <p>Downloader & R36S Optimizer</p>
        </div>
        <nav className="nav">
          <button
            type="button"
            className={`nav-btn ${tab === "search" ? "active" : ""}`}
            onClick={() => setTab("search")}
          >
            Buscar
          </button>
          <button
            type="button"
            className={`nav-btn ${tab === "console" ? "active" : ""}`}
            onClick={() => setTab("console")}
          >
            Por consola
          </button>
          <button
            type="button"
            className={`nav-btn ${tab === "url" ? "active" : ""}`}
            onClick={() => setTab("url")}
          >
            URL directa
          </button>
          <button
            type="button"
            className={`nav-btn ${tab === "settings" ? "active" : ""}`}
            onClick={() => setTab("settings")}
          >
            Ajustes
          </button>
        </nav>
        <div className="sidebar-foot">Tema azul celeste · Núcleo Python</div>
      </aside>

      <main className="main">
        <header className="topbar">
          <div>
            <h2>{titles[tab].title}</h2>
            <span>{titles[tab].subtitle}</span>
          </div>
          <button className="btn btn-ghost" type="button" onClick={() => void openOutput()}>
            Abrir carpeta
          </button>
        </header>

        <div className="content">
          {error && <div className="error-banner">{error}</div>}

          {tab === "search" && (
            <section className="panel">
              <div className="toolbar">
                <div className="field">
                  <label htmlFor="query">Palabra clave</label>
                  <input
                    id="query"
                    value={query}
                    placeholder="mario kart, pokemon, zelda..."
                    onChange={(e) => setQuery(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") void runSearch();
                    }}
                  />
                </div>
                <button className="btn btn-primary" type="button" disabled={loading || busy} onClick={() => void runSearch()}>
                  {loading ? "Buscando..." : "Buscar"}
                </button>
                <button
                  className="btn btn-ghost"
                  type="button"
                  disabled={busy || selectedGames.length === 0}
                  onClick={() => void startDownload(selectedGames)}
                >
                  Descargar seleccionados
                </button>
              </div>
              <GameList
                games={games}
                selected={selected}
                onToggle={(urlKey, value) => setSelected((prev) => ({ ...prev, [urlKey]: value }))}
                onToggleAll={toggleAll}
              />
              <DownloadProgress
                event={progress}
                results={results}
                busy={busy}
                onCancel={() => void cancelDownload()}
              />
            </section>
          )}

          {tab === "console" && (
            <section className="panel">
              <div className="toolbar">
                <div className="field">
                  <label htmlFor="console">Consola</label>
                  <select
                    id="console"
                    value={selectedConsole}
                    onChange={(e) => setSelectedConsole(e.target.value)}
                  >
                    {consoles.map((c) => (
                      <option key={c.slug} value={c.slug}>
                        {c.label} ({c.folder})
                      </option>
                    ))}
                  </select>
                </div>
                <div className="field">
                  <label htmlFor="console-query">Nombre del juego</label>
                  <input
                    id="console-query"
                    value={consoleQuery}
                    placeholder="Opcional: mario, pokemon, zelda..."
                    onChange={(e) => setConsoleQuery(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") void runConsoleList();
                    }}
                  />
                </div>
                <div className="field" style={{ maxWidth: 120, flex: "0 0 120px" }}>
                  <label htmlFor="limit">Límite</label>
                  <input
                    id="limit"
                    type="number"
                    min={1}
                    max={200}
                    value={settings.limit}
                    onChange={(e) =>
                      void persistSettings({ ...settings, limit: Number(e.target.value) || 1 })
                    }
                  />
                </div>
                <button
                  className="btn btn-primary"
                  type="button"
                  disabled={loading || busy}
                  onClick={() => void runConsoleList()}
                >
                  {loading ? "Buscando..." : consoleQuery.trim() ? "Buscar" : "Listar"}
                </button>
                <button
                  className="btn btn-ghost"
                  type="button"
                  disabled={busy || selectedGames.length === 0}
                  onClick={() => void startDownload(selectedGames)}
                >
                  Descargar lote
                </button>
              </div>
              <GameList
                games={games}
                selected={selected}
                onToggle={(urlKey, value) => setSelected((prev) => ({ ...prev, [urlKey]: value }))}
                onToggleAll={toggleAll}
              />
              <DownloadProgress
                event={progress}
                results={results}
                busy={busy}
                onCancel={() => void cancelDownload()}
              />
            </section>
          )}

          {tab === "url" && (
            <section className="panel">
              <div className="toolbar">
                <div className="field">
                  <label htmlFor="url">URL de RomsFun</label>
                  <input
                    id="url"
                    value={url}
                    placeholder="https://romsfun.com/roms/..."
                    onChange={(e) => setUrl(e.target.value)}
                  />
                </div>
                <button
                  className="btn btn-primary"
                  type="button"
                  disabled={busy || !url.trim()}
                  onClick={() => void startDownload(undefined, url.trim())}
                >
                  Descargar
                </button>
              </div>
              <DownloadProgress
                event={progress}
                results={results}
                busy={busy}
                onCancel={() => void cancelDownload()}
              />
            </section>
          )}

          {tab === "settings" && (
            <section className="panel">
              <div className="toolbar">
                <div className="field">
                  <label htmlFor="output">Carpeta de descargas</label>
                  <input id="output" value={settings.outputDir} readOnly />
                </div>
                <button className="btn btn-primary" type="button" onClick={() => void pickOutput()}>
                  Elegir...
                </button>
              </div>
              <label className="toggle-row">
                <input
                  type="checkbox"
                  checked={settings.unzip}
                  onChange={(e) => void persistSettings({ ...settings, unzip: e.target.checked })}
                />
                Extraer archivos comprimidos automáticamente
              </label>
              <label className="toggle-row">
                <input
                  type="checkbox"
                  checked={settings.singleVersion}
                  onChange={(e) =>
                    void persistSettings({ ...settings, singleVersion: e.target.checked })
                  }
                />
                Solo la mejor versión (ES &gt; EN)
              </label>
              <label className="toggle-row">
                <input
                  type="checkbox"
                  checked={settings.cleanTags}
                  onChange={(e) =>
                    void persistSettings({ ...settings, cleanTags: e.target.checked })
                  }
                />
                Limpiar etiquetas de región () []
              </label>
            </section>
          )}
        </div>
      </main>
    </div>
  );
}

function GameList({
  games,
  selected,
  onToggle,
  onToggleAll,
}: {
  games: RomGame[];
  selected: Record<string, boolean>;
  onToggle: (url: string, value: boolean) => void;
  onToggleAll: (value: boolean) => void;
}) {
  if (games.length === 0) {
    return <div className="empty">Sin resultados todavía. Busca o lista una consola.</div>;
  }

  const allSelected = games.every((g) => selected[g.url]);

  return (
    <>
      <div className="toolbar" style={{ marginBottom: 8 }}>
        <button className="btn btn-ghost" type="button" onClick={() => onToggleAll(!allSelected)}>
          {allSelected ? "Deseleccionar todo" : "Seleccionar todo"}
        </button>
        <span className="badge">{games.length} juegos</span>
      </div>
      <div className="game-list">
        {games.map((game) => (
          <label
            key={game.url}
            className={`game-row ${selected[game.url] ? "is-selected" : ""}`}
          >
            <input
              type="checkbox"
              checked={!!selected[game.url]}
              onChange={(e) => onToggle(game.url, e.target.checked)}
            />
            <div className="game-meta">
              <div className="game-title">{game.title}</div>
              <div className="game-console">{game.console}</div>
            </div>
            <span className="badge">{game.console}</span>
          </label>
        ))}
      </div>
    </>
  );
}
