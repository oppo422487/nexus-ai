const { app, BrowserWindow, Menu, dialog, session } = require("electron");
const { spawn } = require("node:child_process");
const http = require("node:http");
const fs = require("node:fs");
const path = require("node:path");

const nativeEngineMode = Boolean(process.env.NEXA_ENGINE_BRIDGE_TOKEN);
if (nativeEngineMode) {
  app.setPath("userData", path.join(app.getPath("appData"), "NexaAIPlusDesktop"));
}
const isDev = process.env.NEXA_ELECTRON_DEV === "1";
const devServerUrl = process.env.NEXA_DEV_SERVER_URL || "http://127.0.0.1:5178";

// Nexa's online neural reply must be able to play after a hands-free command.
app.commandLine.appendSwitch("autoplay-policy", "no-user-gesture-required");

let mainWindow = null;
let backendProcess = null;
let ownsBackend = false;

function backendHealth(timeoutMs = 900) {
  return new Promise((resolve) => {
    const request = http.get("http://127.0.0.1:8766/api/health", { timeout: timeoutMs }, (response) => {
      response.resume();
      resolve(response.statusCode >= 200 && response.statusCode < 500);
    });
    request.on("timeout", () => { request.destroy(); resolve(false); });
    request.on("error", () => resolve(false));
  });
}

function backendCommand() {
  if (app.isPackaged) {
    const executable = path.join(process.resourcesPath, "app", "backend", "nexa-backend.exe");
    return fs.existsSync(executable) ? { executable, args: [], cwd: path.dirname(executable) } : null;
  }
  const backendDir = path.resolve(__dirname, "..", "..", "backend");
  const python = path.join(backendDir, ".venv", "Scripts", "python.exe");
  const script = path.join(backendDir, "run_backend.py");
  return fs.existsSync(python) && fs.existsSync(script)
    ? { executable: python, args: [script], cwd: backendDir }
    : null;
}

async function ensureBackend() {
  if (await backendHealth()) return true;
  const command = backendCommand();
  if (!command) return false;
  const backendData = path.join(app.getPath("userData"), "backend-data");
  const backendModels = path.join(app.getPath("userData"), "models");
  fs.mkdirSync(backendData, { recursive: true });
  fs.mkdirSync(backendModels, { recursive: true });
  backendProcess = spawn(command.executable, command.args, {
    cwd: command.cwd,
    windowsHide: true,
    stdio: "ignore",
    env: {
      ...process.env,
      APP_ENV: "production",
      BACKEND_HOST: "127.0.0.1",
      BACKEND_PORT: "8766",
      NEXA_DATA_DIR: backendData,
      NEXA_MODELS_DIR: backendModels,
      NEXA_ENV_FILE: path.join(app.getPath("userData"), ".env"),
    },
  });
  ownsBackend = true;
  backendProcess.once("exit", () => { backendProcess = null; ownsBackend = false; });
  for (let attempt = 0; attempt < 240; attempt += 1) {
    await new Promise((resolve) => setTimeout(resolve, 250));
    if (await backendHealth()) return true;
    if (!backendProcess) break;
  }
  return false;
}

function stopBackend() {
  if (ownsBackend && backendProcess && !backendProcess.killed) backendProcess.kill();
  backendProcess = null;
  ownsBackend = false;
}

function createWindow() {
  mainWindow = new BrowserWindow({
    title: "Nexa AI",
    width: 1440,
    height: 900,
    minWidth: 1100,
    minHeight: 700,
    center: true,
    backgroundColor: "#020617",
    show: false,
    autoHideMenuBar: true,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, "preload.cjs"),
    },
  });

  mainWindow.once("ready-to-show", () => {
    mainWindow.show();
    mainWindow.focus();
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

  if (isDev) {
    console.log("[Nexa AI] Loading dev server:", devServerUrl);
    mainWindow.loadURL(devServerUrl);
  } else {
    const htmlPath = path.join(__dirname, "../dist/index.html");
    console.log("[Nexa AI] Loading production file:", htmlPath);
    if (nativeEngineMode) mainWindow.loadURL("http://127.0.0.1:8766/suite/?engine=native");
    else mainWindow.loadFile(htmlPath);
  }
}

function configureMicrophonePermission() {
  const trustedPage = (webContents) => {
    const url = webContents?.getURL?.() || "";
    if (nativeEngineMode) return url.startsWith("http://127.0.0.1:8766/suite/");
    return isDev ? url.startsWith(devServerUrl) : url.startsWith("file:");
  };
  session.defaultSession.setPermissionCheckHandler((webContents, permission) => {
    return permission === "media" && trustedPage(webContents);
  });
  session.defaultSession.setPermissionRequestHandler((webContents, permission, callback, details) => {
    const wantsAudio = !details?.mediaTypes || details.mediaTypes.length === 0 || details.mediaTypes.includes("audio");
    callback(permission === "media" && wantsAudio && trustedPage(webContents));
  });
}

const gotLock = app.requestSingleInstanceLock();

if (!gotLock) {
  app.quit();
} else {
  app.whenReady().then(async () => {
    app.name = "Nexa AI";
    Menu.setApplicationMenu(null);
    configureMicrophonePermission();
    const backendReady = await ensureBackend();
    if (!backendReady) {
      dialog.showMessageBox({
        type: "warning",
        title: "Nexa AI backend unavailable",
        message: "The desktop interface will open, but backend features are unavailable.",
        detail: "Run backend\\scripts\\setup-windows.ps1 during development, or reinstall the packaged application.",
      });
    }
    createWindow();

    app.on("second-instance", () => {
      if (mainWindow) {
        if (mainWindow.isMinimized()) mainWindow.restore();
        mainWindow.focus();
      }
    });

    app.on("activate", () => {
      if (BrowserWindow.getAllWindows().length === 0) {
        createWindow();
      }
    });
  });
}

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") {
    app.quit();
  }
});

app.on("before-quit", stopBackend);
