const api = (window as any).noktonAPI;

export const ipc = {
  getSettings: () => api?.getSettings?.() ?? null,
  getModels: () => api?.getModels?.() ?? null,
  getConversations: () => api?.getConversations?.() ?? null,
};
