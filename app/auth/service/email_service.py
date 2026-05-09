import smtplib
import random
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from django.conf import settings

logger = logging.getLogger(__name__)


class EmailService:
    def __init__(self):
        # Read SMTP config from Django settings with safe fallbacks
        self.smtp_server = getattr(settings, 'SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = getattr(settings, 'SMTP_PORT', 587)
        self.email = getattr(settings, 'SMTP_EMAIL', None)
        self.password = getattr(settings, 'SMTP_PASSWORD', None)

    def generate_otp(self):
        return str(random.randint(100000, 999999))

    def send_reset_otp(self, to_email, otp):
        if not self.email or not self.password:
            logger.error('SMTP credentials are not configured. Set SMTP_EMAIL and SMTP_PASSWORD in settings/env.')
            return False

        try:
            msg = MIMEMultipart()
            msg['From'] = self.email
            msg['To'] = to_email
            msg['Subject'] = "Password Reset OTP"

            body = f"""
            Your password reset OTP is: {otp}

            This OTP will expire in 10 minutes.
            If you didn't request this, please ignore this email.
            """

            msg.attach(MIMEText(body, 'plain'))

            server = smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=10)
            server.starttls()
            server.login(self.email, self.password)
            server.send_message(msg)
            server.quit()

            return True
        except Exception:
            logger.exception('Email sending failed')
            return False