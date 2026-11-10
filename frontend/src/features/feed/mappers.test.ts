import { describe, expect, it } from 'vitest';
import { buildFeedQuery, formatDuration, formatRelativeTime, toFeedItemView } from './mappers';
import type { FeedItemDTO } from './types';

const AGORA = Date.parse('2026-10-27T20:00:00Z');

const DTO: FeedItemDTO = {
  id: 'clip-1',
  file_url: '/uploads/clips/job-1/clip_1.mp4',
  duration_seconds: 7.5,
  published_at: '2026-10-27T17:00:00+00:00',
  like_count: 3,
  liked_by_me: true,
  athlete: {
    user_id: 'abc',
    first_name: 'Jeh',
    last_name: 'Rodrigues',
    avatar_url: null,
    position: 'ATACANTE',
    age: 19,
    city: 'Campinas',
    state: 'SP',
    status: 'DISPONIVEL',
  },
};

describe('formatDuration', () => {
  it('arredonda e formata mm:ss', () => {
    expect(formatDuration(7.5)).toBe('00:08');
    expect(formatDuration(75)).toBe('01:15');
  });
});

describe('formatRelativeTime', () => {
  it('lê data ISO com fuso corretamente', () => {
    const agora = new Date('2026-10-27T20:00:00Z').getTime();
    expect(formatRelativeTime('2026-10-27T17:00:00+00:00', agora)).toBe('há 3 h');
  });
});

describe('formatRelativeTime', () => {
  it.each([
    ['2026-10-27T20:00:00Z', 'agora'],
    ['2026-10-27T19:45:00Z', 'há 15 min'],
    ['2026-10-27T17:00:00Z', 'há 3 h'],
    ['2026-10-25T20:00:00Z', 'há 2 d'],
  ])('%s -> %s', (data, esperado) => {
    expect(formatRelativeTime(data, AGORA)).toBe(esperado);
  });
});

describe('toFeedItemView', () => {
  it('formata o card com os dados do atleta', () => {
    const view = toFeedItemView(DTO);

    expect(view.videoUrl).toMatch(/\/uploads\/clips\/job-1\/clip_1\.mp4$/);
    expect(view.durationLabel).toBe('00:08');
    expect(formatRelativeTime(view.publishedAt, AGORA)).toBe('há 3 h');
    expect(view.likeCount).toBe(3);
    expect(view.likedByMe).toBe(true);
    expect(view.athlete).toMatchObject({
      fullName: 'Jeh Rodrigues',
      initial: 'J',
      details: 'Atacante · 19 anos · Campinas/SP',
      isAvailable: true,
      profilePath: '/athletes/abc',
      avatarUrl: null,
    });
  });

  it('omite o que o atleta nao preencheu', () => {
    const view = toFeedItemView(
      { ...DTO, athlete: { ...DTO.athlete, position: null, age: null, city: null, state: 'SP' } },
      AGORA
    );

    expect(view.athlete.details).toBe('SP');
  });

  it('usa "Atleta" quando o perfil esta vazio', () => {
    const view = toFeedItemView(
      { ...DTO, athlete: { ...DTO.athlete, position: null, age: null, city: null, state: null, status: 'CONTRATADO' } },
      AGORA
    );

    expect(view.athlete.details).toBe('Atleta');
    expect(view.athlete.isAvailable).toBe(false);
  });
});

describe('buildFeedQuery', () => {
  it('so manda os filtros preenchidos', () => {
    expect(buildFeedQuery({})).toBe('limit=12');
    expect(buildFeedQuery({ position: 'GOLEIRO', maxAge: 19, q: '  caio ' }, 'abc')).toBe(
      'position=GOLEIRO&max_age=19&q=caio&cursor=abc&limit=12'
    );
  });
});
