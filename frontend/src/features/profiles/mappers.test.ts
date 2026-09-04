import { describe, expect, it } from 'vitest';
import {
  formatCategories,
  formatCnpj,
  formatFoot,
  formatHeight,
  formatLocation,
  formatPosition,
  toAthleteProfileView,
  toClubProfileView,
  toScoutProfileView,
} from './mappers';
import type { AthleteProfileDTO, ClubProfileDTO, ScoutProfileDTO } from './types';

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
