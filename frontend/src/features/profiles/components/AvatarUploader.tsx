import { useRef, useState } from 'react';
import { Trash2, Upload } from 'lucide-react';
import { AVATAR_ACCEPT_ATTR, validateAvatarFile } from '../avatarFile';
import { AvatarCropModal } from './AvatarCropModal';

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

interface PendingCrop {
  file: File;
  objectUrl: string;
}

/**
 * Avatar da tela de edicao: imagem atual (ou inicial), seletor de arquivo e
 * remocao quando ha o que remover. Antes de subir, o arquivo escolhido passa
 * pelo modal de corte (`AvatarCropModal`) para o usuario posicionar e dar
 * zoom na foto; so o recorte confirmado chega a `onSelect`.
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
  const [pendingCrop, setPendingCrop] = useState<PendingCrop | null>(null);
  const [localError, setLocalError] = useState<string | null>(null);

  function handleChange(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = '';

    if (!file) {
      return;
    }

    // Validar aqui, antes do modal de corte, evita abrir a tela de recorte
    // para um arquivo que o servidor recusaria de qualquer forma.
    const erro = validateAvatarFile(file);
    setLocalError(erro);

    if (erro) {
      return;
    }

    setPendingCrop({ file, objectUrl: URL.createObjectURL(file) });
  }

  function closeCropModal() {
    if (pendingCrop) {
      URL.revokeObjectURL(pendingCrop.objectUrl);
    }
    setPendingCrop(null);
  }

  function handleCropConfirm(croppedFile: File) {
    closeCropModal();
    onSelect(croppedFile);
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
        {(localError ?? errorMessage) && (
          <p className="form-status form-status-error" role="alert">
            {localError ?? errorMessage}
          </p>
        )}
      </div>

      {pendingCrop && (
        <AvatarCropModal
          imageSrc={pendingCrop.objectUrl}
          fileName={pendingCrop.file.name}
          mimeType={pendingCrop.file.type}
          onCancel={closeCropModal}
          onConfirm={handleCropConfirm}
        />
      )}
    </section>
  );
}
