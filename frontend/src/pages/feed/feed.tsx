import { useEffect, useMemo, useState } from "react";
import {
	Bookmark,
	Check,
	Clock3,
	Download,
	Heart,
	RefreshCw,
	Search,
	Share2,
	Sparkles,
	Users,
	Video,
} from "lucide-react";
import { ClipHistoryGroup, downloadClip, listClips } from "../../services/api";
import "./feed.css";

type FeedClip = {
	id: string;
	fileUrl: string;
	duration: string;
	playerNumber: number;
	generatedAt: string;
	index: number;
};

const filters = ["Todos os lances", "Goleiros", "Atacantes", "Sub-20", "Disponíveis para clube"];

function formatTime(value: string): string {
	const parts = value.split(":").map(Number);
	if (parts.length === 2 && parts.every(Number.isFinite)) return value;
	const seconds = Number(value);
	if (!Number.isFinite(seconds)) return "--:--";
	return `${String(Math.floor(seconds / 60)).padStart(2, "0")}:${String(Math.floor(seconds % 60)).padStart(2, "0")}`;
}

function relativeDate(value: string): string {
	const [datePart, timePart] = value.split(" - ");
	const [day, month, year] = datePart?.split("/").map(Number) ?? [];
	const [hour, minute] = timePart?.split(":").map(Number) ?? [];
	const timestamp = new Date(year, month - 1, day, hour, minute).getTime();
	if (!Number.isFinite(timestamp)) return "recentemente";
	const minutes = Math.max(1, Math.floor((Date.now() - timestamp) / 60000));
	if (minutes < 60) return `há ${minutes} min`;
	if (minutes < 1440) return `há ${Math.floor(minutes / 60)} h`;
	return `há ${Math.floor(minutes / 1440)} d`;
}

function flattenGroups(groups: ClipHistoryGroup[]): FeedClip[] {
	return groups.flatMap((group) => group.clips.map((clip, index) => ({
		id: clip.id,
		fileUrl: clip.file_url,
		duration: formatTime(clip.duration),
		playerNumber: group.target_number,
		generatedAt: group.generated_at,
		index,
	})));
}

function FeedCard({ clip }: { clip: FeedClip }) {
	const [isLiked, setIsLiked] = useState(false);
	const [isSaved, setIsSaved] = useState(false);
	const [isPlaying, setIsPlaying] = useState(false);

	async function handleDownload() {
		try {
			await downloadClip(clip.fileUrl, `jogador-${clip.playerNumber}-clipe-${clip.index + 1}`);
		} catch {
			window.alert("Não foi possível baixar o clipe. Tente novamente.");
		}
	}

	async function handleShare() {
		if (navigator.share) {
			await navigator.share({ title: `Clipe do jogador #${clip.playerNumber}`, url: window.location.href });
		} else {
			await navigator.clipboard?.writeText(window.location.href);
		}
	}

	return (
		<article className="feed-post">
			<div className="feed-post-header">
				<div className="player-avatar"><Users size={19} /></div>
				<div className="player-meta">
					<strong>Jogador #{clip.playerNumber}</strong>
					<span>Atleta em análise · {relativeDate(clip.generatedAt)}</span>
				</div>
				<button className="post-menu" aria-label="Mais opções" title="Mais opções">•••</button>
			</div>

			<div className="video-frame">
				<video
					src={`${import.meta.env.VITE_API_PATH}${clip.fileUrl}`}
					controls
					muted
					loop
					playsInline
					preload="metadata"
					onMouseEnter={(event) => { setIsPlaying(true); void event.currentTarget.play(); }}
					onMouseLeave={(event) => { setIsPlaying(false); event.currentTarget.pause(); }}
				/>
				{!isPlaying && <span className="video-duration"><Clock3 size={13} /> {clip.duration}</span>}
				<span className="ai-mark"><Sparkles size={13} /> IA</span>
			</div>

			<div className="feed-post-body">
				<div className="ai-tags"><span>Pico de velocidade</span><span>Ação analisada</span></div>
				<p className="post-caption">Lance destacado pela análise automática do SmartScout.</p>
				<div className="post-actions">
					<button className={isLiked ? "action-button active" : "action-button"} onClick={() => setIsLiked(!isLiked)} aria-label="Curtir clipe" title="Curtido">
						<Heart size={19} fill={isLiked ? "currentColor" : "none"} /> <span>{isLiked ? "Curtido" : "Curtir"}</span>
					</button>
					<button className={isSaved ? "action-button active" : "action-button"} onClick={() => setIsSaved(!isSaved)} aria-label="Salvar na shortlist" title="Salvar na shortlist">
						{isSaved ? <Check size={19} /> : <Bookmark size={19} />} <span>{isSaved ? "Salvo" : "Salvar"}</span>
					</button>
					<button className="icon-action" onClick={handleShare} aria-label="Compartilhar clipe" title="Compartilhar"><Share2 size={18} /></button>
					<button className="icon-action" onClick={handleDownload} aria-label="Baixar clipe" title="Baixar"><Download size={18} /></button>
				</div>
			</div>
		</article>
	);
}

export default function Feed() {
	const [groups, setGroups] = useState<ClipHistoryGroup[]>([]);
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState("");
	const [search, setSearch] = useState("");
	const [activeFilter, setActiveFilter] = useState(filters[0]);

	function loadFeed() {
		setLoading(true);
		setError("");
		listClips().then(setGroups).catch((err) => setError(err instanceof Error ? err.message : "Não foi possível carregar o feed.")).finally(() => setLoading(false));
	}

	useEffect(() => { loadFeed(); }, []);

	const clips = useMemo(() => {
		const query = search.trim().toLowerCase();
		return flattenGroups(groups).filter((clip) => !query || `jogador ${clip.playerNumber}`.includes(query) || clip.id.toLowerCase().includes(query));
	}, [groups, search]);

	return (
		<div className="feed-page">
			<div className="feed-shell">
				<header className="feed-hero">
					<div>
						<p className="eyebrow"><Sparkles size={14} /> SCOUT VIEW</p>
						<h1>Descubra o próximo destaque.</h1>
						<p className="feed-subtitle">Lances selecionados pela IA para acelerar suas decisões.</p>
					</div>
					<div className="feed-stat"><Video size={17} /><strong>{clips.length}</strong><span>lances no feed</span></div>
				</header>

				<div className="feed-toolbar">
					<div className="filter-scroll" role="group" aria-label="Filtros do feed">
						{filters.map((filter) => <button key={filter} className={activeFilter === filter ? "filter-pill selected" : "filter-pill"} onClick={() => setActiveFilter(filter)}>{filter}</button>)}
					</div>
					<label className="feed-search"><Search size={17} /><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Buscar jogador ou clipe" aria-label="Buscar jogador ou clipe" /></label>
				</div>

				{loading && <div className="feed-state"><RefreshCw className="spin" size={24} /><p>Preparando os melhores lances...</p></div>}
				{!loading && error && <div className="feed-state"><p>{error}</p><button className="retry-button" onClick={loadFeed}><RefreshCw size={16} /> Tentar novamente</button></div>}
				{!loading && !error && clips.length === 0 && <div className="feed-state"><Video size={30} /><p>Nenhum lance encontrado ainda.</p><span>Gere um clipe para começar a sua vitrine.</span></div>}
				{!loading && !error && clips.length > 0 && <div className="feed-grid">{clips.map((clip) => <FeedCard key={clip.id} clip={clip} />)}</div>}
				{activeFilter !== filters[0] && <p className="filter-note">O filtro “{activeFilter}” ficará mais preciso quando posição e disponibilidade forem adicionadas ao perfil do jogador.</p>}
			</div>
		</div>
	);
}
