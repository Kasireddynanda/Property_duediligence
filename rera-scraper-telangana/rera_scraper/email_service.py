import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging

logger = logging.getLogger("rera.email")

def send_report_confirmation_email(to_email: str, user_name: str, entity_name: str, report_name: str):
    import os
    from dotenv import load_dotenv
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
    load_dotenv(dotenv_path=env_path, override=True)
    smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER", "").strip()
    smtp_pass = os.getenv("SMTP_PASS", "").replace(" ", "")

    if not smtp_user or not smtp_pass:
        logger.info(f"SMTP not configured (skipping email to {to_email})")
        return

    subject = f"Your {report_name} Request Received - Property Discovery"
    
    body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; color: #333; line-height: 1.6;">
        <h2 style="color: #1d4ed8;">Hello {user_name},</h2>
        <p>We have successfully received your request for a <strong>{report_name}</strong> on <strong>{entity_name}</strong>.</p>
        <p>Our systems are currently processing the RERA data and gathering intelligence for this request.</p>
        <br>
        <p>Thank you,</p>
        <p><strong>Property Discovery Team</strong></p>
    </body>
    </html>
    """

    msg = MIMEMultipart()
    msg['From'] = smtp_user
    msg['To'] = to_email
    msg['Subject'] = subject

    msg.attach(MIMEText(body, 'html'))

    try:
        logger.info(f"Sending confirmation email to {to_email}...")
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.send_message(msg)
        server.quit()
        logger.info(f"Email sent successfully to {to_email}")
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {e}")
