import { useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import {
  AlertCircle, ArrowLeft, Ban, CalendarDays, Check, Clock, Inbox, MapPin, Pencil, Trash2, UserRound, Users, Video, X,
} from 'lucide-react';
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
  STATUS_BADGE,
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
  const { data: o, isPending, error } = useOpportunity(id);
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
  const [erro, setErro] = useState<string | null>(null);

  function run<A>(
    m: { mutate: (a: A, o?: { onError?: (e: Error) => void; onSuccess?: () => void }) => void },
    args: A,
    onSuccess?: () => void
  ) {
    setErro(null);
    m.mutate(args, { onSuccess, onError: (e) => setErro(e.message) });
  }

  if (remove.isPending || remove.isSuccess) {
    return <main className="opp-page"><p className="opp-state">Apagando…</p></main>;
  }
  if (isPending) return <main className="opp-page"><p className="opp-state">Carregando…</p></main>;
  if (!o) {
    const naoExiste = error instanceof ApiError && error.notFound;
    return (
      <main className="opp-page">
        <div className="opp-state">
          <p>{naoExiste ? 'Peneira não encontrada.' : 'Não foi possível carregar a peneira.'}</p>
          <Link to="/opportunities" className="opp-btn ghost">Ver peneiras</Link>
        </div>
      </main>
    );
  }

  const idade = ageRangeLabel(o.min_age, o.max_age);
  const inscritos = (applicants.data ?? []).filter((a) => !filtroStatus || a.status === filtroStatus);

  function confirmar() {
    if (confirmacao === 'delete') {
      run(remove, id, () => navigate('/opportunities/mine'));
    } else {
      run(cancel, id);
    }
    setConfirmacao(null);
  }

  return (
    <main className="opp-page">
      <div className="opp-shell">
        <Link to="/opportunities" className="opp-back"><ArrowLeft size={16} aria-hidden /> Peneiras</Link>

        <header className="opp-hero">
          <div>
            <p className="eyebrow">{MODE_LABELS[o.mode].toUpperCase()}</p>
            <h1>{o.title}</h1>
            <p className="opp-subtitle">
              {o.organizer.first_name} {o.organizer.last_name} · {USER_ROLE_LABELS[o.organizer.role]}
            </p>
          </div>
        </header>

        {o.is_cancelled && (
          <p className="opp-alert"><Ban size={18} aria-hidden />Esta peneira foi cancelada pelo organizador.</p>
        )}
        {erro && <p className="opp-alert" role="alert"><AlertCircle size={18} aria-hidden />{erro}</p>}

        <div className="opp-detail">
          <section className="opp-panel">
            <h2>Sobre a peneira</h2>
            <p className="opp-description">{o.description}</p>
          </section>

          <aside className="opp-panel">
            <h2>Detalhes</h2>
            <ul className="opp-meta lg">
              <li><CalendarDays size={18} aria-hidden /><span><span className="sr-only">Data: </span>{formatDateTime(o.event_at)}</span></li>
              <li><MapPin size={18} aria-hidden /><span><span className="sr-only">Local: </span>{locationLabel(o)}{o.address ? ` · ${o.address}` : ''}</span></li>
              <li><Clock size={18} aria-hidden /><span>Inscrições até {formatDateTime(o.registration_deadline)}</span></li>
              <li><UserRound size={18} aria-hidden /><span>{positionsLabel(o.positions)}{idade ? ` · ${idade}` : ''}</span></li>
              <li><Users size={18} aria-hidden /><span>{spotsLabel(o.spots_left)}</span></li>
            </ul>
            {o.meeting_url && (
              <p className="opp-link-row">
                <Video size={18} aria-hidden />
                <span className="sr-only">Link da avaliação: </span>
                <a href={o.meeting_url} target="_blank" rel="noreferrer">{o.meeting_url}</a>
              </p>
            )}

            {user?.role === 'ATHLETE' && (
              <section className="opp-aside" aria-label="Sua inscrição">
                <hr className="opp-divider" />
                {o.my_application ? (
                  <>
                    <p>
                      Sua inscrição:{' '}
                      <span className={`opp-badge ${STATUS_BADGE[o.my_application.status]}`}>
                        {APPLICATION_STATUS_LABELS[o.my_application.status]}
                      </span>
                    </p>
                    {o.my_application.status === 'PENDENTE' && !o.is_cancelled && (
                      <button className="opp-btn ghost" onClick={() => run(unapply, id)} disabled={unapply.isPending}>
                        Cancelar inscrição
                      </button>
                    )}
                  </>
                ) : !o.is_open ? (
                  !o.is_cancelled && <p className="opp-hint">{o.spots_left === 0 ? 'Vagas esgotadas.' : 'Inscrições encerradas.'}</p>
                ) : o.eligibility && !o.eligibility.eligible ? (
                  <>
                    <button className="opp-btn" disabled>Inscrever-se</button>
                    <p className="opp-reason">
                      {o.eligibility.reason} <Link to="/profiles/me/edit">Editar perfil</Link>
                    </p>
                  </>
                ) : (
                  <button className="opp-btn" onClick={() => run(apply, id)} disabled={apply.isPending}>
                    Inscrever-se
                  </button>
                )}
              </section>
            )}

            {isOwner && (
              <nav className="opp-aside" aria-label="Gerenciar peneira">
                <hr className="opp-divider" />
                {!o.is_cancelled && (
                  <>
                    <Link to={`/opportunities/${id}/edit`} className="opp-btn ghost"><Pencil size={16} aria-hidden />Editar</Link>
                    <button className="opp-btn ghost" onClick={() => setConfirmacao('cancel')}>
                      <Ban size={16} aria-hidden />Cancelar peneira
                    </button>
                  </>
                )}
                <button className="opp-btn danger-ghost" onClick={() => setConfirmacao('delete')}>
                  <Trash2 size={16} aria-hidden />Apagar
                </button>
              </nav>
            )}
          </aside>
        </div>

        {isOwner && (
          <section className="opp-panel opp-applicants-panel">
            <div className="opp-panel-head">
              <h2>Inscritos ({applicants.data?.length ?? 0})</h2>
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
            </div>
            {inscritos.length === 0 ? (
              <div className="opp-state"><Inbox size={36} aria-hidden /><p>Nenhum inscrito.</p></div>
            ) : (
              <div className="opp-table-wrap">
                <table className="opp-applicants">
                  <thead>
                    <tr>
                      <th>Atleta</th><th>Posição</th><th>Idade</th><th>Cidade</th><th>Status</th>
                      <th><span className="sr-only">Ações</span></th>
                    </tr>
                  </thead>
                  <tbody>
                    {inscritos.map((a) => (
                      <tr key={a.athlete_id}>
                        <td><Link to={`/athletes/${a.athlete_id}`}>{a.first_name} {a.last_name}</Link></td>
                        <td>{a.position ? POSITION_LABELS[a.position] : '—'}</td>
                        <td>{a.age ?? '—'}</td>
                        <td>{[a.city, a.state].filter(Boolean).join('/') || '—'}</td>
                        <td><span className={`opp-badge ${STATUS_BADGE[a.status]}`}>{APPLICATION_STATUS_LABELS[a.status]}</span></td>
                        <td>
                          {!o.is_cancelled && (
                            <span className="opp-actions">
                              {a.status !== 'APROVADA' && (
                                <button
                                  className="opp-btn sm"
                                  disabled={setStatus.isPending}
                                  aria-label={`Aprovar ${a.first_name} ${a.last_name}`}
                                  onClick={() => run(setStatus, { athleteId: a.athlete_id, status: 'APROVADA' })}
                                >
                                  <Check size={14} aria-hidden />Aprovar
                                </button>
                              )}
                              {a.status !== 'RECUSADA' && (
                                <button
                                  className="opp-btn ghost sm"
                                  disabled={setStatus.isPending}
                                  aria-label={`Recusar ${a.first_name} ${a.last_name}`}
                                  onClick={() => run(setStatus, { athleteId: a.athlete_id, status: 'RECUSADA' })}
                                >
                                  <X size={14} aria-hidden />Recusar
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
        )}

        {confirmacao && (
          <div
            className="opp-modal-backdrop"
            onKeyDown={(e) => e.key === 'Escape' && setConfirmacao(null)}
            onClick={(e) => e.target === e.currentTarget && setConfirmacao(null)}
          >
            <div className="opp-modal" role="dialog" aria-modal="true" aria-labelledby="opp-confirm-title">
              <h2 id="opp-confirm-title">{confirmacao === 'delete' ? 'Apagar peneira?' : 'Cancelar peneira?'}</h2>
              <p>
                {confirmacao === 'delete'
                  ? 'A peneira e todas as inscrições serão removidas. Não dá para desfazer.'
                  : 'Ninguém mais poderá se inscrever. Os inscritos verão que a peneira foi cancelada.'}
              </p>
              <div className="opp-actions">
                <button className="opp-btn ghost" autoFocus onClick={() => setConfirmacao(null)}>Voltar</button>
                <button className="opp-btn danger" onClick={confirmar}>Confirmar</button>
              </div>
            </div>
          </div>
        )}
      </div>
    </main>
  );
}
