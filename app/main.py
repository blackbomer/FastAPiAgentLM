from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from app.model import ExtractionRequest, ExtractionResponse
from app.agent import procesar_documento, procesar_dades_venda
from app.document_parser import detectar_tipo_y_extraer
from app.security.data_anonymizer import get_anonymizer
import os

app = FastAPI(title="Agent IA Documents")

@app.get("/")
async def root():
    return {
        "message": "Agent IA Documents API",
        "version": "1.0.0",
        "endpoints": {
            "swagger": "/docs",
            "redoc": "/redoc",
            "extraer": "/extraer",
            "extraer-archivo": "/extraer-archivo",
            "extraer-dades-venda": "/extraer-dades-venda"
        }
    }

@app.post("/extraer", response_model=ExtractionResponse)
async def extraer(req: ExtractionRequest):
    try:
        resultado_json = await procesar_documento(
            req.texto, 
            proveedor=req.proveedor, 
            anonymize=req.anonymize
        )
        
        estadisticas = None
        if req.anonymize:
            anonymizer = get_anonymizer()
            _, stats = anonymizer.anonymize(req.texto, req.proveedor)
            estadisticas = {
                "total_reemplazos": stats.total_replacements,
                "por_tipo": stats.by_type
            }
        
        return {
            "resultado": resultado_json,
            "estadisticas_anonimizacion": estadisticas
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/extraer-archivo")
async def extraer_desde_archivo(
    file: UploadFile = File(...),
    proveedor: str = Form(None),
    anonymize: bool = Form(True)
):
    try:
        print(f"DEBUG: Parámetros recibidos - proveedor: {proveedor}, anonymize: {anonymize}")
        
        temp_path = f"/tmp/{file.filename}"
        with open(temp_path, "wb") as f:
            f.write(await file.read())

        texto = detectar_tipo_y_extraer(temp_path)
        print(f"DEBUG: Texto extraído (primeros 200 chars): {texto[:200]}")
        
        resultado = await procesar_documento(texto, proveedor, anonymize)

        os.remove(temp_path)
        return {"resultado": resultado}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error procesando archivo: {e}")


@app.post("/extraer-dades-venda")
async def extraer_dades_venda(
    file: UploadFile = File(...),
    anonymize: bool = Form(True)
):
    try:
        print(f"DEBUG DADES VENDA: Parámetros recibidos - anonymize: {anonymize}")
        
        temp_path = f"/tmp/{file.filename}"
        with open(temp_path, "wb") as f:
            f.write(await file.read())

        texto = detectar_tipo_y_extraer(temp_path)
        print(f"DEBUG DADES VENDA: Texto extraído (primeros 200 chars): {texto[:200]}")
        
        resultado = await procesar_dades_venda(texto, None, anonymize)

        os.remove(temp_path)
        return {"resultado": resultado}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error procesando dades venda: {e}")
