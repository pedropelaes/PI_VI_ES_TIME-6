import type { ClubProfileView } from '../types';

interface Props {
  profile: ClubProfileView;
}

/** O que so o clube tem: razao social, CNPJ e categorias de base. */
export function ClubDetails({ profile }: Props) {
  return (
    <div className="profile-details">
      <div className="detail-box">
        <div className="detail-label">Razao Social</div>
        <div className="detail-value">{profile.legalNameLabel}</div>
      </div>
      <div className="detail-box">
        <div className="detail-label">CNPJ</div>
        <div className="detail-value">{profile.cnpjLabel}</div>
      </div>
      <div className="detail-box detail-box-wide">
        <div className="detail-label">Categorias</div>
        {profile.categoryLabels.length === 0 ? (
          <div className="detail-value">Nenhuma categoria informada</div>
        ) : (
          <div className="category-list">
            {profile.categoryLabels.map((category) => (
              <span className="badge badge-neutral" key={category}>
                {category}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
