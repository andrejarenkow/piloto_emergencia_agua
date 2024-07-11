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
def read_dados(ttl=50):

    dados_coletas = pd.read_excel('https://docs.google.com/spreadsheets/d/e/2PACX-1vQkzpN-gUEQdxaWa6WI1UsI3DGvILGZRTnKogYn5k-KgW5eBzpv36pJJut73U7FjGeZjPuZeBA2p30u/pub?output=xlsx',
                      sheet_name='ID das amostras')

    dados_coletas = dados_coletas[dados_coletas['Tipo de amostra'] != 'branco de ácido'].reset_index(drop=True)

    # completar valores foward fill
    for i in ['Semana de coleta', 'CRS', 'Município', 'Nome da forma de abastecimento']:
      dados_coletas[i].fillna(method='ffill', inplace=True)
      

    dados = pd.read_excel('https://docs.google.com/spreadsheets/d/e/2PACX-1vQkzpN-gUEQdxaWa6WI1UsI3DGvILGZRTnKogYn5k-KgW5eBzpv36pJJut73U7FjGeZjPuZeBA2p30u/pub?output=xlsx',
                      sheet_name='Pontos de coleta')

    dados = dados.dropna(subset=['Latitude ETA']).reset_index(drop=True)
    dados['cor'] = 'red'
    
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

    return gdf_pontos, gdf_area_inundada, dados, dados_coletas

gdf_pontos, gdf_area_inundada, dados, dados_coletas = read_dados()
dicionario_pontos = dados.set_index('Nome da forma de abastecimento').to_dict()
#gdf_pontos = pd.concat( [gdf_pontos_500_metros, gdf_pontos_dentro], ignore_index=True)
#st.title('Formas de abastecimento de água geolocalizadas e área inundada RS, maio 2024')
tab_producao, tab_planejamento = st.tabs(['Pontos escolhidos','Planejamento'])

with tab_producao:
    col1_, col2_ = st.columns([1,1])

    #with col1_:
        
    
    # Supondo que dados seja o DataFrame original
    df = dados.copy()
    
    # Cria o mapa centralizado na média das coordenadas
    map_center = [-31, -52]
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
    #folium.GeoJson(
    #    gdf_area_inundada,
    #    name='Área Inundada',
    #    style_function=estilo_area_inundada
    #).add_to(m)
    
    # Cria um FeatureGroup para cada tipo de ponto
    fg_eta = folium.FeatureGroup(name="Ponto da ETA")
    fg_captacao = folium.FeatureGroup(name="Ponto de Captação")
    
    # Adiciona os pontos "Ponto da ETA" ao FeatureGroup correspondente
    for _, row in df.iterrows():
        folium.Marker(
            location=[row['Latitude ETA'], row['Longitude ETA']],
            popup=row['Nome da forma de abastecimento'],
            icon=folium.Icon(color='green')
        ).add_to(fg_eta)
    
    # Adiciona os pontos "Ponto de Captação" ao FeatureGroup correspondente
    for _, row in df.iterrows():
        folium.Marker(
            location=[row['Latitude ponto captação'], row['Longitude ponto captação']],
            popup=row['Nome da forma de abastecimento'],
            icon=folium.Icon(color='blue')  # Alterar a cor conforme necessário
        ).add_to(fg_captacao)
    
    # Adiciona os FeatureGroups ao mapa
    fg_eta.add_to(m)
    fg_captacao.add_to(m)
    
    # Adicionar um controle de camadas
    folium.LayerControl().add_to(m)

    with col2_:
        st_data = st_folium(m,
                            key="new",
                            feature_group_to_add=fg_eta,
                            height=600,
                            width=800,
                           returned_objects=["last_object_clicked_popup"])


    with col1_:
        st.metric('Total de pontos', len(df))
        selecionado = st_data["last_object_clicked_popup"]
        # Supondo que 'dados' é o seu DataFrame
        ETA_escolhida = selecionado
        
        # Filtrando os dados para a ETA escolhida
        eta = dados_coletas[dados_coletas['Nome da forma de abastecimento'] == ETA_escolhida].reset_index(drop=True)
        
        # Convertendo a coluna "Data da Coleta" para datetime, se ainda não estiver
        eta['Data da Coleta'] = pd.to_datetime(eta['Data da Coleta'], errors='coerce')
        
        # Extraindo datas únicas e convertendo para o formato desejado
        datas_unicas = eta['Data da Coleta'].dropna().dt.strftime('%d/%m/%Y').unique()
        
        # Convertendo a lista de datas únicas para uma string separada por vírgulas
        datas_formatadas = ', '.join(datas_unicas)
        
        print(f'Datas da coleta da {ETA_escolhida}: {datas_formatadas}')

        if (selecionado) != None:
            
            st.write(f"Ponto selecionado: {selecionado}")
            st.write(f"Município: {dicionario_pontos['Município'][selecionado]}")
            st.write(f"Regional de Saúde: {dicionario_pontos['CRS'][selecionado]}")
            st.write(f"Manancial: {dicionario_pontos['Nome do manancial'][selecionado]}")
            st.write(f"Instituição responsável: {dicionario_pontos['Instituição responsável'][selecionado]}")
            st.write(f"Código SISAGUA: {dicionario_pontos['Código da forma de abastecimento SISAGUA'][selecionado]}")
            st.write(f'Datas da coleta: {datas_formatadas}')

        else:
            st.write('Selecione um ponto no mapa')
        


with tab_planejamento:
    col1, col2 = st.columns([1,1])
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
    # Verificar os tipos de geometria no GeoDataFrame
    # Filtrar apenas geometrias do tipo Point
    #gdf_pontos = gdf_pontos[gdf_pontos.geometry.type == 'Point']
    # Extrair latitude e longitude das geometrias
    gdf_pontos['lat'] = gdf_pontos.geometry.centroid.y
    gdf_pontos['lon'] = gdf_pontos.geometry.centroid.x
    # Passo 2: Converter o GeoDataFrame em GeoJSON
    geojson = gdf_area_inundada.to_crs(epsg=4326).__geo_interface__
    # Passo 3: Criar o mapa scatter_mapbox usando Plotly Express
    
    fig = px.scatter_mapbox(
        gdf_pontos,
        lat='lat',
        lon='lon',
        color='Distância',
        zoom=6,
        height=800
    )
    
    # Adicionar o GeoJSON ao mapa
    # Configurar o token do Mapbox
    token = 'pk.eyJ1IjoiYW5kcmUtamFyZW5rb3ciLCJhIjoiY2xkdzZ2eDdxMDRmMzN1bnV6MnlpNnNweSJ9.4_9fi6bcTxgy5mGaTmE4Pw'
    px.set_mapbox_access_token(token)
    fig.update_layout(mapbox_style="carto-darkmatter")
    fig.update_layout(
        mapbox={
            'layers': [
                {
                    'source': geojson,
                    'type': "fill",
                    'color': 'rgba(173, 216, 230, 0.3)'
                }
            ]
        }
    )
    
    # Exibir o mapa
    with col2:
        st.plotly_chart(fig)
