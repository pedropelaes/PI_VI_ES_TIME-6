import { Link } from 'react-router-dom';
import { ClipboardList } from 'lucide-react';
import { useMyApplications } from '../../features/opportunities/hooks/queries';
import { APPLICATION_STATUS_LABELS, STATUS_BADGE } from '../../features/opportunities/mappers';
import { OpportunityCard } from './OpportunityCard';
import './opportunities.css';

export default function MyApplications() {
  const { data, isPending, isError } = useMyApplications();

  return (
    <main className="opp-page">
      <div className="opp-shell">
        <header className="opp-hero">
          <div>
            <p className="eyebrow">OPORTUNIDADES</p>
            <h1>Minhas inscrições</h1>
            <p className="opp-subtitle">Acompanhe o status de cada peneira em que você se inscreveu.</p>
          </div>
          <Link to="/opportunities" className="opp-btn ghost">Ver peneiras abertas</Link>
        </header>
        {isPending ? (
          <p className="opp-state">Carregando…</p>
        ) : isError ? (
          <p className="opp-state">Não foi possível carregar suas inscrições.</p>
        ) : data.length === 0 ? (
          <div className="opp-state">
            <ClipboardList size={40} aria-hidden />
            <p>Você ainda não se inscreveu em nenhuma peneira.</p>
          </div>
        ) : (
          <div className="opp-grid">
            {data.map((a) => (
              <OpportunityCard
                key={a.opportunity.id}
                o={a.opportunity}
                extra={<span className={`opp-badge ${STATUS_BADGE[a.status]}`}>{APPLICATION_STATUS_LABELS[a.status]}</span>}
              />
            ))}
          </div>
        )}
      </div>
    </main>
  );
}
