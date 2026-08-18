import '@testing-library/jest-dom';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import PatientPage from './PatientPage';
import { getSession, sendMessage, speakText } from '../services/api';

jest.mock('react-markdown', () => ({ children }) => children);

jest.mock('../services/api', () => ({
  sendMessage: jest.fn(),
  speakText: jest.fn(),
  transcribeAudio: jest.fn(),
  analyzeReport: jest.fn(),
  getSession: jest.fn(),
}));

beforeEach(() => {
  window.scrollTo = jest.fn();
  getSession.mockRejectedValue({ status: 404 });
});

test('the stop button aborts an active chat request and restores send', async () => {
  let requestSignal;
  sendMessage.mockImplementation((message, sessionId, language, signal) => {
    requestSignal = signal;
    return new Promise((resolve, reject) => {
      signal.addEventListener('abort', () => reject(new DOMException('Aborted', 'AbortError')));
    });
  });

  render(
    <PatientPage
      sessionId="session-1"
      isHome={false}
      onFirstMessage={() => 'session-1'}
      onUpdateTitle={() => {}}
    />
  );

  fireEvent.change(screen.getByPlaceholderText('How can I help you today?'), {
    target: { value: 'I have a headache' },
  });
  fireEvent.click(screen.getByRole('button', { name: 'Send message' }));

  const stopButton = await screen.findByRole('button', { name: 'Stop response' });
  fireEvent.click(stopButton);

  expect(requestSignal.aborted).toBe(true);
  await waitFor(() => {
    expect(screen.getByRole('button', { name: 'Send message' })).toBeInTheDocument();
  });
  expect(screen.queryByText(/could not reach/i)).not.toBeInTheDocument();
});

test('assistant replies are silent until Read aloud is pressed', async () => {
  sendMessage.mockResolvedValue({ response: 'Please rest and drink water.' });
  speakText.mockResolvedValue(new Blob(['audio'], { type: 'audio/mpeg' }));
  URL.createObjectURL = jest.fn(() => 'blob:test-audio');
  URL.revokeObjectURL = jest.fn();
  const play = jest.fn().mockResolvedValue(undefined);
  global.Audio = jest.fn(() => ({ play, pause: jest.fn(), currentTime: 0 }));

  render(
    <PatientPage
      sessionId="session-2"
      isHome={false}
      onFirstMessage={() => 'session-2'}
      onUpdateTitle={() => {}}
    />
  );

  fireEvent.change(screen.getByPlaceholderText('How can I help you today?'), {
    target: { value: 'I have a headache' },
  });
  fireEvent.click(screen.getByRole('button', { name: 'Send message' }));

  await screen.findByText('Please rest and drink water.');
  expect(speakText).not.toHaveBeenCalled();

  fireEvent.click(screen.getByRole('button', { name: 'Read aloud' }));
  await waitFor(() => expect(speakText).toHaveBeenCalledWith(
    'Please rest and drink water.', 'en', expect.anything()
  ));
  await waitFor(() => expect(play).toHaveBeenCalled());
});

test('a saved consultation loads its messages when selected', async () => {
  getSession.mockResolvedValue({
    language: 'en',
    messages: [
      { role: 'user', content: 'Previous symptom' },
      { role: 'assistant', content: 'Previous guidance' },
    ],
  });

  render(
    <PatientPage
      sessionId="saved-session"
      isHome={false}
      onFirstMessage={() => 'saved-session'}
      onUpdateTitle={() => {}}
    />
  );

  expect(await screen.findByText('Previous symptom')).toBeInTheDocument();
  expect(screen.getByText('Previous guidance')).toBeInTheDocument();
  expect(getSession).toHaveBeenCalledWith('saved-session');
});
