from pydantic import BaseModel, Field, ConfigDict
from typing import Optional


class MessageSchema(BaseModel):
    """Pydantic schema for an incoming Twilio WhatsApp webhook payload."""

    message_sid: str = Field(..., alias="MessageSid")
    num_media: int = Field(..., alias="NumMedia")
    message_type: str = Field(..., alias="MessageType")
    media_url: Optional[str] = Field(default=None, alias="MediaUrl0")
    media_content_type: Optional[str] = Field(default=None, alias="MediaContentType0")
    wa_id: str = Field(..., alias="WaId")
    status: str = Field(..., alias="SmsStatus")
    to: str = Field(..., alias="To")
    from_: str = Field(..., alias="From")
    body: Optional[str] = Field(default=None, alias="Body")
    audio_transcription: Optional[str] = Field(default=None)
    message_service_sid: Optional[str] = Field(default=None, alias="MessagingServiceSid")
    price: Optional[str] = Field(default=None)
    price_unit: Optional[str] = Field(default=None)

    model_config = ConfigDict(populate_by_name=True)
