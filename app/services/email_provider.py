import smtplib
from email.message import EmailMessage

from app.core.config import get_settings


class EmailProvider:

    def __init__(self) -> None:
        settings = get_settings()

        self.host = settings.smtp_host
        self.port = settings.smtp_port
        self.username = settings.smtp_username
        self.password = settings.smtp_password
        self.sender = settings.smtp_sender

    async def send_brochure(
            self,
            customer_email: str,
            idempotency_key: str,
    ) -> str:

        if not customer_email:
            raise ValueError("customer_email is required")

        message = EmailMessage()

        message["From"] = self.sender
        message["To"] = customer_email
        message["Subject"] = "Product brochure"

        message.set_content(
            "Thank you for speaking with us.\n\n"
            "Please find the requested product brochure attached."
        )

        # Replace this with the actual brochure attachment.
        # Keep the attachment path/configuration outside the agent.
        #
        # with open(settings.brochure_path, "rb") as file:
        #     message.add_attachment(
        #         file.read(),
        #         maintype="application",
        #         subtype="pdf",
        #         filename="brochure.pdf",
        #     )

        with smtplib.SMTP(
                self.host,
                self.port,
                timeout=15,
        ) as smtp:

            smtp.starttls()

            smtp.login(
                self.username,
                self.password,
            )

            smtp.send_message(message)

        return idempotency_key