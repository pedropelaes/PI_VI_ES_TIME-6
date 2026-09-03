import type {
  AthleteProfileDTO,
  AthleteProfileView,
  AthleteStatus,
  DominantFoot,
  Position,
} from './types';

const SEM_VALOR = '—';

const POSITION_LABELS: Record<Position, string> = {
  GOLEIRO: 'Goleiro',
  ZAGUEIRO: 'Zagueiro',
  LATERAL: 'Lateral',
  VOLANTE: 'Volante',
  MEIA: 'Meia',
  ATACANTE: 'Atacante',
};

const FOOT_LABELS: Record<DominantFoot, string> = {
  DESTRO: 'Destro',
  CANHOTO: 'Canhoto',
  AMBIDESTRO: 'Ambidestro',
};

const STATUS_LABELS: Record<AthleteStatus, string> = {
  DISPONIVEL: 'Disponivel para Clube',
  CONTRATADO: 'Contratado',
  NAO_DISPONIVEL: 'Nao disponivel',
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

export function formatLocation(city: string | null, state: string | null): string {
  const parts = [city, state].filter((part): part is string => Boolean(part));

  if (parts.length === 0) {
    return 'Local nao informado';
  }

  return parts.join(', ');
}

export function formatPosition(position: Position | null): string {
  if (position == null) {
    return 'Posicao nao informada';
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
    avatarUrl: dto.avatar_url,
    clipsCount: dto.clips_count,
  };
}
