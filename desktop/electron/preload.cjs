const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("romsfunDesktop", {
  getApiBase: () => ipcRenderer.invoke("get-api-base"),
  pickDirectory: (defaultPath) => ipcRenderer.invoke("pick-directory", defaultPath),
  openPath: (targetPath) => ipcRenderer.invoke("open-path", targetPath),
  getDefaultOutput: () => ipcRenderer.invoke("get-default-output"),
});
