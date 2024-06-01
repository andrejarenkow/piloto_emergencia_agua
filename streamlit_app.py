import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import json
import requests
import geopandas as gpd

st.set_page_config(
    page_title="Vigiagua Emergência",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state='collapsed')

# Lê os dados de um arquivo Excel online
@st.cache_data
def read_dados():
    dados_function = pd.read_csv('pontos_captacao_rs_2024_com_lat_lon.csv')
    
    return dados_function

dados = read_dados()
col1, col2 = st.columns([1,2])
filtros_container = st.container()
with filtros_container:
    with col1:
        crs = st.multiselect('Coordenadoria Regional de Saúde', options=sorted(dados['Regional de Saúde'].unique()), default=dados['Regional de Saúde'].unique(), placeholder='Selecione uma CRS', key='crs')
        tipo_forma_abastecimento = st.multiselect('Tipo da forma de abastecimento', options = ['SAA','SAC','SAI'], default=['SAA','SAC','SAI'])
            
        # Cria um seletor para escolher o município com base na Regional de Saúde selecionada
        #municipio = st.selectbox('MUNICÍPIO', options=sorted(dados[dados['Regional de Saúde']==crs]['Município'].unique()), index=None, placeholder='Selecione uma município', key='municipio')
               
        # Criação do DataFrame
        if crs != None:
            df = dados[(dados['Regional de Saúde'].isin(crs))&(dados['Tipo da Forma de Abastecimento'].isin(tipo_forma_abastecimento))].reset_index(drop=True)
        
        else:
            df = dados.copy()

with col2:
    # URL do arquivo GeoJSON
    url = 'https://github.com/andrejarenkow/geodata/raw/main/municipios_rs_CRS/RS_Municipios_2021.json'
    
    # Carregar o arquivo GeoJSON via URL
    response = requests.get(url)
    geojson_data = response.json()
    
    
    # Configurar o token do Mapbox
    token = 'pk.eyJ1IjoiYW5kcmUtamFyZW5rb3ciLCJhIjoiY2xkdzZ2eDdxMDRmMzN1bnV6MnlpNnNweSJ9.4_9fi6bcTxgy5mGaTmE4Pw'
    px.set_mapbox_access_token(token)
    
    
    
    # Criação do mapa com os pontos
    fig = px.scatter_mapbox(
        df, 
        lat='Latitude_corrigida', 
        lon='Longitude_corrigida', 
        height=800,
        hover_name='Nome da Forma de Abastecimento', 
        hover_data=['Município', 'Nome da Instiuição'], 
        title = 'Formas de abastecimento com geolocalização',
        color='Tipo da Forma de Abastecimento'
    )
    
    
    
    # Configuração do mapa
    fig.update_layout(
        mapbox_style="dark",
        mapbox_zoom=6,
        mapbox_center={"lat": -29.5, "lon": -53.5}
    )
    
    st.plotly_chart(fig)
