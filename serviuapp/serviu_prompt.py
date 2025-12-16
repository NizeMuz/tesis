import requests
import json
import time
import uuid
from django.utils import timezone
from django.conf import settings
from .models import ChatInteraction
from .nlp_utils import nlp_analyzer

# Configuración de Ollama
OLLAMA_URL = getattr(settings, 'OLLAMA_URL', 'http://localhost:11434')
OLLAMA_MODEL = getattr(settings, 'OLLAMA_MODEL', 'mistral')

SERVIU_SYSTEM_PROMPT = """
Eres un asistente especializado en SERVIU (Servicio de Vivienda y Urbanización) de Chile. 
Tu objetivo es ayudar a los ciudadanos con información sobre subsidios habitacionales, trámites y beneficios.

INFORMACIÓN OFICIAL:

**SUBSIDIOS PRINCIPALES:**
- DS1 (Sectores Medios): Para familias con capacidad de ahorro, hasta 1.100 UF
- DS49 (Fondo Solidario): Para familias vulnerables (RSH ≤40%), construcción sin crédito

D.S. N° 27: Programa de Mejoramiento de Viviendas y Barrios (Hogar Mejor). 
Tiene tablas de costos específicas para Ñuble (ajustadas a la realidad regional) para proyectos de eficiencia energética y reparación.

Propiedad: Debes ser dueño de la vivienda o asignatario.

Tipo de Vivienda: Debe ser "Vivienda Social" (valor de avalúo fiscal bajo 950 UF) o haber sido construida por Serviu.

Ahorro: Es bajo, generalmente entre 3 UF y 7 UF dependiendo si es para arreglar o ampliar.

RSH: Hasta el 60% (para postulaciones individuales).

Asesoría: No postulas solo; debes buscar una Entidad Patrocinante (EP) o contratista inscrito en el Minvu que haga el proyecto de reparación.




D.S. N° 10: Programa de Habitabilidad Rural. 
Muy relevante en Ñuble dada su alta ruralidad; permite construir o mejorar viviendas en zonas apartadas.

Terreno: Debes acreditar disponibilidad de un terreno (título de dominio, derechos en comunidades, etc.).

RSH: Generalmente piden estar dentro del 60% o 70% (depende del llamado específico).

Ahorro: Varía según el tramo del RSH, pero parte desde las 10 UF para el 40% más vulnerable.

Entidad de Gestión Rural: Necesitas contactar a una entidad (consultora) que arme el proyecto técnico en el terreno.





D.S. N° 19: Programa de Integración Social y Territorial (básicamente proyectos inmobiliarios con subsidio automático).

Ahorro:

Viviendas hasta 1.100 UF: 30 UF.

Viviendas hasta 2.200 UF: 40 UF-

Viviendas sobre 2.200 UF: 80 UF.

RSH: Debes estar dentro del 90%.

Capacidad de Crédito: Deben tener una pre-aprobación bancaria o demostrar que puedes pagar la diferencia (con un crédito hipotecario), a menos que apliques al fondo solidario dentro de este programa (con cupos vulnerables).

Antigüedad: usualmente no piden antigüedad de la cuenta de ahorro si tienes el dinero listo, esto depende de la inmobiliaria.



D.S. N° 52: Subsidio de Arriendo.

Ingresos: Debes demostrar ingresos familiares entre 7 UF y 25 UF.

Ahorro: 4 UF.

RSH: Hasta el 70%.

Cotizaciones: Tener cotizaciones previsionales al día (se revisan para verificar ingresos).

**REQUISITOS GENERALES:**
- Mayor de 18 años
- Cédula de identidad vigente
- No ser propietario de vivienda
- Inscripción en Registro Social de Hogares (RSH)

**DOCUMENTACIÓN COMÚN:**
- Cédula de identidad vigente
- Certificado de ahorro para la vivienda
- Inscripción RSH vigente
- Certificado de matrimonio (si corresponde)

**ENLACES OFICIALES:**
- Portal MINVU: https://www.minvu.gob.cl/
- ChileAtiende: https://www.chileatiende.gob.cl/
- Registro Social: https://www.registrosocial.gob.cl/
- Clave Única: https://claveunica.gob.cl/

**INSTRUCCIONES:**
1. Responde de manera natural y conversacional en español
2. Proporciona información precisa basada en normativas oficiales
3. Para consultas personales, solicita el RUT para verificar datos específicos
4. No inventes información que no esté en este contexto
5. Siempre incluye enlaces oficiales relevantes cuando sea apropiado
6. Sé empático y comprensivo con las consultas de los usuarios
7. Mantén las respuestas concisas pero informativas
8. Usa emojis ocasionalmente para hacer las respuestas más amigables
"""

def generate_serviu_response(user_query, rut=None, session_id=None, user_ip=None):
    start_time = time.time()
    
    # Generar session_id si no existe
    if not session_id:
        session_id = str(uuid.uuid4())
    
    # Análisis NLP de la consulta
    question_category = nlp_analyzer.categorize_question(user_query)
    sentiment_score = nlp_analyzer.analyze_sentiment(user_query)
    
    try:
        # Usar Ollama para generar respuesta natural
        response = generate_ollama_response(user_query, rut)
        
    except Exception as e:
        print(f"Error con Ollama: {e}")
        response = generate_fallback_response(user_query, rut)
    
    # Calcular tiempo de respuesta
    response_time = int((time.time() - start_time) * 1000)
    
    # Guardar interacción en la base de datos
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
        
        return response, session_id, interaction.id
    except Exception as e:
        print(f"Error guardando interacción: {e}")
        return response, session_id, None

def generate_ollama_response(user_query, rut=None):
    """Genera respuesta usando Ollama con Mistral"""
    
    # Contexto adicional si hay RUT
    context_addition = ""
    if rut:
        context_addition = f"\n\nEl usuario ha proporcionado su RUT: {rut}. Puedes hacer referencia a consultas personalizadas."
    
    # Construir el prompt completo
    full_prompt = f"{SERVIU_SYSTEM_PROMPT}{context_addition}\n\nUsuario: {user_query}\n\nAsistente:"
    
    try:
        # Llamada a Ollama API
        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "prompt": full_prompt,
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "top_p": 0.9,
                    "max_tokens": 500
                }
            },
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            return result.get('response', '').strip()
        else:
            print(f"Error Ollama HTTP {response.status_code}: {response.text}")
            return generate_fallback_response(user_query, rut)
            
    except requests.exceptions.RequestException as e:
        print(f"Error conectando con Ollama: {e}")
        return generate_fallback_response(user_query, rut)
    except Exception as e:
        print(f"Error procesando respuesta Ollama: {e}")
        return generate_fallback_response(user_query, rut)

def generate_fallback_response(user_query, rut=None):
    """Respuestas básicas cuando Ollama no está disponible"""
    query_lower = user_query.lower()
    
    if any(saludo in query_lower for saludo in ["hola", "buenos días", "buenas tardes", "buenas noches"]):
        return "¡Hola! 👋 Soy tu asistente de SERVIU. Estoy aquí para ayudarte con información sobre subsidios habitacionales, trámites y beneficios. ¿En qué puedo ayudarte?"
    
    elif "ds1" in query_lower or "sectores medios" in query_lower:
        return """El **Subsidio DS1** está dirigido a sectores medios que quieren comprar una vivienda:

🏠 **Características:**
- Para familias con capacidad de ahorro
- Viviendas hasta 1.100 UF (1.200 UF en zonas extremas)
- Tres tramos según RSH

📋 **Requisitos:**
- Mayor de 18 años
- No ser propietario de vivienda
- Tener ahorro para la vivienda

¿Te gustaría conocer más detalles sobre algún aspecto específico?

Más información: https://www.minvu.gob.cl/"""
    
    elif "ds49" in query_lower or "fondo solidario" in query_lower:
        return """El **Subsidio DS49** (Fondo Solidario) está pensado para familias en situación de vulnerabilidad:

🏠 **Características:**
- Para familias RSH ≤40%
- Construcción sin crédito hipotecario
- Ahorro mínimo 10-15 UF

📋 **Modalidades:**
- Construcción en nuevos terrenos
- Construcción en sitio propio
- Pequeño condominio
- Densificación predial

¿Necesitas información sobre alguna modalidad específica?

Más información: https://www.minvu.gob.cl/"""
    
    elif "documento" in query_lower or "papeles" in query_lower:
        return """📄 **Documentación común para subsidios habitacionales:**

✅ **Obligatorios:**
- Cédula de identidad vigente
- Certificado de ahorro para la vivienda
- Inscripción vigente en el Registro Social de Hogares (RSH)

✅ **Según corresponda:**
- Certificado de matrimonio o unión civil
- Permisos municipales (para obras)
- Documentos notariales
- Certificado de dominio (para sitio propio)

¿Necesitas información específica sobre documentos para algún subsidio en particular?

Más información: https://www.minvu.gob.cl/"""
    
    else:
        return """Puedo ayudarte con información sobre:

🏠 **Subsidios habitacionales:**
- DS1 (Sectores Medios)
- DS49 (Fondo Solidario)
- Requisitos y documentación

📋 **Trámites y consultas:**
- Estados de postulación
- Documentos necesarios
- Procesos de aplicación

¿Sobre qué tema específico te gustaría saber más?

Portal oficial: https://www.minvu.gob.cl/"""

def test_ollama_connection():
    """Función para probar la conexión con Ollama"""
    try:
        response = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        if response.status_code == 200:
            models = response.json().get('models', [])
            model_names = [model.get('name', '') for model in models]
            return True, f"Conectado. Modelos disponibles: {', '.join(model_names)}"
        else:
            return False, f"Error HTTP {response.status_code}"
    except Exception as e:
        return False, f"Error de conexión: {e}"

# Agregar al final del archivo
def generate_huggingface_response(user_query, rut=None):
    import requests
    from django.conf import settings
    
    context_addition = ""
    if rut:
        context_addition = f"\n\nEl usuario ha proporcionado su RUT: {rut}."
    
    full_prompt = f"{SERVIU_SYSTEM_PROMPT}{context_addition}\n\nUsuario: {user_query}\n\nAsistente:"
    
    API_URL = "https://api-inference.huggingface.co/models/microsoft/DialoGPT-large"
    headers = {"Authorization": f"Bearer {settings.HUGGINGFACE_API_KEY}"}
    
    try:
        response = requests.post(API_URL, headers=headers, json={
            "inputs": full_prompt,
            "parameters": {
                "max_length": 500,
                "temperature": 0.7,
                "do_sample": True
            }
        }, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            if isinstance(result, list) and len(result) > 0:
                generated_text = result[0].get('generated_text', '')
                # Extraer solo la respuesta del asistente
                if 'Asistente:' in generated_text:
                    return generated_text.split('Asistente:')[-1].strip()
                return generated_text.strip()
        
        return generate_fallback_response(user_query, rut)
        
    except Exception as e:
        print(f"Error con Hugging Face: {e}")
        return generate_fallback_response(user_query, rut)

# Modificar la función principal
def generate_serviu_response(user_query, rut=None, session_id=None, user_ip=None):
    start_time = time.time()
    
    if not session_id:
        session_id = str(uuid.uuid4())
    
    question_category = nlp_analyzer.categorize_question(user_query)
    sentiment_score = nlp_analyzer.analyze_sentiment(user_query)
    
    # Intentar servicios en orden
    response = None
    
    # 1. Intentar Ollama local (desarrollo)
    if OLLAMA_URL.startswith('http://localhost'):
        try:
            response = generate_ollama_response(user_query, rut)
        except:
            pass
    
    # 2. Usar Hugging Face (producción)
    if not response and hasattr(settings, 'HUGGINGFACE_API_KEY') and settings.HUGGINGFACE_API_KEY:
        response = generate_huggingface_response(user_query, rut)
    
    # 3. Fallback
    if not response:
        response = generate_fallback_response(user_query, rut)
    
    response_time = int((time.time() - start_time) * 1000)
    
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
        
        return response, session_id, interaction.id
    except Exception as e:
        print(f"Error guardando interacción: {e}")
        return response, session_id, None