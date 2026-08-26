from twilio.rest import Client

from app.core.config import get_settings

settings = get_settings()

twilio_client = Client(
    settings.twilio_account_sid,
    settings.twilio_auth_token,
)


def create_outbound_call(to_number: str, twiml_url: str):
    return twilio_client.calls.create(
        to=to_number,
        from_=settings.twilio_phone_number,
        url=twiml_url,
    )