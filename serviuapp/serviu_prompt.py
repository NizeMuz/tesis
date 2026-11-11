import os
import json
import time
import uuid
import logging
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum

from django.utils import timezone
from django.conf import settings
from .models import ChatInteraction
from .nlp_utils import nlp_analyzer

logger = logging.getLogger(__name__)


class AIProvider(Enum):
    """Proveedores de IA soportados"""
    OLLAMA = "ollama"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    HUGGINGFACE = "huggingface"
    DEEPSEEK = "deepseek"
    FALLBACK = "fallback"


@dataclass
class AIConfig:
    """Configuración para cada proveedor"""
    provider: AIProvider
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model: Optional[str] = None
    timeout: int = 30
    max_tokens: int = 500
    temperature: float = 0.7
    enabled: bool = True


class AIProviderBase(ABC):
    """Clase base abstracta para proveedores de IA"""

    def __init__(self, config: AIConfig):
        self.config = config

    @abstractmethod
    def generate(self, prompt: str, system_prompt: str, **kwargs) -> str:
        """Genera una respuesta del modelo"""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Verifica si el proveedor está disponible"""
        pass

    def _build_messages(self, system_prompt: str, user_prompt: str) -> List[Dict[str, str]]:
        """Construye el formato de mensajes estándar"""
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]


class OllamaProvider(AIProviderBase):
    """Proveedor para Ollama (local)"""

    def generate(self, prompt: str, system_prompt: str, **kwargs) -> str:
        import requests

        full_prompt = f"{system_prompt}\n\nUsuario: {prompt}\n\nAsistente:"

        response = requests.post(
            f"{self.config.base_url}/api/generate",
            json={
                "model": self.config.model,
                "prompt": full_prompt,
                "stream": False,
                "options": {
                    "temperature": self.config.temperature,
                    "top_p": 0.9,
                    "num_predict": self.config.max_tokens
                }
            },
            timeout=self.config.timeout
        )
        response.raise_for_status()
        return response.json().get('response', '').strip()

    def is_available(self) -> bool:
        try:
            import requests
            response = requests.get(f"{self.config.base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get('models', [])
                model_names = [m.get('name', '') for m in models]
                return self.config.model in model_names or f"{self.config.model}:latest" in model_names
            return False
        except Exception:
            return False


class OpenAIProvider(AIProviderBase):
    """Proveedor para OpenAI (GPT-4, GPT-3.5)"""

    def generate(self, prompt: str, system_prompt: str, **kwargs) -> str:
        import requests

        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.config.model,
            "messages": self._build_messages(system_prompt, prompt),
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature
        }

        response = requests.post(
            f"{self.config.base_url}/chat/completions",
            headers=headers,
            json=payload,
            timeout=self.config.timeout
        )
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content'].strip()

    def is_available(self) -> bool:
        return bool(self.config.api_key)


class AnthropicProvider(AIProviderBase):
    """Proveedor para Anthropic (Claude)"""

    def generate(self, prompt: str, system_prompt: str, **kwargs) -> str:
        import requests

        headers = {
            "x-api-key": self.config.api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01"
        }

        payload = {
            "model": self.config.model,
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature,
            "system": system_prompt,
            "messages": [{"role": "user", "content": prompt}]
        }

        response = requests.post(
            f"{self.config.base_url}/v1/messages",
            headers=headers,
            json=payload,
            timeout=self.config.timeout
        )
        response.raise_for_status()
        return response.json()['content'][0]['text'].strip()

    def is_available(self) -> bool:
        return bool(self.config.api_key)


class HuggingFaceProvider(AIProviderBase):
    """Proveedor para Hugging Face Inference API"""

    def generate(self, prompt: str, system_prompt: str, **kwargs) -> str:
        import requests

        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json"
        }

        full_prompt = f"{system_prompt}\n\nUsuario: {prompt}\n\nAsistente:"

        payload = {
            "inputs": full_prompt,
            "parameters": {
                "max_new_tokens": self.config.max_tokens,
                "temperature": self.config.temperature,
                "do_sample": True,
                "return_full_text": False
            }
        }

        response = requests.post(
            f"https://api-inference.huggingface.co/models/{self.config.model}",
            headers=headers,
            json=payload,
            timeout=self.config.timeout
        )
        response.raise_for_status()

        result = response.json()
        if isinstance(result, list) and len(result) > 0:
            return result[0].get('generated_text', '').strip()
        return str(result).strip()

    def is_available(self) -> bool:
        return bool(self.config.api_key)


class DeepSeekProvider(AIProviderBase):
    """Proveedor para DeepSeek (API compatible con OpenAI)"""

    def generate(self, prompt: str, system_prompt: str, **kwargs) -> str:
        import requests

        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.config.model,
            "messages": self._build_messages(system_prompt, prompt),
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature
        }

        response = requests.post(
            f"{self.config.base_url}/chat/completions",
            headers=headers,
            json=payload,
            timeout=self.config.timeout
        )
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content'].strip()

    def is_available(self) -> bool:
        return bool(self.config.api_key)


class FallbackProvider(AIProviderBase):
    """Proveedor de respaldo con respuestas predefinidas"""

    def __init__(self, config: AIConfig):
        super().__init__(config)
        self.responses = self._load_fallback_responses()

    def _load_fallback_responses(self) -> Dict[str, str]:
        return {
            "saludo": """¡Hola! 👋 Soy tu asistente de SERVIU (Servicio de Vivienda y Urbanización de Chile).
Estoy aquí para ayudarte con información sobre subsidios habitacionales, trámites y beneficios.

¿En qué puedo ayudarte hoy? Puedes consultarme sobre:
🏠 **DS1** - Subsidio Sectores Medios (compra de vivienda)
🏠 **DS49** - Fondo Solidario (construcción sin crédito)
🏠 **DS10** - Habitabilidad Rural
🏠 **DS19** - Integración Social y Territorial
🏠 **DS27** - Mejoramiento de Viviendas (Hogar Mejor)
🏠 **DS52** - Subsidio de Arriendo
🏠 **DS255** - Programa de Eficiencia Energética
📋 Requisitos, documentación y trámites""",

            "ds1": """**Subsidio DS1 - Sectores Medios** 🏠

**¿Para quién?** Familias con capacidad de ahorro que quieren comprar vivienda nueva o usada.

**Montos (2024):**
- Tramo 1 (RSH ≤40%): hasta 550 UF
- Tramo 2 (RSH 40-70%): hasta 500 UF
- Tramo 3 (RSH 70-90%): hasta 450 UF
- Zonas extremas: +50 UF adicionales

**Requisitos:**
✅ Mayor de 18 años
✅ No ser propietario de vivienda
✅ Ahorro mínimo: 30-80 UF según valor vivienda
✅ RSH vigente dentro del 90%
✅ Capacidad de crédito (preaprobación bancaria)

**Tipologías:** Vivienda nueva/usada, construcción en sitio propio, densificación predial.

Más info: https://www.minvu.gob.cl/subsidio-sectores-medios/""",

            "ds49": """**Subsidio DS49 - Fondo Solidario de Elección de Vivienda** 🏠

**¿Para quién?** Familias vulnerables (RSH ≤40%) sin capacidad de crédito.

**Modalidades:**
1. **Construcción en terreno propio** - Ahorro 10 UF
2. **Construcción en terreno del Serviu** - Ahorro 10 UF
3. **Pequeño condominio** - Ahorro 10 UF
4. **Densificación predial** - Ahorro 10 UF

**Requisitos:**
✅ RSH ≤40%
✅ Ahorro mínimo 10 UF
✅ No ser propietario
✅ Entidad Patrocinante (EP) obligatoria
✅ Grupo familiar ≥2 personas (excepto adultos mayores/discapacidad)

**Ventaja:** No requiere crédito hipotecario. El subsidio cubre el 100% de la vivienda.

Más info: https://www.minvu.gob.cl/fondo-solidario/""",

            "ds10": """**Subsidio DS10 - Habitabilidad Rural** 🏠

**¿Para quién?** Familias en zonas rurales para construir o mejorar vivienda.

**Requisitos:**
✅ Terreno propio (título de dominio, derechos agua, etc.)
✅ RSH ≤60-70% (según llamado)
✅ Ahorro desde 10 UF (tramo vulnerable) a 80 UF
✅ Entidad de Gestión Rural (consultora técnica)

**Tipologías:**
- Construcción nueva (hasta 60 m²)
- Ampliación/mejoramiento
- Reparación estructural

**Especial Ñuble:** Tablas de costos ajustadas a realidad regional.

Más info: https://www.minvu.gob.cl/habitabilidad-rural/""",

            "ds19": """**Subsidio DS19 - Integración Social y Territorial** 🏠

**¿Para quién?** Familias que compran en proyectos inmobiliarios con subsidio automático.

**Ahorro requerido:**
- Vivienda ≤1.100 UF: 30 UF
- Vivienda 1.100-2.200 UF: 40 UF
- Vivienda >2.200 UF: 80 UF

**Requisitos:**
✅ RSH ≤90%
✅ Preaprobación bancaria (salvo cupo vulnerabilidad)
✅ Proyecto inmobiliario autorizado MINVU

**Ventaja:** Subsidio se descuenta directo en la inmobiliaria.

Más info: https://www.minvu.gob.cl/ds19/""",

            "ds27": """**Subsidio DS27 - Mejoramiento de Viviendas (Hogar Mejor)** 🏠

**¿Para quién?** Propietarios/asignatarios de vivienda social (avalúo <950 UF).

**Líneas de acción:**
- **CAP I** - Reparaciones (techos, muros, pisos): 3-7 UF ahorro
- **CAP II** - Ampliaciones: 5-10 UF ahorro
- **CAP III** - Eficiencia energética: 3-7 UF ahorro

**Requisitos:**
✅ Propietario o asignatario
✅ Vivienda social (<950 UF avalúo)
✅ RSH ≤60% (individual) o ≤70% (grupal)
✅ Entidad Patrocinante o contratista MINVU

**Ñuble:** Tablas de costos regionales para eficiencia energética.

Más info: https://www.minvu.gob.cl/hogar-mejor/""",

            "ds52": """**Subsidio DS52 - Subsidio de Arriendo** 🏠

**¿Para quién?** Familias que arriendan y necesitan apoyo temporal.

**Requisitos:**
✅ Ingresos familiares 7-25 UF
✅ Ahorro 4 UF
✅ RSH ≤70%
✅ Cotizaciones previsionales al día
✅ No ser propietario

**Beneficio:** 4,2 UF mensuales (17 UF zona extrema) por hasta 8 años (renovable c/2 años).

Más info: https://www.minvu.gob.cl/subsidio-arriendo/""",

            "ds255": """**Subsidio DS255 - Eficiencia Energética** 🏠

**¿Para quién?** Propietarios de vivienda social para mejoras térmicas.

**Tipologías financiadas:**
- Aislamiento térmico (muros, techos, pisos)
- Ventanas termopanel
- Calefactores eficientes (pellet, leña certificada)
- Fotovoltaico, colectores solares
- Mejoramiento envolvente

**Requisitos:**
✅ Vivienda social (<950 UF)
✅ RSH ≤70%
✅ Ahorro según tipología

Más info: https://www.minvu.gob.cl/eficiencia-energetica/""",

            "documentos": """**Documentación Común para Subsidios** 📄

**Obligatorios:**
✅ Cédula de identidad vigente (todos los mayores de 18)
✅ Certificado de ahorro para la vivienda (cuenta ahorro MINVU)
✅ Inscripción vigente Registro Social de Hogares (RSH)
✅ Certificado de matrimonio/unión civil (si aplica)

**Según subsidio:**
• **DS1/DS19:** Preaprobación bancaria, certificado dominio (sitio propio)
• **DS49/DS10/DS27:** Entidad Patrocinante, proyecto técnico, permisos municipales
• **DS52:** Cotizaciones previsionales al día, contrato arriendo
• **DS255:** Certificado avalúo fiscal, diagnóstico energético

Portal oficial: https://www.minvu.gob.cl/ | ChileAtiende: https://www.chileatiende.gob.cl/""",

            "requisitos": """**Requisitos Generales (Todos los Subsidios)** ✅

1. **Edad:** Mayor de 18 años
2. **Identidad:** Cédula vigente
3. **Propiedad:** No ser propietario de vivienda (salvo DS27/DS255)
4. **RSH:** Inscripción vigente en Registro Social de Hogares
5. **Ahorro:** Cuenta de ahorro para la vivienda (banco autorizado)
6. **Grupo familiar:** Acreditación según subsidio

**Clave Única:** Necesaria para trámites online en https://claveunica.gob.cl/

Más info: https://www.registrosocial.gob.cl/""",

            "default": """Puedo ayudarte con información sobre subsidios habitacionales chilenos:

🏠 **Subsidios principales:**
- **DS1** - Sectores Medios (compra vivienda)
- **DS49** - Fondo Solidario (construcción sin crédito)
- **DS10** - Habitabilidad Rural
- **DS19** - Integración Social (proyectos inmobiliarios)
- **DS27** - Mejoramiento (Hogar Mejor)
- **DS52** - Subsidio de Arriendo
- **DS255** - Eficiencia Energética

📋 **Temas:**
- Requisitos y documentación
- Montos y tramos según RSH
- Procesos de postulación
- Entidades Patrocinantes

¿Sobre qué tema específico quieres saber?

🔗 **Enlaces oficiales:**
- MINVU: https://www.minvu.gob.cl/
- ChileAtiende: https://www.chileatiende.gob.cl/
- Registro Social: https://www.registrosocial.gob.cl/
- Clave Única: https://claveunica.gob.cl/"""
        }

    def generate(self, prompt: str, system_prompt: str, **kwargs) -> str:
        prompt_lower = prompt.lower()

        # Detección de intención simple por palabras clave
        if any(w in prompt_lower for w in ["hola", "buenos", "buenas", "saludo", "que tal"]):
            return self.responses["saludo"]
        elif "ds1" in prompt_lower or "sectores medios" in prompt_lower:
            return self.responses["ds1"]
        elif "ds49" in prompt_lower or "fondo solidario" in prompt_lower:
            return self.responses["ds49"]
        elif "ds10" in prompt_lower or "rural" in prompt_lower:
            return self.responses["ds10"]
        elif "ds19" in prompt_lower or "integracion" in prompt_lower or "pist" in prompt_lower:
            return self.responses["ds19"]
        elif "ds27" in prompt_lower or "mejoramiento" in prompt_lower or "hogar mejor" in prompt_lower or "cap i" in prompt_lower or "cap ii" in prompt_lower or "cap iii" in prompt_lower:
            return self.responses["ds27"]
        elif "ds52" in prompt_lower or "arriendo" in prompt_lower:
            return self.responses["ds52"]
        elif "ds255" in prompt_lower or "eficiencia" in prompt_lower or "energetica" in prompt_lower or "termico" in prompt_lower:
            return self.responses["ds255"]
        elif "documento" in prompt_lower or "papeles" in prompt_lower or "certificado" in prompt_lower:
            return self.responses["documentos"]
        elif "requisito" in prompt_lower:
            return self.responses["requisitos"]
        else:
            return self.responses["default"]

    def is_available(self) -> bool:
        return True


# ============================================================
# SYSTEM PROMPT MEJORADO - COMPREHENSIVE SERVIU KNOWLEDGE
# ============================================================

SERVIU_SYSTEM_PROMPT = """
Eres un asistente especializado experto en SERVIU (Servicio de Vivienda y Urbanización) y el Ministerio de Vivienda y Urbanismo (MINVU) de Chile. Tu misión es proporcionar información precisa, actualizada y útil sobre subsidios habitacionales, programas y trámites a ciudadanos chilenos.

===========================================
CONOCIMIENTO BASE OFICIAL (2024-2025)
===========================================

**SUBSIDIOS PRINCIPALES Y MONTOS ACTUALES:**

📌 **DS1 - SUBSIDIO SECTORES MEDIOS** (Compra de vivienda nueva/usada)
• Tramo 1 (RSH ≤40%): 550 UF | Tramo 2 (40-70%): 500 UF | Tramo 3 (70-90%): 450 UF
• Zonas extremas (Aysén, Magallanes, Palena): +50 UF adicional
• Ahorro: 30 UF (≤1.100 UF), 40 UF (1.100-2.200 UF), 80 UF (>2.200 UF)
• Requiere preaprobación bancaria | Vivienda hasta 2.200 UF (2.400 UF zona extrema)

📌 **DS49 - FONDO SOLIDARIO DE ELECCIÓN DE VIVIENDA** (Construcción sin crédito)
• Objetivo: RSH ≤40% | Ahorro: 10 UF (todos los tramos)
• Modalidades: Sitio propio, terreno Serviu, pequeño condominio, densificación predial
• **NO requiere crédito hipotecario** - subsidio cubre 100% vivienda
• Entidad Patrocinante (EP) obligatoria | Grupo familiar ≥2 (salvo excepciones)

📌 **DS10 - HABITABILIDAD RURAL** (Zonas rurales)
• Construcción nueva (hasta 60 m²), ampliación, mejoramiento, reparación
• RSH ≤60-70% según llamado | Ahorro: 10-80 UF según tramo
• Terreno: título dominio, derechos agua, comunidad indígena, etc.
• Entidad de Gestión Rural (consultora) obligatoria
• **Región de Ñuble:** Tablas de costos regionales ajustadas

📌 **DS19 - INTEGRACIÓN SOCIAL Y TERRITORIAL** (Proyectos inmobiliarios)
• Subsidio automático en proyectos autorizados MINVU
• Ahorro: 30 UF (≤1.100 UF), 40 UF (1.100-2.200 UF), 80 UF (>2.200 UF)
• RSH ≤90% | Preaprobación bancaria (salvo cupo vulnerabilidad ≤70%)
• Descuento directo en inmobiliaria

📌 **DS27 - MEJORAMIENTO DE VIVIENDAS Y BARRIOS (HOGAR MEJOR)**
• Propietarios/asignatarios vivienda social (avalúo fiscal <950 UF)
• RSH ≤60% individual / ≤70% grupal | Ahorro 3-10 UF según línea
• **CAP I:** Reparaciones (techos, muros, pisos, instalaciones) - 3-7 UF
• **CAP II:** Ampliaciones (nuevos dormitorios, baños) - 5-10 UF
• **CAP III:** Eficiencia energética (aislamiento, termopanel, calefactores) - 3-7 UF
• Entidad Patrocinante o contratista inscrito MINVU obligatorio
• **Ñuble:** Tablas de costos regionales para eficiencia energética

📌 **DS52 - SUBSIDIO DE ARRIENDO**
• Ingresos familiares 7-25 UF | Ahorro: 4 UF | RSH ≤70%
• Cotizaciones previsionales al día | No propietario
• Beneficio: 4,2 UF/mes (17 UF zona extrema) × 8 años (renovable c/2 años)
• Permite arrendar en mercado formal

📌 **DS255 - PROGRAMA EFICIENCIA ENERGÉTICA VIVIENDA SOCIAL**
• Aislamiento térmico (muros, techos, pisos, ventiladas)
• Ventanas termopanel / herméticas
• Calefactores eficientes (pellet, leña cert. SEC, split inverter)
• Energías renovables: fotovoltaico, colectores solares térmicos
• RSH ≤70% | Vivienda social <950 UF

📌 **DS120 - LEASING HABITACIONAL** (Poco común, vigente)
• Arriendo con promesa de compra | Ahorro 10% valor vivienda
• RSH ≤70% | Plazo 10-20 años

===========================================
REQUISITOS TRANSVERSALES
===========================================
✅ Mayor 18 años | ✅ Cédula identidad vigente | ✅ No propietario (salvo DS27/DS255)
✅ RSH vigente (https://www.registrosocial.gob.cl/) | ✅ Cuenta ahorro vivienda (banco autorizado)
✅ Clave Única para trámites online (https://claveunica.gob.cl/)

===========================================
DOCUMENTACIÓN BASE POR PROGRAMA
===========================================
**Todos:** Cédula, certificado ahorro, RSH vigente, cert. matrimonio/AC (si aplica)
**DS1/DS19:** Preaprobación bancaria, cert. dominio (sitio propio)
**DS49/DS10/DS27:** EP + proyecto técnico + permisos municipales + cert. dominio
**DS52:** Cotizaciones al día, contrato arriendo, cert. ingresos
**DS255:** Cert. avalúo fiscal, diagnóstico energético (si aplica)

===========================================
ENTIDADES CLAVE Y ENLACES OFICIALES
===========================================
🌐 **MINVU:** https://www.minvu.gob.cl/ | **ChileAtiende:** https://www.chileatiende.gob.cl/
🌐 **Registro Social:** https://www.registrosocial.gob.cl/ | **Clave Única:** https://claveunica.gob.cl/
🌐 **SERVIU Regional:** https://www.serviu.gob.cl/ (seleccionar región)
🌐 **Entidades Patrocinantes:** https://www.minvu.gob.cl/entidades-patrocinantes/
🌐 **Llamados abiertos:** https://www.minvu.gob.cl/llamados/

===========================================
INSTRUCCIONES DE COMPORTAMIENTO
===========================================
1. **Tono:** Profesional, empático, cercano, chileno (uso "usted" o "tú" según contexto)
2. **Precisión:** Solo información verificada en normativas oficiales. Si no sabes, dilo.
3. **Estructura:** Usa emojis 📋🏠✅🔗 para organizar. Viñetas para listas. **Negritas** para datos clave.
4. **Personalización:** Si el usuario da RUT, menciona que puedes consultar estado específico (simulado).
5. **Enlaces:** Siempre incluye enlaces oficiales relevantes al final.
6. **Derivación:** Para trámites complejos, sugiere contactar SERVIU regional o Entidad Patrocinante.
7. **Actualidad:** Menciona que montos/requisitos pueden cambiar por llamados anuales.
8. **Conciso pero completo:** Responde lo preguntado + 1 dato útil extra relacionado.
9. **Nunca inventes:** Si no está en tu conocimiento, deriva a fuentes oficiales.
10. **Idioma:** Español de Chile, términos locales (UF, RSH, EP, MINVU, SERVIU).
"""


# ============================================================
# FACTORY Y GESTIÓN DE PROVEEDORES
# ============================================================

class AIProviderFactory:
    """Factory para crear y gestionar proveedores de IA"""

    _providers: Dict[AIProvider, AIProviderBase] = {}
    _configs: Dict[AIProvider, AIConfig] = {}
    _initialized = False

    @classmethod
    def initialize(cls):
        """Inicializa configuraciones desde settings/env"""
        if cls._initialized:
            return

        # Ollama (Local)
        cls._configs[AIProvider.OLLAMA] = AIConfig(
            provider=AIProvider.OLLAMA,
            base_url=getattr(settings, 'OLLAMA_URL', 'http://localhost:11434'),
            model=getattr(settings, 'OLLAMA_MODEL', 'mistral'),
            timeout=30,
            enabled=True
        )

        # OpenAI
        openai_key = getattr(settings, 'OPENAI_API_KEY', None) or os.getenv('OPENAI_API_KEY')
        cls._configs[AIProvider.OPENAI] = AIConfig(
            provider=AIProvider.OPENAI,
            api_key=openai_key,
            base_url='https://api.openai.com/v1',
            model='gpt-4o-mini',
            timeout=30,
            enabled=bool(openai_key)
        )

        # Anthropic
        anthropic_key = getattr(settings, 'ANTHROPIC_API_KEY', None) or os.getenv('ANTHROPIC_API_KEY')
        cls._configs[AIProvider.ANTHROPIC] = AIConfig(
            provider=AIProvider.ANTHROPIC,
            api_key=anthropic_key,
            base_url='https://api.anthropic.com',
            model='claude-3-5-haiku-20241022',
            timeout=30,
            enabled=bool(anthropic_key)
        )

        # Hugging Face
        hf_key = getattr(settings, 'HUGGINGFACE_API_KEY', None) or os.getenv('HUGGINGFACE_API_KEY')
        cls._configs[AIProvider.HUGGINGFACE] = AIConfig(
            provider=AIProvider.HUGGINGFACE,
            api_key=hf_key,
            model='microsoft/DialoGPT-large',
            timeout=30,
            enabled=bool(hf_key)
        )

        # DeepSeek
        ds_key = getattr(settings, 'DEEPSEEK_API_KEY', None) or os.getenv('DEEPSEEK_API_KEY')
        cls._configs[AIProvider.DEEPSEEK] = AIConfig(
            provider=AIProvider.DEEPSEEK,
            api_key=ds_key,
            base_url='https://api.deepseek.com/v1',
            model='deepseek-chat',
            timeout=30,
            enabled=bool(ds_key)
        )

        # Fallback (siempre disponible)
        cls._configs[AIProvider.FALLBACK] = AIConfig(
            provider=AIProvider.FALLBACK,
            enabled=True
        )

        cls._initialized = True

    @classmethod
    def get_provider(cls, provider: AIProvider) -> AIProviderBase:
        """Obtiene una instancia del proveedor (singleton)"""
        cls.initialize()

        if provider not in cls._providers:
            config = cls._configs.get(provider)
            if not config:
                raise ValueError(f"Proveedor {provider} no configurado")

            provider_map = {
                AIProvider.OLLAMA: OllamaProvider,
                AIProvider.OPENAI: OpenAIProvider,
                AIProvider.ANTHROPIC: AnthropicProvider,
                AIProvider.HUGGINGFACE: HuggingFaceProvider,
                AIProvider.DEEPSEEK: DeepSeekProvider,
                AIProvider.FALLBACK: FallbackProvider,
            }

            provider_class = provider_map.get(provider)
            if not provider_class:
                raise ValueError(f"Proveedor {provider} no implementado")

            cls._providers[provider] = provider_class(config)

        return cls._providers[provider]

    @classmethod
    def get_available_providers(cls) -> List[AIProvider]:
        """Retorna lista de proveedores disponibles en orden de prioridad"""
        cls.initialize()

        # Orden de prioridad configurable via env
        priority_order = [
            AIProvider.OLLAMA,      # Local - prioridad 1 (gratis, privado)
            AIProvider.OPENAI,      # Cloud - prioridad 2
            AIProvider.ANTHROPIC,   # Cloud - prioridad 3
            AIProvider.DEEPSEEK,    # Cloud - prioridad 4
            AIProvider.HUGGINGFACE, # Cloud - prioridad 5
            AIProvider.FALLBACK,    # Siempre último
        ]

        available = []
        for provider in priority_order:
            config = cls._configs.get(provider)
            if config and config.enabled:
                try:
                    instance = cls.get_provider(provider)
                    if instance.is_available():
                        available.append(provider)
                        logger.info(f"Proveedor IA disponible: {provider.value}")
                    else:
                        logger.warning(f"Proveedor IA no disponible: {provider.value}")
                except Exception as e:
                    logger.warning(f"Error verificando {provider.value}: {e}")

        return available


def get_ai_provider_chain() -> List[AIProviderBase]:
    """Retorna la cadena de proveedores disponibles en orden de prioridad"""
    providers = []
    for provider_type in AIProviderFactory.get_available_providers():
        providers.append(AIProviderFactory.get_provider(provider_type))
    return providers


# ============================================================
# FUNCIÓN PRINCIPAL - GENERAR RESPUESTA SERVIU
# ============================================================

def generate_serviu_response(
    user_query: str,
    rut: Optional[str] = None,
    session_id: Optional[str] = None,
    user_ip: Optional[str] = None
) -> tuple[str, str, Optional[int]]:
    """
    Genera respuesta del asistente SERVIU usando cadena de proveedores con fallback.

    Returns:
        tuple: (response_text, session_id, interaction_id)
    """
    start_time = time.time()

    # Generar session_id si no existe
    if not session_id:
        session_id = str(uuid.uuid4())

    # Análisis NLP de la consulta
    question_category = nlp_analyzer.categorize_question(user_query)
    sentiment_score = nlp_analyzer.analyze_sentiment(user_query)

    # Construir prompt con contexto de RUT si existe
    context_addition = ""
    if rut:
        context_addition = f"\n\n[CONTEXTO ADICIONAL] El usuario ha proporcionado su RUT: {rut}. Si pregunta por su estado de postulación o datos personales, indícale que debe consultar directamente en SERVIU o ChileAtiende con su Clave Única."

    full_system_prompt = f"{SERVIU_SYSTEM_PROMPT}{context_addition}"

    # Intentar proveedores en cadena
    response = None
    used_provider = AIProvider.FALLBACK

    for provider in get_ai_provider_chain():
        try:
            logger.info(f"Intentando proveedor: {provider.config.provider.value}")
            response = provider.generate(user_query, full_system_prompt)
            used_provider = provider.config.provider
            logger.info(f"Respuesta generada con: {used_provider.value}")
            break
        except Exception as e:
            logger.warning(f"Error con {provider.config.provider.value}: {e}")
            continue

    # Fallback garantizado
    if not response:
        fallback = AIProviderFactory.get_provider(AIProvider.FALLBACK)
        response = fallback.generate(user_query, full_system_prompt)
        used_provider = AIProvider.FALLBACK

    # Calcular tiempo de respuesta
    response_time = int((time.time() - start_time) * 1000)

    # Guardar interacción en base de datos
    interaction_id = None
    try:
        interaction = ChatInteraction.objects.create(
            session_id=session_id,
            user_question=user_query,
            ai_response=response,
            user_rut=rut,
            user_ip=user_ip,
            response_time_ms=response_time,
            question_category=question_category,
            sentiment_score=sentiment_score
        )
        interaction_id = interaction.id
        logger.info(f"Interacción guardada: ID={interaction_id}, Provider={used_provider.value}, Time={response_time}ms")
    except Exception as e:
        logger.error(f"Error guardando interacción: {e}")

    return response, session_id, interaction_id


# ============================================================
# UTILIDADES ADICIONALES
# ============================================================

def test_all_providers() -> Dict[str, Any]:
    """Prueba todos los proveedores configurados y retorna estado"""
    AIProviderFactory.initialize()
    results = {}

    for provider_type, config in AIProviderFactory._configs.items():
        if not config.enabled:
            results[provider_type.value] = {"enabled": False, "available": False, "error": "Deshabilitado"}
            continue

        try:
            provider = AIProviderFactory.get_provider(provider_type)
            available = provider.is_available()
            results[provider_type.value] = {
                "enabled": True,
                "available": available,
                "model": config.model,
                "base_url": config.base_url
            }
        except Exception as e:
            results[provider_type.value] = {"enabled": True, "available": False, "error": str(e)}

    return results


def get_provider_status() -> Dict[str, Any]:
    """Retorna estado actual de todos los proveedores"""
    return {
        "available_chain": [p.value for p in AIProviderFactory.get_available_providers()],
        "providers": test_all_providers(),
        "fallback_always_available": True
    }