import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Iterable, Union

from pydantic import EmailStr

from config import APP_NAME, SMTP_PASSWORD, SMTP_PORT, SMTP_SERVER, SMTP_USERNAME


def send_email(email: Union[EmailStr, Iterable[EmailStr]], subject: str, body: str):
    recipients = [str(email)] if isinstance(email, str) else [str(item) for item in email]
    if not SMTP_USERNAME or not SMTP_PASSWORD:
        return {"message": "SMTP credentials are not configured", "status": "error"}

    msg = MIMEMultipart()
    msg["From"] = f"{APP_NAME} <{SMTP_USERNAME}>"
    msg["To"] = ", ".join(recipients)
    msg["Subject"] = subject

    msg.attach(MIMEText(body, "html"))

    try:
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.sendmail(SMTP_USERNAME, recipients, msg.as_string())
            return {"message": "Email sent successfully", "status": "success"}
    except Exception as e:
        return {"message": str(e), "status": "error"}
