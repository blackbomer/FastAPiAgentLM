from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Optional
from app.security.data_anonymizer import get_anonymizer

router = APIRouter(prefix="/admin/anonymization", tags=["admin", "anonymization"])

class ProviderConfigModel(BaseModel):
    nombres_empresa: List[str] = []
    direcciones: List[str] = []
    telefonos: List[str] = []
    emails: List[str] = []
    iban: List[str] = []
    cuentas_bancarias: List[str] = []
    contactos: List[str] = []
    codigos_especiales: List[str] = []

class AddProviderDataModel(BaseModel):
    proveedor: str
    field: str
    value: str

class TestAnonymizationModel(BaseModel):
    texto: str
    proveedor: Optional[str] = None
    apply_heuristics: bool = True

@router.get("/proveedores")
async def listar_proveedores():
    anonymizer = get_anonymizer()
    return {"proveedores": list(anonymizer.provider_config.keys())}

@router.get("/proveedor/{proveedor}")
async def obtener_config_proveedor(proveedor: str):
    anonymizer = get_anonymizer()
    if proveedor not in anonymizer.provider_config:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")
    
    return {
        "proveedor": proveedor,
        "configuracion": anonymizer.provider_config[proveedor]
    }

@router.post("/proveedor/{proveedor}")
async def crear_actualizar_proveedor(proveedor: str, config: ProviderConfigModel):
    anonymizer = get_anonymizer()
    
    anonymizer.provider_config[proveedor] = config.dict()
    
    anonymizer.save_provider_config()
    
    return {
        "message": f"Configuración para {proveedor} guardada exitosamente",
        "proveedor": proveedor,
        "configuracion": anonymizer.provider_config[proveedor]
    }

@router.post("/proveedor/agregar-dato")
async def agregar_dato_proveedor(data: AddProviderDataModel):
    anonymizer = get_anonymizer()
    
    try:
        anonymizer.add_provider_data(data.proveedor, data.field, data.value)
        anonymizer.save_provider_config()
        
        return {
            "message": f"Dato agregado exitosamente",
            "proveedor": data.proveedor,
            "field": data.field,
            "value": data.value
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/proveedor/{proveedor}")
async def eliminar_proveedor(proveedor: str):
    anonymizer = get_anonymizer()
    
    if proveedor not in anonymizer.provider_config:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")
    
    del anonymizer.provider_config[proveedor]
    anonymizer.save_provider_config()
    
    return {"message": f"Proveedor {proveedor} eliminado exitosamente"}

@router.post("/test")
async def probar_anonimizacion(test_data: TestAnonymizationModel):
    anonymizer = get_anonymizer()
    
    texto_anonimizado, stats = anonymizer.anonymize(
        test_data.texto,
        test_data.proveedor,
        test_data.apply_heuristics
    )
    
    return {
        "texto_original": test_data.texto,
        "texto_anonimizado": texto_anonimizado,
        "estadisticas": {
            "total_reemplazos": stats.total_replacements,
            "por_tipo": stats.by_type
        },
        "proveedor_usado": test_data.proveedor
    }

@router.get("/patrones")
async def obtener_patrones_regex():
    anonymizer = get_anonymizer()
    return {
        "patrones_regex": {
            tipo: [pattern for pattern in patterns]
            for tipo, patterns in anonymizer.regex_patterns.items()
        }
    }


