import { ApiError, sendMessage } from './api';

afterEach(() => {
  jest.restoreAllMocks();
});

test('sendMessage forwards the abort signal and parses JSON', async () => {
  const controller = new AbortController();
  global.fetch = jest.fn().mockResolvedValue({
    ok: true,
    headers: { get: () => 'application/json' },
    json: async () => ({ response: 'Hello' }),
  });

  await expect(sendMessage('hi', 'session-1', 'en', controller.signal))
    .resolves.toEqual({ response: 'Hello' });

  expect(fetch).toHaveBeenCalledWith(
    'http://localhost:8000/api/triage/chat',
    expect.objectContaining({ signal: controller.signal })
  );
});

test('sendMessage rejects non-successful HTTP responses', async () => {
  global.fetch = jest.fn().mockResolvedValue({
    ok: false,
    status: 503,
    headers: { get: () => 'application/json' },
    json: async () => ({ detail: 'Provider unavailable' }),
  });

  await expect(sendMessage('hi', 'session-1')).rejects.toMatchObject({
    name: 'ApiError',
    message: 'Provider unavailable',
    status: 503,
  });
  expect(ApiError).toBeDefined();
});
