import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { ClipsTab } from './ClipsTab';
import type { AthleteClipView } from '../types';

const CLIPS: AthleteClipView[] = [
  { id: 'clip-1', durationLabel: '1:05', videoUrl: 'http://api.local/uploads/clips/1.mp4' },
  { id: 'clip-2', durationLabel: '0:42', videoUrl: 'http://api.local/uploads/clips/2.mp4' },
];

describe('ClipsTab', () => {
  it('mostra o estado de carregando', () => {
    render(<ClipsTab clips={[]} isLoading isError={false} />);

    expect(screen.getByText('Carregando clipes...')).toBeInTheDocument();
  });

  it('mostra o estado de erro', () => {
    render(<ClipsTab clips={[]} isLoading={false} isError />);

    expect(screen.getByText('Não foi possível carregar os clipes')).toBeInTheDocument();
  });

  it('mostra o estado vazio quando o atleta nao tem clipes', () => {
    render(<ClipsTab clips={[]} isLoading={false} isError={false} />);

    expect(screen.getByText('Este atleta ainda não publicou clipes.')).toBeInTheDocument();
  });

  it('renderiza os clipes quando ha dados', () => {
    render(<ClipsTab clips={CLIPS} isLoading={false} isError={false} />);

    expect(screen.getByText('1:05')).toBeInTheDocument();
    expect(screen.getByText('0:42')).toBeInTheDocument();
    expect(screen.queryByText('Este atleta ainda não publicou clipes.')).not.toBeInTheDocument();
  });
});
