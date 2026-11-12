import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useOpportunities } from '../../features/opportunities/hooks/useOpportunities';
import { MODE_LABELS } from '../../features/opportunities/mappers';
import type { OpportunityFilters, OpportunityMode } from '../../features/opportunities/types';
import { POSITION_OPTIONS } from '../../features/profiles/options';
import type { Position } from '../../features/profiles/types';
import { getUser } from '../../services/api';
import { OpportunityCard } from './OpportunityCard';
import './opportunities.css';

export default function Opportunities() {
  const role = getUser()?.role;
  const isOrganizer = role === 'CLUB' || role === 'SCOUT';
  const [filters, setFilters] = useState<OpportunityFilters>({});
  const [busca, setBusca] = useState('');
  const [uf, setUf] = useState('');
  const { items, isLoading, isError, hasNextPage, isFetchingNextPage, fetchNextPage } = useOpportunities(filters);

  const set = (patch: OpportunityFilters) => setFilters((atual) => ({ ...atual, ...patch }));

  return (
    <main className="opp-page">
      <div className="opp-shell">
        <header className="opp-hero">
          <div>
            <p className="eyebrow">OPORTUNIDADES</p>
            <h1>Peneiras abertas</h1>
          </div>
          <nav className="opp-actions">
            {role === 'ATHLETE' && (
              <Link to="/opportunities/applications" className="opp-btn ghost">Minhas inscrições</Link>
            )}
            {isOrganizer && (
              <>
                <Link to="/opportunities/mine" className="opp-btn ghost">Minhas peneiras</Link>
                <Link to="/opportunities/new" className="opp-btn">Publicar peneira</Link>
              </>
            )}
          </nav>
        </header>

        <form
          className="opp-filters"
          aria-label="Filtros"
          onSubmit={(e) => {
            e.preventDefault();
            set({ q: busca.trim() || undefined });
          }}
        >
          <input
            type="search"
            placeholder="Buscar por título ou organizador"
            aria-label="Buscar"
            value={busca}
            onChange={(e) => setBusca(e.target.value)}
          />
          <select
            aria-label="Modalidade"
            value={filters.mode ?? ''}
            onChange={(e) => set({ mode: (e.target.value || undefined) as OpportunityMode | undefined })}
          >
            <option value="">Todas as modalidades</option>
            {Object.entries(MODE_LABELS).map(([value, label]) => (
              <option key={value} value={value}>{label}</option>
            ))}
          </select>
          <select
            aria-label="Posição"
            value={filters.position ?? ''}
            onChange={(e) => set({ position: (e.target.value || undefined) as Position | undefined })}
          >
            <option value="">Todas as posições</option>
            {POSITION_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
          <input
            aria-label="UF"
            placeholder="UF"
            maxLength={2}
            size={3}
            value={uf}
            onChange={(e) => {
              const valor = e.target.value.toUpperCase();
              setUf(valor);
              // UF só filtra completa; parcial ou vazio limpa o filtro.
              set({ state: valor.length === 2 ? valor : undefined });
            }}
          />
          {role === 'ATHLETE' && (
            <label className="opp-toggle">
              <input
                type="checkbox"
                checked={Boolean(filters.eligible)}
                onChange={(e) => set({ eligible: e.target.checked || undefined })}
              />
              Elegíveis para mim
            </label>
          )}
          <button type="submit" className="opp-btn ghost">Buscar</button>
        </form>

        {isLoading ? (
          <p className="opp-state">Carregando peneiras…</p>
        ) : isError ? (
          <p className="opp-state">Não foi possível carregar as peneiras.</p>
        ) : items.length === 0 ? (
          <p className="opp-state">Nenhuma peneira aberta com esses filtros.</p>
        ) : (
          <>
            <div className="opp-grid">
              {items.map((o) => <OpportunityCard key={o.id} o={o} />)}
            </div>
            {hasNextPage && (
              <p className="opp-state">
                <button className="opp-btn ghost" onClick={fetchNextPage} disabled={isFetchingNextPage}>
                  Carregar mais
                </button>
              </p>
            )}
          </>
        )}
      </div>
    </main>
  );
}
