const { app, BrowserWindow, dialog, ipcMain, shell } = require("electron");
const path = require("path");
const { spawn } = require("child_process");
const http = require("http");
const fs = require("fs");

const API_HOST = "127.0.0.1";
const API_PORT = 8765;
const API_URL = `http://${API_HOST}:${API_PORT}`;
const ROOT_DIR = path.resolve(__dirname, "..", "..");
const isDev = !app.isPackaged;

let mainWindow = null;
let apiProcess = null;

function resolvePython() {
  const venvPy = path.join(ROOT_DIR, ".venv", "bin", "python3");
  if (fs.existsSync(venvPy)) return venvPy;
  return process.platform === "win32" ? "python" : "python3";
}

function waitForApi(timeoutMs = 20000) {
  const start = Date.now();
  return new Promise((resolve, reject) => {
    const tick = () => {
      const req = http.get(`${API_URL}/api/health`, (res) => {
        res.resume();
        if (res.statusCode === 200) {
          resolve();
          return;
        }
        retry();
      });
      req.on("error", retry);
      req.setTimeout(1500, () => {
        req.destroy();
        retry();
      });
    };
    const retry = () => {
      if (Date.now() - start > timeoutMs) {
        reject(new Error("La API de Python no respondió a tiempo"));
        return;
      }
      setTimeout(tick, 400);
    };
    tick();
  });
}

async function startApiServer() {
  // Reutilizar API si ya está levantada (p. ej. sesión previa)
  try {
    await waitForApi(1500);
    console.log("[api] reusing existing server");
    return;
  } catch {
    /* start a fresh one */
  }

  const python = resolvePython();
  const script = path.join(ROOT_DIR, "api_server.py");
  apiProcess = spawn(python, [script, "--host", API_HOST, "--port", String(API_PORT)], {
    cwd: ROOT_DIR,
    env: { ...process.env, VIRTUAL_ENV: path.join(ROOT_DIR, ".venv") },
    stdio: ["ignore", "pipe", "pipe"],
  });

  apiProcess.stdout.on("data", (chunk) => {
    console.log(`[api] ${chunk}`.trimEnd());
  });
  apiProcess.stderr.on("data", (chunk) => {
    console.error(`[api] ${chunk}`.trimEnd());
  });
  apiProcess.on("exit", (code) => {
    console.log(`[api] exited with code ${code}`);
    apiProcess = null;
  });

  return waitForApi();
}

function stopApiServer() {
  if (!apiProcess) return;
  try {
    apiProcess.kill("SIGTERM");
  } catch {
    /* ignore */
  }
  apiProcess = null;
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1180,
    height: 760,
    minWidth: 920,
    minHeight: 640,
    backgroundColor: "#0B1F33",
    title: "RomsFun Downloader",
    autoHideMenuBar: true,
    webPreferences: {
      preload: path.join(__dirname, "preload.cjs"),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false,
    },
  });

  if (isDev) {
    mainWindow.loadURL("http://127.0.0.1:5173");
  } else {
    mainWindow.loadFile(path.join(__dirname, "..", "dist", "index.html"));
  }

  mainWindow.on("closed", () => {
    mainWindow = null;
  });
}

ipcMain.handle("get-api-base", () => API_URL);

ipcMain.handle("pick-directory", async (_event, defaultPath) => {
  const result = await dialog.showOpenDialog(mainWindow, {
    title: "Carpeta de descargas",
    defaultPath: defaultPath || path.join(ROOT_DIR, "downloads"),
    properties: ["openDirectory", "createDirectory"],
  });
  if (result.canceled || !result.filePaths.length) return null;
  return result.filePaths[0];
});

ipcMain.handle("open-path", async (_event, targetPath) => {
  if (!targetPath) return false;
  await shell.openPath(targetPath);
  return true;
});

ipcMain.handle("get-default-output", () => path.join(ROOT_DIR, "downloads"));

app.whenReady().then(async () => {
  try {
    await startApiServer();
  } catch (err) {
    dialog.showErrorBox(
      "Error al iniciar el núcleo Python",
      `${err.message}\n\nVerifica que exista .venv y las dependencias del proyecto.`
    );
    app.quit();
    return;
  }
  createWindow();
});

app.on("window-all-closed", () => {
  stopApiServer();
  if (process.platform !== "darwin") app.quit();
});

app.on("before-quit", () => {
  stopApiServer();
});

app.on("activate", () => {
  if (BrowserWindow.getAllWindows().length === 0) createWindow();
});
