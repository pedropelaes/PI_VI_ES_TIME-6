import { Clock3, Play } from 'lucide-react';
import type { AthleteClipView } from '../types';

interface ClipsTabProps {
  clips: AthleteClipView[];
  isLoading: boolean;
  isError: boolean;
}

/**
 * Nao ha coluna de thumbnail no modelo de clipe (decisao da spec, §7.5): o
 * `<video preload="metadata">` mostra o primeiro quadro sem custo de backend.
 */
export function ClipsTab({ clips, isLoading, isError }: ClipsTabProps) {
  if (isLoading) {
    return (
      <div className="placeholder-tab">
        <Play size={48} />
        <p>Carregando clipes...</p>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="placeholder-tab">
        <Play size={48} />
        <h3>Não foi possível carregar os clipes</h3>
        <p>Tente novamente em instantes.</p>
      </div>
    );
  }

  if (clips.length === 0) {
    return (
      <div className="placeholder-tab">
        <Play size={48} />
        <h3>Nenhum clipe por aqui ainda</h3>
        <p>Este atleta ainda não publicou clipes.</p>
      </div>
    );
  }

  return (
    <div className="profile-clips-grid">
      {clips.map((clip) => (
        <div className="profile-clip-card" key={clip.id}>
          <div className="profile-clip-thumbnail">
            {/*
              `controls` e o que torna o clipe assistivel: sem ele o <video>
              servia so de thumbnail e clicar no card nao fazia nada, apesar do
              cursor: pointer. `preload="metadata"` continua carregando apenas o
              primeiro quadro ate alguem dar play.
            */}
            <video src={clip.videoUrl} preload="metadata" controls />
          </div>
          <div className="profile-clip-info">
            <div className="profile-clip-meta">
              <Clock3 size={14} /> {clip.durationLabel}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
