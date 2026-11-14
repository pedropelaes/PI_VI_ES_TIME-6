import { Link } from 'react-router-dom';
import { Megaphone, Plus } from 'lucide-react';
import { useMyOpportunities } from '../../features/opportunities/hooks/queries';
import type { MyOpportunityDTO } from '../../features/opportunities/types';
import { OpportunityCard } from './OpportunityCard';
import './opportunities.css';

function estado(o: MyOpportunityDTO): { label: string; badge: string } {
  return o.is_open ? { label: 'Aberta', badge: 'success' } : { label: 'Encerrada', badge: 'muted' };
}

export default function MyOpportunities() {
  const { data, isPending, isError } = useMyOpportunities();

  return (
    <main className="opp-page">
      <div className="opp-shell">
        <header className="opp-hero">
          <div>
            <p className="eyebrow">OPORTUNIDADES</p>
            <h1>Minhas peneiras</h1>
            <p className="opp-subtitle">Gerencie suas peneiras e avalie os atletas inscritos.</p>
          </div>
          <Link to="/opportunities/new" className="opp-btn"><Plus size={18} aria-hidden />Publicar peneira</Link>
        </header>
        {isPending ? (
          <p className="opp-state">Carregando…</p>
        ) : isError ? (
          <p className="opp-state">Não foi possível carregar suas peneiras.</p>
        ) : data.length === 0 ? (
          <div className="opp-state">
            <Megaphone size={40} aria-hidden />
            <p>Você ainda não publicou nenhuma peneira.</p>
          </div>
        ) : (
          <div className="opp-grid">
            {data.map((o) => {
              const e = estado(o);
              return (
                <OpportunityCard
                  key={o.id}
                  o={o}
                  extra={
                    <>
                      {/* "Cancelada" já aparece no topo do card */}
                      {!o.is_cancelled && <span className={`opp-badge ${e.badge}`}>{e.label}</span>}
                      <span>
                        <strong>{o.counts.pendente}</strong> em análise · <strong>{o.counts.aprovada}</strong> aprovadas ·{' '}
                        <strong>{o.counts.recusada}</strong> recusadas
                      </span>
                    </>
                  }
                />
              );
            })}
          </div>
        )}
      </div>
    </main>
  );
}
