import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import axe from 'axe-core';
import { describe, expect, it, vi } from 'vitest';
import { App } from '../src/App';

const capabilities = {
  schema_version: '1', fixture: true, real_model_available: false,
  admission: 'closed', learning_claim_status: 'NOT_RUN',
  approved_checkpoint_ids: [], approved_comparison_ids: [],
};

describe('foundation component (mocked HTTP, not system E2E)', () => {
  it('shows loading while the response is pending', () => {
    vi.stubGlobal('fetch', vi.fn(() => new Promise(() => {})));
    render(<App />);
    expect(screen.getByRole('status')).toHaveTextContent('Checking service capabilities');
    expect(screen.queryByText('Real model available')).not.toBeInTheDocument();
  });

  it('persistently labels fixtures and reports closed admission with no learning claim', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => capabilities }));
    const { container } = render(<App />);
    expect(await screen.findByRole('note')).toHaveTextContent('FIXTURE — NOT REAL MODEL');
    expect(screen.getByRole('status')).toHaveTextContent('Real model unavailable');
    expect(screen.getByText('Closed')).toBeInTheDocument();
    expect(screen.getByText('Not evaluated')).toBeInTheDocument();
    // jsdom cannot evaluate rendered contrast; actual captures receive visual review.
    const report = await axe.run(container, { rules: { 'color-contrast': { enabled: false } } });
    expect(report.violations).toEqual([]);
  });

  it('reports an unavailable real profile without substituting a fixture', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => ({ ...capabilities, fixture: false, admission: 'unavailable' }) }));
    render(<App />);
    expect(await screen.findByText('Real model unavailable')).toBeInTheDocument();
    expect(screen.getByText('Unavailable')).toBeInTheDocument();
    expect(screen.queryByRole('note')).not.toBeInTheDocument();
  });

  it.each([
    { ...capabilities, fixture: 'false' },
    { ...capabilities, unexpected: true },
    { ...capabilities, admission: 'pretend' },
    { ...capabilities, approved_checkpoint_ids: Array(33).fill('checkpoint') },
  ])('rejects malformed API capabilities %#', async (payload) => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => payload }));
    render(<App />);
    expect(await screen.findByRole('alert')).toHaveTextContent('invalid capabilities response');
    expect(screen.queryByText('Real model available')).not.toBeInTheDocument();
    expect(screen.queryByText('Closed')).not.toBeInTheDocument();
  });

  it('allows keyboard retry after an actual HTTP error state', async () => {
    const request = vi.fn().mockResolvedValueOnce({ ok: false }).mockResolvedValueOnce({ ok: true, json: async () => capabilities });
    vi.stubGlobal('fetch', request);
    const user = userEvent.setup();
    render(<App />);
    expect(await screen.findByRole('alert')).toHaveTextContent('service is unavailable');
    await user.tab();
    expect(screen.getByRole('link', { name: 'FLYTRAP home' })).toHaveFocus();
    await user.tab();
    expect(screen.getByRole('button', { name: 'Retry connection' })).toHaveFocus();
    await user.keyboard('{Enter}');
    expect(await screen.findByRole('note')).toHaveTextContent('FIXTURE — NOT REAL MODEL');
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });

  it('shows a network failure instead of available capabilities', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('Network disconnected')));
    render(<App />);
    expect(await screen.findByRole('alert')).toHaveTextContent('Network disconnected');
    expect(screen.queryByText('Closed')).not.toBeInTheDocument();
  });
});
