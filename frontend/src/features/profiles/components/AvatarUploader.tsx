import { useRef } from 'react';
import { Trash2, Upload } from 'lucide-react';
import { AVATAR_ACCEPT_ATTR } from '../avatarFile';

interface Props {
  /** Ja absoluta; null exibe a inicial do nome. */
  avatarUrl: string | null;
  initial: string;
  fullName: string;
  onSelect: (file: File) => void;
  onRemove: () => void;
  isBusy: boolean;
  errorMessage: string | null;
}

/**
 * Avatar da tela de edicao: imagem atual (ou inicial), seletor de arquivo e
 * remocao quando ha o que remover. Sem corte nem redimensionamento (decisao E3).
 */
export function AvatarUploader({
  avatarUrl,
  initial,
  fullName,
  onSelect,
  onRemove,
  isBusy,
  errorMessage,
}: Props) {
  const inputRef = useRef<HTMLInputElement>(null);

  function handleChange(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];

    if (file) {
      onSelect(file);
    }

    // Zerar permite reescolher o mesmo arquivo depois de um erro: sem isso o
    // input nao dispara change de novo para o mesmo nome.
    event.target.value = '';
  }

  return (
    <section className="avatar-uploader">
      <div className="public-avatar avatar-uploader-preview">
        {avatarUrl ? (
          <img
            className="public-avatar-image"
            src={avatarUrl}
            alt={`Foto de perfil de ${fullName}`}
          />
        ) : (
          initial
        )}
      </div>

      <div className="avatar-uploader-actions">
        <h2 className="avatar-uploader-title">Foto de perfil</h2>
        <p className="avatar-uploader-hint">JPEG, PNG ou WebP, até 2 MB.</p>

        <input
          ref={inputRef}
          id="avatar-file"
          className="avatar-uploader-input"
          type="file"
          accept={AVATAR_ACCEPT_ATTR}
          aria-label="Escolher foto de perfil"
          onChange={handleChange}
          disabled={isBusy}
        />

        <div className="avatar-uploader-buttons">
          <button
            type="button"
            className="btn-secondary"
            onClick={() => inputRef.current?.click()}
            disabled={isBusy}
          >
            <Upload size={18} /> Escolher imagem
          </button>

          {avatarUrl && (
            <button
              type="button"
              className="btn-secondary"
              onClick={onRemove}
              disabled={isBusy}
            >
              <Trash2 size={18} /> Remover foto
            </button>
          )}
        </div>

        {isBusy && <p className="form-status">Enviando imagem...</p>}
        {errorMessage && (
          <p className="form-status form-status-error" role="alert">
            {errorMessage}
          </p>
        )}
      </div>
    </section>
  );
}
