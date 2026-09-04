import { httpGet, httpPut } from '../../shared/lib/httpClient';
import type { AthleteProfileDTO, ClubProfileDTO, ScoutProfileDTO } from './types';

/**
 * Uma rota publica por papel (decisao Q2). Cada uma devolve 404 quando o id nao
 * existe ou existe com outro papel — do ponto de vista do cliente, nao existe
 * scout com aquele id.
 */
export function getAthleteProfile(userId: string): Promise<AthleteProfileDTO> {
  return httpGet<AthleteProfileDTO>(`/profiles/athletes/${userId}`);
}

export function getScoutProfile(userId: string): Promise<ScoutProfileDTO> {
  return httpGet<ScoutProfileDTO>(`/profiles/scouts/${userId}`);
}

export function getClubProfile(userId: string): Promise<ClubProfileDTO> {
  return httpGet<ClubProfileDTO>(`/profiles/clubs/${userId}`);
}

/**
 * `/profiles/me` e polimorfico (Q3): o papel vem do JWT, nao da URL. O formato
 * `{ role, profile }` (Q4) da narrowing limpo no TypeScript.
 */
export type MyProfileDTO =
  | { role: 'ATHLETE'; profile: AthleteProfileDTO }
  | { role: 'SCOUT'; profile: ScoutProfileDTO }
  | { role: 'CLUB'; profile: ClubProfileDTO };

export function getMyProfile(): Promise<MyProfileDTO> {
  return httpGet<MyProfileDTO>('/profiles/me');
}

/**
 * Atualizacao parcial dos campos do papel do autenticado. Enviar campo de outro
 * papel e 422 no servidor — a tela de edicao (fora desta fatia) e quem restringe
 * o formulario ao papel certo.
 */
export function updateMyProfile(changes: Record<string, unknown>): Promise<MyProfileDTO> {
  return httpPut<MyProfileDTO>('/profiles/me', changes);
}
