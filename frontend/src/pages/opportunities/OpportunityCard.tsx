import type { ReactNode } from 'react';
import { Link } from 'react-router-dom';
import {
  ageRangeLabel,
  formatDateTime,
  locationLabel,
  MODE_LABELS,
  positionsLabel,
  spotsLabel,
} from '../../features/opportunities/mappers';
import type { OpportunitySummaryDTO } from '../../features/opportunities/types';
import { USER_ROLE_LABELS } from '../../shared/lib/userRole';

/** Card usado na lista, em "minhas peneiras" e em "minhas inscrições". `extra` vai no rodapé. */
export function OpportunityCard({ o, extra }: { o: OpportunitySummaryDTO; extra?: ReactNode }) {
  const idade = ageRangeLabel(o.min_age, o.max_age);
  return (
    <article className="opp-card">
      <Link to={`/opportunities/${o.id}`} className="opp-card-link">
        <div className="opp-card-top">
          <span className={`opp-badge ${o.mode === 'ONLINE' ? 'online' : ''}`}>{MODE_LABELS[o.mode]}</span>
          {o.is_cancelled && <span className="opp-badge danger">Cancelada</span>}
        </div>
        <h2>{o.title}</h2>
        <p className="opp-org">
          {o.organizer.first_name} {o.organizer.last_name} · {USER_ROLE_LABELS[o.organizer.role]}
        </p>
        <ul className="opp-meta">
          <li>Data: {formatDateTime(o.event_at)}</li>
          <li>Local: {locationLabel(o)}</li>
          <li>Inscrições até {formatDateTime(o.registration_deadline)}</li>
          <li>
            {positionsLabel(o.positions)}
            {idade ? ` · ${idade}` : ''}
          </li>
          <li>{spotsLabel(o.spots_left)}</li>
        </ul>
      </Link>
      {extra && <div className="opp-card-extra">{extra}</div>}
    </article>
  );
}
