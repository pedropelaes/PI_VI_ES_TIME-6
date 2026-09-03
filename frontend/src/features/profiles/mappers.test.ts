import { describe, expect, it } from 'vitest';
import { formatFoot, formatHeight, formatLocation, formatPosition, toAthleteProfileView } from './mappers';
import type { AthleteProfileDTO } from './types';

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
    expect(formatLocation(null, null)).toBe('Local nao informado');
  });
});

describe('formatPosition e formatFoot', () => {
  it('traduz a posicao para rotulo legivel', () => {
    expect(formatPosition('ATACANTE')).toBe('Atacante');
    expect(formatPosition('GOLEIRO')).toBe('Goleiro');
    expect(formatPosition(null)).toBe('Posicao nao informada');
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
    expect(view.statusLabel).toBe('Disponivel para Clube');
    expect(view.ageLabel).toBe('19');
    expect(view.clipsCount).toBe(42);
  });

  it('usa travessao para idade ausente', () => {
    expect(toAthleteProfileView({ ...DTO, age: null }).ageLabel).toBe('—');
  });

  it('traduz os demais status', () => {
    expect(toAthleteProfileView({ ...DTO, status: 'CONTRATADO' }).statusLabel).toBe('Contratado');
    expect(toAthleteProfileView({ ...DTO, status: 'NAO_DISPONIVEL' }).statusLabel).toBe('Nao disponivel');
  });
});
