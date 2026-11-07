const { contextBridge } = require("electron");

contextBridge.exposeInMainWorld("nexa", {
  platform: process.platform,
  appMode: "desktop",
  backendUrl: "http://127.0.0.1:8766"
});