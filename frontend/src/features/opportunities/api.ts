import { httpDelete, httpGet, httpPatch, httpPost } from '../../shared/lib/httpClient';
import { buildOpportunityQuery } from './mappers';
import type {
  ApplicantDTO,
  ApplicationDTO,
  ApplicationStatus,
  MyApplicationDTO,
  MyOpportunityDTO,
  OpportunityDetailDTO,
  OpportunityFilters,
  OpportunityInput,
  OpportunityPageDTO,
} from './types';

export function getOpportunities(filters: OpportunityFilters, cursor?: string | null) {
  return httpGet<OpportunityPageDTO>(`/opportunities?${buildOpportunityQuery(filters, cursor)}`);
}

export function getOpportunity(id: string) {
  return httpGet<OpportunityDetailDTO>(`/opportunities/${id}`);
}

export function createOpportunity(input: OpportunityInput) {
  return httpPost<OpportunityDetailDTO>('/opportunities', input);
}

export function updateOpportunity(id: string, input: OpportunityInput) {
  return httpPatch<OpportunityDetailDTO>(`/opportunities/${id}`, input);
}

export function cancelOpportunity(id: string) {
  return httpPost<OpportunityDetailDTO>(`/opportunities/${id}/cancel`);
}

export function deleteOpportunity(id: string) {
  return httpDelete<void>(`/opportunities/${id}`);
}

export function getMyOpportunities() {
  return httpGet<MyOpportunityDTO[]>('/opportunities/mine');
}

export function getApplicants(id: string) {
  return httpGet<ApplicantDTO[]>(`/opportunities/${id}/applications`);
}

export function setApplicationStatus(id: string, athleteId: string, status: ApplicationStatus) {
  return httpPatch<ApplicationDTO>(`/opportunities/${id}/applications/${athleteId}`, { status });
}

export function applyToOpportunity(id: string) {
  return httpPost<ApplicationDTO>(`/opportunities/${id}/apply`);
}

export function cancelApplication(id: string) {
  return httpDelete<void>(`/opportunities/${id}/apply`);
}

export function getMyApplications() {
  return httpGet<MyApplicationDTO[]>('/opportunities/applications/me');
}
