import { API_BASE } from '../../shared/lib/httpClient';
import type {
  AthleteProfileDTO,
  AthleteProfileView,
  AthleteStatus,
  ClubCategory,
  ClubProfileDTO,
  ClubProfileView,
  DominantFoot,
  Position,
  ScoutProfileDTO,
  ScoutProfileView,
} from './types';

const SEM_VALOR = '—';

export const POSITION_LABELS: Record<Position, string> = {
  GOLEIRO: 'Goleiro',
  ZAGUEIRO: 'Zagueiro',
  LATERAL: 'Lateral',
  VOLANTE: 'Volante',
  MEIA: 'Meia',
  ATACANTE: 'Atacante',
};

export const FOOT_LABELS: Record<DominantFoot, string> = {
  DESTRO: 'Destro',
  CANHOTO: 'Canhoto',
  AMBIDESTRO: 'Ambidestro',
};

export const STATUS_LABELS: Record<AthleteStatus, string> = {
  DISPONIVEL: 'Disponível para Clube',
  CONTRATADO: 'Contratado',
  NAO_DISPONIVEL: 'Não disponível',
};

/**
 * Converte centimetros (inteiro, formato da API) para metros no padrao
 * brasileiro: virgula decimal e duas casas sempre presentes, ex. 178 -> "1,78 m".
 * Um valor exato de metro (ex. 100 -> "1,00 m") mantem as duas casas por
 * consistencia visual com os demais valores, em vez de virar "1 m".
 */
export function formatHeight(heightCm: number | null): string {
  if (heightCm == null) {
    return SEM_VALOR;
  }

  const meters = Math.floor(heightCm / 100);
  const centimeters = heightCm % 100;
  const centimetersLabel = String(centimeters).padStart(2, '0');

  return `${meters},${centimetersLabel} m`;
}

/**
 * `avatar_url` chega relativo (`/uploads/avatars/...`) porque o backend monta o
 * StaticFiles sob o prefixo da API. Concatenar com VITE_API_PATH e a mesma
 * convencao ja usada para clipes e thumbnails.
 */
export function resolveAvatarUrl(avatarUrl: string | null): string | null {
  if (!avatarUrl) {
    return null;
  }

  // Uma URL absoluta (outro storage, no futuro) ja esta pronta para uso.
  if (/^https?:\/\//i.test(avatarUrl)) {
    return avatarUrl;
  }

  return `${API_BASE}${avatarUrl}`;
}

export function formatLocation(city: string | null, state: string | null): string {
  const parts = [city, state].filter((part): part is string => Boolean(part));

  if (parts.length === 0) {
    return 'Local não informado';
  }

  return parts.join(', ');
}

export function formatPosition(position: Position | null): string {
  if (position == null) {
    return 'Posição não informada';
  }

  return POSITION_LABELS[position];
}

export function formatFoot(foot: DominantFoot | null): string {
  if (foot == null) {
    return SEM_VALOR;
  }

  return FOOT_LABELS[foot];
}

export function toAthleteProfileView(dto: AthleteProfileDTO): AthleteProfileView {
  const fullName = `${dto.first_name} ${dto.last_name}`.trim();

  return {
    userId: dto.user_id,
    fullName,
    initial: dto.first_name.charAt(0).toUpperCase(),
    positionLabel: formatPosition(dto.position),
    statusLabel: STATUS_LABELS[dto.status],
    location: formatLocation(dto.city, dto.state),
    ageLabel: dto.age == null ? SEM_VALOR : String(dto.age),
    heightLabel: formatHeight(dto.height_cm),
    footLabel: formatFoot(dto.dominant_foot),
    currentClub: dto.current_club,
    bio: dto.bio,
    avatarUrl: resolveAvatarUrl(dto.avatar_url),
    clipsCount: dto.clips_count,
  };
}

export const CATEGORY_LABELS: Record<ClubCategory, string> = {
  SUB_15: 'Sub-15',
  SUB_17: 'Sub-17',
  SUB_20: 'Sub-20',
  PROFISSIONAL: 'Profissional',
};

/** Campo opcional de texto: vazio ou ausente vira travessao. */
function textOrDash(value: string | null): string {
  const trimmed = value?.trim();

  return trimmed ? trimmed : SEM_VALOR;
}

/**
 * Formata os 14 digitos do CNPJ como 00.000.000/0000-00. O backend guarda o
 * campo sem validar digito verificador (fora de escopo desta fatia), entao um
 * valor com tamanho diferente e devolvido como veio, em vez de ser mutilado.
 */
export function formatCnpj(cnpj: string | null): string {
  if (cnpj == null) {
    return SEM_VALOR;
  }

  const digits = cnpj.replace(/\D/g, '');

  if (digits.length !== 14) {
    return textOrDash(cnpj);
  }

  return `${digits.slice(0, 2)}.${digits.slice(2, 5)}.${digits.slice(5, 8)}/${digits.slice(8, 12)}-${digits.slice(12)}`;
}

/**
 * Traduz as categorias de base para rotulos legiveis. Uma categoria que o front
 * ainda nao conhece aparece como veio, em vez de sumir da tela.
 */
export function formatCategories(categories: string[]): string[] {
  return categories.map(
    (category) => CATEGORY_LABELS[category as ClubCategory] ?? category
  );
}

export function toScoutProfileView(dto: ScoutProfileDTO): ScoutProfileView {
  return {
    userId: dto.user_id,
    fullName: `${dto.first_name} ${dto.last_name}`.trim(),
    initial: dto.first_name.charAt(0).toUpperCase(),
    organizationLabel: textOrDash(dto.organization),
    credentialLabel: textOrDash(dto.credential),
    location: formatLocation(dto.city, dto.state),
    bio: dto.bio,
    avatarUrl: resolveAvatarUrl(dto.avatar_url),
  };
}

export function toClubProfileView(dto: ClubProfileDTO): ClubProfileView {
  return {
    userId: dto.user_id,
    fullName: `${dto.first_name} ${dto.last_name}`.trim(),
    initial: dto.first_name.charAt(0).toUpperCase(),
    legalNameLabel: textOrDash(dto.legal_name),
    cnpjLabel: formatCnpj(dto.cnpj),
    categoryLabels: formatCategories(dto.categories),
    location: formatLocation(dto.city, dto.state),
    bio: dto.bio,
    avatarUrl: resolveAvatarUrl(dto.avatar_url),
  };
}
