import { useState } from "react";
import { AlertCircle, Download, EyeOff, Send, Trash2 } from "lucide-react";
import './ClipCard.css';
import { downloadClip, deleteClip, publishClip, unpublishClip } from "../../services/api";

export type ClipStatus = 'generating' | 'completed' | 'error' | 'expired';

export interface ClipData {
    id: string;
    title: string;
    status: ClipStatus;
    progress?: number;
    thumbnailUrl?: string;
    duration?: string;
    videoUrl?: string;
    published?: boolean;
}

interface ClipCardProps {
    clip: ClipData;
    onDeleted?: (clipId: string) => void;
    onPublishChanged?: (clipId: string, published: boolean) => void;
}

export function ClipCard({ clip, onDeleted, onPublishChanged }: ClipCardProps) {
    const [publishing, setPublishing] = useState(false);

    async function handleDownload() {
        if (!clip.videoUrl) return;
        try {
            await downloadClip(clip.videoUrl, clip.title);
        } catch (err) {
            console.error("Erro ao baixar clipe:", err);
            alert("Não foi possível baixar o clipe. Tente novamente.");
        }
    }

    async function handleDelete() {
        if (!window.confirm(`Apagar o clipe "${clip.title}"? Essa ação não pode ser desfeita.`)) return;
        try {
            await deleteClip(clip.id);
            onDeleted?.(clip.id);
        } catch (err) {
            console.error("Erro ao apagar clipe:", err);
            alert("Não foi possível apagar o clipe. Tente novamente.");
        }
    }

    async function handleTogglePublish() {
        if (publishing) return;
        setPublishing(true);
        try {
            if (clip.published) {
                await unpublishClip(clip.id);
                onPublishChanged?.(clip.id, false);
            } else {
                await publishClip(clip.id);
                onPublishChanged?.(clip.id, true);
            }
        } catch (err) {
            console.error("Erro ao alterar publicação do clipe:", err);
            alert(err instanceof Error ? err.message : "Não foi possível alterar a publicação do clipe.");
        } finally {
            setPublishing(false);
        }
    }

    // EARLY RETURN: Renderiza o Skeleton se estiver processando
    if (clip.status === 'generating') {
        return (
            <div className="clip-card">
                {/* Parte superior (Mídia) com gradiente claro */}
                <div className="clip-card-media skeleton-shimmer-light"></div>

                {/* Parte inferior (Info) com gradiente escuro */}
                <div className="clip-card-info skeleton-shimmer-dark">
                    <div className="skeleton-text-line"></div>
                </div>
            </div>
        );
    }

    // Renderização normal para Concluído, Erro ou Expirado
    return (
        <div className="clip-card">

            <div className={`clip-card-media ${clip.status}`}>
                {clip.status === 'error' && (
                    <div className="media-overlay error">
                        <AlertCircle size={32} color="#EF4444" />
                        <span>Falha ao separar clipe</span>
                    </div>
                )}

                {clip.status === 'expired' && (
                    <div className="media-overlay expired">
                        <AlertCircle size={32} color="#9ca3af" />
                        <span style={{ marginTop: '8px' }}>Clipe expirado</span>
                    </div>
                )}

                {clip.status === 'completed' && clip.videoUrl && (
                    <video
                        className="clip-video"
                        src={`${import.meta.env.VITE_API_PATH}${clip.videoUrl}`}
                        controls
                        preload="auto"
                    />
                )}
            </div>

            {(clip.status === 'completed' || clip.status === 'expired') && (
                <div className="clip-card-info">
                    <h3 className="clip-title">{clip.title}</h3>
                    <div className="clip-actions">
                        {clip.status === 'completed' && (
                            <>
                                <button
                                    className="publish-button"
                                    onClick={handleTogglePublish}
                                    disabled={publishing}
                                    title={clip.published ? "Remover do feed" : "Publicar no feed"}
                                    aria-label={clip.published ? `Remover ${clip.title} do feed` : `Publicar ${clip.title} no feed`}
                                >
                                    {clip.published ? <EyeOff size={18} /> : <Send size={18} />}
                                    <span>{clip.published ? "Remover do feed" : "Publicar no feed"}</span>
                                </button>
                                <button
                                    className="download-button"
                                    onClick={handleDownload}
                                    disabled={!clip.videoUrl}
                                    title={clip.videoUrl ? "Baixar clipe" : "URL do clipe não disponível"}
                                    aria-label={`Baixar ${clip.title}`}
                                >
                                    <Download size={18} />
                                </button>
                                <button
                                    className="delete-button"
                                    onClick={handleDelete}
                                    title="Apagar clipe"
                                    aria-label={`Apagar ${clip.title}`}
                                >
                                    <Trash2 size={18} />
                                </button>
                            </>
                        )}
                    </div>
                </div>
            )}

        </div>
    );
}