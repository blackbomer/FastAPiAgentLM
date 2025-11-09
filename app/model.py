from pydantic import BaseModel
from typing import Optional, Any

class ExtractionRequest(BaseModel):
    texto: str
    proveedor: Optional[str] = None
    anonymize: bool = True

class ExtractionResponse(BaseModel):
    resultado: Any
    estadisticas_anonimizacion: Optional[dict] = None
