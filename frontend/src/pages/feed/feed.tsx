import { useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { Clock3, Download, Heart, RefreshCw, Search, Share2, Sparkles, Video } from "lucide-react";
import { downloadClip } from "../../services/api";
import { useFeed } from "../../features/feed/hooks/useFeed";
import { useToggleLike } from "../../features/feed/hooks/useToggleLike";
import type { FeedFilters, FeedItemView } from "../../features/feed/types";
import "./feed.css";

interface FilterPreset {
	id: string;
	label: string;
	filters: FeedFilters;
}

// "Sub-20" = até 19 anos completos.
const FILTERS: FilterPreset[] = [
	{ id: "todos", label: "Todos os lances", filters: {} },
	{ id: "goleiros", label: "Goleiros", filters: { position: "GOLEIRO" } },
	{ id: "zagueiros", label: "Zagueiros", filters: { position: "ZAGUEIRO" } },
	{ id: "laterais", label: "Laterais", filters: { position: "LATERAL" } },
	{ id: "volantes", label: "Volantes", filters: { position: "VOLANTE" } },
	{ id: "meias", label: "Meias", filters: { position: "MEIA" } },
	{ id: "atacantes", label: "Atacantes", filters: { position: "ATACANTE" } },
	{ id: "sub20", label: "Sub-20", filters: { maxAge: 19 } },
	{ id: "disponiveis", label: "Disponíveis para clube", filters: { status: "DISPONIVEL" } },
];

const SEARCH_DEBOUNCE_MS = 400;

/** Espera o usuário parar de digitar antes de buscar, pra não chamar a API a cada letra. */
function useDebounced<T>(value: T, delay: number): T {
	const [debounced, setDebounced] = useState(value);
	useEffect(() => {
		const id = setTimeout(() => setDebounced(value), delay);
		return () => clearTimeout(id);
	}, [value, delay]);
	return debounced;
}

function FeedCard({ clip }: { clip: FeedItemView }) {
	const [isPlaying, setIsPlaying] = useState(false);
	const toggleLike = useToggleLike();
	const { athlete } = clip;

	async function handleDownload() {
		try {
			const nome = athlete.fullName.toLowerCase().replace(/\s+/g, "-");
			await downloadClip(clip.fileUrl, `${nome}-${clip.id.slice(0, 8)}`);
		} catch {
			window.alert("Não foi possível baixar o clipe. Tente novamente.");
		}
	}

	async function handleShare() {
		const url = `${window.location.origin}${athlete.profilePath}`;
		try {
			if (navigator.share) {
				await navigator.share({ title: `${athlete.fullName} no SmartScout`, url });
			} else {
				await navigator.clipboard?.writeText(url);
			}
		} catch {
			// Usuário cancelou o compartilhamento: nada a fazer.
		}
	}

	return (
		<article className="feed-post">
			<div className="feed-post-header">
				<Link to={athlete.profilePath} className="player-avatar" aria-label={`Ver perfil de ${athlete.fullName}`}>
					{athlete.avatarUrl ? <img src={athlete.avatarUrl} alt="" /> : athlete.initial}
				</Link>
				<div className="player-meta">
					<Link to={athlete.profilePath} className="player-name">{athlete.fullName}</Link>
					<span>{athlete.details} · {clip.publishedLabel}</span>
				</div>
			</div>

			<div className="video-frame">
				<video
					src={clip.videoUrl}
					controls
					muted
					loop
					playsInline
					preload="metadata"
					onMouseEnter={(event) => { setIsPlaying(true); void event.currentTarget.play().catch(() => {}); }}
					onMouseLeave={(event) => { setIsPlaying(false); event.currentTarget.pause(); }}
				/>
				{!isPlaying && <span className="video-duration"><Clock3 size={13} /> {clip.durationLabel}</span>}
				<span className="ai-mark"><Sparkles size={13} /> IA</span>
			</div>

			<div className="feed-post-body">
				{athlete.isAvailable && <div className="ai-tags"><span>Disponível para clube</span></div>}
				<div className="post-actions">
					<button
						className={clip.likedByMe ? "action-button active" : "action-button"}
						onClick={() => toggleLike.mutate({ clipId: clip.id, like: !clip.likedByMe })}
						aria-pressed={clip.likedByMe}
						aria-label={clip.likedByMe ? "Descurtir clipe" : "Curtir clipe"}
					>
						<Heart size={19} fill={clip.likedByMe ? "currentColor" : "none"} />
						<span>{clip.likeCount}</span>
					</button>
					<button className="icon-action" onClick={handleShare} aria-label="Compartilhar perfil do atleta" title="Compartilhar"><Share2 size={18} /></button>
					<button className="icon-action" onClick={handleDownload} aria-label="Baixar clipe" title="Baixar"><Download size={18} /></button>
				</div>
			</div>
		</article>
	);
}

export default function Feed() {
	const [activeFilterId, setActiveFilterId] = useState(FILTERS[0].id);
	const [search, setSearch] = useState("");
	const debouncedSearch = useDebounced(search, SEARCH_DEBOUNCE_MS);

	const filters = useMemo<FeedFilters>(() => {
		const preset = FILTERS.find((f) => f.id === activeFilterId) ?? FILTERS[0];
		return { ...preset.filters, q: debouncedSearch.trim() || undefined };
	}, [activeFilterId, debouncedSearch]);

	const { items, isLoading, isError, error, hasNextPage, isFetchingNextPage, fetchNextPage, refetch } = useFeed(filters);
	const isFiltered = activeFilterId !== FILTERS[0].id || Boolean(filters.q);

	// Scroll infinito: quando o "sentinela" no fim da lista aparece na tela, busca a próxima página.
	const sentinelRef = useRef<HTMLDivElement | null>(null);
	useEffect(() => {
		const el = sentinelRef.current;
		if (!el || !hasNextPage || typeof IntersectionObserver === "undefined") return;
		const observer = new IntersectionObserver((entries) => {
			if (entries[0]?.isIntersecting && !isFetchingNextPage) fetchNextPage();
		}, { rootMargin: "400px" });
		observer.observe(el);
		return () => observer.disconnect();
	}, [hasNextPage, isFetchingNextPage, fetchNextPage]);

	return (
		<div className="feed-page">
			<div className="feed-shell">
				<header className="feed-hero">
					<div>
						<p className="eyebrow"><Sparkles size={14} /> SCOUT VIEW</p>
						<h1>Descubra o próximo destaque.</h1>
						<p className="feed-subtitle">Lances publicados pelos atletas, recortados pela IA do SmartScout.</p>
					</div>
					<div className="feed-stat"><Video size={17} /><strong>{items.length}{hasNextPage ? "+" : ""}</strong><span>lances no feed</span></div>
				</header>

				<div className="feed-toolbar">
					<div className="filter-scroll" role="group" aria-label="Filtros do feed">
						{FILTERS.map((filter) => (
							<button
								key={filter.id}
								className={activeFilterId === filter.id ? "filter-pill selected" : "filter-pill"}
								aria-pressed={activeFilterId === filter.id}
								onClick={() => setActiveFilterId(filter.id)}
							>
								{filter.label}
							</button>
						))}
					</div>
					<label className="feed-search">
						<Search size={17} />
						<input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Buscar atleta pelo nome" aria-label="Buscar atleta pelo nome" />
					</label>
				</div>

				{isLoading && <div className="feed-state"><RefreshCw className="spin" size={24} /><p>Preparando os melhores lances...</p></div>}

				{!isLoading && isError && (
					<div className="feed-state">
						<p>{error?.message ?? "Não foi possível carregar o feed."}</p>
						<button className="retry-button" onClick={refetch}><RefreshCw size={16} /> Tentar novamente</button>
					</div>
				)}

				{!isLoading && !isError && items.length === 0 && (
					<div className="feed-state">
						<Video size={30} />
						<p>{isFiltered ? "Nenhum lance encontrado com esse filtro." : "Nenhum lance publicado ainda."}</p>
						<span>{isFiltered ? "Tente outro filtro ou limpe a busca." : "Quando os atletas publicarem clipes, eles aparecem aqui."}</span>
					</div>
				)}

				{!isLoading && !isError && items.length > 0 && (
					<>
						<div className="feed-grid">{items.map((clip) => <FeedCard key={clip.id} clip={clip} />)}</div>
						<div ref={sentinelRef} className="feed-sentinel" />
						{hasNextPage && (
							<div className="feed-more">
								<button className="retry-button" onClick={fetchNextPage} disabled={isFetchingNextPage}>
									{isFetchingNextPage ? <><RefreshCw className="spin" size={16} /> Carregando...</> : "Carregar mais"}
								</button>
							</div>
						)}
					</>
				)}
			</div>
		</div>
	);
}