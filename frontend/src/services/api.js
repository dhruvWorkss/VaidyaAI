const BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api';

export const warmUpApi = async (signal) => {
  const response = await fetch(`${BASE_URL}/triage/health`, { signal });
  return parseResponse(response);
};

export class ApiError extends Error {
  constructor(message, status = null) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

const parseResponse = async (response) => {
  const contentType = response.headers.get('content-type') || '';
  const data = contentType.includes('application/json')
    ? await response.json()
    : await response.text();

  if (!response.ok) {
    const detail = typeof data === 'object' ? data?.detail : data;
    throw new ApiError(detail || `Request failed (${response.status})`, response.status);
  }

  return data;
};

export const sendMessage = async (message, sessionId, language = 'en', signal) => {
  const response = await fetch(`${BASE_URL}/triage/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, session_id: sessionId, language }),
    signal,
  });
  return parseResponse(response);
};

export const transcribeAudio = async (audioBlob) => {
  const formData = new FormData();
  formData.append('audio', audioBlob, 'recording.wav');
  const response = await fetch(`${BASE_URL}/triage/transcribe`, {
    method: 'POST',
    body: formData,
  });
  return parseResponse(response);
};

export const speakText = async (text, language = 'en', signal) => {
  const response = await fetch(
    `${BASE_URL}/triage/speak?text=${encodeURIComponent(text)}&language=${language}`,
    { method: 'POST', signal }
  );
  if (!response.ok) {
    throw new ApiError(`Speech request failed (${response.status})`, response.status);
  }
  return response.blob();
};

export const clearSession = async (sessionId) => {
  await fetch(`${BASE_URL}/triage/session/${sessionId}`, { method: 'DELETE' });
};

export const analyzeReport = async (file, language = 'en') => {
  const formData = new FormData();
  formData.append('file', file);
  const response = await fetch(
    `${BASE_URL}/triage/analyze-report?language=${language}`,
    { method: 'POST', body: formData }
  );
  return parseResponse(response);
};

export const getSessions = async () => {
  const response = await fetch(`${BASE_URL}/triage/sessions`);
  return parseResponse(response);
};

export const getSession = async (id) => {
  const response = await fetch(`${BASE_URL}/triage/sessions/${id}`);
  return parseResponse(response);
};
