import type { ScoutProfileView } from '../types';

interface Props {
  profile: ScoutProfileView;
}

/** O que so o scout tem: organizacao e credencial. */
export function ScoutDetails({ profile }: Props) {
  return (
    <div className="profile-details">
      <div className="detail-box">
        <div className="detail-label">Organização</div>
        <div className="detail-value">{profile.organizationLabel}</div>
      </div>
      <div className="detail-box">
        <div className="detail-label">Credencial</div>
        <div className="detail-value">{profile.credentialLabel}</div>
      </div>
    </div>
  );
}
