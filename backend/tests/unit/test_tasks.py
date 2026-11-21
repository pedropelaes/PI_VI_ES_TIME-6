"""Testes da configuração do Celery e registro das tasks de ML."""


def test_celery_app_broker_is_redis():
    from app.celery_app import celery_app

    assert celery_app.conf.broker_url.startswith("redis://")
    # Sem result backend: resultado vai pro DB, não pro Celery.
    assert celery_app.conf.result_backend in (None, "")
    assert celery_app.conf.task_ignore_result is True
    assert celery_app.conf.worker_max_tasks_per_child == 1
    assert celery_app.conf.worker_prefetch_multiplier == 1
    assert celery_app.conf.task_acks_late is True
    assert celery_app.conf.task_reject_on_worker_lost is True


def test_ml_tasks_are_registered():
    # Importar o app registra o módulo de tasks via `include`.
    from app.celery_app import celery_app
    import app.modules.clips.tasks  # noqa: F401

    registered = set(celery_app.tasks.keys())
    assert "app.modules.clips.tasks.download_and_process_drive_video" in registered
    assert "app.modules.clips.tasks.run_fast_scan" in registered
    assert "app.modules.clips.tasks.run_deep_scan" in registered
    assert "app.modules.clips.tasks.run_full_tracking" in registered


def test_importing_tasks_does_not_import_torch():
    """A API importa este módulo; ele não pode puxar torch no topo (import lazy)."""
    import sys

    sys.modules.pop("torch", None)
    import importlib
    import app.modules.clips.tasks as tasks_mod
    importlib.reload(tasks_mod)

    assert "torch" not in sys.modules


def test_worker_entrypoint_resolves_all_mappers():
    """O worker é um entrypoint separado da API e precisa registrar TODOS os models.

    `Video.user` referencia "User" por string e o SQLAlchemy só resolve nomes de
    classes que foram efetivamente importadas. A API importa User via router de
    identity; o worker, não. Sem isso, toda task que toca o banco falha com
    "expression 'User' failed to locate a name".

    Roda em subprocesso porque o conftest já importa `app.main` (que registra
    tudo), o que mascararia o problema se o teste fosse in-process.
    """
    import subprocess
    import sys
    from pathlib import Path

    backend_dir = Path(__file__).resolve().parents[2]
    code = (
        "import app.celery_app, app.modules.clips.tasks; "
        "from sqlalchemy.orm import configure_mappers; "
        "configure_mappers()"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=str(backend_dir),
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr[-800:]


def test_ensure_h264_triggers_on_converting_callback(tmp_path):
    from unittest.mock import patch
    from app.modules.clips.video_utils import ensure_h264

    src = tmp_path / "sample.webm"
    src.write_bytes(b"av1-bytes")
    converted = tmp_path / "sample_h264.mp4"
    events = []

    def fake_run(cmd, check=False):
        converted.write_bytes(b"h264-bytes")

    with patch("app.modules.clips.video_utils.get_video_codec", return_value="av1"):
        with patch("app.modules.clips.video_utils.subprocess.run", side_effect=fake_run):
            out = ensure_h264(src, on_converting=lambda: events.append("CONVERTING"))

    assert events == ["CONVERTING"]
    assert out == converted
    assert not src.exists()
    assert converted.exists()


def test_ensure_h264_skips_callback_when_already_h264(tmp_path):
    from unittest.mock import patch
    from app.modules.clips.video_utils import ensure_h264

    src = tmp_path / "sample.mp4"
    src.write_bytes(b"h264-bytes")
    events = []

    with patch("app.modules.clips.video_utils.get_video_codec", return_value="h264"):
        out = ensure_h264(src, on_converting=lambda: events.append("CONVERTING"))

    assert events == []
    assert out == src
