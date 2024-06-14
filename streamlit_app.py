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

    return gdf_pontos, gdf_area_inundada

gdf_pontos, gdf_area_inundada = read_dados()
#gdf_pontos = pd.concat( [gdf_pontos_500_metros, gdf_pontos_dentro], ignore_index=True)
st.subheader('Formas de abastecimento de água geolocalizadas e área inundada RS, maio 2024')
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
    
    st.dataframe(df_municipio_afetado.sort_values('Alagado SUPERFICIAL', ascending=False))

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
            text=f"Distância: {row['Distância']}<br>Município: {row['Município']}<br>Tipo de Captação: {row['Tipo de captação']}<br>Tipo da Fonte: {row['Tipo da Forma de Abastecimento']}"
        )
    )
    
    # Adicionar o marcador à camada apropriada
    if row['Tipo de captação'] == 'SUBTERRANEO':
        marker.add_to(subterraneo_layer)
    elif row['Tipo de captação'] == 'SUPERFICIAL':
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
    st_data = folium_static(mapa, width=800, height=700)
