from django.shortcuts import render, redirect, get_object_or_404
from tablib import Dataset
from django.http import HttpResponse, JsonResponse
from import_export import resources
from django.db import connection
from django.core.paginator import Paginator
from serviuapp.forms import FormBeneficiarios, FormDecretos, FormResoluciones
from serviuapp.models import Beneficiarios, Resoluciones, Decretos, ChatInteraction
from django.urls import reverse
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.views import View
from django.utils import timezone
from .nlp_utils import nlp_analyzer
import os
import re
import json
import requests


def limpiar_logs(request, log_filename='app.log'):
    log_file_path = os.path.join(settings.BASE_DIR, 'logs', log_filename)
    
    # Limpia el contenido del archivo de logs
    with open(log_file_path, 'w'):
        pass  # Esto borra el contenido del archivo de logs

    # Redirige a la página de importación de beneficiarios
    return redirect('../admin/serviuapp/beneficiarios/import/')

def logs_view(request, log_filename='app.log'):
    log_file_path = os.path.join(settings.BASE_DIR, 'logs', log_filename)

    try:
        with open(log_file_path, 'r') as log_file:
            log_content = log_file.readlines()  # Leemos líneas en lugar de todo el contenido como una cadena
    except FileNotFoundError:
        log_content = ['El archivo de logs no se encontró.']

    return render(request, 'serviutemplate/logs.html', {'log_content': log_content})


def dashboard(request):
    # Procesar filtros
    comunas_filtro = request.GET.getlist('comunas')
    provincias_filtro = request.GET.getlist('provincias')
    ano_imputacion_filtro = request.GET.getlist('ano_imputacion')

    base_query = """
        SELECT * FROM beneficiarios b 
        LEFT JOIN resoluciones r ON b.id_beneficiario = r.resolucion_id_beneficiario 
        LEFT JOIN decretos d ON b.id_beneficiario = d.decreto_id_beneficiario
    """
    filters = []
    params = []

    if comunas_filtro:
        filters.append("b.comuna IN ({})".format(','.join(['%s'] * len(comunas_filtro))))
        params.extend(comunas_filtro)

    if provincias_filtro:
        filters.append("b.provincia IN ({})".format(','.join(['%s'] * len(provincias_filtro))))
        params.extend(provincias_filtro)
        
    if ano_imputacion_filtro:
        filters.append("r.ano_imputacion_res_of IN ({})".format(','.join(['%s'] * len(ano_imputacion_filtro))))
        params.extend(ano_imputacion_filtro)

    # Construir la consulta SQL con o sin filtros
    if filters:
        filter_sql = " WHERE " + " AND ".join(filters)
    else:
        filter_sql = ""

    with connection.cursor() as cursor:
        ##### CONSULTAS DS1 #####
        # Arriendo Glosa 03
        ag_ds1_query = f"SELECT COUNT(*) FROM ({base_query + filter_sql}) AS subquery WHERE tipologia = 'arriendo glosa 03' AND decreto = 'DS-1'"
        cursor.execute(ag_ds1_query, params)
        ag_ds1 = cursor.fetchone()[0]

        # AVC
        avc_ds1_query = f"SELECT COUNT(*) FROM ({base_query + filter_sql}) AS subquery WHERE tipologia = 'avc' AND decreto = 'DS-1'"
        cursor.execute(avc_ds1_query, params)
        avc_ds1 = cursor.fetchone()[0]
        
        # CSP
        csp_ds1_query = f"SELECT COUNT(*) FROM ({base_query + filter_sql}) AS subquery WHERE tipologia = 'CSP' AND decreto = 'DS-1'"
        cursor.execute(csp_ds1_query, params)
        csp_ds1 = cursor.fetchone()[0]
        
        # Blancos
        blanco_ds1_query = f"SELECT COUNT(*) FROM ({base_query + filter_sql}) AS subquery WHERE (tipologia = '' OR tipologia IS NULL) AND decreto = 'DS-1'"
        cursor.execute(blanco_ds1_query, params)
        blanco_ds1 = cursor.fetchone()[0]

        total_count_ds1 = ag_ds1 + avc_ds1 + csp_ds1 + blanco_ds1





        ##### CONSULTAS DS10 #####
        # CCH
        cch_ds10_query = f"SELECT COUNT(*) FROM ({base_query + filter_sql}) AS subquery WHERE tipologia = 'CCH' AND decreto = 'DS-10'"
        cursor.execute(cch_ds10_query, params)
        cch_ds10 = cursor.fetchone()[0]

        # CSR
        csr_ds10_query = f"SELECT COUNT(*) FROM ({base_query + filter_sql}) AS subquery WHERE tipologia = 'CSR' AND decreto = 'DS-10'"
        cursor.execute(csr_ds10_query, params)
        csr_ds10 = cursor.fetchone()[0]

        # MAVE
        mave_ds10_query = f"SELECT COUNT(*) FROM ({base_query + filter_sql}) AS subquery WHERE tipologia = 'MAVE' AND decreto = 'DS-10'"
        cursor.execute(mave_ds10_query, params)
        mave_ds10 = cursor.fetchone()[0]

        # Blancos DS-10
        blanco_ds10_query = f"SELECT COUNT(*) FROM ({base_query + filter_sql}) AS subquery WHERE (tipologia = '' OR tipologia IS NULL) AND decreto = 'DS-10'"
        cursor.execute(blanco_ds10_query, params)
        blanco_ds10 = cursor.fetchone()[0]
        total_count_ds10 = cch_ds10 + csr_ds10 + mave_ds10 + blanco_ds10

        ##### CONSULTAS DS19 #####
        # PIST
        pist_ds19_query = f"SELECT COUNT(*) FROM ({base_query + filter_sql}) AS subquery WHERE tipologia = 'PIST' AND decreto = 'DS-19'"
        cursor.execute(pist_ds19_query, params)
        pist_ds19 = cursor.fetchone()[0]

        # Blancos DS-19
        blanco_ds19_query = f"SELECT COUNT(*) FROM ({base_query + filter_sql}) AS subquery WHERE (tipologia = '' OR tipologia IS NULL) AND decreto = 'DS-19'"
        cursor.execute(blanco_ds19_query, params)
        blanco_ds19 = cursor.fetchone()[0]

        total_count_ds19 = pist_ds19 + blanco_ds19

        ##### CONSULTAS DS27 #####
        # CAP I
        cap1_ds27_query = f"SELECT COUNT(*) FROM ({base_query + filter_sql}) AS subquery WHERE tipologia = 'CAP I' AND decreto = 'DS-27'"
        cursor.execute(cap1_ds27_query, params)
        cap1_ds27 = cursor.fetchone()[0]

        # CAP II
        cap2_ds27_query = f"SELECT COUNT(*) FROM ({base_query + filter_sql}) AS subquery WHERE tipologia = 'CAP II' AND decreto = 'DS-27'"
        cursor.execute(cap2_ds27_query, params)
        cap2_ds27 = cursor.fetchone()[0]

        # CAP III
        cap3_ds27_query = f"SELECT COUNT(*) FROM ({base_query + filter_sql}) AS subquery WHERE tipologia = 'CAP III' AND decreto = 'DS-27'"
        cursor.execute(cap3_ds27_query, params)
        cap3_ds27 = cursor.fetchone()[0]

        # Blancos DS-27
        blanco_ds27_query = f"SELECT COUNT(*) FROM ({base_query + filter_sql}) AS subquery WHERE (tipologia = '' OR tipologia IS NULL) AND decreto = 'DS-27'"
        cursor.execute(blanco_ds27_query, params)
        blanco_ds27 = cursor.fetchone()[0]

        total_count_ds27 = cap1_ds27 + cap2_ds27 + cap3_ds27 + blanco_ds27





        ##### CONSULTAS DS49 #####
        # AVC
        avc_ds49_query = f"SELECT COUNT(*) FROM ({base_query + filter_sql}) AS subquery WHERE tipologia = 'AVC' AND decreto = 'DS-49'"
        cursor.execute(avc_ds49_query, params)
        avc_ds49 = cursor.fetchone()[0]

        # CNT
        cnt_ds49_query = f"SELECT COUNT(*) FROM ({base_query + filter_sql}) AS subquery WHERE tipologia = 'CNT' AND decreto = 'DS-49'"
        cursor.execute(cnt_ds49_query, params)
        cnt_ds49 = cursor.fetchone()[0]

        # CNT INDUST
        cnti_ds49_query = f"SELECT COUNT(*) FROM ({base_query + filter_sql}) AS subquery WHERE tipologia = 'CNT INDUST' AND decreto = 'DS-49'"
        cursor.execute(cnti_ds49_query, params)
        cnti_ds49 = cursor.fetchone()[0]

        # CSP
        csp_ds49_query = f"SELECT COUNT(*) FROM ({base_query + filter_sql}) AS subquery WHERE tipologia = 'CSP' AND decreto = 'DS-49'"
        cursor.execute(csp_ds49_query, params)
        csp_ds49 = cursor.fetchone()[0]

        # Blancos DS-49
        blanco_ds49_query = f"SELECT COUNT(*) FROM ({base_query + filter_sql}) AS subquery WHERE (tipologia = '' OR tipologia IS NULL) AND decreto = 'DS-49'"
        cursor.execute(blanco_ds49_query, params)
        blanco_ds49 = cursor.fetchone()[0]

        total_count_ds49 = avc_ds49 + cnt_ds49 + cnti_ds49 + csp_ds49 + blanco_ds49

        ##### CONSULTAS DS52 #####
        # ARRIENDO
        arriendo_ds52_query = f"SELECT COUNT(*) FROM ({base_query + filter_sql}) AS subquery WHERE tipologia = 'ARRIENDO' AND decreto = 'DS-52'"
        cursor.execute(arriendo_ds52_query, params)
        arriendo_ds52 = cursor.fetchone()[0]

        # Blancos DS-52
        blanco_ds52_query = f"SELECT COUNT(*) FROM ({base_query + filter_sql}) AS subquery WHERE (tipologia = '' OR tipologia IS NULL) AND decreto = 'DS-52'"
        cursor.execute(blanco_ds52_query, params)
        blanco_ds52 = cursor.fetchone()[0]

        total_count_ds52 = arriendo_ds52 + blanco_ds52





        ##### CONSULTAS DS255 #####
        # CALEFACTOR
        calefactor_ds255_query = f"SELECT COUNT(*) FROM ({base_query + filter_sql}) AS subquery WHERE tipologia = 'CALEFACTOR' AND decreto = 'DS-255'"
        cursor.execute(calefactor_ds255_query, params)
        calefactor_ds255 = cursor.fetchone()[0]

        # CC.SS
        ccss_ds255_query = f"SELECT COUNT(*) FROM ({base_query + filter_sql}) AS subquery WHERE tipologia = 'CC.SS' AND decreto = 'DS-255'"
        cursor.execute(ccss_ds255_query, params)
        ccss_ds255 = cursor.fetchone()[0]
        
        # COLECTOR
        colector_ds255_query = f"SELECT COUNT(*) FROM ({base_query + filter_sql}) AS subquery WHERE tipologia = 'colector' AND decreto = 'DS-255'"
        cursor.execute(colector_ds255_query, params)
        colector_ds255 = cursor.fetchone()[0]

        # FOTOVOLTAICO
        fotov_ds255_query = f"SELECT COUNT(*) FROM ({base_query + filter_sql}) AS subquery WHERE tipologia = 'FOTOVOLTAICO' AND decreto = 'DS-255'"
        cursor.execute(fotov_ds255_query, params)
        fotov_ds255 = cursor.fetchone()[0]

        # MEJORAMIENTO
        mejoramiento_ds255_query = f"SELECT COUNT(*) FROM ({base_query + filter_sql}) AS subquery WHERE tipologia = 'MEJORAMIENTO' AND decreto = 'DS-255'"
        cursor.execute(mejoramiento_ds255_query, params)
        mejoramiento_ds255 = cursor.fetchone()[0]

        # PDA
        pda_ds255_query = f"SELECT COUNT(*) FROM ({base_query + filter_sql}) AS subquery WHERE tipologia = 'PDA' AND decreto = 'DS-255'"
        cursor.execute(pda_ds255_query, params)
        pda_ds255 = cursor.fetchone()[0]

        # TBM
        tbm_ds255_query = f"SELECT COUNT(*) FROM ({base_query + filter_sql}) AS subquery WHERE tipologia = 'TBM' AND decreto = 'DS-255'"
        cursor.execute(tbm_ds255_query, params)
        tbm_ds255 = cursor.fetchone()[0]

        # TÉRMICO
        termico_ds255_query = f"SELECT COUNT(*) FROM ({base_query + filter_sql}) AS subquery WHERE tipologia = 'TÉRMICO' AND decreto = 'DS-255'"
        cursor.execute(termico_ds255_query, params)
        termico_ds255 = cursor.fetchone()[0]

        # TÉRMICO PDA
        termicopda_ds255_query = f"SELECT COUNT(*) FROM ({base_query + filter_sql}) AS subquery WHERE tipologia = 'TÉRMICO PDA' AND decreto = 'DS-255'"
        cursor.execute(termicopda_ds255_query, params)
        termicopda_ds255 = cursor.fetchone()[0]

        # Blancos DS-255
        blanco_ds255_query = f"SELECT COUNT(*) FROM ({base_query + filter_sql}) AS subquery WHERE (tipologia = '' OR tipologia IS NULL) AND decreto = 'DS-255'"
        cursor.execute(blanco_ds255_query, params)
        blanco_ds255 = cursor.fetchone()[0]

        total_count_ds255 = calefactor_ds255 + ccss_ds255 + colector_ds255 + fotov_ds255 + mejoramiento_ds255 + pda_ds255 + tbm_ds255 + termico_ds255 + termicopda_ds255 + blanco_ds255

        ##### CONSULTAS LEASING (DS-120) #####
        # AVC
        avc_leasing_query = f"SELECT COUNT(*) FROM ({base_query + filter_sql}) AS subquery WHERE tipologia = 'AVC' AND decreto = 'DS-120'"
        cursor.execute(avc_leasing_query, params)
        avc_leasing = cursor.fetchone()[0]





    
# Pasar los datos al contexto de la plantilla
    context = {
        # DETALLE DS-1
        'ag_ds1': ag_ds1,
        'avc_ds1': avc_ds1,
        'csp_ds1': csp_ds1,
        'blanco_ds1': blanco_ds1,
        'total_count_ds1': total_count_ds1,

        
        # DETALLE DS-10
        'cch_ds10': cch_ds10,
        'csr_ds10': csr_ds10,
        'mave_ds10': mave_ds10,
        'blanco_ds10': blanco_ds10,  
        'total_count_ds10': total_count_ds10,


        # DETALLE DS-19
        'pist_ds19': pist_ds19,
        'blanco_ds19': blanco_ds19,
        'total_count_ds19':total_count_ds19,  

        # DETALLE DS-27
        'cap1_ds27': cap1_ds27,
        'cap2_ds27': cap2_ds27,
        'cap3_ds27': cap3_ds27,
        'blanco_ds27': blanco_ds27, 
        'total_count_ds27': total_count_ds27,


        # DETALLE DS-49
        'avc_ds49': avc_ds49,
        'cnt_ds49': cnt_ds49,
        'cnti_ds49': cnti_ds49,
        'csp_ds49': csp_ds49,
        'blanco_ds49': blanco_ds49,  
        'total_count_ds49': total_count_ds49,


        # DETALLE DS-52
        'arriendo_ds52': arriendo_ds52,
        'blanco_ds52': blanco_ds52,
        'total_count_ds52': total_count_ds52,
    

        # DETALLE DS-255
        'calefactor_ds255': calefactor_ds255,
        'ccss_ds255': ccss_ds255,
        'colector_ds255': colector_ds255,
        'fotov_ds255': fotov_ds255,
        'mejoramiento_ds255': mejoramiento_ds255,
        'pda_ds255': pda_ds255,
        'tbm_ds255': tbm_ds255,
        'termico_ds255': termico_ds255,
        'termicopda_ds255': termicopda_ds255,
        'blanco_ds255': blanco_ds255,  
        'total_count_ds255': total_count_ds255,


        # DETALLE LEASING
        'avc_leasing': avc_leasing,
        
        # FILTROS SELECCIONADOS
        'selected_comunas': comunas_filtro,
        'selected_provincias': provincias_filtro,
        'selected_anos': ano_imputacion_filtro,
    
    }

    
    return render(request, 'serviutemplate/dashboard.html', context)





def filtros(request):
    comunas_filtro = request.GET.getlist('comunas')
    provincias_filtro = request.GET.getlist('provincias')
    ano_imputacion_filtro = request.GET.getlist('ano_imputacion')

    base_query = """
        SELECT * FROM beneficiarios b 
        LEFT JOIN resoluciones r ON b.id_beneficiario = r.resolucion_id_beneficiario 
        LEFT JOIN decretos d ON b.id_beneficiario = d.decreto_id_beneficiario
    """
    filters = []
    params = []

    if comunas_filtro:
        filters.append("b.comuna IN ({})".format(','.join(['%s'] * len(comunas_filtro))))
        params.extend(comunas_filtro)

    if provincias_filtro:
        filters.append("b.provincia IN ({})".format(','.join(['%s'] * len(provincias_filtro))))
        params.extend(provincias_filtro)
        
    if ano_imputacion_filtro:
        filters.append("r.ano_imputacion_res_of IN ({})".format(','.join(['%s'] * len(ano_imputacion_filtro))))
        params.extend(ano_imputacion_filtro)

    # Construir la consulta SQL con o sin filtros
    if filters:
        filter_sql = " WHERE " + " AND ".join(filters)
        sql_query = base_query + filter_sql
    else:
        filter_sql = ""
        sql_query = base_query
        
    #CONSULTAS DS-1
    ds1_avc_count_query = f"SELECT COUNT(*) FROM ({base_query + filter_sql}) AS subquery WHERE tipologia = 'AVC' AND decreto = 'DS-1'"
    ds1_arriendog3_count_query = f"SELECT COUNT(*) FROM ({base_query + filter_sql}) AS subquery WHERE tipologia = 'ARRIENDO GLOSA 03' AND decreto = 'DS-1'"
    ds1_csp_count_query = f"SELECT COUNT(*) FROM ({base_query + filter_sql}) AS subquery WHERE tipologia = 'CSP' AND decreto = 'DS-1'"
    
    
    
    
    #CONSULTAS DS-10
    ds10_cch_count_query = f"SELECT COUNT(*) FROM ({base_query + filter_sql}) AS subquery WHERE tipologia = 'CCH' AND decreto = 'DS-10'"
    ds10_csr_count_query = f"SELECT COUNT(*) FROM ({base_query + filter_sql}) AS subquery WHERE tipologia = 'CSR' AND decreto = 'DS-10'"
    ds10_mave_count_query = f"SELECT COUNT(*) FROM ({base_query + filter_sql}) AS subquery WHERE tipologia = 'MAVE' AND decreto = 'DS-10'"
    
    
    
    
    #CONSULTAS DS-19
    ds19_pist_count_query = f"SELECT COUNT(*) FROM ({base_query + filter_sql}) AS subquery WHERE tipologia = 'PIST' AND decreto = 'DS-19'"
    
    
    
    #CONSULTAS DS-27
    ds27_cap1_count_query = f"SELECT COUNT(*) FROM ({base_query + filter_sql}) AS subquery WHERE tipologia = 'CAP I' AND decreto = 'DS-27'"
    ds27_cap2_count_query = f"SELECT COUNT(*) FROM ({base_query + filter_sql}) AS subquery WHERE tipologia = 'CAP II' AND decreto = 'DS-27'"
    ds27_cap3_count_query = f"SELECT COUNT(*) FROM ({base_query + filter_sql}) AS subquery WHERE tipologia = 'CAP III' AND decreto = 'DS-27'"
    
    
    
    
    #CONSULTAS DS-49
    ds49_avc_count_query = f"SELECT COUNT(*) FROM ({base_query + filter_sql}) AS subquery WHERE tipologia = 'AVC' AND decreto = 'DS-49'"
    ds49_cnt_count_query = f"SELECT COUNT(*) FROM ({base_query + filter_sql}) AS subquery WHERE tipologia = 'CNT' AND decreto = 'DS-49'"
    ds49_cnti_count_query = f"SELECT COUNT(*) FROM ({base_query + filter_sql}) AS subquery WHERE tipologia = 'CNT INDUST' AND decreto = 'DS-49'"
    ds49_csp_count_query = f"SELECT COUNT(*) FROM ({base_query + filter_sql}) AS subquery WHERE tipologia = 'CSP' AND decreto = 'DS-49'"
    
    
    
    
    #CONSULTAS DS-52
    ds52_arriendo_count_query = f"SELECT COUNT(*) FROM ({base_query + filter_sql}) AS subquery WHERE tipologia = 'ARRIENDO' AND decreto = 'DS-52'"
    
    
    
    #CONSULTAS DS-255
    ds255_calefactor_count_query = f"SELECT COUNT(*) FROM ({base_query + filter_sql}) AS subquery WHERE tipologia = 'CALEFACTOR' AND decreto = 'DS-255'"
    ds255_ccss_count_query = f"SELECT COUNT(*) FROM ({base_query + filter_sql}) AS subquery WHERE tipologia = 'CC.SS' AND decreto = 'DS-255'"
    ds255_colector_count_query = f"SELECT COUNT(*) FROM ({base_query + filter_sql}) AS subquery WHERE tipologia = 'COLECTOR' AND decreto = 'DS-255'"
    ds255_fotov_count_query = f"SELECT COUNT(*) FROM ({base_query + filter_sql}) AS subquery WHERE tipologia = 'FOTOVOLTAICO' AND decreto = 'DS-255'"
    ds255_mejoramiento_count_query = f"SELECT COUNT(*) FROM ({base_query + filter_sql}) AS subquery WHERE tipologia = 'MEJORAMIENTO' AND decreto = 'DS-255'"
    ds255_pda_count_query = f"SELECT COUNT(*) FROM ({base_query + filter_sql}) AS subquery WHERE tipologia = 'PDA' AND decreto = 'DS-255'"
    ds255_tbm_count_query = f"SELECT COUNT(*) FROM ({base_query + filter_sql}) AS subquery WHERE tipologia = 'TBM' AND decreto = 'DS-255'"
    ds255_termico_count_query = f"SELECT COUNT(*) FROM ({base_query + filter_sql}) AS subquery WHERE tipologia = 'TERMICO' AND decreto = 'DS-255'"
    ds255_termicopda_count_query = f"SELECT COUNT(*) FROM ({base_query + filter_sql}) AS subquery WHERE tipologia = 'TÉRMICO PDA' AND decreto = 'DS-255'"

    
    
    
    #CONSULTAS LEASING
    ls_avc_count_query = f"SELECT COUNT(*) FROM ({base_query + filter_sql}) AS subquery WHERE tipologia = 'AVC' AND decreto = 'DS-120'"

    with connection.cursor() as cursor:
        
        cursor.execute(sql_query, params)
        rows = cursor.fetchall()

        # Obtener los nombres de las columnas
        column_names = [col[0] for col in cursor.description]




        # EJECUCION DE CONSULTAS COUNT DS-1
        cursor.execute(ds1_avc_count_query, params)
        ds1_avc_total_count = cursor.fetchone()[0]
        
        cursor.execute(ds1_arriendog3_count_query, params)
        ds1_arriendog3_total_count = cursor.fetchone()[0]
        
        cursor.execute(ds1_csp_count_query, params)
        ds1_csp_total_count = cursor.fetchone()[0]
        
        ds1_total = ds1_avc_total_count + ds1_arriendog3_total_count + ds1_csp_total_count
        
        
        
        
        
        # EJECUCION DE CONSULTAS COUNT DS-10
        cursor.execute(ds10_cch_count_query, params)
        ds10_cch_total_count = cursor.fetchone()[0]
        
        cursor.execute(ds10_csr_count_query, params)
        ds10_csr_total_count = cursor.fetchone()[0]
        
        cursor.execute(ds10_mave_count_query, params)
        ds10_mave_total_count = cursor.fetchone()[0]
        
        ds10_total = ds10_cch_total_count + ds10_csr_total_count + ds10_mave_total_count
        
        
        
        
        # EJECUCION DE CONSULTAS COUNT DS-19
        cursor.execute(ds19_pist_count_query, params)
        ds19_pist_total_count = cursor.fetchone()[0]
        
        
        
        
        # EJECUCION DE CONSULTAS COUNT DS-27
        cursor.execute(ds27_cap1_count_query, params)
        ds27_cap1_total_count = cursor.fetchone()[0]
        
        cursor.execute(ds27_cap2_count_query, params)
        ds27_cap2_total_count = cursor.fetchone()[0]
        
        cursor.execute(ds27_cap3_count_query, params)
        ds27_cap3_total_count = cursor.fetchone()[0]
        
        ds27_total = ds27_cap1_total_count + ds27_cap2_total_count + ds27_cap3_total_count
        
        
        
        
        # EJECUCION DE CONSULTAS COUNT DS-49
        cursor.execute(ds49_avc_count_query, params)
        ds49_avc_total_count = cursor.fetchone()[0]
        
        cursor.execute(ds49_cnt_count_query, params)
        ds49_cnt_total_count = cursor.fetchone()[0]
        
        cursor.execute(ds49_cnti_count_query, params)
        ds49_cnti_total_count = cursor.fetchone()[0]
        
        cursor.execute(ds49_csp_count_query, params)
        ds49_csp_total_count = cursor.fetchone()[0]
        
        ds49_total = ds49_avc_total_count + ds49_cnt_total_count + ds49_cnti_total_count + ds49_csp_total_count
        
        
        
        # EJECUCION DE CONSULTAS COUNT DS-52
        cursor.execute(ds52_arriendo_count_query, params)
        ds52_arriendo_total_count = cursor.fetchone()[0]
        
        
        
        # EJECUCION DE CONSULTAS COUNT DS-255
        cursor.execute(ds255_calefactor_count_query, params)
        ds255_calefactor_total_count = cursor.fetchone()[0]
        
        cursor.execute(ds255_ccss_count_query, params)
        ds255_ccss_total_count = cursor.fetchone()[0]
        
        cursor.execute(ds255_colector_count_query, params)
        ds255_colector_total_count = cursor.fetchone()[0]
        
        cursor.execute(ds255_fotov_count_query, params)
        ds255_fotov_total_count = cursor.fetchone()[0]
        
        cursor.execute(ds255_mejoramiento_count_query, params)
        ds255_mejoramiento_total_count = cursor.fetchone()[0]
        
        cursor.execute(ds255_pda_count_query, params)
        ds255_pda_total_count = cursor.fetchone()[0]
        
        cursor.execute(ds255_tbm_count_query, params)
        ds255_tbm_total_count = cursor.fetchone()[0]
        
        cursor.execute(ds255_termico_count_query, params)
        ds255_termico_total_count = cursor.fetchone()[0]
        
        cursor.execute(ds255_termicopda_count_query, params)
        ds255_termicopda_total_count = cursor.fetchone()[0]
        
        ds255_total = ds255_calefactor_total_count + ds255_ccss_total_count + ds255_colector_total_count + ds255_fotov_total_count + ds255_mejoramiento_total_count + ds255_pda_total_count + ds255_tbm_total_count + ds255_termico_total_count + ds255_termicopda_total_count
        
        
        
        # EJECUCION DE CONSULTAS LEASING
        cursor.execute(ls_avc_count_query, params)
        ls_avc_total_count = cursor.fetchone()[0]
        
        



    datos = [dict(zip(column_names, row)) for row in rows]

    context = {
        'datos': datos,
        'comunas_filtro': comunas_filtro,
        'provincias_filtro': provincias_filtro,
        
        #DETALLE DS-1
        'ds1_arriendog3_total_count': ds1_arriendog3_total_count,
        'ds1_avc_total_count': ds1_avc_total_count,
        'ds1_csp_total_count': ds1_csp_total_count,
        'ds1_total': ds1_total,
        
        #DETALLE DS-10
        'ds10_cch_total_count': ds10_cch_total_count,
        'ds10_csr_total_count': ds10_csr_total_count,
        'ds10_mave_total_count': ds10_mave_total_count,
        'ds10_total': ds10_total,
        
        #DETALLE DS-19
        'ds19_pist_total_count': ds19_pist_total_count,
        
        #DETALLE DS-27
        'ds27_cap1_total_count': ds27_cap1_total_count,
        'ds27_cap2_total_count': ds27_cap2_total_count,
        'ds27_cap3_total_count': ds27_cap3_total_count,
        'ds27_total': ds27_total,
        
        #DETALLE DS-49
        'ds49_avc_total_count': ds49_avc_total_count,
        'ds49_cnt_total_count': ds49_cnt_total_count,
        'ds49_cnti_total_count': ds49_cnti_total_count,
        'ds49_csp_total_count': ds49_csp_total_count,
        'ds49_total': ds49_total,
        
        #DETALLE DS-52
        'ds52_arriendo_total_count': ds52_arriendo_total_count,
        
        #DETALLE DS-255
        'ds255_calefactor_total_count': ds255_calefactor_total_count,
        'ds255_ccss_total_count': ds255_ccss_total_count,
        'ds255_colector_total_count': ds255_colector_total_count,
        'ds255_fotov_total_count': ds255_fotov_total_count,
        'ds255_mejoramiento_total_count': ds255_mejoramiento_total_count,
        'ds255_pda_total_count': ds255_pda_total_count,
        'ds255_tbm_total_count': ds255_tbm_total_count,
        'ds255_termico_total_count': ds255_termico_total_count,
        'ds255_termicopda_total_count': ds255_termicopda_total_count,
        'ds255_total': ds255_total,
        
        #DETALLE LEASING
        'ls_avc_total_count': ls_avc_total_count,
        
        # Variables para checkboxes
        'selected_comunas': comunas_filtro,
        'selected_provincias': provincias_filtro,
        'selected_anos': ano_imputacion_filtro,
        
    }

    return render(request, 'serviutemplate/filtros.html', context)






def BeneficiariosLista(request):
            
    with connection.cursor() as cursor:

        cursor.execute('''
                SELECT * FROM beneficiarios b 
        LEFT JOIN resoluciones r ON b.id_beneficiario = r.resolucion_id_beneficiario 
        LEFT JOIN decretos d ON b.id_beneficiario = d.decreto_id_beneficiario
        ''')
        datos = cursor.fetchall()
        
        # Obtener el número de elementos por página del parámetro GET
        per_page = request.GET.get('per_page', '10')
        try:
            per_page = int(per_page)
            if per_page not in [5, 10, 20, 50]:
                per_page = 10
        except ValueError:
            per_page = 10
        
        # Si se solicita mostrar todos los registros, no paginar
        if request.GET.get('mostrar_todos') == 'true':
            page_obj = datos
            mostrar_todos = True
        else:
            paginator = Paginator(datos, per_page)
            page_number = request.GET.get("page")
            page_obj = paginator.get_page(page_number)
            mostrar_todos = False

    context = {
        "datos": page_obj,
        "mostrar_todos": mostrar_todos,
        "total_beneficiarios": len(datos),
        "per_page": per_page
    }
    
    return render(request, 'serviutemplate/beneficiarios.html', context)




def Busqueda(request):
    
    rut_filtro = request.GET.getlist('rut_beneficiario')
    
    
    with connection.cursor() as cursor:
        cursor.execute(''' 
                       SELECT * FROM beneficiarios b 
        LEFT JOIN resoluciones r ON b.id_beneficiario = r.resolucion_id_beneficiario 
        LEFT JOIN decretos d ON b.id_beneficiario = d.decreto_id_beneficiario WHERE rut = %s
                       ''', rut_filtro)
    rut_filtrado = cursor.fetchall()
    
    context = {
        'datos': rut_filtrado
    }
    
    return render(request, 'serviutemplate/busqueda.html', context)


def actualizarBeneficiarioDecreto(request, id_decreto):
    decreto = get_object_or_404(Decretos, id_decreto=id_decreto)
    
    if request.method == 'POST':
        form = FormDecretos(request.POST, instance=decreto)
        if form.is_valid():
            decreto_saved = form.save()
            
            # Verificar si existe una resolución asociada, si no, crearla
            try:
                resolucion = Resoluciones.objects.get(resolucion_id_beneficiario=decreto_saved.decreto_id_beneficiario)
            except Resoluciones.DoesNotExist:
                resolucion = Resoluciones.objects.create(
                    resolucion_id_beneficiario=decreto_saved.decreto_id_beneficiario,
                    resolucion=None,
                    fecha_resolucion=None,
                    seleccion='',
                    ano_imputacion_res_of=None
                )
            
            url = reverse('actualizar_resolucion', args=[resolucion.id_resolucion])
            return redirect(url)
    else:
        # Usar solo la instancia del decreto para prellenar el formulario
        form = FormDecretos(instance=decreto)

    data = {
        'form': form,
        }

    return render(request, 'serviutemplate/actualizarDecreto.html', data)



def actualizarBeneficiarioResolucion(request, id_resolucion):
    resolucion = get_object_or_404(Resoluciones, id_resolucion=id_resolucion)
    
    if request.method == 'POST':
        form = FormResoluciones(request.POST, instance=resolucion)
        if form.is_valid():
            form.save()
            return redirect('beneficiarios')
    else:
        # Usar solo la instancia de la resolución para prellenar el formulario
        form = FormResoluciones(instance=resolucion)

    data = {
        'form': form,
        }

    return render(request, 'serviutemplate/actualizarResolucion.html', data)



@login_required
def actualizarBeneficiarios(request, id_beneficiario):
    beneficiario = get_object_or_404(Beneficiarios, id_beneficiario=id_beneficiario)
    
    # Obtener o crear decreto y resolución asociados
    decreto = Decretos.objects.filter(decreto_id_beneficiario=beneficiario).first()
    if not decreto:
        decreto = Decretos.objects.create(
            decreto_id_beneficiario=beneficiario,
            decreto='',
            tipologia='',
            tramo=None
        )
    
    resolucion = Resoluciones.objects.filter(resolucion_id_beneficiario=beneficiario).first()
    if not resolucion:
        resolucion = Resoluciones.objects.create(
            resolucion_id_beneficiario=beneficiario,
            resolucion=None,
            fecha_resolucion=None,
            seleccion='',
            ano_imputacion_res_of=None
        )
    
    if request.method == 'POST':
        # Crear los tres formularios con los datos POST y las instancias existentes
        form_beneficiario = FormBeneficiarios(request.POST, instance=beneficiario)
        form_decreto = FormDecretos(request.POST, instance=decreto)
        form_resolucion = FormResoluciones(request.POST, instance=resolucion)
        
        # Validar y guardar todos los formularios
        if form_beneficiario.is_valid():
            form_beneficiario.save()
            
            if form_decreto.is_valid():
                form_decreto.save()
            
            if form_resolucion.is_valid():
                form_resolucion.save()
            
            # Redirigir a la lista de beneficiarios después de guardar todo
            return redirect('beneficiarios')
    else:
        # Crear formularios con las instancias existentes para prellenar
        form_beneficiario = FormBeneficiarios(instance=beneficiario)
        form_decreto = FormDecretos(instance=decreto)
        form_resolucion = FormResoluciones(instance=resolucion)

    data = {
        'form': form_beneficiario,
        'form_decreto': form_decreto,
        'form_resolucion': form_resolucion,
        'beneficiario': beneficiario,
        'decreto': decreto,
        'resolucion': resolucion,
        }

    return render(request, 'serviutemplate/actualizarBeneficiario.html', data)
    
@login_required
def anadirBeneficiario(request):
    if request.method == 'POST':
        # Crear los tres formularios con los datos POST
        form_beneficiario = FormBeneficiarios(request.POST)
        form_decreto = FormDecretos(request.POST)
        form_resolucion = FormResoluciones(request.POST)
        
        # Validar todos los formularios
        if form_beneficiario.is_valid():
            # Guardar el beneficiario
            beneficiario = form_beneficiario.save()
            
            # Crear y guardar el decreto asociado
            decreto_data = form_decreto.cleaned_data if form_decreto.is_valid() else {}
            decreto = Decretos.objects.create(
                decreto_id_beneficiario=beneficiario,
                decreto=decreto_data.get('decreto', ''),
                tipologia=decreto_data.get('tipologia', ''),
                tramo=decreto_data.get('tramo', None)
            )
            
            # Crear y guardar la resolución asociada
            resolucion_data = form_resolucion.cleaned_data if form_resolucion.is_valid() else {}
            resolucion = Resoluciones.objects.create(
                resolucion_id_beneficiario=beneficiario,
                resolucion=resolucion_data.get('resolucion', None),
                fecha_resolucion=resolucion_data.get('fecha_resolucion', None),
                seleccion=resolucion_data.get('seleccion', ''),
                ano_imputacion_res_of=resolucion_data.get('ano_imputacion_res_of', None)
            )
            
            # Redirigir a la lista de beneficiarios después de guardar todo
            return redirect('beneficiarios')
    else:
        # Crear formularios vacíos para GET
        form_beneficiario = FormBeneficiarios()
        form_decreto = FormDecretos()
        form_resolucion = FormResoluciones()
    
    data = {
        'form': form_beneficiario,
        'form_decreto': form_decreto,
        'form_resolucion': form_resolucion,
    }
    
    return render(request, 'serviutemplate/anadirBeneficiario.html', data)

class ChatView(View):
    def get(self, request):
        return JsonResponse({'error': 'Método no permitido'}, status=405)
    
    def post(self, request):
        try:
            data = json.loads(request.body)
            user_message = data.get('message', '')
            
            # Detectar si el mensaje contiene un RUT
            rut_pattern = r'\b\d{1,2}\.?\d{3}\.?\d{3}[-.]?[0-9kK]\b'
            rut_match = re.search(rut_pattern, user_message)
            rut = rut_match.group().replace('.', '').replace('-', '') if rut_match else None
            
            # Obtener IP del usuario
            user_ip = request.META.get('REMOTE_ADDR')
            
            # Usar la función que guarda en la base de datos
            from .serviu_prompt import generate_serviu_response
            
            ai_response, session_id, interaction_id = generate_serviu_response(
                user_query=user_message,
                rut=rut,
                session_id=request.session.get('chat_session_id'),
                user_ip=user_ip
            )
            
            # Guardar session_id en la sesión
            request.session['chat_session_id'] = session_id
            
            return JsonResponse({
                'response': ai_response,
                'status': 'success',
                'interaction_id': interaction_id
            })
                
        except Exception as e:
            return JsonResponse({
                'error': f'Error: {str(e)}',
                'status': 'error'
            }, status=500)

@login_required
def nlp_analytics_dashboard(request):
    """Dashboard de análisis NLP para interacciones del chat"""
    
    # Obtener estadísticas generales
    total_interactions = ChatInteraction.objects.count()
    
    # Estadísticas por categoría
    category_stats = nlp_analyzer.get_category_statistics()
    
    # Tendencias de sentimiento
    sentiment_trends = nlp_analyzer.get_sentiment_trends(days=30)
    
    # Patrones frecuentes
    frequent_patterns = nlp_analyzer.analyze_frequent_patterns(min_frequency=2)
    
    # Interacciones recientes con análisis
    recent_interactions = []
    interactions = ChatInteraction.objects.order_by('-timestamp')[:20]
    
    for interaction in interactions:
        recent_interactions.append([
            interaction.user_question,
            interaction.ai_response,
            interaction.question_category or 'Sin categoría',
            interaction.sentiment_score or 0,
            interaction.user_rut,
            interaction.timestamp
        ])
    
    context = {
        'total_interactions': total_interactions,
        'category_stats': category_stats,
        'sentiment_trends': sentiment_trends,
        'frequent_patterns': frequent_patterns,
        'recent_interactions': recent_interactions,
    }
    
    return render(request, 'serviutemplate/nlp_dashboard.html', context)

@csrf_exempt
@require_http_methods(["POST"])
def api_analyze_text(request):
    """API para analizar texto usando NLP"""
    try:
        data = json.loads(request.body)
        text = data.get('text', '')
        
        if not text:
            return JsonResponse({'error': 'No se proporcionó texto para analizar'}, status=400)
        
        # Realizar análisis NLP
        category = nlp_analyzer.categorize_question(text)
        sentiment = nlp_analyzer.analyze_sentiment(text)
        keywords = nlp_analyzer.extract_keywords(text, top_n=5)
        
        # Buscar preguntas similares
        similar_questions = nlp_analyzer.find_similar_questions(text, threshold=0.3, limit=3)
        
        similar_data = []
        for item in similar_questions:
            similar_data.append({
                'question': item['interaction'].user_question,
                'response': item['interaction'].ai_response,
                'similarity': round(item['similarity'], 3),
                'category': item['interaction'].question_category
            })
        
        response_data = {
            'text': text,
            'category': category,
            'sentiment_score': round(sentiment, 3),
            'sentiment_label': 'Positivo' if sentiment > 0.1 else 'Negativo' if sentiment < -0.1 else 'Neutral',
            'keywords': keywords,
            'similar_questions': similar_data,
            'analysis_timestamp': timezone.now().isoformat()
        }
        
        return JsonResponse(response_data)
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido'}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'Error en el análisis: {str(e)}'}, status=500)

def get_chart_data(request, decreto):
    """Vista para obtener datos de gráficos en formato JSON con filtros aplicados"""
    # Procesar filtros de la misma manera que en dashboard
    comunas_filtro = request.GET.getlist('comunas')
    provincias_filtro = request.GET.getlist('provincias')
    ano_imputacion_filtro = request.GET.getlist('ano_imputacion')

    base_query = """
        SELECT * FROM beneficiarios b 
        LEFT JOIN resoluciones r ON b.id_beneficiario = r.resolucion_id_beneficiario 
        LEFT JOIN decretos d ON b.id_beneficiario = d.decreto_id_beneficiario
    """
    filters = []
    params = []

    if comunas_filtro:
        filters.append("b.comuna IN ({})".format(','.join(['%s'] * len(comunas_filtro))))
        params.extend(comunas_filtro)

    if provincias_filtro:
        filters.append("b.provincia IN ({})".format(','.join(['%s'] * len(provincias_filtro))))
        params.extend(provincias_filtro)
        
    if ano_imputacion_filtro:
        filters.append("r.ano_imputacion_res_of IN ({})".format(','.join(['%s'] * len(ano_imputacion_filtro))))
        params.extend(ano_imputacion_filtro)

    # Construir la consulta SQL con o sin filtros
    if filters:
        filter_sql = " WHERE " + " AND ".join(filters)
    else:
        filter_sql = ""

    with connection.cursor() as cursor:
        chart_data = {}
        
        if decreto == 'DS-1':
            # Datos para DS-1 con filtros
            ag_ds1_query = f"SELECT COUNT(*) FROM ({base_query + filter_sql}) AS subquery WHERE tipologia = 'arriendo glosa 03' AND decreto = 'DS-1'"
            cursor.execute(ag_ds1_query, params)
            ag_ds1 = cursor.fetchone()[0]
            
            avc_ds1_query = f"SELECT COUNT(*) FROM ({base_query + filter_sql}) AS subquery WHERE tipologia = 'avc' AND decreto = 'DS-1'"
            cursor.execute(avc_ds1_query, params)
            avc_ds1 = cursor.fetchone()[0]
            
            csp_ds1_query = f"SELECT COUNT(*) FROM ({base_query + filter_sql}) AS subquery WHERE tipologia = 'CSP' AND decreto = 'DS-1'"
            cursor.execute(csp_ds1_query, params)
            csp_ds1 = cursor.fetchone()[0]
            
            blanco_ds1_query = f"SELECT COUNT(*) FROM ({base_query + filter_sql}) AS subquery WHERE (tipologia = '' OR tipologia IS NULL) AND decreto = 'DS-1'"
            cursor.execute(blanco_ds1_query, params)
            blanco_ds1 = cursor.fetchone()[0]
            
            chart_data = {
                'labels': ['Arriendo glosa 03', 'AVC', 'CSP', 'Sin tipología'],
                'data': [ag_ds1, avc_ds1, csp_ds1, blanco_ds1],
                'title': 'Distribución DS-1'
            }
            
        elif decreto == 'DS-10':
            # Datos para DS-10 con filtros
            cch_ds10_query = f"SELECT COUNT(*) FROM ({base_query + filter_sql}) AS subquery WHERE tipologia = 'CCH' AND decreto = 'DS-10'"
            cursor.execute(cch_ds10_query, params)
            cch_ds10 = cursor.fetchone()[0]
            
            csr_ds10_query = f"SELECT COUNT(*) FROM ({base_query + filter_sql}) AS subquery WHERE tipologia = 'CSR' AND decreto = 'DS-10'"
            cursor.execute(csr_ds10_query, params)
            csr_ds10 = cursor.fetchone()[0]
            
            mave_ds10_query = f"SELECT COUNT(*) FROM ({base_query + filter_sql}) AS subquery WHERE tipologia = 'MAVE' AND decreto = 'DS-10'"
            cursor.execute(mave_ds10_query, params)
            mave_ds10 = cursor.fetchone()[0]
            
            blanco_ds10_query = f"SELECT COUNT(*) FROM ({base_query + filter_sql}) AS subquery WHERE (tipologia = '' OR tipologia IS NULL) AND decreto = 'DS-10'"
            cursor.execute(blanco_ds10_query, params)
            blanco_ds10 = cursor.fetchone()[0]
            
            chart_data = {
                'labels': ['CCH', 'CSR', 'MAVE', 'Sin tipología'],
                'data': [cch_ds10, csr_ds10, mave_ds10, blanco_ds10],
                'title': 'Distribución DS-10'
            }
            
        elif decreto == 'DS-19':
            # Datos para DS-19 con filtros
            pist_ds19_query = f"SELECT COUNT(*) FROM ({base_query + filter_sql}) AS subquery WHERE tipologia = 'PIST' AND decreto = 'DS-19'"
            cursor.execute(pist_ds19_query, params)
            pist_ds19 = cursor.fetchone()[0]
            
            blanco_ds19_query = f"SELECT COUNT(*) FROM ({base_query + filter_sql}) AS subquery WHERE (tipologia = '' OR tipologia IS NULL) AND decreto = 'DS-19'"
            cursor.execute(blanco_ds19_query, params)
            blanco_ds19 = cursor.fetchone()[0]
            
            chart_data = {
                'labels': ['PIST', 'Sin tipología'],
                'data': [pist_ds19, blanco_ds19],
                'title': 'Distribución DS-19'
            }
            
        elif decreto == 'DS-27':
            # Datos para DS-27 con filtros
            cap1_ds27_query = f"SELECT COUNT(*) FROM ({base_query + filter_sql}) AS subquery WHERE tipologia = 'CAP I' AND decreto = 'DS-27'"
            cursor.execute(cap1_ds27_query, params)
            cap1_ds27 = cursor.fetchone()[0]
            
            cap2_ds27_query = f"SELECT COUNT(*) FROM ({base_query + filter_sql}) AS subquery WHERE tipologia = 'CAP II' AND decreto = 'DS-27'"
            cursor.execute(cap2_ds27_query, params)
            cap2_ds27 = cursor.fetchone()[0]
            
            cap3_ds27_query = f"SELECT COUNT(*) FROM ({base_query + filter_sql}) AS subquery WHERE tipologia = 'CAP III' AND decreto = 'DS-27'"
            cursor.execute(cap3_ds27_query, params)
            cap3_ds27 = cursor.fetchone()[0]
            
            blanco_ds27_query = f"SELECT COUNT(*) FROM ({base_query + filter_sql}) AS subquery WHERE (tipologia = '' OR tipologia IS NULL) AND decreto = 'DS-27'"
            cursor.execute(blanco_ds27_query, params)
            blanco_ds27 = cursor.fetchone()[0]
            
            chart_data = {
                'labels': ['CAP I', 'CAP II', 'CAP III', 'Sin tipología'],
                'data': [cap1_ds27, cap2_ds27, cap3_ds27, blanco_ds27],
                'title': 'Distribución DS-27'
            }
            
        elif decreto == 'DS-49':
            # Datos para DS-49 con filtros
            avc_ds49_query = f"SELECT COUNT(*) FROM ({base_query + filter_sql}) AS subquery WHERE tipologia = 'AVC' AND decreto = 'DS-49'"
            cursor.execute(avc_ds49_query, params)
            avc_ds49 = cursor.fetchone()[0]
            
            cnt_ds49_query = f"SELECT COUNT(*) FROM ({base_query + filter_sql}) AS subquery WHERE tipologia = 'CNT' AND decreto = 'DS-49'"
            cursor.execute(cnt_ds49_query, params)
            cnt_ds49 = cursor.fetchone()[0]
            
            cnti_ds49_query = f"SELECT COUNT(*) FROM ({base_query + filter_sql}) AS subquery WHERE tipologia = 'CNT INDUST' AND decreto = 'DS-49'"
            cursor.execute(cnti_ds49_query, params)
            cnti_ds49 = cursor.fetchone()[0]
            
            csp_ds49_query = f"SELECT COUNT(*) FROM ({base_query + filter_sql}) AS subquery WHERE tipologia = 'CSP' AND decreto = 'DS-49'"
            cursor.execute(csp_ds49_query, params)
            csp_ds49 = cursor.fetchone()[0]
            
            blanco_ds49_query = f"SELECT COUNT(*) FROM ({base_query + filter_sql}) AS subquery WHERE (tipologia = '' OR tipologia IS NULL) AND decreto = 'DS-49'"
            cursor.execute(blanco_ds49_query, params)
            blanco_ds49 = cursor.fetchone()[0]
            
            chart_data = {
                'labels': ['AVC', 'CNT', 'CNT INDUST', 'CSP', 'Sin tipología'],
                'data': [avc_ds49, cnt_ds49, cnti_ds49, csp_ds49, blanco_ds49],
                'title': 'Distribución DS-49'
            }
            
        elif decreto == 'DS-52':
            # Datos para DS-52 con filtros
            arriendo_ds52_query = f"SELECT COUNT(*) FROM ({base_query + filter_sql}) AS subquery WHERE tipologia = 'ARRIENDO' AND decreto = 'DS-52'"
            cursor.execute(arriendo_ds52_query, params)
            arriendo_ds52 = cursor.fetchone()[0]
            
            blanco_ds52_query = f"SELECT COUNT(*) FROM ({base_query + filter_sql}) AS subquery WHERE (tipologia = '' OR tipologia IS NULL) AND decreto = 'DS-52'"
            cursor.execute(blanco_ds52_query, params)
            blanco_ds52 = cursor.fetchone()[0]
            
            chart_data = {
                'labels': ['ARRIENDO', 'Sin tipología'],
                'data': [arriendo_ds52, blanco_ds52],
                'title': 'Distribución DS-52'
            }
            
        elif decreto == 'DS-255':
            # Datos para DS-255 con filtros
            calefactor_ds255_query = f"SELECT COUNT(*) FROM ({base_query + filter_sql}) AS subquery WHERE tipologia = 'CALEFACTOR' AND decreto = 'DS-255'"
            cursor.execute(calefactor_ds255_query, params)
            calefactor_ds255 = cursor.fetchone()[0]
            
            blanco_ds255_query = f"SELECT COUNT(*) FROM ({base_query + filter_sql}) AS subquery WHERE (tipologia = '' OR tipologia IS NULL) AND decreto = 'DS-255'"
            cursor.execute(blanco_ds255_query, params)
            blanco_ds255 = cursor.fetchone()[0]
            
            chart_data = {
                'labels': ['CALEFACTOR', 'Sin tipología'],
                'data': [calefactor_ds255, blanco_ds255],
                'title': 'Distribución DS-255'
            }
            
        elif decreto == 'DS-120':
            # Datos para DS-120 con filtros
            avc_leasing_query = f"SELECT COUNT(*) FROM ({base_query + filter_sql}) AS subquery WHERE tipologia = 'AVC' AND decreto = 'DS-120'"
            cursor.execute(avc_leasing_query, params)
            avc_leasing = cursor.fetchone()[0]
            
            blanco_ds120_query = f"SELECT COUNT(*) FROM ({base_query + filter_sql}) AS subquery WHERE (tipologia = '' OR tipologia IS NULL) AND decreto = 'DS-120'"
            cursor.execute(blanco_ds120_query, params)
            blanco_ds120 = cursor.fetchone()[0]
            
            chart_data = {
                'labels': ['AVC', 'Sin tipología'],
                'data': [avc_leasing, blanco_ds120],
                'title': 'Distribución DS-120'
            }
    
    return JsonResponse(chart_data)
