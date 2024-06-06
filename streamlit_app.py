import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import json
import requests
import geopandas as gpd

st.set_page_config(
    page_title="Vigiagua Emergência",
    page_icon=":potable_water:",
    layout="wide",
    initial_sidebar_state='collapsed')

# Lê os dados de um arquivo Excel online
@st.cache_data
def read_dados():
    dados_function = pd.read_csv('pontos_captacao_rs_2024_com_lat_lon.csv')
    # Função para adicionar '0' se o comprimento for menor que 7
    def pad_zero(value):
        if len(value) < 7:
            return value.zfill(7)
        return value

    # Aplicar a função à coluna 'Regional de Saúde'
    dados_function['Regional de Saúde'] = dados_function['Regional de Saúde'].apply(pad_zero)

    # Função para converter valores para negativos
    def to_negative(value):
        return -abs(value)
    
    # Aplicar a função à coluna 'Valores'
    dados_function['Latitude_corrigida'] = dados_function['Latitude_corrigida'].apply(to_negative)
    dados_function['Longitude_corrigida'] = dados_function['Longitude_corrigida'].apply(to_negative)

    return dados_function

dados = read_dados()
st.subheader('Formas de abastecimento de água geolocalizadas e área inundada RS, maio 2024')
col1, col2 = st.columns([1,2])
filtros_container = st.container(border=True)
    # URL do raster do Google Earth Engine
raster_url = 'https://earthengine.googleapis.com/v1/projects/earthengine-legacy/maps/96bb4b396c3f558be1dca749f38fc520-28b3e69b7b9742b50e651234a75706cc/tiles/{z}/{x}/{y}'
raster_url_uso_solo = 'https://earthengine.googleapis.com/v1/projects/earthengine-legacy/maps/3511bd8ab7783ca38671e6fefbac6ba5-59a31765405c004d57b9f752ac3336a2/tiles/{z}/{x}/{y}'

 
with filtros_container:
    with col1:
        crs = st.multiselect('Coordenadoria Regional de Saúde', options=sorted(dados['Regional de Saúde'].unique()), default=sorted(dados['Regional de Saúde'].unique()), placeholder='Selecione uma CRS', key='crs')
        tipo_forma_abastecimento = st.multiselect('Tipo da forma de abastecimento', options = ['SAA','SAC','SAI'], default=['SAA','SAC','SAI'])
            
        # Cria um seletor para escolher o município com base na Regional de Saúde selecionada
        #municipio = st.selectbox('MUNICÍPIO', options=sorted(dados[dados['Regional de Saúde']==crs]['Município'].unique()), index=None, placeholder='Selecione uma município', key='municipio')
               
        # Criação do DataFrame
        if crs != None:
            df = dados[(dados['Regional de Saúde'].isin(crs))&(dados['Tipo da Forma de Abastecimento'].isin(tipo_forma_abastecimento))].reset_index(drop=True)
        
        else:
            df = dados.copy()

        # Seleção mapa base
        mapa_base = st.selectbox('Selecione o mapa base', options = ["open-street-map", "carto-positron", "carto-darkmatter",
                                                                     "basic", "streets", "outdoors", "light", "dark", "satellite",
                                                                     "satellite-streets" ])
        # Transparências
        transparencia_raster = st.slider('Transparência da mancha de inundação', value=0.8)
        transparencia_pontos = st.slider('Transparência dos pontos', value=0.8)

        # Cor das linhas
        cor_municipios = st.selectbox('Selecione a cor das linhas', options = ['black','white'])

        # Cor das linhas
        selecao_raster = st.selectbox('Selecione o raster', options = [raster_url,raster_url_uso_solo])

        # Cor dos pontos
        cor_superficial = st.color_picker('Cor da captação SUPERFICIAL','#FF4B4B')
        cor_subterraneo = st.color_picker('Cor da captação SUBTERRANEO','#ffcb00')

with col2:
    # URL do arquivo GeoJSON
    url = 'https://github.com/andrejarenkow/geodata/raw/main/municipios_rs_CRS/RS_Municipios_2021.json'
    
    # Carregar o arquivo GeoJSON via URL
    response = requests.get(url)
    geojson_data = response.json()
    
    
    # Configurar o token do Mapbox
    token = 'pk.eyJ1IjoiYW5kcmUtamFyZW5rb3ciLCJhIjoiY2xkdzZ2eDdxMDRmMzN1bnV6MnlpNnNweSJ9.4_9fi6bcTxgy5mGaTmE4Pw'
    px.set_mapbox_access_token(token)

    # Definir um mapa de cores discreto personalizado
    color_discrete_map = {
        'SAA': '#FFCB00',
        'SAC': '#FFCB00',
        'SAI': '#FFCB00',
        # Adicione mais categorias e cores conforme necessário
    }
    
    
    
   
    # Criação do mapa com os pontos
    fig = px.scatter_mapbox(
        df, 
        lat='Latitude_corrigida', 
        lon='Longitude_corrigida', 
        height=800,
        hover_name='Nome da Forma de Abastecimento', 
        hover_data=['Município','Tipo de captação', 'Nome da Instiuição',], 
        color='Tipo de captação',
        color_discrete_sequence=[cor_superficial,cor_subterraneo],
        opacity=transparencia_pontos
        
    )
    
    # Configuração do mapa

    # Carregar o arquivo GeoJSON
    geojson_url = 'RS_Municipios_2021 (4).json'  # Substitua pelo caminho para o seu arquivo GeoJSON
    with open(geojson_url) as f:
        geojson_data = json.load(f)

    geojson_url = 'mapbiomas-brazil-collection-80-area.geojson'  # Substitua pelo caminho para o seu arquivo GeoJSON
    with open(geojson_url) as f:
        geojson_data_indigena = json.load(f)
    
    fig.update_layout(
        mapbox_style=mapa_base,
        mapbox_zoom=5.5,
        mapbox_center={"lat": (df['Latitude_corrigida'].max() + df['Latitude_corrigida'].min()) / 2,
                       "lon": (df['Longitude_corrigida'].max() + df['Longitude_corrigida'].min()) / 2},
        mapbox_layers=[
            {
                'sourcetype': 'raster',
                'source': [raster_url],
                'below': 'traces',
                'opacity': transparencia_raster  # Define a opacidade da camada raster
            },
            {
                    'sourcetype': 'geojson',
                    'source': geojson_data,
                    'type': 'line',  # Tipo de camada (fill, line, symbol)
                    'color': cor_municipios,  # Cor da camada GeoJSON
                    'below': 'traces',
                    'line': {'width':1},
                    'opacity':0.5
                },
             {
                    'sourcetype': 'geojson',
                    'source': geojson_data_indigena,
                    'type': 'fill',  # Tipo de camada (fill, line, symbol)
                    'color': 'red',  # Cor da camada GeoJSON
                    'below': 'traces',
                    'line': {'width':1},
                    'opacity':1
                },
        ]
    )


    
    
    st.plotly_chart(fig)
