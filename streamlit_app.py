import streamlit as st
import plotly.express as px
#import plotly.graph_objects as go
import pandas as pd
import json
import requests
#import geopandas as gpd

pontos_captacao = pd.read_csv('pontos_captacao_rs_2024_com_lat_lon.csv')
#pontos_captacao

pontos_captacao_rs_2024 = pontos_captacao[(pontos_captacao['UF'] == 'RS')& (pontos_captacao['Ano de referência'] == 2024)]
pontos_captacao_rs_2024_com_lat_lon = pontos_captacao_rs_2024.dropna(subset=['Latitude', 'Longitude']).reset_index(drop=True)
pontos_captacao_rs_2024_com_lat_lon['Latitude_corrigida'] = pd.to_numeric(pontos_captacao_rs_2024_com_lat_lon['Latitude'].str.replace(',','.'), errors='coerce')
pontos_captacao_rs_2024_com_lat_lon['Longitude_corrigida'] = pd.to_numeric(pontos_captacao_rs_2024_com_lat_lon['Longitude'].str.replace(',','.'), errors='coerce')

#pontos_captacao_rs_2024_com_lat_lon

# URL do arquivo GeoJSON
url = 'https://github.com/andrejarenkow/geodata/raw/main/municipios_rs_CRS/RS_Municipios_2021.json'

# Carregar o arquivo GeoJSON via URL
response = requests.get(url)
geojson_data = response.json()


# Configurar o token do Mapbox
token = 'pk.eyJ1IjoiYW5kcmUtamFyZW5rb3ciLCJhIjoiY2xkdzZ2eDdxMDRmMzN1bnV6MnlpNnNweSJ9.4_9fi6bcTxgy5mGaTmE4Pw'
px.set_mapbox_access_token(token)

# Criação do DataFrame
df = pontos_captacao_rs_2024_com_lat_lon.copy()

# Criação do mapa com os pontos
fig = px.scatter_mapbox(
    df, 
    lat='Latitude_corrigida', 
    lon='Longitude_corrigida', 
    height=800,
    hover_name='Nome da Forma de Abastecimento', 
    hover_data=['Município', 'Nome da Instiuição'], 
    #color='Tipo da Forma de Abastecimento'
)
"""
# Adicionando os polígonos dos municípios
for feature in geojson_data['features']:
    if feature['geometry']['type'] == 'Polygon':
        coordinates = feature['geometry']['coordinates'][0]
    elif feature['geometry']['type'] == 'MultiPolygon':
        coordinates = feature['geometry']['coordinates'][0][0]
    
    lon = [point[0] for point in coordinates]
    lat = [point[1] for point in coordinates]
    
    fig.add_trace(go.Scattermapbox(
        fill='none',
        hoverinfo ='skip',
        lon=lon,
        lat=lat,
        line=dict(color='white'),
        opacity=0.5,
        mode='lines',
        showlegend =False,
        name=feature['properties']['NM_MUN']
    ))
"""
# Configuração do mapa
fig.update_layout(
    mapbox_style="dark",
    mapbox_zoom=6,
    mapbox_center={"lat": -29.5, "lon": -53.5}
)

st.plotly_chart(fig)
