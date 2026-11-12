import { Link } from 'react-router-dom';
import { useMyOpportunities } from '../../features/opportunities/hooks/queries';
import type { MyOpportunityDTO } from '../../features/opportunities/types';
import { OpportunityCard } from './OpportunityCard';
import './opportunities.css';

function estado(o: MyOpportunityDTO): string {
  if (o.is_cancelled) return 'Cancelada';
  return o.is_open ? 'Aberta' : 'Encerrada';
}

export default function MyOpportunities() {
  const { data, isPending, isError } = useMyOpportunities();

  return (
    <main className="opp-page">
      <div className="opp-shell">
        <header className="opp-hero">
          <h1>Minhas peneiras</h1>
          <Link to="/opportunities/new" className="opp-btn">Publicar peneira</Link>
        </header>
        {isPending ? (
          <p className="opp-state">Carregando…</p>
        ) : isError ? (
          <p className="opp-state">Não foi possível carregar suas peneiras.</p>
        ) : data.length === 0 ? (
          <p className="opp-state">Você ainda não publicou nenhuma peneira.</p>
        ) : (
          <div className="opp-grid">
            {data.map((o) => (
              <OpportunityCard
                key={o.id}
                o={o}
                extra={
                  <span>
                    <strong>{estado(o)}</strong> · {o.counts.pendente} em análise · {o.counts.aprovada} aprovadas ·{' '}
                    {o.counts.recusada} recusadas
                  </span>
                }
              />
            ))}
          </div>
        )}
      </div>
    </main>
  );
}
