import { httpGet, httpPut } from '../../shared/lib/httpClient';
import type { AthleteProfileDTO } from './types';

export function getAthleteProfile(userId: string): Promise<AthleteProfileDTO> {
  return httpGet<AthleteProfileDTO>(`/profiles/athletes/${userId}`);
}

export function getMyProfile(): Promise<AthleteProfileDTO> {
  return httpGet<AthleteProfileDTO>('/profiles/me');
}

export function updateMyProfile(
  changes: Partial<Omit<AthleteProfileDTO, 'user_id' | 'age' | 'clips_count'>>
): Promise<AthleteProfileDTO> {
  return httpPut<AthleteProfileDTO>('/profiles/me', changes);
}
