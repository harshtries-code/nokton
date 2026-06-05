const BASE_URL = 'http://localhost:8765/api';

export async function fetchSettings() {
  const res = await fetch(`${BASE_URL}/settings`);
  return res.json();
}

export async function updateSettings(data: Record<string, unknown>) {
  const res = await fetch(`${BASE_URL}/settings`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  return res.json();
}

export async function fetchModels() {
  const res = await fetch(`${BASE_URL}/models`);
  return res.json();
}

export async function fetchConversations() {
  const res = await fetch(`${BASE_URL}/conversations`);
  return res.json();
}

export async function fetchConversation(id: string) {
  const res = await fetch(`${BASE_URL}/conversations/${id}`);
  return res.json();
}

export async function deleteConversation(id: string) {
  await fetch(`${BASE_URL}/conversations/${id}`, { method: 'DELETE' });
}

export async function exportConversation(id: string, fmt = 'json') {
  const res = await fetch(`${BASE_URL}/conversations/${id}/export?fmt=${fmt}`);
  return res.json();
}
