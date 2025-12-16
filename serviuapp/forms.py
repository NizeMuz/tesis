from django import forms
from serviuapp.models import Beneficiarios
from serviuapp.models import Resoluciones
from serviuapp.models import Decretos
from datetime import datetime

class FormBeneficiarios(forms.ModelForm):
    SEXO_CHOICES = [
        ('M', 'Masculino'),
        ('F', 'Femenino')
    ]
    
    # Mapear el campo nombres a primer_y_segundo_nombre para el template
    primer_y_segundo_nombre = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label='Primer y segundo nombre'
    )
    
    sexo = forms.ChoiceField(
        choices=SEXO_CHOICES, 
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=False
    )
    
    # Definir opciones estáticas para comuna y provincia de la Región de Ñuble
    COMUNA_CHOICES = [
        ('', 'Seleccione una comuna'),
        ('Chillán', 'Chillán'),
        ('Chillán Viejo', 'Chillán Viejo'),
        ('Bulnes', 'Bulnes'),
        ('El Carmen', 'El Carmen'),
        ('Pemuco', 'Pemuco'),
        ('Pinto', 'Pinto'),
        ('Quillón', 'Quillón'),
        ('San Ignacio', 'San Ignacio'),
        ('Yungay', 'Yungay'),
        ('Cobquecura', 'Cobquecura'),
        ('Coelemu', 'Coelemu'),
        ('Ninhue', 'Ninhue'),
        ('Portezuelo', 'Portezuelo'),
        ('Quirihue', 'Quirihue'),
        ('Ránquil', 'Ránquil'),
        ('Treguaco', 'Treguaco'),
        ('Coihueco', 'Coihueco'),
        ('Ñiquén', 'Ñiquén'),
        ('San Carlos', 'San Carlos'),
        ('San Fabián', 'San Fabián'),
        ('San Nicolás', 'San Nicolás'),
    ]
    
    PROVINCIA_CHOICES = [
        ('', 'Seleccione una provincia'),
        ('Diguillín', 'Diguillín'),
        ('Itata', 'Itata'),
        ('Punilla', 'Punilla'),
    ]
    
    comuna = forms.ChoiceField(
        choices=COMUNA_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    provincia = forms.ChoiceField(
        choices=PROVINCIA_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    class Meta:
        model = Beneficiarios
        fields = ['rut', 'dv', 'primer_apellido', 'segundo_apellido', 'comuna', 'provincia', 'codigo_proyecto', 'nombre_grupo', 'sexo']

    def __init__(self, *args, **kwargs):
        super(FormBeneficiarios, self).__init__(*args, **kwargs)
        
        # Si estamos editando un beneficiario existente, prellenar todos los campos
        if self.instance and self.instance.pk:
            self.fields['primer_y_segundo_nombre'].initial = self.instance.nombres
            # Asegurar que todos los campos mantengan sus valores originales
            if self.instance.sexo:
                self.fields['sexo'].initial = self.instance.sexo
            if self.instance.comuna:
                self.fields['comuna'].initial = self.instance.comuna
            if self.instance.provincia:
                self.fields['provincia'].initial = self.instance.provincia
        
        for field in self.fields.values():
            if field.widget.attrs.get('class') != 'form-control':
                field.widget.attrs.update({'class': 'form-control'})
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Preservar valores existentes si los campos están vacíos
        original_instance = None
        if self.instance and self.instance.pk:
            original_instance = Beneficiarios.objects.get(pk=self.instance.pk)
        
        # Mapear primer_y_segundo_nombre al campo nombres del modelo
        if self.cleaned_data.get('primer_y_segundo_nombre'):
            instance.nombres = self.cleaned_data['primer_y_segundo_nombre']
        elif original_instance:
            instance.nombres = original_instance.nombres
        
        # Preservar otros campos si están vacíos
        if not self.cleaned_data.get('primer_apellido') and original_instance:
            instance.primer_apellido = original_instance.primer_apellido
        
        if not self.cleaned_data.get('segundo_apellido') and original_instance:
            instance.segundo_apellido = original_instance.segundo_apellido
        
        if not self.cleaned_data.get('rut') and original_instance:
            instance.rut = original_instance.rut
        
        if not self.cleaned_data.get('dv') and original_instance:
            instance.dv = original_instance.dv
        
        if not self.cleaned_data.get('sexo') and original_instance:
            instance.sexo = original_instance.sexo
        
        if not self.cleaned_data.get('comuna') and original_instance:
            instance.comuna = original_instance.comuna
        
        if not self.cleaned_data.get('provincia') and original_instance:
            instance.provincia = original_instance.provincia
        
        if not self.cleaned_data.get('codigo_proyecto') and original_instance:
            instance.codigo_proyecto = original_instance.codigo_proyecto
        
        if not self.cleaned_data.get('nombre_grupo') and original_instance:
            instance.nombre_grupo = original_instance.nombre_grupo
        
        if commit:
            instance.save()
        return instance
        
        
        
class FormResoluciones(forms.ModelForm):
    numero_resolucion = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label='Número de resolución',
        required=False
    )
    
    class Meta:
        model = Resoluciones
        fields = ['fecha_resolucion', 'seleccion', 'ano_imputacion_res_of']
        widgets = {
            'fecha_resolucion': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'DD/MM/AAAA'}),
            'seleccion': forms.TextInput(attrs={'class': 'form-control'}),
            'ano_imputacion_res_of': forms.NumberInput(attrs={'class': 'form-control'})
        }
    
    def __init__(self, *args, **kwargs):
        super(FormResoluciones, self).__init__(*args, **kwargs)
        
        # Hacer todos los campos no requeridos para preservar valores existentes
        for field_name, field in self.fields.items():
            field.required = False
        
        # Si estamos editando una resolución existente, prellenar todos los campos
        if self.instance and self.instance.pk:
            self.fields['numero_resolucion'].initial = self.instance.resolucion
            # Asegurar que todos los campos mantengan sus valores originales
            if self.instance.fecha_resolucion:
                # Convertir fecha de YYYY-MM-DD a DD/MM/AAAA para mostrar
                if isinstance(self.instance.fecha_resolucion, str):
                    try:
                        fecha_obj = datetime.strptime(self.instance.fecha_resolucion, '%Y-%m-%d')
                        self.fields['fecha_resolucion'].initial = fecha_obj.strftime('%d/%m/%Y')
                    except ValueError:
                        self.fields['fecha_resolucion'].initial = self.instance.fecha_resolucion
                else:
                    # Si es un objeto date
                    self.fields['fecha_resolucion'].initial = self.instance.fecha_resolucion.strftime('%d/%m/%Y')
            if self.instance.seleccion:
                self.fields['seleccion'].initial = self.instance.seleccion
            if self.instance.ano_imputacion_res_of:
                self.fields['ano_imputacion_res_of'].initial = self.instance.ano_imputacion_res_of
        
        for field in self.fields.values():
            if field.widget.attrs.get('class') != 'form-control':
                field.widget.attrs.update({'class': 'form-control'})
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Preservar valores existentes si los campos están vacíos
        original_instance = None
        if self.instance and self.instance.pk:
            original_instance = Resoluciones.objects.get(pk=self.instance.pk)
        
        # Mapear numero_resolucion al campo resolucion del modelo
        if 'numero_resolucion' in self.cleaned_data:
            if self.cleaned_data['numero_resolucion']:
                try:
                    instance.resolucion = int(self.cleaned_data['numero_resolucion'])
                except (ValueError, TypeError):
                    if original_instance:
                        instance.resolucion = original_instance.resolucion
            elif original_instance:
                instance.resolucion = original_instance.resolucion
        
        # Manejar fecha_resolucion - convertir de DD/MM/AAAA a YYYY-MM-DD
        if self.cleaned_data.get('fecha_resolucion'):
            fecha_input = self.cleaned_data['fecha_resolucion']
            if isinstance(fecha_input, str) and '/' in fecha_input:
                try:
                    # Convertir de DD/MM/AAAA a YYYY-MM-DD
                    fecha_obj = datetime.strptime(fecha_input, '%d/%m/%Y')
                    instance.fecha_resolucion = fecha_obj.strftime('%Y-%m-%d')
                except ValueError:
                    # Si no se puede convertir, mantener el valor original
                    instance.fecha_resolucion = fecha_input
            else:
                instance.fecha_resolucion = fecha_input
        elif original_instance:
            instance.fecha_resolucion = original_instance.fecha_resolucion
        
        # Preservar seleccion si está vacía
        if not self.cleaned_data.get('seleccion') and original_instance:
            instance.seleccion = original_instance.seleccion
        
        # Preservar ano_imputacion_res_of si está vacío
        if not self.cleaned_data.get('ano_imputacion_res_of') and original_instance:
            instance.ano_imputacion_res_of = original_instance.ano_imputacion_res_of
        
        if commit:
            instance.save()
        return instance

        
        
class FormDecretos(forms.ModelForm):
    PROGRAMA_CHOICES = [
        ('', 'Seleccione un programa'),
        ('DS-1', 'DS-1'),
        ('DS-10', 'DS-10'),
        ('DS-19', 'DS-19'),
        ('DS-27', 'DS-27'),
        ('DS-49', 'DS-49'),
        ('DS-52', 'DS-52'),
        ('DS-255', 'DS-255'),
        ('DS-120', 'DS-120'),
    ]
    
    TIPOLOGIA_CHOICES = [
        ('', 'Seleccione una tipología'),
        ('Construcción en sitio propio', 'Construcción en sitio propio'),
        ('Adquisición de vivienda construida', 'Adquisición de vivienda construida'),
        ('Densificación predial', 'Densificación predial'),
        ('Mejoramiento de la vivienda', 'Mejoramiento de la vivienda'),
        ('Ampliación de vivienda', 'Ampliación de vivienda'),
    ]
    
    programa = forms.ChoiceField(
        choices=PROGRAMA_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Programa',
        required=False
    )
    
    tipologia = forms.ChoiceField(
        choices=TIPOLOGIA_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=False
    )
    
    class Meta:
        model = Decretos
        fields = ['programa', 'tipologia', 'tramo']
        widgets = {
            'tramo': forms.NumberInput(attrs={'class': 'form-control'})
        }
    
    def __init__(self, *args, **kwargs):
        super(FormDecretos, self).__init__(*args, **kwargs)
        
        # Si estamos editando un decreto existente, prellenar todos los campos
        if self.instance and self.instance.pk:
            self.fields['programa'].initial = self.instance.decreto
            # Asegurar que tipologia mantenga su valor original
            if self.instance.tipologia:
                self.fields['tipologia'].initial = self.instance.tipologia
        
        for field in self.fields.values():
            if field.widget.attrs.get('class') != 'form-control':
                field.widget.attrs.update({'class': 'form-control'})
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Preservar valores existentes si los campos están vacíos
        original_instance = None
        if self.instance and self.instance.pk:
            original_instance = Decretos.objects.get(pk=self.instance.pk)
        
        # Mapear programa al campo decreto del modelo
        if self.cleaned_data.get('programa'):
            instance.decreto = self.cleaned_data['programa']
        elif original_instance:
            instance.decreto = original_instance.decreto
        
        # Preservar tipologia si está vacía
        if not self.cleaned_data.get('tipologia') and original_instance:
            instance.tipologia = original_instance.tipologia
        
        # Preservar tramo si está vacío
        if not self.cleaned_data.get('tramo') and original_instance:
            instance.tramo = original_instance.tramo
        
        if commit:
            instance.save()
        return instance