"""
Testes de integracao do `AthleteProfileRepository`.

Cobrem contra banco real (via fixture `session`) porque a Task 8 vai substituir esta
implementacao por uma fake em dicionario nos testes de servico -- aqui e onde a query real
(joins, enums nativos, contagem) precisa provar que funciona.
"""
import uuid

from sqlmodel import Session

from app.core.security import hash_password
from app.modules.clips.models import Clip, ProcessingJob, Video
from app.modules.identity.models import User, UserRole
from app.modules.profiles.models import (
    AthleteProfile,
    AthleteStatus,
    DominantFoot,
    Position,
)
from app.modules.profiles.repository import (
    AthleteProfileRecord,
    SqlAthleteProfileRepository,
)


def _cria_perfil(session: Session, user: User, **overrides) -> AthleteProfile:
    dados = dict(
        user_id=user.id,
        position=Position.ATACANTE,
        state="SP",
        city="Sao Paulo",
    )
    dados.update(overrides)
    perfil = AthleteProfile(**dados)
    session.add(perfil)
    session.commit()
    session.refresh(perfil)
    return perfil


def _cria_video_job_clip(session: Session, user: User) -> Clip:
    video = Video(
        user_id=user.id,
        original_filename="video.mp4",
        storage_path=f"/uploads/{uuid.uuid4()}.mp4",
    )
    session.add(video)
    session.commit()
    session.refresh(video)

    job = ProcessingJob(video_id=video.id, target_number=10, status="DONE")
    session.add(job)
    session.commit()
    session.refresh(job)

    clip = Clip(
        job_id=job.id,
        storage_path=f"/uploads/{uuid.uuid4()}.mp4",
        start_timestamp=0.0,
        end_timestamp=1.0,
    )
    session.add(clip)
    session.commit()
    session.refresh(clip)
    return clip


def test_get_by_user_id_retorna_registro_populado_para_atleta_com_perfil(
    session: Session, usuario: User
):
    _cria_perfil(
        session,
        usuario,
        position=Position.MEIA,
        height_cm=180,
        dominant_foot=DominantFoot.DESTRO,
        state="RJ",
        city="Niteroi",
        current_club="Time X",
        bio="Bio qualquer",
        avatar_path="/avatars/x.png",
        status=AthleteStatus.DISPONIVEL,
    )

    repo = SqlAthleteProfileRepository(session)
    registro = repo.get_by_user_id(usuario.id)

    assert registro is not None
    assert isinstance(registro, AthleteProfileRecord)
    assert registro.user_id == usuario.id
    assert registro.first_name == usuario.first_name
    assert registro.last_name == usuario.last_name
    assert registro.position == Position.MEIA
    assert registro.height_cm == 180
    assert registro.dominant_foot == DominantFoot.DESTRO
    assert registro.state == "RJ"
    assert registro.city == "Niteroi"
    assert registro.current_club == "Time X"
    assert registro.bio == "Bio qualquer"
    assert registro.avatar_path == "/avatars/x.png"
    assert registro.status == AthleteStatus.DISPONIVEL


def test_get_by_user_id_retorna_none_para_id_inexistente(session: Session):
    repo = SqlAthleteProfileRepository(session)
    assert repo.get_by_user_id(uuid.uuid4()) is None


def test_get_by_user_id_retorna_none_para_usuario_que_nao_e_atleta(session: Session):
    scout = User(
        email="scout@teste.com",
        password_hash=hash_password("senha12345"),
        first_name="Ola",
        last_name="Scout",
        role=UserRole.SCOUT,
    )
    session.add(scout)
    session.commit()
    session.refresh(scout)

    repo = SqlAthleteProfileRepository(session)
    assert repo.get_by_user_id(scout.id) is None


def test_count_clips_retorna_zero_para_atleta_sem_clipes(
    session: Session, usuario: User
):
    _cria_perfil(session, usuario)

    repo = SqlAthleteProfileRepository(session)
    assert repo.count_clips(usuario.id) == 0


def test_count_clips_conta_apenas_clipes_do_atleta_correto(
    session: Session, usuario: User
):
    outro = User(
        email="outro@teste.com",
        password_hash=hash_password("senha12345"),
        first_name="Outro",
        last_name="Atleta",
    )
    session.add(outro)
    session.commit()
    session.refresh(outro)

    _cria_perfil(session, usuario)
    _cria_perfil(session, outro)

    _cria_video_job_clip(session, usuario)
    _cria_video_job_clip(session, usuario)
    _cria_video_job_clip(session, outro)

    repo = SqlAthleteProfileRepository(session)
    assert repo.count_clips(usuario.id) == 2
    assert repo.count_clips(outro.id) == 1


def test_update_aplica_apenas_os_campos_passados_e_mantem_o_resto(
    session: Session, usuario: User
):
    _cria_perfil(
        session,
        usuario,
        position=Position.ZAGUEIRO,
        city="Cidade Original",
        current_club="Clube Original",
    )

    repo = SqlAthleteProfileRepository(session)
    registro = repo.update(usuario.id, {"city": "Cidade Nova"})

    assert registro is not None
    assert registro.city == "Cidade Nova"
    assert registro.position == Position.ZAGUEIRO
    assert registro.current_club == "Clube Original"


def test_update_retorna_none_para_perfil_inexistente(session: Session):
    repo = SqlAthleteProfileRepository(session)
    assert repo.update(uuid.uuid4(), {"city": "X"}) is None


def test_update_avanca_updated_at(session: Session, usuario: User):
    """`onupdate` do SQLAlchemy dispara no flush, entao nao depende do commit do chamador."""
    perfil = _cria_perfil(session, usuario)
    created_at_original = perfil.created_at
    updated_at_original = perfil.updated_at

    repo = SqlAthleteProfileRepository(session)
    registro = repo.update(usuario.id, {"city": "Nova Cidade"})

    assert registro is not None
    perfil_atualizado = session.get(AthleteProfile, usuario.id)
    assert perfil_atualizado.updated_at > updated_at_original
    assert perfil_atualizado.updated_at > created_at_original


def test_update_persiste_apenas_apos_commit_do_chamador(engine, session: Session, usuario: User):
    """
    `update()` nao commita mais (o chamador e dono da transacao). Sem este teste, "ninguem
    commitar" passaria despercebido: a mudanca aparenta aplicada na Session do proprio teste
    (flush + refresh bastam para isso), mas nunca chegaria ao banco para outra conexao ver.

    Le de volta por uma Session **separada** para provar que o dado passou pelo commit, e nao
    apenas pelo identity map da Session que fez o update.
    """
    _cria_perfil(session, usuario, city="Cidade Original")

    repo = SqlAthleteProfileRepository(session)
    repo.update(usuario.id, {"city": "Cidade Persistida"})
    session.commit()  # o chamador decide fechar a transacao -- update() em si nao commita

    with Session(engine) as outra_sessao:
        perfil_de_outra_sessao = outra_sessao.get(AthleteProfile, usuario.id)
        assert perfil_de_outra_sessao is not None
        assert perfil_de_outra_sessao.city == "Cidade Persistida"
