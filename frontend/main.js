const { app, BrowserWindow, ipcMain, Tray, Menu, nativeImage } = require('electron');
const path = require('path');
const { spawn } = require('child_process');

let mainWindow;
let tray;
let backendProcess;

const isDev = process.env.NODE_ENV !== 'production' || !app.isPackaged;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 900,
    height: 680,
    minWidth: 600,
    minHeight: 400,
    frame: true,
    title: 'Nokton',
    icon: path.join(__dirname, 'icon.png'),
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  if (isDev) {
    mainWindow.loadURL('http://localhost:9000');
    mainWindow.webContents.openDevTools({ mode: 'detach' });
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
}

function createTray() {
  try {
    const icon = nativeImage.createEmpty();
    tray = new Tray(icon);
    const contextMenu = Menu.buildFromTemplate([
      { label: 'Show Nokton', click: () => mainWindow && mainWindow.show() },
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
  const backendPath = path.join(__dirname, '..', 'backend');
  backendProcess = spawn('python', ['-m', 'backend.main'], {
    cwd: path.join(__dirname, '..'),
    stdio: ['pipe', 'pipe', 'pipe'],
  });

  backendProcess.stdout.on('data', (data) => {
    console.log(`[backend] ${data}`);
  });

  backendProcess.stderr.on('data', (data) => {
    console.error(`[backend] ${data}`);
  });

  backendProcess.on('close', (code) => {
    console.log(`Backend exited with code ${code}`);
  });
}

function stopBackend() {
  if (backendProcess) {
    backendProcess.kill();
    backendProcess = null;
  }
}

// IPC Handlers
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

app.whenReady().then(() => {
  startBackend();
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

app.on('before-quit', () => {
  stopBackend();
});
