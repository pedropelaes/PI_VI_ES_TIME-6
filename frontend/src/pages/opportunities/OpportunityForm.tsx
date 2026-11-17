import { useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { AlertCircle } from 'lucide-react';
import { createOpportunity, updateOpportunity } from '../../features/opportunities/api';
import { useOpportunity, useOpportunityMutation } from '../../features/opportunities/hooks/queries';
import { EMPTY_FORM, MODE_LABELS, toForm, toInput } from '../../features/opportunities/mappers';
import type { OpportunityFormState, OpportunityInput, OpportunityMode } from '../../features/opportunities/types';
import { getUser } from '../../services/api';
import { POSITION_OPTIONS } from '../../features/profiles/options';
import type { Position } from '../../features/profiles/types';
import './opportunities.css';

/** Mesma página para criar (/opportunities/new) e editar (/opportunities/:id/edit). */
export default function OpportunityForm() {
  const { id } = useParams();
  if (!id) return <Formulario inicial={EMPTY_FORM} />;
  return <Edicao id={id} />;
}

function Edicao({ id }: { id: string }) {
  const { data, isPending, isError } = useOpportunity(id);
  if (isPending) return <main className="opp-page"><p className="opp-state">Carregando…</p></main>;
  if (isError || !data) return <main className="opp-page"><p className="opp-state">Peneira não encontrada.</p></main>;
  if (data.is_cancelled || data.organizer.user_id !== getUser()?.id)
    return <main className="opp-page"><p className="opp-state">Esta peneira não pode ser editada.</p></main>;
  // `key` remonta o form se o id mudar; estado inicial vem pronto, sem useEffect.
  return <Formulario key={id} id={id} inicial={toForm(data)} />;
}

function Formulario({ id, inicial }: { id?: string; inicial: OpportunityFormState }) {
  const navigate = useNavigate();
  const [f, setF] = useState(inicial);
  const save = useOpportunityMutation((input: OpportunityInput) =>
    id ? updateOpportunity(id, input) : createOpportunity(input)
  );

  const campo = (nome: keyof OpportunityFormState) => ({
    value: f[nome] as string,
    onChange: (e: { target: { value: string } }) => setF({ ...f, [nome]: e.target.value }),
  });

  function alternaPosicao(p: Position) {
    setF({ ...f, positions: f.positions.includes(p) ? f.positions.filter((x) => x !== p) : [...f.positions, p] });
  }

  return (
    <main className="opp-page">
      <div className="opp-shell narrow">
        <header className="opp-hero">
          <div>
            <p className="eyebrow">OPORTUNIDADES</p>
            <h1>{id ? 'Editar peneira' : 'Publicar peneira'}</h1>
            <p className="opp-subtitle">Atletas elegíveis poderão se inscrever até o prazo definido.</p>
          </div>
        </header>
        <form
          className="opp-form"
          onSubmit={(e) => {
            e.preventDefault();
            save.mutate(toInput(f), { onSuccess: (salva) => navigate(`/opportunities/${salva.id}`) });
          }}
        >
          {save.isError && (
            <p className="opp-alert" role="alert"><AlertCircle size={18} aria-hidden />{save.error.message}</p>
          )}

          <fieldset>
          <legend>Informações</legend>
          <label>Título<input required minLength={3} maxLength={120} {...campo('title')} /></label>
          <label>Descrição<textarea required rows={5} maxLength={5000} {...campo('description')} /></label>

          </fieldset>

          <fieldset>
          <legend>Local e datas</legend>
          <label>
            Modalidade
            <select
              value={f.mode}
              onChange={(e) => setF({ ...f, mode: e.target.value as OpportunityMode })}
            >
              {Object.entries(MODE_LABELS).map(([value, label]) => (
                <option key={value} value={value}>{label}</option>
              ))}
            </select>
          </label>

          {f.mode === 'PRESENCIAL' ? (
            <div className="opp-row">
              <label>UF<input required minLength={2} maxLength={2} {...campo('state')} /></label>
              <label>Cidade<input required maxLength={100} {...campo('city')} /></label>
              <label>Endereço<input required maxLength={200} {...campo('address')} /></label>
            </div>
          ) : (
            <label>Link da reunião<input required type="url" pattern="https?://.+" maxLength={500} {...campo('meeting_url')} /></label>
          )}

          <div className="opp-row">
            <label>Data do evento<input required type="datetime-local" {...campo('event_at')} /></label>
            <label>Prazo de inscrição<input required type="datetime-local" {...campo('registration_deadline')} /></label>
          </div>
          </fieldset>

          <fieldset>
          <legend>Requisitos</legend>

          <div className="opp-row">
            <label>Idade mínima<input type="number" min={5} max={60} {...campo('min_age')} /></label>
            <label>Idade máxima<input type="number" min={5} max={60} {...campo('max_age')} /></label>
            <label>Vagas<input type="number" placeholder="Ilimitadas" min={1} max={10000} {...campo('max_applications')} /></label>
          </div>

          <div>
            <p className="opp-hint">Posições aceitas — nenhuma marcada aceita todas</p>
            <div className="opp-chips">
            {POSITION_OPTIONS.map((o) => (
              <label key={o.value} className="opp-toggle">
                <input
                  type="checkbox"
                  checked={f.positions.includes(o.value as Position)}
                  onChange={() => alternaPosicao(o.value as Position)}
                />
                {o.label}
              </label>
            ))}
            </div>
          </div>
          </fieldset>

          <div className="opp-form-footer">
            <button type="button" className="opp-btn ghost" onClick={() => navigate(-1)}>Voltar</button>
            <button type="submit" className="opp-btn" disabled={save.isPending}>{id ? 'Salvar' : 'Publicar'}</button>
          </div>
        </form>
      </div>
    </main>
  );
}
