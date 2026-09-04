import { describe, expect, it } from 'vitest';
import {
  buildAthletePayload,
  buildClubPayload,
  buildScoutPayload,
  toAthleteFormValues,
  toClubFormValues,
  toScoutFormValues,
} from './editForm';
import type { AthleteProfileDTO, ClubProfileDTO, ScoutProfileDTO } from './types';

const ATHLETE: AthleteProfileDTO = {
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

const SCOUT: ScoutProfileDTO = {
  user_id: 'def',
  first_name: 'Marina',
  last_name: 'Alves',
  organization: 'Olheiros FC',
  credential: null,
  city: 'Santos',
  state: 'SP',
  bio: null,
  avatar_url: null,
};

const CLUB: ClubProfileDTO = {
  user_id: 'ghi',
  first_name: 'Clube',
  last_name: 'Atletico',
  legal_name: 'Clube Atlético LTDA',
  cnpj: '12345678000190',
  categories: ['SUB_17'],
  city: 'Campinas',
  state: 'SP',
  bio: null,
  avatar_url: null,
};

describe('toAthleteFormValues', () => {
  it('traduz null para campo vazio', () => {
    const values = toAthleteFormValues(ATHLETE);

    expect(values.current_club).toBe('');
    expect(values.club_history).toBe('');
    expect(values.height_cm).toBe('178');
  });

  it('deixa a data de nascimento vazia quando a API nao a devolve', () => {
    // A resposta publica expoe `age`, nao `birth_date`: o campo comeca vazio.
    expect(toAthleteFormValues(ATHLETE).birth_date).toBe('');
  });
});

describe('buildAthletePayload', () => {
  it('nao envia nada quando o formulario nao foi tocado', () => {
    const initial = toAthleteFormValues(ATHLETE);

    expect(buildAthletePayload(initial, initial)).toEqual({});
  });

  it('envia apenas o campo alterado', () => {
    const initial = toAthleteFormValues(ATHLETE);

    expect(buildAthletePayload(initial, { ...initial, city: 'Santos' })).toEqual({
      city: 'Santos',
    });
  });

  it('converte altura para numero', () => {
    const initial = toAthleteFormValues(ATHLETE);

    expect(buildAthletePayload(initial, { ...initial, height_cm: '181' })).toEqual({
      height_cm: 181,
    });
  });

  it('campo apagado vira null, que e como a API limpa o valor', () => {
    const initial = toAthleteFormValues(ATHLETE);

    expect(buildAthletePayload(initial, { ...initial, city: '' })).toEqual({
      city: null,
    });
  });

  it('envia o historico de clubes preservando as quebras de linha', () => {
    const initial = toAthleteFormValues(ATHLETE);
    const historico = 'Ponte Preta (2019-2021)\nGuarani (2022)';

    expect(buildAthletePayload(initial, { ...initial, club_history: historico })).toEqual(
      { club_history: historico }
    );
  });

  it('ignora diferenca de caixa no estado e espaco sobrando', () => {
    const initial = toAthleteFormValues(ATHLETE);

    expect(
      buildAthletePayload(initial, { ...initial, state: 'sp', city: 'Campinas  ' })
    ).toEqual({});
  });

  it('junta varios campos alterados numa unica chamada', () => {
    const initial = toAthleteFormValues(ATHLETE);

    expect(
      buildAthletePayload(initial, {
        ...initial,
        position: 'MEIA',
        status: 'CONTRATADO',
      })
    ).toEqual({ position: 'MEIA', status: 'CONTRATADO' });
  });
});

describe('buildScoutPayload', () => {
  it('envia apenas o campo alterado', () => {
    const initial = toScoutFormValues(SCOUT);

    expect(
      buildScoutPayload(initial, { ...initial, credential: 'CBF-1234' })
    ).toEqual({ credential: 'CBF-1234' });
  });

  it('nao envia nada sem edicao', () => {
    const initial = toScoutFormValues(SCOUT);

    expect(buildScoutPayload(initial, initial)).toEqual({});
  });
});

describe('buildClubPayload', () => {
  it('nao envia nada sem edicao', () => {
    const initial = toClubFormValues(CLUB);

    expect(buildClubPayload(initial, initial)).toEqual({});
  });

  it('envia a lista inteira de categorias quando ela muda', () => {
    const initial = toClubFormValues(CLUB);

    expect(
      buildClubPayload(initial, { ...initial, categories: ['SUB_17', 'SUB_20'] })
    ).toEqual({ categories: ['SUB_17', 'SUB_20'] });
  });

  it('CNPJ reescrito com mascara sobre o mesmo numero nao e alteracao', () => {
    const initial = toClubFormValues(CLUB);

    expect(
      buildClubPayload(initial, { ...initial, cnpj: '12.345.678/0001-90' })
    ).toEqual({});
  });

  it('envia o CNPJ so com digitos', () => {
    const initial = toClubFormValues(CLUB);

    expect(
      buildClubPayload(initial, { ...initial, cnpj: '99.999.999/0001-99' })
    ).toEqual({ cnpj: '99999999000199' });
  });
});
