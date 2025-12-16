import re
import string
from collections import Counter
from django.db.models import Count, Q
from .models import ChatInteraction

class NLPAnalyzer:
    """Clase para análisis de lenguaje natural de consultas SERVIU"""
    
    def __init__(self):
        # Palabras clave por categoría
        self.categories = {
            'subsidios': {
                'keywords': ['subsidio', 'ds49', 'ds1', 'fondo solidario', 'sectores medios', 
                           'postulacion', 'postular', 'beneficio', 'vivienda'],
                'weight': 2
            },
            'tramites': {
                'keywords': ['trámite', 'tramite', 'documentos', 'requisitos', 'proceso',
                           'como hacer', 'pasos', 'procedimiento'],
                'weight': 2
            },
            'cuenta_ahorro': {
                'keywords': ['cuenta', 'ahorro', 'desbloqueo', 'bloqueo', 'saldo',
                           'libreta', 'banco'],
                'weight': 2
            },
            'consulta_personal': {
                'keywords': ['rut', 'mi situacion', 'mis subsidios', 'mi cuenta',
                           'mi tramite', 'estado', 'consultar'],
                'weight': 3
            },
            'informacion_general': {
                'keywords': ['que es', 'como funciona', 'informacion', 'explicar',
                           'serviu', 'minvu'],
                'weight': 1
            },
            'problemas_reclamos': {
                'keywords': ['problema', 'error', 'reclamo', 'queja', 'no funciona',
                           'ayuda', 'soporte'],
                'weight': 2
            },
            'saludo_despedida': {
                'keywords': ['hola', 'buenos dias', 'buenas tardes', 'gracias',
                           'adios', 'chao'],
                'weight': 1
            }
        }
        
        # Palabras de sentimiento
        self.sentiment_words = {
            'positive': ['gracias', 'excelente', 'bueno', 'perfecto', 'útil', 'genial',
                        'fantástico', 'increíble', 'maravilloso', 'satisfecho'],
            'negative': ['malo', 'terrible', 'horrible', 'pésimo', 'no sirve', 'problema',
                        'error', 'molesto', 'frustrado', 'enojado', 'decepcionado']
        }
        
        # Palabras vacías en español
        self.stop_words = {
            'el', 'la', 'de', 'que', 'y', 'a', 'en', 'un', 'es', 'se', 'no', 'te',
            'lo', 'le', 'da', 'su', 'por', 'son', 'con', 'para', 'al', 'del', 'los',
            'las', 'una', 'como', 'pero', 'sus', 'me', 'ya', 'o', 'si', 'porque',
            'esta', 'entre', 'cuando', 'muy', 'sin', 'sobre', 'ser', 'tiene', 'le',
            'todo', 'esta', 'tambien', 'fue', 'había', 'han', 'hay'
        }
    
    def preprocess_text(self, text):
        """Preprocesa el texto para análisis"""
        if not text:
            return ""
        
        # Convertir a minúsculas
        text = text.lower()
        
        # Remover puntuación
        text = text.translate(str.maketrans('', '', string.punctuation))
        
        # Remover números
        text = re.sub(r'\d+', '', text)
        
        # Remover espacios extra
        text = ' '.join(text.split())
        
        return text
    
    def categorize_question(self, question):
        """Categoriza automáticamente las preguntas usando palabras clave ponderadas"""
        if not question:
            return 'otros'
        
        processed_text = self.preprocess_text(question)
        category_scores = {}
        
        for category, data in self.categories.items():
            score = 0
            keywords = data['keywords']
            weight = data['weight']
            
            for keyword in keywords:
                if keyword in processed_text:
                    score += weight
            
            if score > 0:
                category_scores[category] = score
        
        if category_scores:
            return max(category_scores, key=category_scores.get)
        
        return 'otros'
    
    def analyze_sentiment(self, text):
        """Analiza el sentimiento del texto (-1 a 1)"""
        if not text:
            return 0.0
        
        processed_text = self.preprocess_text(text)
        words = processed_text.split()
        
        positive_count = 0
        negative_count = 0
        
        for word in words:
            if word in self.sentiment_words['positive']:
                positive_count += 1
            elif word in self.sentiment_words['negative']:
                negative_count += 1
        
        total_sentiment_words = positive_count + negative_count
        
        if total_sentiment_words == 0:
            return 0.0
        
        # Calcular score normalizado
        sentiment_score = (positive_count - negative_count) / total_sentiment_words
        
        # Ajustar intensidad basada en palabras intensificadoras
        intensifiers = ['muy', 'super', 'extremadamente', 'totalmente']
        for intensifier in intensifiers:
            if intensifier in processed_text:
                sentiment_score *= 1.5
                break
        
        # Limitar entre -1 y 1
        return max(-1.0, min(1.0, sentiment_score))
    
    def extract_keywords(self, text, top_n=10):
        """Extrae las palabras clave más importantes del texto"""
        if not text:
            return []
        
        processed_text = self.preprocess_text(text)
        words = [word for word in processed_text.split() 
                if word not in self.stop_words and len(word) > 2]
        
        word_freq = Counter(words)
        return word_freq.most_common(top_n)
    
    def get_question_similarity(self, question1, question2):
        """Calcula la similitud entre dos preguntas usando Jaccard"""
        if not question1 or not question2:
            return 0.0
        
        words1 = set(self.preprocess_text(question1).split())
        words2 = set(self.preprocess_text(question2).split())
        
        # Remover palabras vacías
        words1 = words1 - self.stop_words
        words2 = words2 - self.stop_words
        
        if not words1 or not words2:
            return 0.0
        
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        return intersection / union if union > 0 else 0.0
    
    def find_similar_questions(self, question, threshold=0.3, limit=5):
        """Encuentra preguntas similares en la base de datos"""
        similar_questions = []
        
        # Obtener todas las preguntas de la base de datos
        all_interactions = ChatInteraction.objects.all()[:1000]  # Limitar para performance
        
        for interaction in all_interactions:
            similarity = self.get_question_similarity(question, interaction.user_question)
            
            if similarity >= threshold:
                similar_questions.append({
                    'interaction': interaction,
                    'similarity': similarity
                })
        
        # Ordenar por similitud y limitar resultados
        similar_questions.sort(key=lambda x: x['similarity'], reverse=True)
        return similar_questions[:limit]
    
    def get_category_statistics(self):
        """Obtiene estadísticas por categoría"""
        stats = ChatInteraction.objects.values('question_category').annotate(
            count=Count('id')
        ).order_by('-count')
        
        return list(stats)
    
    def get_sentiment_trends(self, days=30):
        """Obtiene tendencias de sentimiento en los últimos días"""
        from django.utils import timezone
        from datetime import timedelta
        
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)
        
        interactions = ChatInteraction.objects.filter(
            timestamp__range=[start_date, end_date],
            sentiment_score__isnull=False
        )
        
        # Usar umbral ±0.1 para que coincida con las etiquetas del dashboard
        positive = interactions.filter(sentiment_score__gt=0.1).count()
        neutral = interactions.filter(sentiment_score__gte=-0.1, sentiment_score__lte=0.1).count()
        negative = interactions.filter(sentiment_score__lt=-0.1).count()
        
        total = positive + neutral + negative
        if total == 0:
            return {'positive': 0, 'neutral': 0, 'negative': 0}
        return {
            'positive': round((positive / total) * 100, 2),
            'neutral': round((neutral / total) * 100, 2),
            'negative': round((negative / total) * 100, 2)
        }
    
    def analyze_frequent_patterns(self, min_frequency=3):
        """Analiza patrones frecuentes en las preguntas"""
        all_questions = ChatInteraction.objects.values_list('user_question', flat=True)
        
        # Extraer todas las palabras clave
        all_keywords = []
        for question in all_questions:
            keywords = self.extract_keywords(question, top_n=5)
            all_keywords.extend([kw[0] for kw in keywords])
        
        # Contar frecuencias
        keyword_freq = Counter(all_keywords)
        frequent_patterns = keyword_freq.most_common(20)
        
        # Filtrar por frecuencia mínima
        return [(word, freq) for word, freq in frequent_patterns if freq >= min_frequency]

# Instancia global del analizador
nlp_analyzer = NLPAnalyzer()