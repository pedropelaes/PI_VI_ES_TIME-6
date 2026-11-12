import { Link } from 'react-router-dom';
import { useMyApplications } from '../../features/opportunities/hooks/queries';
import { APPLICATION_STATUS_LABELS } from '../../features/opportunities/mappers';
import type { ApplicationStatus } from '../../features/opportunities/types';
import { OpportunityCard } from './OpportunityCard';
import './opportunities.css';

const BADGE: Record<ApplicationStatus, string> = { PENDENTE: '', APROVADA: 'success', RECUSADA: 'danger' };

export default function MyApplications() {
  const { data, isPending, isError } = useMyApplications();

  return (
    <main className="opp-page">
      <div className="opp-shell">
        <header className="opp-hero">
          <h1>Minhas inscrições</h1>
          <Link to="/opportunities" className="opp-btn ghost">Ver peneiras abertas</Link>
        </header>
        {isPending ? (
          <p className="opp-state">Carregando…</p>
        ) : isError ? (
          <p className="opp-state">Não foi possível carregar suas inscrições.</p>
        ) : data.length === 0 ? (
          <p className="opp-state">Você ainda não se inscreveu em nenhuma peneira.</p>
        ) : (
          <div className="opp-grid">
            {data.map((a) => (
              <OpportunityCard
                key={a.opportunity.id}
                o={a.opportunity}
                extra={<span className={`opp-badge ${BADGE[a.status]}`}>{APPLICATION_STATUS_LABELS[a.status]}</span>}
              />
            ))}
          </div>
        )}
      </div>
    </main>
  );
}
