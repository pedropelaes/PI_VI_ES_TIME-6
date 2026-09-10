import { describe, expect, it } from 'vitest';
import {
  formatCategories,
  formatCnpj,
  formatDuration,
  formatFoot,
  formatHeight,
  formatLocation,
  formatPosition,
  resolveAvatarUrl,
  resolveClipUrl,
  toAthleteClipView,
  toAthleteProfileView,
  toClubProfileView,
  toScoutProfileView,
} from './mappers';
import type {
  AthleteClipDTO,
  AthleteProfileDTO,
  ClubProfileDTO,
  ScoutProfileDTO,
} from './types';

const DTO: AthleteProfileDTO = {
  user_id: 'abc',
  first_name: 'Jeh',
  last_name: 'Rodrigues',
  position: 'ATACANTE',
  status: 'DISPONIVEL',
  age: 19,
  height_cm: 178,
  dominant_foot: 'DESTRO',
  city: 'Campinas',
  state: 'SP',
  current_club: null,
  club_history: null,
  bio: null,
  avatar_url: null,
  clips_count: 42,
};

describe('formatHeight', () => {
  it('converte centimetros em metros', () => {
    expect(formatHeight(178)).toBe('1,78 m');
  });

  it('preenche o zero a esquerda nos centimetros', () => {
    expect(formatHeight(205)).toBe('2,05 m');
  });

  it('devolve travessao quando nao ha altura', () => {
    expect(formatHeight(null)).toBe('—');
  });
});

describe('formatLocation', () => {
  it('junta cidade e estado', () => {
    expect(formatLocation('Campinas', 'SP')).toBe('Campinas, SP');
  });

  it('usa so o que existe', () => {
    expect(formatLocation('Campinas', null)).toBe('Campinas');
    expect(formatLocation(null, 'SP')).toBe('SP');
  });

  it('devolve texto neutro quando nao ha nada', () => {
    expect(formatLocation(null, null)).toBe('Local não informado');
  });
});

describe('formatPosition e formatFoot', () => {
  it('traduz a posicao para rotulo legivel', () => {
    expect(formatPosition('ATACANTE')).toBe('Atacante');
    expect(formatPosition('GOLEIRO')).toBe('Goleiro');
    expect(formatPosition(null)).toBe('Posição não informada');
  });

  it('traduz o pe dominante', () => {
    expect(formatFoot('DESTRO')).toBe('Destro');
    expect(formatFoot(null)).toBe('—');
  });
});

describe('toAthleteProfileView', () => {
  it('monta o view model a partir do DTO', () => {
    const view = toAthleteProfileView(DTO);

    expect(view.fullName).toBe('Jeh Rodrigues');
    expect(view.initial).toBe('J');
    expect(view.location).toBe('Campinas, SP');
    expect(view.heightLabel).toBe('1,78 m');
    expect(view.positionLabel).toBe('Atacante');
    expect(view.statusLabel).toBe('Disponível para Clube');
    expect(view.ageLabel).toBe('19');
    expect(view.clipsCount).toBe(42);
  });

  it('usa travessao para idade ausente', () => {
    expect(toAthleteProfileView({ ...DTO, age: null }).ageLabel).toBe('—');
  });

  it('traduz os demais status', () => {
    expect(toAthleteProfileView({ ...DTO, status: 'CONTRATADO' }).statusLabel).toBe('Contratado');
    expect(toAthleteProfileView({ ...DTO, status: 'NAO_DISPONIVEL' }).statusLabel).toBe('Não disponível');
  });

  it('repassa o historico de clubes sem alterar o texto (quebras de linha inclusas)', () => {
    const texto = 'Base - Clube Local (2022-2024)\nSub-20 - Regional FC (2024-2025)';

    expect(toAthleteProfileView({ ...DTO, club_history: texto }).clubHistory).toBe(texto);
  });

  it('mantem null quando o atleta nao escreveu historico', () => {
    expect(toAthleteProfileView({ ...DTO, club_history: null }).clubHistory).toBeNull();
  });
});

const SCOUT_DTO: ScoutProfileDTO = {
  user_id: 'scout-1',
  first_name: 'Ana',
  last_name: 'Souza',
  organization: 'Cruzeiro',
  credential: 'CBF-1234',
  city: 'Belo Horizonte',
  state: 'MG',
  bio: 'Observadora de base.',
  avatar_url: null,
};

const CLUB_DTO: ClubProfileDTO = {
  user_id: 'club-1',
  first_name: 'Clube',
  last_name: 'Atletico',
  legal_name: 'Clube Atletico Ltda',
  cnpj: '12345678000195',
  categories: ['SUB_15', 'PROFISSIONAL'],
  city: 'Campinas',
  state: 'SP',
  bio: null,
  avatar_url: null,
};

describe('formatCnpj', () => {
  it('formata os 14 digitos no padrao brasileiro', () => {
    expect(formatCnpj('12345678000195')).toBe('12.345.678/0001-95');
  });

  it('aceita um valor ja pontuado sem duplicar a pontuacao', () => {
    expect(formatCnpj('12.345.678/0001-95')).toBe('12.345.678/0001-95');
  });

  it('devolve travessao quando nao ha CNPJ', () => {
    expect(formatCnpj(null)).toBe('—');
    expect(formatCnpj('   ')).toBe('—');
  });

  it('devolve como veio quando o tamanho nao e 14, em vez de mutilar', () => {
    // O backend guarda o campo sem validar (fora de escopo da fatia).
    expect(formatCnpj('123')).toBe('123');
  });
});

describe('formatCategories', () => {
  it('traduz as categorias de base', () => {
    expect(formatCategories(['SUB_15', 'SUB_17', 'SUB_20', 'PROFISSIONAL'])).toEqual([
      'Sub-15',
      'Sub-17',
      'Sub-20',
      'Profissional',
    ]);
  });

  it('mantem na tela uma categoria que o front ainda nao conhece', () => {
    expect(formatCategories(['SUB_11'])).toEqual(['SUB_11']);
  });

  it('lida com a lista vazia', () => {
    expect(formatCategories([])).toEqual([]);
  });
});

describe('toScoutProfileView', () => {
  it('monta o view model a partir do DTO', () => {
    const view = toScoutProfileView(SCOUT_DTO);

    expect(view.userId).toBe('scout-1');
    expect(view.fullName).toBe('Ana Souza');
    expect(view.initial).toBe('A');
    expect(view.organizationLabel).toBe('Cruzeiro');
    expect(view.credentialLabel).toBe('CBF-1234');
    expect(view.location).toBe('Belo Horizonte, MG');
    expect(view.bio).toBe('Observadora de base.');
  });

  it('usa travessao para organizacao e credencial ausentes', () => {
    const view = toScoutProfileView({ ...SCOUT_DTO, organization: null, credential: null });

    expect(view.organizationLabel).toBe('—');
    expect(view.credentialLabel).toBe('—');
  });

  it('cai no texto neutro quando nao ha cidade nem estado', () => {
    const view = toScoutProfileView({ ...SCOUT_DTO, city: null, state: null });

    expect(view.location).toBe('Local não informado');
  });
});

describe('toClubProfileView', () => {
  it('monta o view model a partir do DTO', () => {
    const view = toClubProfileView(CLUB_DTO);

    expect(view.userId).toBe('club-1');
    expect(view.fullName).toBe('Clube Atletico');
    expect(view.legalNameLabel).toBe('Clube Atletico Ltda');
    expect(view.cnpjLabel).toBe('12.345.678/0001-95');
    expect(view.categoryLabels).toEqual(['Sub-15', 'Profissional']);
    expect(view.location).toBe('Campinas, SP');
    expect(view.bio).toBeNull();
  });

  it('usa travessao para razao social e CNPJ ausentes', () => {
    const view = toClubProfileView({ ...CLUB_DTO, legal_name: null, cnpj: null });

    expect(view.legalNameLabel).toBe('—');
    expect(view.cnpjLabel).toBe('—');
  });
});

describe('resolveAvatarUrl', () => {
  it('prefixa o caminho relativo com a base da API', () => {
    // O backend devolve "/uploads/avatars/...", servido sob o prefixo da API.
    expect(resolveAvatarUrl('/uploads/avatars/abc.png')).toContain(
      '/uploads/avatars/abc.png'
    );
    expect(resolveAvatarUrl('/uploads/avatars/abc.png')).not.toBe(
      '/uploads/avatars/abc.png'
    );
  });

  it('devolve null quando nao ha avatar', () => {
    expect(resolveAvatarUrl(null)).toBeNull();
  });

  it('deixa passar uma URL absoluta', () => {
    expect(resolveAvatarUrl('https://cdn.exemplo.com/a.png')).toBe(
      'https://cdn.exemplo.com/a.png'
    );
  });

  it('o view model do atleta ja entrega a URL pronta para o img', () => {
    const view = toAthleteProfileView({ ...DTO, avatar_url: '/uploads/avatars/abc.png' });

    expect(view.avatarUrl).toContain('/uploads/avatars/abc.png');
  });
});

describe('formatDuration', () => {
  it('formata segundos como m:ss', () => {
    expect(formatDuration(65)).toBe('1:05');
  });

  it('arredonda um valor fracionario', () => {
    expect(formatDuration(65.6)).toBe('1:06');
  });

  it('preenche o zero a esquerda nos segundos', () => {
    expect(formatDuration(5)).toBe('0:05');
  });

  it('lida com duracao zero', () => {
    expect(formatDuration(0)).toBe('0:00');
  });
});

describe('resolveClipUrl', () => {
  it('prefixa o caminho relativo com a base da API', () => {
    expect(resolveClipUrl('/uploads/clips/job-1/clip.mp4')).toContain(
      '/uploads/clips/job-1/clip.mp4'
    );
    expect(resolveClipUrl('/uploads/clips/job-1/clip.mp4')).not.toBe(
      '/uploads/clips/job-1/clip.mp4'
    );
  });

  it('deixa passar uma URL absoluta', () => {
    expect(resolveClipUrl('https://cdn.exemplo.com/clip.mp4')).toBe(
      'https://cdn.exemplo.com/clip.mp4'
    );
  });
});

describe('toAthleteClipView', () => {
  const CLIP_DTO: AthleteClipDTO = {
    id: 'clip-1',
    duration_seconds: 65,
    file_url: '/uploads/clips/job-1/clip-1.mp4',
    created_at: '2026-09-01T10:00:00Z',
  };

  it('monta o view model a partir do DTO', () => {
    const view = toAthleteClipView(CLIP_DTO);

    expect(view.id).toBe('clip-1');
    expect(view.durationLabel).toBe('1:05');
    expect(view.videoUrl).toContain('/uploads/clips/job-1/clip-1.mp4');
  });
});
