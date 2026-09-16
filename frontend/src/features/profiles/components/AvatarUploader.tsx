import { useEffect, useRef, useState } from 'react';
import { Pencil, Trash2, Upload } from 'lucide-react';
import { AVATAR_ACCEPT_ATTR, guessAvatarMimeType, validateAvatarFile } from '../avatarFile';
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

interface ImagemParaCorte {
  imageSrc: string;
  fileName: string;
  mimeType: string;
}

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
  const [pendingCrop, setPendingCrop] = useState<ImagemParaCorte | null>(null);
  const [localError, setLocalError] = useState<string | null>(null);

  // A foto original (antes de qualquer corte) escolhida nesta sessao. E ela
  // que o lapis reabre depois -- a `avatarUrl` e so a versao ja recortada
  // que foi salva. Sem a original guardada aqui (ex.: apos recarregar a
  // pagina), o lapis cai de volta pra `avatarUrl` mesmo, na falta de outra.
  const [original, setOriginal] = useState<ImagemParaCorte | null>(null);

  // Libera a object URL da original guardada quando o componente desmonta.
  useEffect(() => {
    return () => {
      if (original) {
        URL.revokeObjectURL(original.imageSrc);
      }
    };
  }, [original]);

  function handleChange(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = '';

    if (!file) {
      return;
    }

    const erro = validateAvatarFile(file);
    setLocalError(erro);

    if (erro) {
      return;
    }

    // Troca a original guardada: libera a anterior (se houver) antes de
    // criar a nova.
    if (original) {
      URL.revokeObjectURL(original.imageSrc);
    }

    const novaOriginal: ImagemParaCorte = {
      imageSrc: URL.createObjectURL(file),
      fileName: file.name,
      mimeType: file.type,
    };

    setOriginal(novaOriginal);
    setPendingCrop(novaOriginal);
  }

  function handleEditClick() {
    if (original) {
      setPendingCrop(original);
      return;
    }

    if (avatarUrl) {
      setPendingCrop({
        imageSrc: avatarUrl,
        fileName: 'avatar',
        mimeType: guessAvatarMimeType(avatarUrl),
      });
      return;
    }

    inputRef.current?.click();
  }

  function closeCropModal() {
    setPendingCrop(null);
  }

  function handleCropConfirm(croppedFile: File) {
    closeCropModal();
    onSelect(croppedFile);
  }

  function handleRemove() {
    if (original) {
      URL.revokeObjectURL(original.imageSrc);
      setOriginal(null);
    }
    onRemove();
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

        <button
          type="button"
          className="avatar-uploader-edit-overlay"
          onClick={handleEditClick}
          disabled={isBusy}
          aria-label={avatarUrl ? 'Cortar foto de perfil' : 'Editar foto de perfil'}
        >
          <Pencil size={20} />
        </button>
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
              onClick={handleRemove}
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
          imageSrc={pendingCrop.imageSrc}
          fileName={pendingCrop.fileName}
          mimeType={pendingCrop.mimeType}
          onCancel={closeCropModal}
          onConfirm={handleCropConfirm}
        />
      )}
    </section>
  );
}