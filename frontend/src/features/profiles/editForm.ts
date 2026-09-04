import type {
  AthleteProfileDTO,
  ClubProfileDTO,
  ScoutProfileDTO,
} from './types';

/**
 * Valores do formulario: tudo string (ou lista de strings), que e o que um
 * `<input>` devolve. A conversao para o tipo da API acontece no momento de
 * montar o payload, e so para os campos que mudaram.
 */
export interface AthleteFormValues {
  position: string;
  birth_date: string;
  height_cm: string;
  dominant_foot: string;
  city: string;
  state: string;
  current_club: string;
  club_history: string;
  bio: string;
  status: string;
}

export interface ScoutFormValues {
  organization: string;
  credential: string;
  city: string;
  state: string;
  bio: string;
}

export interface ClubFormValues {
  legal_name: string;
  cnpj: string;
  categories: string[];
  city: string;
  state: string;
  bio: string;
}

/** `null` da API vira campo vazio na tela; o caminho de volta e emptyToNull. */
function text(value: string | null | undefined): string {
  return value ?? '';
}

export function toAthleteFormValues(dto: AthleteProfileDTO): AthleteFormValues {
  return {
    position: text(dto.position),
    // A resposta publica expoe `age`, nao a data: sem birth_date no corpo, o
    // campo comeca vazio e so entra no payload se o usuario preencher.
    birth_date: text(dto.birth_date),
    height_cm: dto.height_cm == null ? '' : String(dto.height_cm),
    dominant_foot: text(dto.dominant_foot),
    city: text(dto.city),
    state: text(dto.state),
    current_club: text(dto.current_club),
    club_history: text(dto.club_history),
    bio: text(dto.bio),
    status: dto.status,
  };
}

export function toScoutFormValues(dto: ScoutProfileDTO): ScoutFormValues {
  return {
    organization: text(dto.organization),
    credential: text(dto.credential),
    city: text(dto.city),
    state: text(dto.state),
    bio: text(dto.bio),
  };
}

export function toClubFormValues(dto: ClubProfileDTO): ClubFormValues {
  return {
    legal_name: text(dto.legal_name),
    cnpj: text(dto.cnpj),
    categories: [...dto.categories],
    city: text(dto.city),
    state: text(dto.state),
    bio: text(dto.bio),
  };
}

function sameValue(a: unknown, b: unknown): boolean {
  if (Array.isArray(a) && Array.isArray(b)) {
    return a.length === b.length && a.every((item, index) => item === b[index]);
  }

  return a === b;
}

/**
 * Chaves cujo valor difere do que veio da API. E daqui que sai o "enviar apenas
 * os campos alterados": mandar o formulario inteiro reescreveria com valores
 * identicos campos em que o usuario nunca tocou.
 */
export function changedKeys<T extends object>(initial: T, current: T): (keyof T)[] {
  return (Object.keys(current) as (keyof T)[]).filter(
    (key) => !sameValue(initial[key], current[key])
  );
}

/** Campo de texto apagado significa "limpar", que na API e null. */
function emptyToNull(value: string): string | null {
  const trimmed = value.trim();

  return trimmed === '' ? null : trimmed;
}

function numberOrNull(value: string): number | null {
  const trimmed = value.trim();

  return trimmed === '' ? null : Number(trimmed);
}

/** Estado tem 2 letras maiusculas no backend; normalizar evita 422 bobo. */
function normalizeState(value: string): string {
  return value.trim().toUpperCase();
}

function onlyDigits(value: string): string {
  return value.replace(/\D/g, '');
}

/**
 * Normaliza antes de comparar: digitar "12.345.678/0001-90" sobre o mesmo CNPJ
 * ja gravado nao e uma alteracao, "sp" sobre "SP" tambem nao, e um espaco a
 * mais no fim da bio tampouco. Sem isso o diff acusaria mudanca e o payload
 * mandaria de volta um valor identico ao que ja esta no banco.
 */
function trimStrings<T extends object>(values: T): T {
  const entries = Object.entries(values).map(([key, value]) => [
    key,
    typeof value === 'string' ? value.trim() : value,
  ]);

  return Object.fromEntries(entries) as T;
}

export function normalizeAthlete(values: AthleteFormValues): AthleteFormValues {
  const trimmed = trimStrings(values);

  return { ...trimmed, state: normalizeState(trimmed.state) };
}

export function normalizeScout(values: ScoutFormValues): ScoutFormValues {
  const trimmed = trimStrings(values);

  return { ...trimmed, state: normalizeState(trimmed.state) };
}

export function normalizeClub(values: ClubFormValues): ClubFormValues {
  const trimmed = trimStrings(values);

  return {
    ...trimmed,
    state: normalizeState(trimmed.state),
    cnpj: onlyDigits(trimmed.cnpj),
  };
}

export function buildAthletePayload(
  initial: AthleteFormValues,
  current: AthleteFormValues
): Record<string, unknown> {
  const normalized = normalizeAthlete(current);
  const payload: Record<string, unknown> = {};

  for (const key of changedKeys(normalizeAthlete(initial), normalized)) {
    payload[key] =
      key === 'height_cm'
        ? numberOrNull(normalized.height_cm)
        : emptyToNull(normalized[key]);
  }

  return payload;
}

export function buildScoutPayload(
  initial: ScoutFormValues,
  current: ScoutFormValues
): Record<string, unknown> {
  const normalized = normalizeScout(current);
  const payload: Record<string, unknown> = {};

  for (const key of changedKeys(normalizeScout(initial), normalized)) {
    payload[key] = emptyToNull(normalized[key]);
  }

  return payload;
}

export function buildClubPayload(
  initial: ClubFormValues,
  current: ClubFormValues
): Record<string, unknown> {
  const normalized = normalizeClub(current);
  const payload: Record<string, unknown> = {};

  for (const key of changedKeys(normalizeClub(initial), normalized)) {
    // `categories` e substituida inteira quando enviada; lista vazia limpa.
    if (key === 'categories') {
      payload[key] = normalized.categories;
      continue;
    }

    payload[key] = emptyToNull(normalized[key]);
  }

  return payload;
}
