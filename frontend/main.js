const { app, BrowserWindow, ipcMain, Tray, Menu, nativeImage, session } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const fs = require('fs');
const http = require('http');

let mainWindow;
let splashWindow;
let tray;
let backendProcess;

const isDev = !app.isPackaged;
const RESOURCES_PATH = app.isPackaged
  ? path.join(process.resourcesPath)
  : path.join(__dirname, '..');

function getIcon(name) {
  const p = path.join(__dirname, 'build', name);
  return fs.existsSync(p) ? p : path.join(__dirname, name);
}

function createSplashWindow() {
  splashWindow = new BrowserWindow({
    width: 400,
    height: 300,
    frame: false,
    transparent: true,
    alwaysOnTop: true,
    resizable: false,
    icon: getIcon('icon.png'),
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  const splashHtml = `
    <!DOCTYPE html>
    <html>
    <head>
      <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
          background: transparent;
          display: flex;
          align-items: center;
          justify-content: center;
          height: 100vh;
          font-family: 'Segoe UI', monospace;
          -webkit-app-region: drag;
        }
        .container {
          background: rgba(10, 10, 18, 0.95);
          border: 1px solid rgba(0, 212, 255, 0.25);
          border-radius: 12px;
          padding: 40px 50px;
          text-align: center;
          box-shadow: 0 8px 40px rgba(0, 0, 0, 0.5), 0 0 1px rgba(0, 212, 255, 0.4);
        }
        .title {
          color: #00d4ff;
          font-size: 28px;
          font-weight: bold;
          letter-spacing: 6px;
          margin-bottom: 20px;
          text-shadow: 0 0 10px rgba(0, 212, 255, 0.3);
        }
        .spinner {
          width: 40px;
          height: 40px;
          border: 3px solid rgba(0, 212, 255, 0.1);
          border-top: 3px solid #00d4ff;
          border-radius: 50%;
          animation: spin 1s linear infinite;
          margin: 0 auto 16px;
        }
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
        .status {
          color: rgba(0, 212, 255, 0.6);
          font-size: 11px;
          letter-spacing: 2px;
        }
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.4; }
        }
        .status { animation: pulse 2s ease-in-out infinite; }
      </style>
    </head>
    <body>
      <div class="container">
        <div class="title">NOKTON</div>
        <div class="spinner"></div>
        <div class="status">INITIALIZING COGNITIVE CORE...</div>
      </div>
    </body>
    </html>
  `;

  splashWindow.loadURL(`data:text/html;charset=utf-8,${encodeURIComponent(splashHtml)}`);
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 900,
    height: 680,
    minWidth: 600,
    minHeight: 400,
    frame: true,
    title: 'Nokton',
    icon: getIcon('icon.png'),
    show: false, // Don't show until ready
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  mainWindow.on('ready-to-show', () => {
    if (splashWindow) {
      splashWindow.close();
      splashWindow = null;
    }
    mainWindow.show();
  });

  if (isDev) {
    mainWindow.loadURL('http://localhost:9000');
    // Open DevTools only when requested or if debug env is set
    if (process.env.DEBUG_DEVTOOLS === 'true') {
      mainWindow.webContents.openDevTools({ mode: 'detach' });
    }
  } else {
    mainWindow.loadFile(path.join(__dirname, 'dist', 'index.html'));
  }

  mainWindow.on('close', (event) => {
    if (tray) {
      event.preventDefault();
      mainWindow.hide();
    }
  });

  mainWindow.on('closed', () => {
    mainWindow = null;
  });

  mainWindow.webContents.on('did-fail-load', (event, errorCode, errorDescription, validatedURL) => {
    const logPath = isDev ? 'error.log' : path.join(app.getPath('userData'), 'error.log');
    fs.appendFileSync(logPath, `Failed to load: ${validatedURL}, error: ${errorCode} ${errorDescription}\n`);
    // Fallback to local index.html if the webpack dev server is not running
    if (isDev && validatedURL.startsWith('http://localhost:9000')) {
      console.log('Dev server at localhost:9000 not reachable. Falling back to local built file...');
      mainWindow.loadFile(path.join(__dirname, 'dist', 'index.html'));
    }
  });

  mainWindow.webContents.on('console-message', (event, level, message, line, sourceId) => {
    if (isDev) {
      fs.appendFileSync('error.log', `[${level}] ${sourceId}:${line} - ${message}\n`);
    }
  });
}

function createTray() {
  try {
    const iconPath = getIcon('icon_tray.png');
    const icon = fs.existsSync(iconPath)
      ? nativeImage.createFromPath(iconPath).resize({ width: 16, height: 16 })
      : nativeImage.createEmpty();
    tray = new Tray(icon);
    const contextMenu = Menu.buildFromTemplate([
      { label: 'Show Nokton', click: () => mainWindow && mainWindow.show() },
      { type: 'separator' },
      { label: 'Quit', click: () => {
        tray = null;
        app.quit();
      }},
    ]);
    tray.setToolTip('Nokton');
    tray.setContextMenu(contextMenu);
    tray.on('click', () => mainWindow && mainWindow.show());
  } catch (e) {
    console.error('Tray creation failed:', e);
  }
}

function startBackend() {
  let cmd, args = [], opts;

  if (app.isPackaged) {
    // Look for PyInstaller-bundled backend
    const bundledExe = path.join(RESOURCES_PATH, 'backend', 'nokton-backend', 'nokton-backend.exe');
    const bundledExeFlat = path.join(RESOURCES_PATH, 'backend', 'nokton-backend.exe');

    if (fs.existsSync(bundledExe)) {
      cmd = bundledExe;
      opts = { cwd: path.dirname(bundledExe), stdio: ['pipe', 'pipe', 'pipe'] };
    } else if (fs.existsSync(bundledExeFlat)) {
      cmd = bundledExeFlat;
      opts = { cwd: path.dirname(bundledExeFlat), stdio: ['pipe', 'pipe', 'pipe'] };
    } else {
      // Fallback: try system Python
      cmd = 'python';
      args = ['-m', 'backend.main'];
      opts = { cwd: RESOURCES_PATH, stdio: ['pipe', 'pipe', 'pipe'] };
    }
  } else {
    cmd = 'python';
    args = ['-m', 'backend.main'];
    opts = { cwd: path.join(__dirname, '..'), stdio: ['pipe', 'pipe', 'pipe'] };
  }

  console.log(`Starting backend: ${cmd} ${args.join(' ')}`);
  backendProcess = spawn(cmd, args, opts);

  backendProcess.stdout.on('data', (data) => {
    console.log(`[backend] ${data}`);
  });

  backendProcess.stderr.on('data', (data) => {
    console.error(`[backend] ${data}`);
  });

  backendProcess.on('close', (code) => {
    console.log(`Backend exited with code ${code}`);
    backendProcess = null;
  });

  backendProcess.on('error', (err) => {
    console.error(`Backend spawn error: ${err.message}`);
    backendProcess = null;
  });
}

function stopBackend() {
  return new Promise((resolve) => {
    if (!backendProcess) {
      resolve();
      return;
    }

    const timeout = setTimeout(() => {
      // Force kill after 3 seconds
      try {
        backendProcess.kill('SIGKILL');
      } catch (e) {}
      backendProcess = null;
      resolve();
    }, 3000);

    backendProcess.on('close', () => {
      clearTimeout(timeout);
      backendProcess = null;
      resolve();
    });

    // Try graceful shutdown first
    try {
      backendProcess.kill('SIGTERM');
    } catch (e) {
      clearTimeout(timeout);
      backendProcess = null;
      resolve();
    }
  });
}

/**
 * Poll the backend health endpoint until it responds OK.
 * Returns a promise that resolves when backend is ready,
 * or rejects after maxWaitMs.
 */
function waitForBackend(maxWaitMs = 30000, intervalMs = 500) {
  return new Promise((resolve, reject) => {
    const startTime = Date.now();

    function check() {
      const req = http.get('http://127.0.0.1:8765/api/health', (res) => {
        if (res.statusCode === 200) {
          resolve();
        } else {
          retry();
        }
      });
      req.on('error', () => retry());
      req.setTimeout(1000, () => {
        req.destroy();
        retry();
      });
    }

    function retry() {
      if (Date.now() - startTime >= maxWaitMs) {
        reject(new Error('Backend did not start within timeout'));
        return;
      }
      setTimeout(check, intervalMs);
    }

    check();
  });
}

ipcMain.handle('get-settings', async () => {
  try {
    const response = await fetch('http://localhost:8765/api/settings');
    return await response.json();
  } catch (e) {
    return null;
  }
});

ipcMain.handle('get-models', async () => {
  try {
    const response = await fetch('http://localhost:8765/api/models');
    return await response.json();
  } catch (e) {
    return null;
  }
});

ipcMain.handle('get-conversations', async () => {
  try {
    const response = await fetch('http://localhost:8765/api/conversations');
    return await response.json();
  } catch (e) {
    return { conversations: [] };
  }
});

app.whenReady().then(async () => {
  session.defaultSession.webRequest.onHeadersReceived((details, callback) => {
    callback({
      responseHeaders: {
        ...details.responseHeaders,
        'Content-Security-Policy': ["default-src 'self' 'unsafe-inline' 'unsafe-eval' data: ws://localhost:8765 http://localhost:8765 ws://localhost:9000 http://localhost:9000; style-src 'self' 'unsafe-inline' http://localhost:9000 https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' data: http://localhost:9000; connect-src 'self' ws://localhost:8765 http://localhost:8765 ws://localhost:9000 http://localhost:9000 https://fonts.googleapis.com https://fonts.gstatic.com"],
      },
    });
  });

  // Show splash while backend starts
  createSplashWindow();
  startBackend();

  try {
    await waitForBackend(30000, 500);
    console.log('Backend is ready');
  } catch (e) {
    console.error('Backend health check failed:', e.message);
    // Continue anyway — the frontend will show connection errors
  }

  createWindow();
  createTray();

  app.on('activate', () => {
    if (mainWindow === null) {
      createWindow();
    } else {
      mainWindow.show();
    }
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('before-quit', async (event) => {
  event.preventDefault();
  await stopBackend();
  app.exit(0);
});
