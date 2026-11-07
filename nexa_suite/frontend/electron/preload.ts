import { contextBridge } from "electron";

contextBridge.exposeInMainWorld("nexa", {
  platform: process.platform,
  appMode: "desktop",
});