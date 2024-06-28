import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import json
import requests
import geopandas as gpd
import math
import folium
import geopandas as gpd
from folium.features import GeoJsonTooltip
from streamlit_folium import st_folium, folium_static

st.set_page_config(
    page_title="Vigiagua Emergência",
    page_icon=":potable_water:",
    layout="wide",
    initial_sidebar_state='collapsed')

col1, col2, col3 = st.columns([1,4,1])

col3.image('https://github.com/andrejarenkow/csv/blob/master/logo_cevs%20(2).png?raw=true', width=100)
col2.subheader('Formas de abastecimento de água geolocalizadas e área inundada RS, maio 2024')
col1.image('https://github.com/andrejarenkow/csv/blob/master/logo_estado%20(3)%20(1).png?raw=true', width=150)

# Lê os dados de um arquivo Excel online
@st.cache_data
def read_dados():

    dados = pd.read_excel('https://docs.google.com/spreadsheets/d/e/2PACX-1vQkzpN-gUEQdxaWa6WI1UsI3DGvILGZRTnKogYn5k-KgW5eBzpv36pJJut73U7FjGeZjPuZeBA2p30u/pub?output=xlsx',
                      sheet_name='Pontos de coleta')

    dados = dados.dropna(subset=['Latitude ETA']).reset_index(drop=True)
    
    #Pontos avaliados pela Babi dentro da mancha de inundação
    gdf_pontos_dentro = gpd.read_file('shapefiles/pontos_dentro_show.gpkg', encoding='utf-8').set_crs(epsg=4326)
    gdf_pontos_dentro['Distância'] = 'Alagado'


    #Pontos avaliados pela Babi a 500 metros da mancha de inundação
    gdf_pontos_500_metros = gpd.read_file('shapefiles/pontos_500_e_mergulhadores_denovo.gpkg', encoding='utf-8' ).set_crs(epsg=4326, allow_override=True)
    gdf_pontos_500_metros['Distância'] = 'até 500 metros'
    
    #Área inundada
    gdf_area_inundada = gpd.read_file('shapefiles/area_inundada_unificada.shp').to_crs(epsg=4326)
    
    # Função para adicionar '0' se o comprimento for menor que 7
    def pad_zero(value):
        if len(value) < 7:
            return value.zfill(7)
        return value

    # Aplicar a função à coluna 'Regional de Saúde'
    gdf_pontos = pd.concat([gdf_pontos_dentro, gdf_pontos_500_metros], ignore_index=True)
    gdf_pontos = gdf_pontos.drop_duplicates(subset=['Latitude_corrigida'], keep='first')
    gdf_pontos['Regional de Saúde'] = gdf_pontos['Regional de Saúde'].apply(pad_zero)
    gdf_pontos = gdf_pontos[gdf_pontos['Tipo de captação']=='SUPERFICIAL'].reset_index(drop=True)

        # Função para corrigir coordenadas
    def corrigir_coordenada(numero):
        # Certifique-se de que o número é positivo para manipulação
        numero_transformado = abs(numero)
        
        # Obtenha o logaritmo de base 10 do número transformado
        log_base10 = math.log10(numero_transformado)
        
        # Arredonde o logaritmo para baixo e subtraia 1 para obter a posição correta da vírgula
        log_arredondado = math.floor(log_base10) - 1
        
        # Divida o número pela potência de 10 correspondente
        numero_consertado = -1 * numero_transformado / (10 ** log_arredondado)
        
        return numero_consertado
    
    # Aplicar a função à coluna 'Valores'
    #dados_function['Latitude_corrigida'] = dados_function['Latitude_corrigida'].apply(corrigir_coordenada)
    #dados_function['Longitude_corrigida'] = dados_function['Longitude_corrigida'].apply(corrigir_coordenada)

    return gdf_pontos, gdf_area_inundada, dados

gdf_pontos, gdf_area_inundada, dados = read_dados()
#gdf_pontos = pd.concat( [gdf_pontos_500_metros, gdf_pontos_dentro], ignore_index=True)
#st.title('Formas de abastecimento de água geolocalizadas e área inundada RS, maio 2024')
tab_producao, tab_planejamento = st.tabs(['Pontos escolhidos','Planejamento'])

with tab_producao:
    df = dados.copy()

    # Cria o mapa centralizado na média das coordenadas
    map_center = [df['Latitude ETA'].mean(), df['Longitude ETA'].mean()]
    m = folium.Map(location=map_center, zoom_start=7)

        # Função para estilizar a área inundada
    def estilo_area_inundada(feature):
        return {
            'fillColor': '#77b7f7',
            'color': '#77b7f7',
            'weight': 1,
            'fillOpacity': 0.6,
        }
    
    # Adicionar gdf_area_inundada ao mapa com estilo
    folium.GeoJson(
        gdf_area_inundada,
        name='Área Inundada',
        style_function=estilo_area_inundada
    ).add_to(m)
    
    
    # Adicionar um controle de camadas
    folium.LayerControl().add_to(mapa)
    
    # Adiciona os pontos do DataFrame no mapa
    for _, row in df.iterrows():
        folium.Marker(
            location=[row['Latitude ETA'], row['Longitude ETA']],
            popup=row['Nome da forma de abastecimento'],
        ).add_to(m)

    st_data = folium_static(m, width=800, height=700)

with tab_planejamento:
    col1, col2 = st.columns([1,1])
    filtros_container = st.container(border=True)
    
    with col1:
        st.write(
            """
    Para o painel das formas de abastecimento de água e a área inundada no RS em maio de 2024, foram utilizados pontos de abastecimento de água,
    cujas coordenadas foram retiradas do sistema SISAGUA, e a mancha de inundação foi obtida a partir dos dados fornecidos por pesquisadores da UFRGS
    (disponíveis em Sistema de Informações Geográficas Único). Ambos os conjuntos de dados foram inseridos no software QGIS, 
    onde foram cruzados para identificar quais pontos de abastecimento estariam inundados de acordo com a mancha de inundação. 
    Em seguida, foi gerado um buffer de 500 metros ao redor de todos os pontos de abastecimento, permitindo uma nova análise para identificar os pontos próximos à área de inundação,
    tratando-os como pontos de alerta para futuros eventos climáticos extremos.
                """
        )
        df_municipio_afetado = pd.pivot_table(gdf_pontos, index='Município', columns=['Distância','Tipo de captação'], values='geometry', aggfunc='count').fillna(0).astype(int) 
        df_municipio_afetado.columns = [f"{level1} {level2}" if level2 else level1 for level1, level2 in df_municipio_afetado.columns]
    
        # Criando 3 colunas para metricas
        col_total1, col_total2, col_total3  = st.columns(3)
        col_total1.metric('Total de pontos', len(gdf_pontos))
        col_total2.metric('Total de pontos superficial', (gdf_pontos['Tipo de captação']=='SUPERFICIAL').sum())
    
        # Imprimindo dataframe
        #gdf_pontos.columns
        st.dataframe(gdf_pontos[['Município','Regional de Saúde','Distância',
                    'Nome da Forma de Abastecimento', 'Tipo de captação',
                   'Sigla da Instituição']])
        #st.dataframe(df_municipio_afetado)
    
    # Definir o centro do mapa
    centro_mapa = [-30, -52]  # substitua pela latitude e longitude do centro do seu mapa
    
    # Criar o mapa
    mapa = folium.Map(location=centro_mapa, zoom_start=7)
    
    # Função para obter o ícone baseado na coluna 'Distância' e 'Tipo de ca'
    def get_icon(distancia, tipo_de_ca):
        if tipo_de_ca == 'SUBTERRANEO':
            icon = 'circle-arrow-down'  # exemplo de ícone para subterrâneo
        elif tipo_de_ca == 'SUPERFICIAL':
            icon = 'tint'  # exemplo de ícone para superficial
        else:
            icon = 'info-sign'  # ícone padrão se o valor não for encontrado
        
        if distancia == 'Alagado':
            color = 'red'
    
        else:
            color = 'orange'  # cor padrão se o valor não for encontrado
        
        return folium.Icon(color=color, icon=icon)
    
    # Criar grupos de camadas
    subterraneo_layer = folium.FeatureGroup(name='Subterrâneo')
    superficial_layer = folium.FeatureGroup(name='Superficial')
    
    # Adicionar gdf_pontos ao mapa com ícones personalizados e grupos de camadas
    for idx, row in gdf_pontos.iterrows():
        marker = folium.Marker(
            location=[row.geometry.centroid.y, row.geometry.centroid.x],
            icon=get_icon(row['Distância'], row['Tipo de captação']),
            tooltip=folium.Tooltip(
                text=f"Distância: {row['Distância']}<br>Município: {row['Município']}<br>Nome: {row['Nome da Forma de Abastecimento']}<br>Tipo de Captação: {row['Tipo de captação']}<br>Tipo da Fonte: {row['Tipo da Forma de Abastecimento']}"
            )
        )
        
        # Adicionar o marcador à camada apropriada
        if row['Tipo de captação'] == 'SUBTERRANEO':
            marker.add_to(subterraneo_layer)
        elif row['Tipo de captação'] == 'SUPERFICIAL':
            marker.add_to(superficial_layer)
    
    # Adicionar as camadas ao mapa
    #subterraneo_layer.add_to(mapa)
    superficial_layer.add_to(mapa)
    
    # Função para estilizar a área inundada
    def estilo_area_inundada(feature):
        return {
            'fillColor': '#77b7f7',
            'color': '#77b7f7',
            'weight': 1,
            'fillOpacity': 0.6,
        }
    
    # Adicionar gdf_area_inundada ao mapa com estilo
    folium.GeoJson(
        gdf_area_inundada,
        name='Área Inundada',
        style_function=estilo_area_inundada
    ).add_to(mapa)
    
    
    # Adicionar um controle de camadas
    folium.LayerControl().add_to(mapa)
    
    
    # Exibir o mapa
    with col2:
        st_data = folium_static(mapa, width=800, height=700)



