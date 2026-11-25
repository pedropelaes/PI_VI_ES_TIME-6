import logging
import os
import resend

logger = logging.getLogger(__name__)


def send_reset_email(to_email: str, token: str) -> None:
    api_key = (os.getenv("RESEND_API_KEY") or "").strip()
    from_email = os.getenv("RESEND_FROM_EMAIL", "onboarding@resend.dev")
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173").rstrip("/")
    reset_link = f"{frontend_url}/new-password?token={token}"

    if not api_key:
        logger.warning(
            "RESEND_API_KEY não configurada — envio de e-mail ignorado. "
            "Link de redefinição para %s: %s",
            to_email,
            reset_link,
        )
        return

    resend.api_key = api_key
    try:
        resend.Emails.send({
            "from": from_email,
            "to": "smartscoutltda@gmail.com",
            "subject": "Redefinição de senha — SmartScout",
            "html": f"""
                <div style="font-family: sans-serif; max-width: 480px; margin: auto;">
                    <h2>Redefinir sua senha</h2>
                    <p>Clique no botão abaixo para criar uma nova senha. O link expira em 1 hora.</p>
                    <a href="{reset_link}"
                       style="display:inline-block; padding: 12px 24px; background:#2872A1;
                              color:white; border-radius:8px; text-decoration:none; font-weight:600;">
                        Redefinir senha
                    </a>
                    <p style="margin-top:24px; color:#999; font-size:12px;">
                        Se você não solicitou isso, ignore este e-mail.
                    </p>
                </div>
            """,
        })
    except Exception:
        logger.exception(
            "Falha ao enviar e-mail de redefinição via Resend para %s. Link gerado: %s",
            to_email,
            reset_link,
        )
        raise
