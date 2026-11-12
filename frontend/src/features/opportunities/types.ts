import type { UserRole } from '../../shared/lib/userRole';
import type { Position } from '../profiles/types';

/** Respostas cruas da API (snake_case), espelhando backend/app/modules/opportunities/schemas.py. */
export type OpportunityMode = 'PRESENCIAL' | 'ONLINE';
export type ApplicationStatus = 'PENDENTE' | 'APROVADA' | 'RECUSADA';

export interface OrganizerDTO {
  user_id: string;
  first_name: string;
  last_name: string;
  role: UserRole;
  avatar_url: string | null;
}

export interface OpportunitySummaryDTO {
  id: string;
  title: string;
  mode: OpportunityMode;
  state: string | null;
  city: string | null;
  event_at: string;
  registration_deadline: string;
  min_age: number | null;
  max_age: number | null;
  positions: Position[];
  spots_left: number | null;
  is_cancelled: boolean;
  organizer: OrganizerDTO;
}

export interface OpportunityDetailDTO extends OpportunitySummaryDTO {
  description: string;
  address: string | null;
  meeting_url: string | null;
  max_applications: number | null;
  is_open: boolean;
  cancelled_at: string | null;
  my_application: { status: ApplicationStatus } | null;
  eligibility: { eligible: boolean; reason: string | null } | null;
}

export interface OpportunityPageDTO {
  items: OpportunitySummaryDTO[];
  next_cursor: string | null;
}

export interface ApplicationCountsDTO {
  pendente: number;
  aprovada: number;
  recusada: number;
}

export interface MyOpportunityDTO extends OpportunitySummaryDTO {
  is_open: boolean;
  counts: ApplicationCountsDTO;
}

export interface ApplicantDTO {
  athlete_id: string;
  first_name: string;
  last_name: string;
  avatar_url: string | null;
  position: Position | null;
  age: number | null;
  city: string | null;
  state: string | null;
  status: ApplicationStatus;
  created_at: string;
}

export interface ApplicationDTO {
  opportunity_id: string;
  athlete_id: string;
  status: ApplicationStatus;
}

export interface MyApplicationDTO {
  status: ApplicationStatus;
  created_at: string;
  opportunity: OpportunitySummaryDTO;
}

/** Filtros de GET /opportunities. Ausente = sem filtro. */
export interface OpportunityFilters {
  mode?: OpportunityMode;
  state?: string;
  position?: Position;
  q?: string;
  eligible?: boolean;
}

/** Corpo de POST/PATCH. Datas em ISO com fuso. */
export interface OpportunityInput {
  title: string;
  description: string;
  mode: OpportunityMode;
  state: string | null;
  city: string | null;
  address: string | null;
  meeting_url: string | null;
  event_at: string;
  registration_deadline: string;
  min_age: number | null;
  max_age: number | null;
  positions: Position[];
  max_applications: number | null;
}

/** Estado do formulário: tudo string, como os inputs entregam. */
export interface OpportunityFormState {
  title: string;
  description: string;
  mode: OpportunityMode;
  state: string;
  city: string;
  address: string;
  meeting_url: string;
  event_at: string;
  registration_deadline: string;
  min_age: string;
  max_age: string;
  positions: Position[];
  max_applications: string;
}
