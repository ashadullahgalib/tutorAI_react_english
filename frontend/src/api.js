const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';
const API_KEY = process.env.REACT_APP_API_KEY || '';

const headers = () => ({
  'Authorization': `Bearer ${API_KEY}`,
});

export async function createSession() {
  const res = await fetch(`${API_URL}/session/new`, {
    method: 'POST',
    headers: headers(),
  });
  if (!res.ok) throw new Error(`Session creation failed: ${res.status}`);
  return res.json();
}

export async function getSubjects() {
  const res = await fetch(`${API_URL}/subjects`, {
    headers: headers(),
  });
  if (!res.ok) throw new Error(`Failed to load subjects: ${res.status}`);
  return res.json();
}

export async function sendTextMessage(sessionId, message, subject) {
  const res = await fetch(`${API_URL}/chat`, {
    method: 'POST',
    headers: { ...headers(), 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId, message, subject }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `Request failed: ${res.status}`);
  }
  return res.json();
}

export async function sendImageMessage(sessionId, message, subject, imageFile) {
  const formData = new FormData();
  formData.append('session_id', sessionId);
  formData.append('message', message || 'Please read and solve the problem shown in this photo.');
  formData.append('subject', subject);
  formData.append('image', imageFile, imageFile.name);

  const res = await fetch(`${API_URL}/chat/image`, {
    method: 'POST',
    headers: headers(), // Do NOT set Content-Type — browser sets multipart boundary automatically
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `Image request failed: ${res.status}`);
  }
  return res.json();
}

export async function clearSession(sessionId) {
  const res = await fetch(`${API_URL}/session/${sessionId}`, {
    method: 'DELETE',
    headers: headers(),
  });
  if (!res.ok) throw new Error(`Clear session failed: ${res.status}`);
  return res.json();
}

export async function healthCheck() {
  const res = await fetch(`${API_URL}/health`, { headers: headers() });
  return res.json();
}
