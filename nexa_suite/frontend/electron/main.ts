import { app, BrowserWindow, Menu } from "electron";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const devServerUrl =
  process.env.VITE_DEV_SERVER_URL || process.env.NEXA_DEV_SERVER_URL;

const isDevelopment = Boolean(devServerUrl);

function createWindow(): void {
  const mainWindow = new BrowserWindow({
    title: "Nexa AI",
    width: 1440,
    height: 900,
    minWidth: 1100,
    minHeight: 700,
    backgroundColor: "#020617",
    show: false,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, "preload.js"),
    },
  });

  mainWindow.once("ready-to-show", () => {
    mainWindow.show();
  });

  mainWindow.webContents.on("did-finish-load", () => {
    console.log("[Nexa AI] Renderer loaded successfully.");
  });

  mainWindow.webContents.on(
    "did-fail-load",
    (_event, errorCode, errorDescription, validatedURL) => {
      console.error("[Nexa AI] Renderer load failed:", {
        errorCode,
        errorDescription,
        validatedURL,
      });
    }
  );

  mainWindow.webContents.on("console-message", (_event, level, message) => {
    console.log("[Renderer Console]", level, message);
  });

  if (isDevelopment && devServerUrl) {
    console.log("[Nexa AI] Loading dev server:", devServerUrl);
    mainWindow.loadURL(devServerUrl);
    mainWindow.webContents.openDevTools({ mode: "detach" });
  } else {
    const htmlPath = path.join(__dirname, "../dist/index.html");
    console.log("[Nexa AI] Loading production file:", htmlPath);
    mainWindow.loadFile(htmlPath);
  }
}

app.whenReady().then(() => {
  Menu.setApplicationMenu(null);
  createWindow();

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") {
    app.quit();
  }
});