from django.contrib import admin
from import_export.admin import ImportExportModelAdmin
from .models import Beneficiarios
from .resources import BeneficiariosResource

class BeneficiariosAdmin(ImportExportModelAdmin):
    skip_import_confirm = True
    resource_class = BeneficiariosResource
    list_display = ["id_beneficiario", "rut"]


admin.site.register(Beneficiarios, BeneficiariosAdmin)
admin.site.site_header = 'ServiuApp Admin'
admin.site.site_title = 'ServiuApp'
