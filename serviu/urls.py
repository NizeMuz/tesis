"""

URL configuration for serviu project.



The `urlpatterns` list routes URLs to views. For more information please see:

    https://docs.djangoproject.com/en/4.2/topics/http/urls/

Examples:

Function views

    1. Add an import:  from my_app import views

    2. Add a URL to urlpatterns:  path('', views.home, name='home')

Class-based views

    1. Add an import:  from other_app.views import Home

    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')

Including another URLconf

    1. Import the include() function: from django.urls import include, path

    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))

"""

from django.contrib import admin

from django.urls import path, include

from django.http import HttpResponse

from django.contrib.auth import views as auth_views

from serviuapp.views import dashboard, filtros, BeneficiariosLista, Busqueda, actualizarBeneficiarios, anadirBeneficiario, actualizarBeneficiarioDecreto, actualizarBeneficiarioResolucion,logs_view,limpiar_logs, get_chart_data, ChatView, nlp_analytics_dashboard, api_analyze_text



def healthcheck(request):

    return HttpResponse("OK", status=200)



urlpatterns = [

    path('admin/', admin.site.urls),

    path('accounts/login/', auth_views.LoginView.as_view(template_name='admin/login.html'), name='login'),

    path('accounts/logout/', auth_views.LogoutView.as_view(next_page='/'), name='logout'),

    path('', dashboard, name="dashboard"),

    path('filtros/', filtros, name="filtros"),

    path('beneficiarios/', BeneficiariosLista, name="beneficiarios"),

    path('beneficiarios/anadir_beneficiario/', anadirBeneficiario, name="anadir_beneficiario"),

    path('beneficiarios/busqueda', Busqueda, name="busqueda"),

    path('chart_data/<str:decreto>/', get_chart_data, name='chart_data'),

    path('beneficiarios/actualizar_beneficiario/<int:id_beneficiario>', actualizarBeneficiarios, name="actualizar_beneficiario"),

    path('beneficiarios/actualizar_beneficiario/actualizar_decreto/<int:id_decreto>', actualizarBeneficiarioDecreto, name="actualizar_decreto"),

    path('healthcheck/', healthcheck, name='healthcheck'),

    path('beneficiarios/actualizar_beneficiario/actualizar_resolucion/<int:id_resolucion>', actualizarBeneficiarioResolucion, name="actualizar_resolucion"),

    path('logs/', logs_view, name='logs_view'),

    path('beneficiarios/logs/', logs_view, name='logs_view'),

    path('limpiar-logs/', limpiar_logs, name='limpiar_logs'),

    path('chat/', ChatView.as_view(), name='chat'),

    path('nlp-dashboard/', nlp_analytics_dashboard, name='nlp_dashboard'),

    path('api/analyze-text/', api_analyze_text, name='api_analyze_text'),

]



