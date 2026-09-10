import type { Area } from 'react-easy-crop';

/**
 * Carrega a imagem fora da tela para poder desenha-la no canvas de corte.
 */
function loadImage(src: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const image = new Image();
    image.addEventListener('load', () => resolve(image));
    image.addEventListener('error', reject);
    image.src = src;
  });
}

/**
 * Recorta `imageSrc` na area `crop` (em pixels da imagem original, como
 * devolvida pelo react-easy-crop) e devolve um File pronto para upload, com
 * o mesmo nome/tipo do arquivo escolhido pelo usuario.
 */
export async function cropImageToFile(
  imageSrc: string,
  crop: Area,
  fileName: string,
  mimeType: string
): Promise<File> {
  const image = await loadImage(imageSrc);
  const canvas = document.createElement('canvas');
  canvas.width = crop.width;
  canvas.height = crop.height;

  const ctx = canvas.getContext('2d');
  if (!ctx) {
    throw new Error('Não foi possível preparar o recorte da imagem.');
  }

  ctx.drawImage(
    image,
    crop.x,
    crop.y,
    crop.width,
    crop.height,
    0,
    0,
    crop.width,
    crop.height
  );

  const blob = await new Promise<Blob | null>((resolve) => {
    canvas.toBlob(resolve, mimeType);
  });

  if (!blob) {
    throw new Error('Não foi possível preparar o recorte da imagem.');
  }

  return new File([blob], fileName, { type: mimeType });
}
