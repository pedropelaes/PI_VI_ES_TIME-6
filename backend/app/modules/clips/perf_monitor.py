"""Monitor de desempenho do worker durante a geração dos clipes.

Mede apenas o processo do worker (e seus filhos, ex.: ffmpeg) e a GPU.

Uso:
    with PerformanceMonitor("tracking", job_id, video_path, output_dir):
        pipeline.process(...)
"""
import json
import threading
import time
from datetime import datetime
from pathlib import Path

import psutil


class PerformanceMonitor:
    def __init__(self, phase: str, job_id, video_path: str, output_dir: str, interval: float = 1.0):
        self.phase = phase
        self.job_id = str(job_id)
        self.video_path = str(video_path)
        self.output_dir = Path(output_dir)
        self.interval = interval
        self.samples: list[dict] = []
        self._stop = threading.Event()
        self._thread = None
        self._process = psutil.Process()
        self._procs: dict[int, psutil.Process] = {}
        self._nvml = None
        self._gpu = None
        self._t0 = 0.0
        self._started_at = None

    # ---------- GPU ----------
    def _init_gpu(self):
        try:
            import pynvml
            pynvml.nvmlInit()
            self._nvml = pynvml
            self._gpu = pynvml.nvmlDeviceGetHandleByIndex(0)
        except Exception as e:
            print(f"[PERF] GPU indisponível para monitoramento: {e}")

    def _gpu_name(self):
        if not self._gpu:
            return None
        try:
            name = self._nvml.nvmlDeviceGetName(self._gpu)
            return name.decode() if isinstance(name, bytes) else name
        except Exception:
            return None

    # ---------- Processos (worker + filhos) ----------
    def _proc_tree(self):
        try:
            current = [self._process] + self._process.children(recursive=True)
        except psutil.Error:
            current = [self._process]
        for p in current:
            if p.pid not in self._procs:
                self._procs[p.pid] = p
                try:
                    p.cpu_percent(None)  # primeira leitura sempre retorna 0
                except psutil.Error:
                    pass
        return [self._procs[p.pid] for p in current]

    # ---------- Coleta ----------
    def _sample(self) -> dict:
        cpu, ram = 0.0, 0
        for p in self._proc_tree():
            try:
                cpu += p.cpu_percent(None)
                ram += p.memory_info().rss
            except psutil.Error:
                pass

        s = {
            "t": round(time.perf_counter() - self._t0, 1),
            # % do total de núcleos (100% = todos os núcleos ocupados)
            "cpu_pct": cpu / (psutil.cpu_count() or 1),
            "ram_mb": ram / 2**20,
        }

        if self._gpu:
            n, h = self._nvml, self._gpu
            readers = {
                "gpu_util": lambda: n.nvmlDeviceGetUtilizationRates(h).gpu,
                "vram_mb": lambda: n.nvmlDeviceGetMemoryInfo(h).used / 2**20,
                "gpu_temp_c": lambda: n.nvmlDeviceGetTemperature(h, n.NVML_TEMPERATURE_GPU),
                "gpu_power_w": lambda: n.nvmlDeviceGetPowerUsage(h) / 1000,
            }
            for key, read in readers.items():
                try:
                    s[key] = float(read())
                except Exception:
                    pass  # no WSL2, temperatura/energia podem não estar disponíveis
        return s

    def _run(self):
        while not self._stop.wait(self.interval):
            self.samples.append(self._sample())

    # ---------- Resumo ----------
    def _video_info(self) -> dict:
        try:
            import cv2
            cap = cv2.VideoCapture(self.video_path)
            if not cap.isOpened():
                return {}
            frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
            if frames <= 0:
                frames = 0
            fps = cap.get(cv2.CAP_PROP_FPS) or 0
            w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            cap.release()
            return {
                "frames": frames,
                "fps": round(fps, 2),
                "duracao_s": round(frames / fps, 1) if fps > 0 and frames > 0 else None,
                "resolucao": f"{w}x{h}",
            }
        except Exception:
            return {}

    def _stats(self, key):
        vals = [s[key] for s in self.samples if key in s]
        if not vals:
            return None
        return {"media": round(sum(vals) / len(vals), 1), "max": round(max(vals), 1)}

    def _summary(self, elapsed: float, error: bool) -> dict:
        video = self._video_info()
        dur, frames = video.get("duracao_s"), video.get("frames")
        return {
            "job_id": self.job_id,
            "fase": self.phase,
            "inicio": self._started_at,
            "status": "erro" if error else "ok",
            "tempo_total_s": round(elapsed, 1),
            "fator_tempo_real": round(dur / elapsed, 2) if dur and elapsed else None,
            "fps_processamento": round(frames / elapsed, 1) if frames and elapsed else None,
            "hardware": {
                "cpu_nucleos": psutil.cpu_count(),
                "gpu": self._gpu_name(),
            },
            "video": video,
            "cpu_worker_pct": self._stats("cpu_pct"),
            "ram_worker_mb": self._stats("ram_mb"),
            "gpu_util_pct": self._stats("gpu_util"),
            "vram_mb": self._stats("vram_mb"),
            "gpu_temp_c": self._stats("gpu_temp_c"),
            "gpu_power_w": self._stats("gpu_power_w"),
            "amostras": len(self.samples),
            "serie": self.samples,  # série temporal para gráficos
        }

    def _print_summary(self, r: dict):
        def fmt(stat, unit=""):
            return f"média {stat['media']}{unit} | pico {stat['max']}{unit}" if stat else "n/d"

        print(f"[PERF] ===== {r['fase'].upper()} | job {r['job_id']} | {r['status']} =====")
        fator = f"{r['fator_tempo_real']}x" if r["fator_tempo_real"] else "n/d"
        fps = r["fps_processamento"] or "n/d"
        print(f"[PERF] Tempo: {r['tempo_total_s']}s | Fator tempo real: {fator} | FPS: {fps}")
        print(f"[PERF] CPU worker: {fmt(r['cpu_worker_pct'], '%')}")
        print(f"[PERF] RAM worker: {fmt(r['ram_worker_mb'], ' MB')}")
        print(f"[PERF] GPU ({r['hardware']['gpu']}): {fmt(r['gpu_util_pct'], '%')}")
        print(f"[PERF] VRAM: {fmt(r['vram_mb'], ' MB')}")
        print(f"[PERF] Temp GPU: {fmt(r['gpu_temp_c'], '°C')} | Energia: {fmt(r['gpu_power_w'], ' W')}")

    # ---------- Context manager ----------
    def __enter__(self):
        self._init_gpu()
        self._started_at = datetime.now().isoformat(timespec="seconds")
        self._t0 = time.perf_counter()
        self._proc_tree()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, exc_type, exc, tb):
        elapsed = time.perf_counter() - self._t0
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=5)
        try:
            result = self._summary(elapsed, error=exc_type is not None)
            self._print_summary(result)
            logs_dir = self.output_dir / "logs"
            logs_dir.mkdir(parents=True, exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            out = logs_dir / f"perf_{self.phase}_{ts}.json"
            out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"[PERF] Relatório salvo em {out}")
        except Exception as e:
            print(f"[PERF] Falha ao gerar relatório (ignorado): {e}")
        finally:
            if self._nvml:
                try:
                    self._nvml.nvmlShutdown()
                except Exception:
                    pass
        return False  # não engole a exceção do processamento