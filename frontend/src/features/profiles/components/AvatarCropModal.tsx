import { useCallback, useState } from 'react';
import Cropper from 'react-easy-crop';
import type { Area, Point } from 'react-easy-crop';
import { cropImageToFile } from '../cropImage';
import './AvatarCropModal.css';

interface Props {
  imageSrc: string;
  fileName: string;
  mimeType: string;
  onCancel: () => void;
  onConfirm: (file: File) => void;
}

/**
 * Modal de corte exibido depois de escolher a imagem: o usuario arrasta e
 * aplica zoom ate posicionar o recorte circular como quiser, e so entao o
 * arquivo recortado segue para upload.
 */
export function AvatarCropModal({ imageSrc, fileName, mimeType, onCancel, onConfirm }: Props) {
  const [crop, setCrop] = useState<Point>({ x: 0, y: 0 });
  const [zoom, setZoom] = useState(1);
  const [croppedAreaPixels, setCroppedAreaPixels] = useState<Area | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Referencia estavel: sem useCallback, o Cropper recebe uma funcao nova a
  // cada render e reexecuta o efeito que reporta a area recortada.
  const handleCropComplete = useCallback((_area: Area, areaPixels: Area) => {
    setCroppedAreaPixels(areaPixels);
  }, []);

  async function handleConfirm() {
    if (!croppedAreaPixels) {
      return;
    }

    setIsProcessing(true);
    setErrorMessage(null);

    try {
      const file = await cropImageToFile(imageSrc, croppedAreaPixels, fileName, mimeType);
      onConfirm(file);
    } catch {
      setErrorMessage('Não foi possível recortar a imagem. Tente novamente.');
      setIsProcessing(false);
    }
  }

  return (
    <div className="avatar-crop-overlay" role="dialog" aria-modal="true" aria-label="Ajustar foto de perfil">
      <div className="avatar-crop-dialog">
        <h2 className="avatar-crop-title">Ajustar foto de perfil</h2>

        <div className="avatar-crop-stage">
          <Cropper
            image={imageSrc}
            crop={crop}
            zoom={zoom}
            aspect={1}
            cropShape="round"
            showGrid={false}
            onCropChange={setCrop}
            onZoomChange={setZoom}
            onCropComplete={handleCropComplete}
          />
        </div>

        <label className="avatar-crop-zoom-label" htmlFor="avatar-crop-zoom">
          Zoom
          <input
            id="avatar-crop-zoom"
            type="range"
            min={1}
            max={3}
            step={0.01}
            value={zoom}
            onChange={(event) => setZoom(Number(event.target.value))}
          />
        </label>

        {errorMessage && (
          <p className="form-status form-status-error" role="alert">
            {errorMessage}
          </p>
        )}

        <div className="avatar-crop-actions">
          <button
            type="button"
            className="btn-secondary"
            onClick={onCancel}
            disabled={isProcessing}
          >
            Cancelar
          </button>
          <button
            type="button"
            className="btn-primary"
            onClick={handleConfirm}
            disabled={isProcessing || !croppedAreaPixels}
          >
            {isProcessing ? 'Aplicando...' : 'Aplicar recorte'}
          </button>
        </div>
      </div>
    </div>
  );
}
