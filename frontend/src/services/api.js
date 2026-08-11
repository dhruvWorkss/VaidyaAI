 const BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api';

export const sendMessage = async (message, sessionId, language = 'en') => {
  const response = await fetch(`${BASE_URL}/triage/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, session_id: sessionId, language }),
  });
  return response.json();
};

export const transcribeAudio = async (audioBlob) => {
  const formData = new FormData();
  formData.append('audio', audioBlob, 'recording.wav');
  const response = await fetch(`${BASE_URL}/triage/transcribe`, {
    method: 'POST',
    body: formData,
  });
  return response.json();
};

export const speakText = async (text, language = 'en') => {
  const response = await fetch(
    `${BASE_URL}/triage/speak?text=${encodeURIComponent(text)}&language=${language}`,
    { method: 'POST' }
  );
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
  return response.json();
};

export const getSessions = async () => {
  const response = await fetch(`${BASE_URL}/triage/sessions`);
  return response.json();
};

export const getSession = async (id) => {
  const response = await fetch(`${BASE_URL}/triage/sessions/${id}`);
  return response.json();
};
