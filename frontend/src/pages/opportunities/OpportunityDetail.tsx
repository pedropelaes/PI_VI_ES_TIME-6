import { useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import {
  applyToOpportunity,
  cancelApplication,
  cancelOpportunity,
  deleteOpportunity,
  setApplicationStatus,
} from '../../features/opportunities/api';
import { useApplicants, useOpportunity, useOpportunityMutation } from '../../features/opportunities/hooks/queries';
import {
  ageRangeLabel,
  APPLICATION_STATUS_LABELS,
  formatDateTime,
  locationLabel,
  MODE_LABELS,
  positionsLabel,
  spotsLabel,
} from '../../features/opportunities/mappers';
import type { ApplicationStatus } from '../../features/opportunities/types';
import { POSITION_LABELS } from '../../features/profiles/mappers';
import { getUser } from '../../services/api';
import { ApiError } from '../../shared/lib/httpClient';
import { USER_ROLE_LABELS } from '../../shared/lib/userRole';
import './opportunities.css';

type Confirmacao = 'cancel' | 'delete' | null;

export default function OpportunityDetail() {
  const { id = '' } = useParams();
  const navigate = useNavigate();
  const user = getUser();
  const { data: o, isPending, isError, error } = useOpportunity(id);
  const isOwner = Boolean(o && user && o.organizer.user_id === user.id);
  const applicants = useApplicants(id, isOwner);

  const apply = useOpportunityMutation(applyToOpportunity);
  const unapply = useOpportunityMutation(cancelApplication);
  const cancel = useOpportunityMutation(cancelOpportunity);
  const remove = useOpportunityMutation(deleteOpportunity);
  const setStatus = useOpportunityMutation((a: { athleteId: string; status: ApplicationStatus }) =>
    setApplicationStatus(id, a.athleteId, a.status)
  );

  const [confirmacao, setConfirmacao] = useState<Confirmacao>(null);
  const [filtroStatus, setFiltroStatus] = useState<ApplicationStatus | ''>('');

  if (isPending) return <main className="opp-page"><p className="opp-state">Carregando…</p></main>;
  if (isError || !o) {
    const naoExiste = error instanceof ApiError && error.notFound;
    return (
      <main className="opp-page">
        <p className="opp-state">{naoExiste ? 'Peneira não encontrada.' : 'Não foi possível carregar a peneira.'}</p>
      </main>
    );
  }

  const erroAcao = [apply, unapply, cancel, remove, setStatus].find((m) => m.isError)?.error?.message;
  const idade = ageRangeLabel(o.min_age, o.max_age);
  const inscritos = (applicants.data ?? []).filter((a) => !filtroStatus || a.status === filtroStatus);

  function confirmar() {
    if (confirmacao === 'delete') {
      remove.mutate(id, { onSuccess: () => navigate('/opportunities/mine') });
    } else {
      cancel.mutate(id);
    }
    setConfirmacao(null);
  }

  return (
    <main className="opp-page">
      <div className="opp-shell">
        <Link to="/opportunities" className="opp-btn ghost">← Peneiras</Link>

        <header className="opp-hero">
          <div>
            <p className="eyebrow">{MODE_LABELS[o.mode].toUpperCase()}</p>
            <h1>{o.title}</h1>
            <p className="opp-org">
              {o.organizer.first_name} {o.organizer.last_name} · {USER_ROLE_LABELS[o.organizer.role]}
            </p>
          </div>
        </header>

        {o.is_cancelled && <p className="opp-alert">Esta peneira foi cancelada pelo organizador.</p>}
        {erroAcao && <p className="opp-alert" role="alert">{erroAcao}</p>}

        <section className="opp-panel">
          <ul className="opp-meta">
            <li>Data: {formatDateTime(o.event_at)}</li>
            <li>Local: {locationLabel(o)}{o.address ? ` · ${o.address}` : ''}</li>
            <li>Inscrições até {formatDateTime(o.registration_deadline)}</li>
            <li>{positionsLabel(o.positions)}{idade ? ` · ${idade}` : ''}</li>
            <li>{spotsLabel(o.spots_left)}</li>
          </ul>
          {o.meeting_url && (
            <p>
              Link da avaliação:{' '}
              <a href={o.meeting_url} target="_blank" rel="noreferrer">{o.meeting_url}</a>
            </p>
          )}
          <p className="opp-description">{o.description}</p>
        </section>

        {user?.role === 'ATHLETE' && (
          <section className="opp-panel" aria-label="Sua inscrição">
            {o.my_application ? (
              <>
                <p>
                  Status da inscrição: <strong>{APPLICATION_STATUS_LABELS[o.my_application.status]}</strong>
                </p>
                {o.my_application.status === 'PENDENTE' && !o.is_cancelled && (
                  <button className="opp-btn ghost" onClick={() => unapply.mutate(id)} disabled={unapply.isPending}>
                    Cancelar inscrição
                  </button>
                )}
              </>
            ) : !o.is_open ? (
              !o.is_cancelled && <p>Inscrições encerradas.</p>
            ) : o.eligibility && !o.eligibility.eligible ? (
              <>
                <button className="opp-btn" disabled>Inscrever-se</button>
                <p className="opp-reason">
                  {o.eligibility.reason} <Link to="/profiles/me/edit">Editar perfil</Link>
                </p>
              </>
            ) : (
              <button className="opp-btn" onClick={() => apply.mutate(id)} disabled={apply.isPending}>
                Inscrever-se
              </button>
            )}
          </section>
        )}

        {isOwner && (
          <>
            <nav className="opp-actions">
              {!o.is_cancelled && (
                <>
                  <Link to={`/opportunities/${id}/edit`} className="opp-btn ghost">Editar</Link>
                  <button className="opp-btn ghost" onClick={() => setConfirmacao('cancel')}>Cancelar peneira</button>
                </>
              )}
              <button className="opp-btn danger" onClick={() => setConfirmacao('delete')}>Apagar</button>
            </nav>

            <section className="opp-panel">
              <h2>Inscritos</h2>
              <select
                aria-label="Filtrar inscritos por status"
                value={filtroStatus}
                onChange={(e) => setFiltroStatus(e.target.value as ApplicationStatus | '')}
              >
                <option value="">Todos</option>
                {Object.entries(APPLICATION_STATUS_LABELS).map(([value, label]) => (
                  <option key={value} value={value}>{label}</option>
                ))}
              </select>
              {inscritos.length === 0 ? (
                <p className="opp-state">Nenhum inscrito.</p>
              ) : (
                <div className="opp-table-wrap">
                  <table className="opp-applicants">
                    <thead>
                      <tr><th>Atleta</th><th>Posição</th><th>Idade</th><th>Cidade</th><th>Status</th><th /></tr>
                    </thead>
                    <tbody>
                      {inscritos.map((a) => (
                        <tr key={a.athlete_id}>
                          <td><Link to={`/athletes/${a.athlete_id}`}>{a.first_name} {a.last_name}</Link></td>
                          <td>{a.position ? POSITION_LABELS[a.position] : '—'}</td>
                          <td>{a.age ?? '—'}</td>
                          <td>{[a.city, a.state].filter(Boolean).join('/') || '—'}</td>
                          <td>{APPLICATION_STATUS_LABELS[a.status]}</td>
                          <td>
                            {!o.is_cancelled && (
                              <span className="opp-actions">
                                {a.status !== 'APROVADA' && (
                                  <button className="opp-btn" onClick={() => setStatus.mutate({ athleteId: a.athlete_id, status: 'APROVADA' })}>
                                    Aprovar
                                  </button>
                                )}
                                {a.status !== 'RECUSADA' && (
                                  <button className="opp-btn ghost" onClick={() => setStatus.mutate({ athleteId: a.athlete_id, status: 'RECUSADA' })}>
                                    Recusar
                                  </button>
                                )}
                              </span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </section>
          </>
        )}

        {confirmacao && (
          <div className="opp-modal-backdrop">
            <div className="opp-modal" role="dialog" aria-modal="true" aria-labelledby="opp-confirm-title">
              <h2 id="opp-confirm-title">{confirmacao === 'delete' ? 'Apagar peneira?' : 'Cancelar peneira?'}</h2>
              <p>
                {confirmacao === 'delete'
                  ? 'A peneira e todas as inscrições serão removidas. Não dá para desfazer.'
                  : 'Ninguém mais poderá se inscrever. Os inscritos verão que a peneira foi cancelada.'}
              </p>
              <div className="opp-actions">
                <button className="opp-btn ghost" onClick={() => setConfirmacao(null)}>Voltar</button>
                <button className="opp-btn danger" onClick={confirmar}>Confirmar</button>
              </div>
            </div>
          </div>
        )}
      </div>
    </main>
  );
}
