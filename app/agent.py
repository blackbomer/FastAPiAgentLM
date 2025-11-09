import json
import os
from datetime import datetime
import tiktoken
import openai
import logging
from app.security.data_anonymizer import get_anonymizer

logger = logging.getLogger(__name__)

# Clau d'API d'OpenAI carregada des del fitxer .env
openai.api_key = os.getenv("OPENAI_API_KEY")

with open(os.path.join(os.path.dirname(__file__), "prompt.txt"), encoding="utf-8") as f:
    PROMPT_BASE = f.read()

with open(os.path.join(os.path.dirname(__file__), "prompt_dades_venda.txt"), encoding="utf-8") as f:
    PROMPT_DADES_VENDA = f.read()

MODEL_NAME = "gpt-4o"
MAX_TOTAL_TOKENS = 128000
MAX_OUTPUT_TOKENS = 4096
TOKEN_SAFETY_MARGIN = 1000

def contar_tokens(modelo, texto):
    try:
        encoding = tiktoken.encoding_for_model(modelo)
    except Exception:
        encoding = tiktoken.get_encoding("cl100k_base")
    
    return len(encoding.encode(texto))

async def procesar_documento(texto_extraido: str, proveedor: str = None, anonymize: bool = True) -> list:
    logger.info(f"Procesando documento para proveedor: {proveedor or 'No especificado'}")
    
    if anonymize:
        anonymizer = get_anonymizer()
        texto_seguro, stats = anonymizer.anonymize(texto_extraido, proveedor)
        logger.info(f"Datos anonimizados: {stats.total_replacements} elementos")
    else:
        texto_seguro = texto_extraido
        logger.warning("Anonimización DESACTIVADA: se enviarán datos sensibles a OpenAI")
    
    prompt = PROMPT_BASE.replace("{documento_extraido}", texto_seguro)
    
    prompt_tokens = contar_tokens(MODEL_NAME, prompt)
    logger.info(f"Tokens en prompt: {prompt_tokens}")

    if prompt_tokens + MAX_OUTPUT_TOKENS > (MAX_TOTAL_TOKENS - TOKEN_SAFETY_MARGIN):
        exceso = prompt_tokens + MAX_OUTPUT_TOKENS - (MAX_TOTAL_TOKENS - TOKEN_SAFETY_MARGIN)
        logger.warning(f"El prompt excede el límite de tokens. Recortando {exceso} tokens...")
        texto_seguro = texto_seguro[:-exceso*4]
        prompt = PROMPT_BASE.replace("{documento_extraido}", texto_seguro)

    try:
        os.makedirs("logs", exist_ok=True)
        with open("logs/openai_requests.txt", "a", encoding="utf-8") as f:
            f.write(f"\n{'='*80}\n{datetime.now():%Y-%m-%d %H:%M:%S}\n")
            f.write(f"Proveedor: {proveedor or 'No especificado'} | Anonimizado: {anonymize}\n")
            f.write(f"{'-'*80}\n{prompt[:3000]}...\n")
    except Exception as e:
        logger.warning(f"No se pudo guardar el log: {e}")

    response = openai.ChatCompletion.create(
        model=MODEL_NAME,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        max_tokens=MAX_OUTPUT_TOKENS
    )

    resultado = response.choices[0].message.content.strip()

    for marker in ("```json", "```"):
        if resultado.startswith(marker):
            resultado = resultado[len(marker):].strip()
        if resultado.endswith("```"):
            resultado = resultado[:-3].strip()

    try:
        data = json.loads(resultado)
        if isinstance(data, list):
            return data
        else:
            logger.warning("La respuesta no es un array JSON, devolviendo []")
            return []
    except json.JSONDecodeError as e:
        logger.error(f"Error al parsear JSON: {e}")
        logger.debug(f"Respuesta bruta: {resultado[:1000]}")
        return []


async def procesar_dades_venda(texto_extraido: str, proveedor: str = None, anonymize: bool = True) -> list:
    logger.info(f"Procesando dades venda para proveedor: {proveedor or 'No especificado'}")
    
    if anonymize:
        anonymizer = get_anonymizer()
        texto_seguro, stats = anonymizer.anonymize(texto_extraido, proveedor)
        logger.info(f"Datos anonimizados: {stats.total_replacements} elementos")
    else:
        texto_seguro = texto_extraido
        logger.warning("Anonimización DESACTIVADA: se enviarán datos sensibles a OpenAI")
    
    prompt = PROMPT_DADES_VENDA.replace("{documento_extraido}", texto_seguro)
    
    prompt_tokens = contar_tokens(MODEL_NAME, prompt)
    logger.info(f"Tokens en prompt: {prompt_tokens}")

    if prompt_tokens + MAX_OUTPUT_TOKENS > (MAX_TOTAL_TOKENS - TOKEN_SAFETY_MARGIN):
        exceso = prompt_tokens + MAX_OUTPUT_TOKENS - (MAX_TOTAL_TOKENS - TOKEN_SAFETY_MARGIN)
        logger.warning(f"El prompt excede el límite de tokens. Recortando {exceso} tokens...")
        texto_seguro = texto_seguro[:-exceso*4]
        prompt = PROMPT_DADES_VENDA.replace("{documento_extraido}", texto_seguro)

    try:
        os.makedirs("logs", exist_ok=True)
        with open("logs/openai_requests_dades_venda.txt", "a", encoding="utf-8") as f:
            f.write(f"\n{'='*80}\n{datetime.now():%Y-%m-%d %H:%M:%S}\n")
            f.write(f"Proveedor: {proveedor or 'No especificado'} | Anonimizado: {anonymize}\n")
            f.write(f"{'-'*80}\n{prompt[:3000]}...\n")
    except Exception as e:
        logger.warning(f"No se pudo guardar el log: {e}")

    response = openai.ChatCompletion.create(
        model=MODEL_NAME,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        max_tokens=MAX_OUTPUT_TOKENS
    )

    resultado = response.choices[0].message.content.strip()

    for marker in ("```json", "```"):
        if resultado.startswith(marker):
            resultado = resultado[len(marker):].strip()
        if resultado.endswith("```"):
            resultado = resultado[:-3].strip()

    try:
        data = json.loads(resultado)
        if isinstance(data, list):
            return data
        else:
            logger.warning("La respuesta no es un array JSON, devolviendo []")
            return []
    except json.JSONDecodeError as e:
        logger.error(f"Error al parsear JSON: {e}")
        logger.debug(f"Respuesta bruta: {resultado[:1000]}")
        return []