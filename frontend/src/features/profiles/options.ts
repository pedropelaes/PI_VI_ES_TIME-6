import {
  CATEGORY_LABELS,
  FOOT_LABELS,
  POSITION_LABELS,
  STATUS_LABELS,
} from './mappers';

export interface SelectOption {
  value: string;
  label: string;
}

/**
 * As opcoes dos selects saem dos mesmos mapas que o perfil publico usa para
 * exibir os rotulos: um enum novo aparece nos dois lugares de uma vez.
 */
function toOptions(labels: Record<string, string>): SelectOption[] {
  return Object.entries(labels).map(([value, label]) => ({ value, label }));
}

export const POSITION_OPTIONS = toOptions(POSITION_LABELS);
export const FOOT_OPTIONS = toOptions(FOOT_LABELS);
export const STATUS_OPTIONS = toOptions(STATUS_LABELS);
export const CATEGORY_OPTIONS = toOptions(CATEGORY_LABELS);
