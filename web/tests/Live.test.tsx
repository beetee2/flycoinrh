import { StrictMode } from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { Live } from '../src/live/Live';
import examples from '../src/live/generated/examples.json';

// Mocked idle HTTP fixtures only; no device or neural worker is involved.
const health = examples.find(example => example.contract === 'LiveHealth' && example.valid)!.value;
const config = examples.find(example => example.contract === 'LiveConfig' && example.valid)!.value;
function mockReads() {
  const fetcher = vi.fn().mockImplementation(async (path: string) => ({
    ok: true, status: 200, json: async () => path === '/health/live' ? health : config,
  }));
  vi.stubGlobal('fetch', fetcher);
  return fetcher;
}

describe('OBS00 live idle page', () => {
  it('shows honest idle state and makes only health/config reads', async () => {
    const fetcher = mockReads();
    render(<Live />);
    expect(await screen.findByText('Idle · foundation service available')).toBeInTheDocument();
    expect(screen.getByText(/Capture and inference are unavailable in OBS00/)).toBeInTheDocument();
    expect(screen.getByText('Off by default')).toBeInTheDocument();
    expect(screen.getByText('Explicit selection required')).toBeInTheDocument();
    expect(screen.queryByRole('button')).not.toBeInTheDocument();
    expect(fetcher.mock.calls.map(call => call[0])).toEqual(['/health/live', '/api/live/config']);
    for (const call of fetcher.mock.calls) expect(call[1]).toMatchObject({ method: 'GET', cache: 'no-store' });
  });

  it.each([409, 503])('reports HTTP %s and never claims service ready', async status => {
    const fetcher = mockReads();
    fetcher.mockResolvedValue({ ok: false, status });
    render(<Live />);
    expect(await screen.findByRole('alert')).toHaveTextContent(`HTTP ${status}`);
    expect(screen.queryByText('Idle · foundation service available')).not.toBeInTheDocument();
    expect(fetcher).toHaveBeenCalledTimes(2);
  });

  it('reports disconnected transport without retrying', async () => {
    const fetcher = mockReads();
    fetcher.mockRejectedValue(new Error('Failed to fetch'));
    render(<Live />);
    expect(await screen.findByRole('alert')).toHaveTextContent('Failed to fetch');
    expect(fetcher).toHaveBeenCalledTimes(2);
  });

  it.each(['/health/live', '/api/live/config'])('rejects an invalid %s response', async badPath => {
    const fetcher = mockReads();
    fetcher.mockImplementation(async (path: string) => ({
      ok: true, json: async () => path === badPath ? { invented: true } : path === '/health/live' ? health : config,
    }));
    render(<Live />);
    expect(await screen.findByRole('alert')).toHaveTextContent('Invalid live');
    expect(screen.queryByText('Idle · foundation service available')).not.toBeInTheDocument();
  });

  it('aborts reads on cleanup and remains read-only during StrictMode remount', async () => {
    const fetcher = mockReads();
    const view = render(<StrictMode><Live /></StrictMode>);
    await waitFor(() => expect(screen.getByRole('status')).toHaveTextContent('Idle'));
    expect(fetcher).toHaveBeenCalledTimes(4);
    expect(fetcher.mock.calls[0][1].signal.aborted).toBe(true);
    for (const call of fetcher.mock.calls) {
      expect(['/health/live', '/api/live/config']).toContain(call[0]);
      expect(call[1].method).toBe('GET');
    }
    view.unmount();
    for (const call of fetcher.mock.calls) expect(call[1].signal.aborted).toBe(true);
  });
});
