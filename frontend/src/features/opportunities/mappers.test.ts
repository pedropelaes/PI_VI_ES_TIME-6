import { describe, expect, it } from 'vitest';
import {
  ageRangeLabel,
  buildOpportunityQuery,
  EMPTY_FORM,
  formatDateTime,
  isoToLocalInput,
  localInputToIso,
  locationLabel,
  positionsLabel,
  spotsLabel,
  toInput,
} from './mappers';

describe('buildOpportunityQuery', () => {
  it('omite filtros vazios e inclui cursor', () => {
    expect(buildOpportunityQuery({})).toBe('');
    expect(
      buildOpportunityQuery({ mode: 'ONLINE', state: 'SP', position: 'MEIA', q: '  sub 17 ', eligible: true }, 'abc')
    ).toBe('mode=ONLINE&state=SP&position=MEIA&q=sub+17&eligible=true&cursor=abc');
  });

  it('não manda eligible=false', () => {
    expect(buildOpportunityQuery({ eligible: false })).toBe('');
  });
});

describe('rótulos', () => {
  it('faixa etária', () => {
    expect(ageRangeLabel(15, 17)).toBe('15 a 17 anos');
    expect(ageRangeLabel(15, null)).toBe('A partir de 15 anos');
    expect(ageRangeLabel(null, 17)).toBe('Até 17 anos');
    expect(ageRangeLabel(null, null)).toBeNull();
  });

  it('vagas', () => {
    expect(spotsLabel(null)).toBe('Vagas ilimitadas');
    expect(spotsLabel(1)).toBe('1 vaga restante');
    expect(spotsLabel(0)).toBe('0 vagas restantes');
  });

  it('local e posições', () => {
    expect(locationLabel({ mode: 'ONLINE', city: null, state: null })).toBe('Online');
    expect(locationLabel({ mode: 'PRESENCIAL', city: 'Campinas', state: 'SP' })).toBe('Campinas/SP');
    expect(positionsLabel([])).toBe('Todas as posições');
    expect(positionsLabel(['GOLEIRO', 'MEIA'])).toBe('Goleiro, Meia');
  });
});

describe('datas', () => {
  it('formata no fuso local (pinado em America/Sao_Paulo no vitest)', () => {
    const texto = formatDateTime('2026-12-01T12:00:00Z');
    expect(texto).toContain('01/12/2026');
    expect(texto).toContain('09:00');
  });

  it('datetime-local ida e volta', () => {
    expect(isoToLocalInput(localInputToIso('2026-12-01T09:30'))).toBe('2026-12-01T09:30');
  });
});

describe('toInput', () => {
  it('peneira online zera os campos de local e converte números', () => {
    const input = toInput({
      ...EMPTY_FORM,
      title: ' Peneira ',
      description: 'Desc',
      mode: 'ONLINE',
      state: 'SP',
      city: 'Campinas',
      address: 'Rua A',
      meeting_url: 'https://meet.example.com/x',
      event_at: '2026-12-01T09:00',
      registration_deadline: '2026-11-25T09:00',
      min_age: '15',
      max_age: '',
      max_applications: '30',
    });
    expect(input.title).toBe('Peneira');
    expect([input.state, input.city, input.address]).toEqual([null, null, null]);
    expect(input.meeting_url).toBe('https://meet.example.com/x');
    expect([input.min_age, input.max_age, input.max_applications]).toEqual([15, null, 30]);
    expect(input.event_at).toBe(localInputToIso('2026-12-01T09:00'));
  });

  it('peneira presencial zera o link e põe UF em maiúsculas', () => {
    const input = toInput({ ...EMPTY_FORM, mode: 'PRESENCIAL', state: 'sp', meeting_url: 'https://x', event_at: '2026-12-01T09:00', registration_deadline: '2026-11-25T09:00' });
    expect(input.state).toBe('SP');
    expect(input.meeting_url).toBeNull();
  });
});
