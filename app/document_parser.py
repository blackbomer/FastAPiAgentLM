import os
from PyPDF2 import PdfReader
import pytesseract
import pandas as pd
from pdf2image import convert_from_path
from PIL import Image
import xml.etree.ElementTree as ET

def detectar_tipo_y_extraer(filepath: str) -> str:
    ext = os.path.splitext(filepath)[1].lower()
    
    print(f"DEBUG: Extensión detectada: '{ext}' para archivo: {filepath}")

    if ext in [".pdf"]:
        return extraer_texto_pdf(filepath)
    elif ext in [".xlsx", ".xls"]:
        return extraer_texto_excel(filepath)
    elif ext in [".csv", ".txt"]:
        return extraer_texto_txt_csv(filepath)
    elif ext in [".xml"]:
        return extraer_texto_xml(filepath)
    elif ext in [".png", ".jpg", ".jpeg", ".tiff"]:
        return extraer_texto_imagen(filepath)
    else:
        if not ext or ext == "":
            try:
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    first_line = f.readline().strip()
                    if first_line.startswith('<?xml') or first_line.startswith('<'):
                        print(f"DEBUG: Detectado XML por contenido")
                        return extraer_texto_xml(filepath)
            except:
                pass
        
        raise ValueError(f"Tipo de archivo no soportado: '{ext}' para archivo: {filepath}")

def extraer_texto_pdf(filepath):
    try:
        reader = PdfReader(filepath)
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
        if text.strip():
            return text
    except Exception:
        pass

    pages = convert_from_path(filepath, dpi=300)
    return "\n".join([pytesseract.image_to_string(p, lang="spa") for p in pages])


def extraer_texto_excel(filepath):
    df = pd.read_excel(filepath, sheet_name=0)
    return df.to_string(index=False)

def extraer_texto_txt_csv(filepath):
    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()

def extraer_texto_imagen(filepath):
    image = Image.open(filepath)
    return pytesseract.image_to_string(image, lang="spa+eng+deu+cat")

def extraer_texto_xml(filepath):
    try:
        tree = ET.parse(filepath)
        root = tree.getroot()
        
        print(f"DEBUG XML: Root element: {root.tag}")
        
        def extract_text_recursive(element, level=0):
            text_parts = []
            indent = "  " * level
            
            if any(keyword in element.tag.lower() for keyword in ['item', 'product', 'article', 'line', 'articulo', 'producto']):
                if element.text and element.text.strip():
                    text_parts.append(f"{element.tag}: {element.text.strip()}")
                
                if element.attrib:
                    for attr_name, attr_value in element.attrib.items():
                        text_parts.append(f"  {attr_name}: {attr_value}")
                
                for child in element:
                    if child.text and child.text.strip():
                        text_parts.append(f"  {child.tag}: {child.text.strip()}")
                    if child.attrib:
                        for attr_name, attr_value in child.attrib.items():
                            text_parts.append(f"    {attr_name}: {attr_value}")
            else:
                if element.text and element.text.strip():
                    text_parts.append(f"{indent}{element.tag}: {element.text.strip()}")
                
                if element.attrib:
                    for attr_name, attr_value in element.attrib.items():
                        text_parts.append(f"{indent}  {attr_name}: {attr_value}")
                
                for child in element:
                    text_parts.extend(extract_text_recursive(child, level + 1))
            
            return text_parts
        
        text_lines = extract_text_recursive(root)
        result = "\n".join(text_lines)
        
        print(f"DEBUG XML: Texto extraído (primeros 500 chars): {result[:500]}")
        
        return result
        
    except ET.ParseError as e:
        print(f"ERROR XML Parse: {e}")
        raise ValueError(f"Error al parsear XML: {e}")
    except Exception as e:
        print(f"ERROR XML General: {e}")
        raise ValueError(f"Error al procesar archivo XML: {e}")
