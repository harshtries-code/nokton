const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('noktonAPI', {
  getSettings: () => ipcRenderer.invoke('get-settings'),
  getModels: () => ipcRenderer.invoke('get-models'),
  getConversations: () => ipcRenderer.invoke('get-conversations'),
});
