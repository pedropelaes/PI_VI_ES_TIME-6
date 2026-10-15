import { ArrowRight, Image, VideoIcon, X } from "lucide-react";
import React, { SyntheticEvent, useRef, useState, useEffect, KeyboardEvent } from "react";
import { useNavigate } from "react-router-dom";
import "rc-slider/assets/index.css";
import './input.css';
import { createJob, createJobFromGoogleDrive, API_BASE } from "../../services/api";
import { useGoogleDrivePicker, GoogleDriveFile } from "../../features/clips/hooks/useGoogleDrivePicker";
import Slider from "rc-slider";

function GoogleDriveIcon({ size = 20 }: { size?: number }) {
    return (
        <svg width={size} height={size} viewBox="0 0 87.3 78" xmlns="http://www.w3.org/2000/svg">
            <path d="m6.6 66.85 3.85 6.65c.8 1.4 1.95 2.5 3.3 3.3l13.75-23.8H0c0 1.55.4 3.1 1.2 4.5z" fill="#0066da"/>
            <path d="M43.65 25 29.9 1.2c-1.35.8-2.5 1.9-3.3 3.3l-25.4 44C.4 49.9 0 51.45 0 53h27.5z" fill="#00ac47"/>
            <path d="M73.55 76.8c1.35-.8 2.5-1.9 3.3-3.3l1.6-2.75 7.65-13.25c.8-1.4 1.2-2.95 1.2-4.5H59.8l5.85 13.8z" fill="#ea4335"/>
            <path d="M43.65 25 57.4 1.2C56.05.4 54.5 0 52.9 0H34.4c-1.6 0-3.15.45-4.5 1.2z" fill="#00832d"/>
            <path d="M59.8 53H27.5L13.75 76.8c1.35.8 2.9 1.2 4.5 1.2h50.8c1.6 0 3.15-.45 4.5-1.2z" fill="#2684fc"/>
            <path d="m73.4 26.5-12.7-22c-.8-1.4-1.95-2.5-3.3-3.3L43.65 25l16.15 28h27.45c0-1.55-.4-3.1-1.2-4.5z" fill="#ffba00"/>
        </svg>
    );
}

const formatSecondsToMask = (seconds: number, hasHours: boolean): string => {
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = Math.floor(seconds % 60);
    if (hasHours) return `${h.toString().padStart(2, "0")}:${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
    return `${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
};

const parseMaskToSeconds = (timeStr: string): number | null => {
    const parts = timeStr.split(":").map(p => parseInt(p, 10));
    if (parts.some(isNaN)) return null;
    if (parts.length === 3) return parts[0] * 3600 + parts[1] * 60 + parts[2];
    if (parts.length === 2) return parts[0] * 60 + parts[1];
    if (parts.length === 1) return parts[0];
    return null;
};

const applyTimeMask = (value: string, hasHours: boolean): string => {
    let raw = value.replace(/\D/g, "");
    const maxLength = hasHours ? 6 : 4;
    raw = raw.substring(0, maxLength);
    if (raw.length > 4) return `${raw.slice(0, 2)}:${raw.slice(2, 4)}:${raw.slice(4)}`;
    if (raw.length > 2) return `${raw.slice(0, 2)}:${raw.slice(2)}`;
    return raw;
};

export default function InputPage() {
    const navigate = useNavigate();
    const fileInputRef  = useRef<HTMLInputElement>(null);
    const videoInputRef = useRef<HTMLInputElement>(null);
    const videoElementRef = useRef<HTMLVideoElement>(null);

    const { openPicker, error: pickerHookError } = useGoogleDrivePicker();

    const [refNumber, setRefNumber] = useState<number | string>("");
    const [imageFile, setImageFile]   = useState<File | null>(null);
    const [imagePreview, setImagePreview] = useState<string>("");
    const [videoFile, setVideoFile]   = useState<File | null>(null);
    const [videoPreview, setVideoPreview] = useState<string>("");
    const [videoError, setVideoError] = useState<boolean>(false);
    const [driveFile, setDriveFile]   = useState<GoogleDriveFile | null>(null);
    const [drivePickerLoading, setDrivePickerLoading] = useState(false);
    const [isDragging, setIsDragging] = useState<boolean>(false);
    const [videoDuration, setVideoDuration] = useState<number>(0);
    const [timeRange, setTimeRange] = useState<[number, number]>([0, 0]);
    const [startInputStr, setStartInputStr] = useState<string>("0:00");
    const [endInputStr, setEndInputStr]     = useState<string>("0:00");
    const [loading, setLoading] = useState(false);
    const [error, setError]     = useState("");

    const hasHours = videoDuration >= 3600;

    useEffect(() => {
        if (pickerHookError) {
            setError(pickerHookError);
        }
    }, [pickerHookError]);

    useEffect(() => {
        if (!imageFile) { setImagePreview(""); return; }
        const url = URL.createObjectURL(imageFile);
        setImagePreview(url);
        return () => URL.revokeObjectURL(url);
    }, [imageFile]);

    useEffect(() => {
        if (videoFile) {
            const url = URL.createObjectURL(videoFile);
            setVideoPreview(url);
            setVideoError(false);
            return () => URL.revokeObjectURL(url);
        }
    }, [videoFile]);

    useEffect(() => {
        if (videoDuration > 0) {
            setStartInputStr(formatSecondsToMask(timeRange[0], hasHours));
            setEndInputStr(formatSecondsToMask(timeRange[1], hasHours));
        }
    }, [timeRange, videoDuration, hasHours]);

    const handleImageClick  = () => fileInputRef.current?.click();
    const handleImageChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (file) setImageFile(file);
    };
    const removeImage = (e: SyntheticEvent) => {
        e.stopPropagation();
        setImageFile(null);
        if (fileInputRef.current) fileInputRef.current.value = "";
    };

    const handleVideoClick  = () => videoInputRef.current?.click();
    const handleVideoChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (file) {
            setDriveFile(null);
            setVideoFile(file);
            setVideoError(false);
        }
    };

    const removeVideo = (e: SyntheticEvent) => {
        e.stopPropagation();
        setVideoFile(null);
        setDriveFile(null);
        setVideoPreview("");
        setVideoError(false);
        setVideoDuration(0);
        setTimeRange([0, 0]);
        setStartInputStr("0:00");
        setEndInputStr("0:00");
        if (videoInputRef.current) videoInputRef.current.value = "";
    };

    const handleGoogleDriveClick = async () => {
        setError("");
        setDrivePickerLoading(true);
        try {
            const selected = await openPicker();
            if (selected) {
                setDriveFile(selected);
                setVideoFile(null);
                setVideoError(false);

                // Configura streaming proxy com suporte a Range requests para o <video>
                const streamUrl = `${API_BASE}/jobs/drive-preview/${selected.id}?access_token=${encodeURIComponent(selected.token)}`;
                setVideoPreview(streamUrl);

                // Se a API do Drive já informou a duração nos metadados, inicializa antecipadamente
                if (selected.durationMillis && selected.durationMillis > 0) {
                    const durationSec = Math.floor(selected.durationMillis / 1000);
                    const videoHasH = durationSec >= 3600;
                    setVideoDuration(durationSec);
                    setTimeRange([0, durationSec]);
                    setStartInputStr(formatSecondsToMask(0, videoHasH));
                    setEndInputStr(formatSecondsToMask(durationSec, videoHasH));
                } else {
                    setVideoDuration(0);
                    setTimeRange([0, 0]);
                    setStartInputStr("0:00");
                    setEndInputStr("0:00");
                }
            }
        } catch (err: any) {
            setError(err.message || "Erro ao conectar ao Google Drive.");
        } finally {
            setDrivePickerLoading(false);
        }
    };

    const handleDragOver  = (e: React.DragEvent<HTMLDivElement>) => { e.preventDefault(); setIsDragging(true); };
    const handleDragLeave = (e: React.DragEvent<HTMLDivElement>) => { e.preventDefault(); setIsDragging(false); };
    const handleDrop      = (e: React.DragEvent<HTMLDivElement>) => {
        e.preventDefault();
        setIsDragging(false);
        const file = e.dataTransfer.files?.[0];
        if (file && file.type.startsWith("video/")) {
            setDriveFile(null);
            setVideoFile(file);
            setVideoError(false);
        }
    };

    const handleNumberChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const value = e.target.value;
        if (value === "") { setRefNumber(""); return; }
        const num = parseInt(value, 10);
        if (num >= 1 && num <= 999) setRefNumber(num);
    };

    const handleLoadedMetadata = () => {
        if (videoElementRef.current) {
            const duration = Math.floor(videoElementRef.current.duration);
            if (!isNaN(duration) && duration > 0) {
                const videoHasHours = duration >= 3600;
                setVideoDuration(duration);
                setTimeRange([0, duration]);
                setStartInputStr(formatSecondsToMask(0, videoHasHours));
                setEndInputStr(formatSecondsToMask(duration, videoHasHours));
            }
        }
    };

    const handleVideoError = () => {
        // Se falhar o decode nativo no <video> e for Drive, fallback para o player do Google
        if (driveFile) {
            setVideoError(true);
        }
    };

    const handleTimeInputChange = (e: React.ChangeEvent<HTMLInputElement>, type: 'start' | 'end') => {
        const maskedValue = applyTimeMask(e.target.value, hasHours);
        if (type === 'start') setStartInputStr(maskedValue);
        else setEndInputStr(maskedValue);
    };

    const validateAndUpdateTime = (type: 'start' | 'end') => {
        setError("");
        const inputStr = type === 'start' ? startInputStr : endInputStr;
        const currentSeconds = parseMaskToSeconds(inputStr);
        const resetInput = () => {
            if (type === 'start') setStartInputStr(formatSecondsToMask(timeRange[0], hasHours));
            else setEndInputStr(formatSecondsToMask(timeRange[1], hasHours));
        };
        if (currentSeconds === null) { setError("Formato de tempo inválido."); resetInput(); return; }
        const clampedSeconds = videoDuration > 0 ? Math.max(0, Math.min(currentSeconds, videoDuration)) : Math.max(0, currentSeconds);
        const [startTime, endTime] = timeRange;
        if (type === 'start') {
            if (videoDuration > 0 && clampedSeconds >= endTime) { setError("O tempo de início deve ser menor que o de fim."); resetInput(); }
            else setTimeRange([clampedSeconds, endTime]);
        } else {
            if (clampedSeconds <= startTime) { setError("O tempo de fim deve ser maior que o de início."); resetInput(); }
            else setTimeRange([startTime, clampedSeconds]);
        }
    };

    const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>, type: 'start' | 'end') => {
        if (e.key === 'Enter') { validateAndUpdateTime(type); e.currentTarget.blur(); }
    };

    const handleAnalyze = async () => {
        setError("");
        if (!videoFile && !driveFile) {
            setError("Selecione um vídeo antes de continuar.");
            return;
        }
        if (refNumber === "" || Number(refNumber) < 1) {
            setError("Informe o número de referência do jogador.");
            return;
        }

        setLoading(true);
        try {
            let jobId: string;
            const sTs = timeRange[0];
            const eTs = timeRange[1];

            if (driveFile) {
                const res = await createJobFromGoogleDrive({
                    fileId: driveFile.id,
                    googleAccessToken: driveFile.token,
                    targetNumber: Number(refNumber),
                    startTs: sTs,
                    endTs: eTs,
                });
                jobId = res.job_id;
            } else if (videoFile) {
                const res = await createJob(
                    videoFile, 
                    Number(refNumber), 
                    sTs, 
                    eTs
                );
                jobId = res.job_id;
            } else {
                return;
            }

            localStorage.setItem("job_start_ts", String(sTs));
            localStorage.setItem("job_end_ts", String(eTs));
            navigate(`/processing-clips/${jobId}`);
        } catch (err: any) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    const inputWidthStyle = { width: hasHours ? '90px' : '65px' };

    return (
        <div className="input-page">
            <div className="input-card">

                <input ref={fileInputRef}  id="image-upload" type="file" accept="image/*" style={{ display: "none" }} onChange={handleImageChange} />
                <input ref={videoInputRef} id="video-upload" type="file" accept="video/*" style={{ display: "none" }} onChange={handleVideoChange} />

                {videoPreview ? (
                    <div className="video-preview-wrapper">
                        <div style={{position: "relative"}}>
                            {driveFile && (
                                <div className="drive-preview-badge">
                                    <GoogleDriveIcon size={16} />
                                    <span className="drive-preview-title" title={driveFile.name}>{driveFile.name}</span>
                                </div>
                            )}

                            {videoError && driveFile ? (
                                <iframe
                                    src={`https://drive.google.com/file/d/${driveFile.id}/preview`}
                                    className="video-preview-element"
                                    style={{ border: "none", minHeight: "250px", width: "100%" }}
                                    allow="autoplay"
                                    title={driveFile.name}
                                />
                            ) : (
                                <video
                                    ref={videoElementRef}
                                    src={videoPreview}
                                    onLoadedMetadata={handleLoadedMetadata}
                                    onError={handleVideoError}
                                    controls
                                    className="video-preview-element"
                                />
                            )}

                            <button onClick={removeVideo} title="Remover vídeo" className="btn-remove-video">
                                <X size={16} strokeWidth={3} />
                            </button>
                        </div>

                        {videoDuration > 0 && (
                            <div className="trim-controls">
                                <p className="trim-title">Selecione apenas o trecho do vídeo que contém a partida</p>
                                <div className="trim-labels">
                                    <div style={{display: 'flex', alignItems: 'center', gap: '6px'}}>
                                        <span>Início:</span>
                                        <input
                                            type="text"
                                            className="time-input-editable"
                                            style={inputWidthStyle}
                                            value={startInputStr}
                                            onChange={(e) => handleTimeInputChange(e, 'start')}
                                            onBlur={() => validateAndUpdateTime('start')}
                                            onKeyDown={(e) => handleKeyDown(e, 'start')}
                                        />
                                    </div>
                                    <div style={{display: 'flex', alignItems: 'center', gap: '6px'}}>
                                        <span>Fim:</span>
                                        <input
                                            type="text"
                                            className="time-input-editable"
                                            style={inputWidthStyle}
                                            value={endInputStr}
                                            onChange={(e) => handleTimeInputChange(e, 'end')}
                                            onBlur={() => validateAndUpdateTime('end')}
                                            onKeyDown={(e) => handleKeyDown(e, 'end')}
                                        />
                                    </div>
                                </div>
                                <Slider
                                    range
                                    min={0}
                                    max={videoDuration}
                                    value={timeRange}
                                    onChange={(val) => setTimeRange(val as [number, number])}
                                    allowCross={false}
                                />
                                <p className="trim-hint">Arraste os tracinhos ou digite o tempo acima para cortar.</p>
                            </div>
                        )}
                    </div>
                ) : (
                    <>
                        <div
                            className={`upload-area ${isDragging ? "dragging" : ""}`}
                            onClick={handleVideoClick}
                            onDragOver={handleDragOver}
                            onDragLeave={handleDragLeave}
                            onDrop={handleDrop}
                        >
                            <VideoIcon size={80} color="rgba(255,255,255,0.25)" strokeWidth={0.75} />
                            <p className="upload-area-text">
                                <span>Clique para selecionar</span> ou arraste<br />o seu vídeo aqui
                            </p>
                        </div>

                        <div className="upload-divider">
                            <span>ou</span>
                        </div>

                        <button
                            type="button"
                            className="btn-google-drive"
                            onClick={handleGoogleDriveClick}
                            disabled={drivePickerLoading || loading}
                        >
                            <GoogleDriveIcon size={20} />
                            {drivePickerLoading ? "Conectando ao Google..." : "Importar do Google Drive"}
                        </button>
                    </>
                )}

                <div className="inputs-row">
                    <div className="input-group" style={{ flex: 1, textAlign: "left" }}>
                        <label className="input-label">Número de referência (0-999)</label>
                        <div className="input-wrapper">
                            <input
                                type="number"
                                className="input-base"
                                placeholder="Ex: 10"
                                min="1" max="999"
                                value={refNumber}
                                onChange={handleNumberChange}
                                onKeyDown={(e) => { if (["e","E","+","-","."].includes(e.key)) e.preventDefault(); }}
                            />
                        </div>
                    </div>

                    <div className="input-group" style={{ flex: 1, textAlign: "left" }}>
                        <label className="input-label">Imagem de referência (opcional)</label>
                        {imagePreview ? (
                            <div className="image-preview-wrapper preview-container">
                                <img src={imagePreview} alt="Preview tático" className="image-preview-img" />
                                <button onClick={removeImage} title="Remover imagem" className="btn-remove-preview">
                                    <X size={12} strokeWidth={3} />
                                </button>
                            </div>
                        ) : (
                            <div className="input-wrapper image-select-wrapper" onClick={handleImageClick}>
                                <span className="input-icon"><Image size={18} /></span>
                                <div className="input-base with-icon image-select-text">Selecionar imagem</div>
                            </div>
                        )}
                    </div>
                </div>

                {error && <p className="input-error">{error}</p>}

                <button
                    className="btn btn-primary btn-analyze"
                    onClick={handleAnalyze}
                    disabled={loading}
                >
                    {loading ? (driveFile ? "Importando do Google Drive..." : "Enviando vídeo...") : "Iniciar análise"}
                    {!loading && <ArrowRight size={20} className="btn-analyze-icon" />}
                </button>

                {loading && (
                    <div className="upload-progress-container">
                        <div className="upload-progress-fill" />
                    </div>
                )}

            </div>
        </div>
    );
}
