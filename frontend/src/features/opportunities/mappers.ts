import { POSITION_LABELS } from '../profiles/mappers';
import type { Position } from '../profiles/types';
import type {
  ApplicationStatus,
  OpportunityDetailDTO,
  OpportunityFilters,
  OpportunityFormState,
  OpportunityInput,
  OpportunityMode,
} from './types';

export const MODE_LABELS: Record<OpportunityMode, string> = {
  PRESENCIAL: 'Presencial',
  ONLINE: 'Online',
};

export const APPLICATION_STATUS_LABELS: Record<ApplicationStatus, string> = {
  PENDENTE: 'Em análise',
  APROVADA: 'Aprovada',
  RECUSADA: 'Recusada',
};

export function buildOpportunityQuery(filters: OpportunityFilters, cursor?: string | null): string {
  const params = new URLSearchParams();
  if (filters.mode) params.set('mode', filters.mode);
  if (filters.state) params.set('state', filters.state);
  if (filters.position) params.set('position', filters.position);
  const q = filters.q?.trim();
  if (q) params.set('q', q);
  if (filters.eligible) params.set('eligible', 'true');
  if (cursor) params.set('cursor', cursor);
  return params.toString();
}

// Fuso do navegador, o mesmo que o formulário usa (localInputToIso/isoToLocalInput).
const DATA_HORA = new Intl.DateTimeFormat('pt-BR', {
  day: '2-digit',
  month: '2-digit',
  year: 'numeric',
  hour: '2-digit',
  minute: '2-digit',
});

export function formatDateTime(iso: string): string {
  return DATA_HORA.format(new Date(iso));
}

export function locationLabel(o: { mode: OpportunityMode; city: string | null; state: string | null }): string {
  if (o.mode === 'ONLINE') return 'Online';
  return [o.city, o.state].filter(Boolean).join('/');
}

export function ageRangeLabel(min: number | null, max: number | null): string | null {
  if (min != null && max != null) return `${min} a ${max} anos`;
  if (min != null) return `A partir de ${min} anos`;
  if (max != null) return `Até ${max} anos`;
  return null;
}

export function positionsLabel(positions: Position[]): string {
  return positions.length ? positions.map((p) => POSITION_LABELS[p]).join(', ') : 'Todas as posições';
}

export function spotsLabel(spots: number | null): string {
  if (spots === null) return 'Vagas ilimitadas';
  return spots === 1 ? '1 vaga restante' : `${spots} vagas restantes`;
}

/** `<input type="datetime-local">` ("2026-12-01T09:00", hora local) → ISO UTC. */
export function localInputToIso(value: string): string {
  return new Date(value).toISOString();
}

/** ISO → valor de `<input type="datetime-local">` na hora local. */
export function isoToLocalInput(iso: string): string {
  const d = new Date(iso);
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

export const EMPTY_FORM: OpportunityFormState = {
  title: '',
  description: '',
  mode: 'PRESENCIAL',
  state: '',
  city: '',
  address: '',
  meeting_url: '',
  event_at: '',
  registration_deadline: '',
  min_age: '',
  max_age: '',
  positions: [],
  max_applications: '',
};

export function toForm(o: OpportunityDetailDTO): OpportunityFormState {
  const texto = (v: string | number | null) => (v == null ? '' : String(v));
  return {
    title: o.title,
    description: o.description,
    mode: o.mode,
    state: texto(o.state),
    city: texto(o.city),
    address: texto(o.address),
    meeting_url: texto(o.meeting_url),
    event_at: isoToLocalInput(o.event_at),
    registration_deadline: isoToLocalInput(o.registration_deadline),
    min_age: texto(o.min_age),
    max_age: texto(o.max_age),
    positions: o.positions,
    max_applications: texto(o.max_applications),
  };
}

/** Form → corpo da API. Zera os campos do modo que não vale (o backend faria o mesmo). */
export function toInput(f: OpportunityFormState): OpportunityInput {
  const num = (s: string) => (s.trim() === '' ? null : Number(s));
  const presencial = f.mode === 'PRESENCIAL';
  return {
    title: f.title.trim(),
    description: f.description.trim(),
    mode: f.mode,
    state: presencial ? f.state.trim().toUpperCase() : null,
    city: presencial ? f.city.trim() : null,
    address: presencial ? f.address.trim() : null,
    meeting_url: presencial ? null : f.meeting_url.trim(),
    event_at: localInputToIso(f.event_at),
    registration_deadline: localInputToIso(f.registration_deadline),
    min_age: num(f.min_age),
    max_age: num(f.max_age),
    positions: f.positions,
    max_applications: num(f.max_applications),
  };
}
