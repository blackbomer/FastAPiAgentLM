import re
import json
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

@dataclass
class AnonymizationStats:
    total_replacements: int = 0
    by_type: Dict[str, int] = None
    
    def __post_init__(self):
        if self.by_type is None:
            self.by_type = {}

class DataAnonymizer:
    
    def __init__(self, config_path: Optional[str] = None):
        if config_path:
            self.config_path = config_path
        else:
            possible_paths = [
                "app/config/anonymization_config.json",
                "../app/config/anonymization_config.json",
                "FastApiAgent/app/config/anonymization_config.json"
            ]
            
            for path in possible_paths:
                if Path(path).exists():
                    self.config_path = path
                    break
            else:
                self.config_path = "app/config/anonymization_config.json"
        
        self.provider_config = self._load_provider_config()
        self.stats = AnonymizationStats()
        
        self.regex_patterns = {
            'cif_nif_nie': [
                r'\b[XYZ]\d{7}[A-Z]\b',
                r'\b\d{8}[A-Z]\b',
                r'\b[ABCDEFGHJNPQRSUVW]\d{6,7}[0-9A-J]\b',
                r'\b[ABCDEFGHJNPQRSUVW]\d{8}\b',
                r'\b[ABCDEFGHJNPQRSUVW]\d{8}[0-9A-J]\b',
                r'\b[ABCDEFGHJNPQRSUVW]\d{8}\b',
                r'\b[ABCDEFGHJNPQRSUVW]\d{8}\b',
            ],
            
            'email': [
                r'\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b'
            ],
            
            'telefono': [
                r'\b(?:\+34|0034)?\s*[6789]\d{8}\b',
                r'\b(?:\+34|0034)?\s*9\d{8}\b',
                r'\b\+\d{1,3}\s*\d{3,4}\s*\d{3,4}\s*\d{3,4}\b',
                r'\b(?:\+34|0034)?\s*\d{3}\s*\d{3}\s*\d{3}\b',
                r'\b(?:\+34|0034)?\s*\d{2}\s*\d{3}\s*\d{2}\s*\d{2}\b',
                r'\b\d{3}-\d{3}-\d{3}\b',
            ],
            
            'iban': [
                r'\bES\d{2}\s*\d{4}\s*\d{4}\s*\d{2}\s*\d{10}\b',
                r'\b[A-Z]{2}\d{2}\s*(?:\d{4}\s*){3,8}\d{1,4}\b',
                r'\b[A-Z]{2}\d{2}-\d{4}-\d{4}-\d{2}-\d{10}\b',
                r'\b[A-Z]{2}\d{2}(?:-\d{4}){3,8}-\d{1,4}\b',
            ],
            
            'cuenta_bancaria': [
                r'\b\d{4}\s*\d{4}\s*\d{2}\s*\d{10}\b',
                r'\b\d{20}\b',
            ],
            
            'direccion': [
                r'(?i)\b(?:C\/|Calle|Avda?\.?|Avenida|Paseo|Plaza|Pz\.?|Polígono|Pol\.?)\s+[^,\n\r]{5,50}',
                r'(?i)\b\d{5}\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b',
                r'(?i)\b(?:Av\.?|Avenida)\s+[A-Za-z]+\s+\d+[^,\n\r]*\b',
            ],
            
            'numero_documento': [
                r'\b(?:FAC|FACT|PED|ALB|ORD)[A-Z0-9\-]{3,15}\b',
                r'\b\d{4,8}\/\d{2,4}\b',
            ],
            
            'precio': [
                r'\b\d{1,6}[,\.]\d{2}\s*€\b',
                r'\b€\s*\d{1,6}[,\.]\d{2}\b',
            ],
        }
    
    def _load_provider_config(self) -> Dict:
        try:
            if Path(self.config_path).exists():
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"No se pudo cargar configuración de proveedores: {e}")
        return {}
    
    def _apply_regex_patterns(self, texto: str) -> str:
        for pattern_type, patterns in self.regex_patterns.items():
            for pattern in patterns:
                matches = len(re.findall(pattern, texto))
                if matches > 0:
                    self.stats.by_type[pattern_type] = self.stats.by_type.get(pattern_type, 0) + matches
                    self.stats.total_replacements += matches
                    
                    placeholder = f'[{pattern_type.upper()}]'
                    texto = re.sub(pattern, placeholder, texto)
        
        return texto
    
    def _apply_provider_config(self, texto: str, proveedor: str = None) -> str:
        if not proveedor or proveedor not in self.provider_config:
            return texto
        
        config = self.provider_config[proveedor]
        
        for field, values in config.items():
            if isinstance(values, list):
                for value in values:
                    if value and value.strip():
                        escaped_value = re.escape(value.strip())
                        if field == 'codigos_especiales':
                            if any(char.isdigit() for char in value):
                                pattern = rf'(?:CIF:\s*)?{escaped_value}'
                            else:
                                pattern = rf'{escaped_value}'
                        else:
                            pattern = rf'\b{escaped_value}\b'
                        
                        matches = len(re.findall(pattern, texto, re.IGNORECASE))
                        if matches > 0:
                            if field == 'nombres_empresa':
                                placeholder = '[NOMBRES_EMPRESA_PROVEEDOR]'
                            elif field == 'codigos_especiales' and any(char.isdigit() for char in value):
                                placeholder = '[CIF]'
                            else:
                                placeholder = f'[{field.upper()}_PROVEEDOR]'
                            texto = re.sub(pattern, placeholder, texto, flags=re.IGNORECASE)
                            
                            self.stats.by_type[f'{field}_proveedor'] = self.stats.by_type.get(f'{field}_proveedor', 0) + matches
                            self.stats.total_replacements += matches
        
        return texto
    
    def _apply_heuristic_detection(self, texto: str) -> str:
        lines = texto.split('\n')
        processed_lines = []
        
        for line in lines:
            line_upper = line.upper().strip()
            
            if (len(line_upper) > 10 and 
                len(line_upper) < 80 and 
                line_upper.isalpha() and 
                line_upper == line.strip().upper()):
                
                processed_lines.append('[NOMBRE_EMPRESA_DETECTADO]')
                self.stats.by_type['empresa_heuristica'] = self.stats.by_type.get('empresa_heuristica', 0) + 1
                self.stats.total_replacements += 1
                continue
            
            if (any(keyword in line_upper for keyword in ['CALLE', 'AVENIDA', 'PLAZA', 'PASEO']) and
                any(char.isdigit() for char in line)):
                
                processed_lines.append('[DIRECCION_DETECTADA]')
                self.stats.by_type['direccion_heuristica'] = self.stats.by_type.get('direccion_heuristica', 0) + 1
                self.stats.total_replacements += 1
                continue
            
            processed_lines.append(line)
        
        return '\n'.join(processed_lines)
    
    def anonymize(self, texto: str, proveedor: str = None, 
                  apply_heuristics: bool = True) -> Tuple[str, AnonymizationStats]:
        if not texto or not texto.strip():
            return texto, self.stats
        
        self.stats = AnonymizationStats()
        
        logger.info(f"Iniciando anonimización{f' para proveedor: {proveedor}' if proveedor else ''}")
        
        print(f"DEBUG Anonymizer: proveedor recibido = '{proveedor}'")
        print(f"DEBUG Anonymizer: proveedores disponibles = {list(self.provider_config.keys())}")
        
        if proveedor and proveedor in self.provider_config:
            config = self.provider_config[proveedor]
            print(f"DEBUG Anonymizer: config encontrada = {config}")
            if config.get('anonimizar', True) == False:
                logger.info(f"Anonimización completamente deshabilitada para proveedor: {proveedor}")
                print(f"DEBUG Anonymizer: ANONIMIZACION COMPLETAMENTE DESHABILITADA!")
                return texto, self.stats
        else:
            print(f"DEBUG Anonymizer: Proveedor no encontrado o None, continuando con anonimización")
        
        texto = self._apply_regex_patterns(texto)
        
        if proveedor:
            texto = self._apply_provider_config(texto, proveedor)
        else:
            for provider_name in self.provider_config.keys():
                if not provider_name.startswith('_'):
                    texto = self._apply_provider_config(texto, provider_name)
        
        if apply_heuristics:
            texto = self._apply_heuristic_detection(texto)
        
        logger.info(f"Anonimización completada: {self.stats.total_replacements} reemplazos realizados")
        
        return texto, self.stats
    
    def create_provider_config_template(self, proveedor: str) -> Dict:
        return {
            proveedor: {
                "nombres_empresa": [],
                "direcciones": [],
                "telefonos": [],
                "emails": [],
                "iban": [],
                "cuentas_bancarias": [],
                "contactos": [],
                "codigos_especiales": []
            }
        }
    
    def add_provider_data(self, proveedor: str, field: str, value: str):
        if proveedor not in self.provider_config:
            self.provider_config[proveedor] = self.create_provider_config_template(proveedor)[proveedor]
        
        if field not in self.provider_config[proveedor]:
            self.provider_config[proveedor][field] = []
        
        if value not in self.provider_config[proveedor][field]:
            self.provider_config[proveedor][field].append(value)
    
    def save_provider_config(self):
        try:
            Path(self.config_path).parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.provider_config, f, indent=2, ensure_ascii=False)
            logger.info(f"Configuración guardada en {self.config_path}")
        except Exception as e:
            logger.error(f"Error guardando configuración: {e}")


_anonymizer_instance = None

def get_anonymizer() -> DataAnonymizer:
    global _anonymizer_instance
    if _anonymizer_instance is None:
        _anonymizer_instance = DataAnonymizer()
    return _anonymizer_instance


