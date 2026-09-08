import { describe, expect, it } from 'vitest';

describe('infra de testes', () => {
  it('roda e enxerga os matchers do jest-dom', () => {
    const el = document.createElement('div');
    el.textContent = 'ok';
    document.body.appendChild(el);

    expect(el).toBeInTheDocument();
  });
});
