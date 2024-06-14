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

# Lê os dados de um arquivo Excel online
@st.cache_data
def read_dados():
    #Pontos avaliados pela Babi dentro da mancha de inundação
    gdf_pontos_dentro = gpd.read_file('shapefiles/pontos_dentro.shp', encoding='utf-8').set_crs(epsg=4326)
    gdf_pontos_dentro['Distância'] = 'Dentro - Alagado'
    gdf_pontos_dentro['style'] = [{'color':'red'}]*len(gdf_pontos_dentro)

    #Pontos avaliados pela Babi a 100 metros da mancha de inundação
    gdf_pontos_100_metros = gpd.read_file('shapefiles/pontos_100m_real.shp', encoding='utf-8' ).set_crs(epsg=4326)
    gdf_pontos_100_metros['Distância'] = '100 metros'
    gdf_pontos_100_metros['style'] = [{'color':'orange'}]*len(gdf_pontos_100_metros)

    #Área inundada
    gdf_area_inundada = gpd.read_file('shapefiles/area_inundada_unificada.shp').to_crs(epsg=4326)
    
    # Função para adicionar '0' se o comprimento for menor que 7
    def pad_zero(value):
        if len(value) < 7:
            return value.zfill(7)
        return value

    # Aplicar a função à coluna 'Regional de Saúde'
    gdf_pontos_dentro['Regional d'] = gdf_pontos_dentro['Regional d'].apply(pad_zero)
    gdf_pontos_100_metros['Regional d'] = gdf_pontos_100_metros['Regional d'].apply(pad_zero)


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

    return gdf_pontos_dentro, gdf_pontos_100_metros, gdf_area_inundada

gdf_pontos_dentro, gdf_pontos_100_metros, gdf_area_inundada = read_dados()
gdf_pontos = pd.concat( [gdf_pontos_100_metros, gdf_pontos_dentro], ignore_index=True)
st.subheader('Formas de abastecimento de água geolocalizadas e área inundada RS, maio 2024')
col1, col2 = st.columns([1,2])
filtros_container = st.container(border=True)

# Definir o centro do mapa
centro_mapa = [-30, -52]  # substitua pela latitude e longitude do centro do seu mapa

# Criar o mapa
mapa = folium.Map(location=centro_mapa, zoom_start=7)

# Função para obter o ícone baseado na coluna 'Distância' e 'Tipo de ca'
def get_icon(distancia, tipo_de_ca):
    if tipo_de_ca == 'SUBTERRANEO':
        icon = 'tint'  # exemplo de ícone para subterrâneo
    elif tipo_de_ca == 'SUPERFICIAL':
        icon = 'cloud'  # exemplo de ícone para superficial
    else:
        icon = 'info-sign'  # ícone padrão se o valor não for encontrado
    
    if distancia == 'Dentro - Alagado':
        color = 'red'
    elif distancia == '100 metros':
        color = 'orange'
    else:
        color = 'gray'  # cor padrão se o valor não for encontrado
    
    return folium.Icon(color=color, icon=icon)

# Criar grupos de camadas
subterraneo_layer = folium.FeatureGroup(name='Subterrâneo')
superficial_layer = folium.FeatureGroup(name='Superficial')

# Adicionar gdf_pontos ao mapa com ícones personalizados e grupos de camadas
for idx, row in gdf_pontos.iterrows():
    marker = folium.Marker(
        location=[row.geometry.y, row.geometry.x],
        icon=get_icon(row['Distância'], row['Tipo de ca']),
        tooltip=folium.Tooltip(
            text=f"Distância: {row['Distância']}<br>Município: {row['Município']}<br>Tipo de Captação: {row['Tipo de ca']}<br>Tipo da Fonte: {row['Tipo da Fo']}"
        )
    )
    
    # Adicionar o marcador à camada apropriada
    if row['Tipo de ca'] == 'SUBTERRANEO':
        marker.add_to(subterraneo_layer)
    elif row['Tipo de ca'] == 'SUPERFICIAL':
        marker.add_to(superficial_layer)

# Adicionar as camadas ao mapa
subterraneo_layer.add_to(mapa)
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
    st_data = folium_static(mapa, width=1000, height=700)
