# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models



class Beneficiarios(models.Model):
    id_beneficiario = models.AutoField(primary_key=True)
    rut = models.CharField(max_length=50)
    dv = models.CharField(max_length=10)
    nombres = models.CharField(max_length=255)
    primer_apellido = models.CharField(max_length=100)
    segundo_apellido = models.CharField(max_length=100, blank=True)
    comuna = models.CharField(max_length=100)
    provincia = models.CharField(max_length=100)
    codigo_proyecto = models.CharField(max_length=100,blank=True)
    nombre_grupo = models.CharField(max_length=255, blank=True)
    sexo = models.CharField(max_length=10, blank=True)

    class Meta:
        managed = True
        db_table = 'beneficiarios'


class Decretos(models.Model):
    id_decreto = models.AutoField(primary_key=True)
    decreto = models.CharField(max_length=10)
    tipologia = models.CharField(max_length=50,blank=True, null=True)
    tramo = models.IntegerField(blank=True, null=True)
    decreto_id_beneficiario = models.ForeignKey(Beneficiarios, on_delete=models.CASCADE, db_column='decreto_id_beneficiario')

    def __str__(self):
        return f"Decreto {self.id_decreto} - Beneficiario {self.decreto_id_beneficiario.id_beneficiario}"


    class Meta:
        managed = True
        db_table = 'decretos'

class Resoluciones(models.Model):
    id_resolucion = models.AutoField(primary_key=True)
    resolucion = models.IntegerField(blank=True,null=True)
    fecha_resolucion = models.DateField(blank=True,null=True)
    seleccion = models.CharField(max_length=50,blank=True,null=True)
    ano_imputacion_res_of = models.IntegerField(blank=True, null=True)
    resolucion_id_beneficiario = models.ForeignKey(Beneficiarios, on_delete=models.CASCADE, db_column='resolucion_id_beneficiario')
    
    def __str__(self):
        return f"Resolucion {self.id_resolucion} - Beneficiario {self.resolucion_id_beneficiario.id_beneficiario}"

    class Meta:
        managed = True
        db_table = 'resoluciones'

class ChatInteraction(models.Model):
    # Información básica de la conversación
    session_id = models.CharField(max_length=100, help_text="ID único de sesión")
    user_question = models.TextField(help_text="Pregunta del usuario")
    ai_response = models.TextField(help_text="Respuesta de la IA")
    timestamp = models.DateTimeField(auto_now_add=True)
    
    # Datos del usuario (opcional)
    user_rut = models.CharField(max_length=50, blank=True, null=True)
    user_ip = models.GenericIPAddressField(blank=True, null=True)
    
    # Métricas de satisfacción
    satisfaction_rating = models.IntegerField(
        choices=[(1, '1 - Muy insatisfecho'), (2, '2 - Insatisfecho'), 
                (3, '3 - Neutral'), (4, '4 - Satisfecho'), (5, '5 - Muy satisfecho')],
        blank=True, null=True
    )
    
    # Análisis automático
    question_category = models.CharField(max_length=100, blank=True, null=True, 
                                       help_text="Categoría automática de la pregunta")
    sentiment_score = models.FloatField(blank=True, null=True, 
                                      help_text="Puntuación de sentimiento (-1 a 1)")
    response_time_ms = models.IntegerField(blank=True, null=True, 
                                         help_text="Tiempo de respuesta en milisegundos")
    
    # Metadatos
    was_helpful = models.BooleanField(blank=True, null=True)
    feedback_text = models.TextField(blank=True, null=True)
    
    class Meta:
        managed = True
        db_table = 'chat_interactions'
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"Chat {self.id} - {self.timestamp.strftime('%Y-%m-%d %H:%M')}"

