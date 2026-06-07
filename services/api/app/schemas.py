from pydantic import BaseModel, Field


class IncomingMessage(BaseModel):
    type: str
    usuario: str = Field(min_length=1, max_length=80)
    timestamp_iso: str
    corpo_texto: str = Field(min_length=1, max_length=500)