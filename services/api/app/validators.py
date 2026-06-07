from datetime import datetime

from pydantic import ValidationError

from app.schemas import IncomingMessage


ALLOWED_MESSAGE_TYPES = {
    "SEND_MESSAGE"
}


def validate_incoming_message(data: dict) -> tuple[bool, dict | str]:
    try:
        message = IncomingMessage(**data)
    except ValidationError as error:
        return False, str(error)
    
    if message.type not in ALLOWED_MESSAGE_TYPES:
        return False, f"Tipo de mensagem inválido: {message.type}"
    
    try:
        datetime.fromisoformat(message.timestamp_iso.replace("Z", "+00:00"))
    except ValueError:
        return False, "timestamp_iso deve estar no formato ISO 8601"
    
    return True, message.model_dump()