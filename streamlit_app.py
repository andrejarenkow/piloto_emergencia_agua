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
from folium import IFrame

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
    link_planilha = 'https://docs.google.com/spreadsheets/d/e/2PACX-1vQkzpN-gUEQdxaWa6WI1UsI3DGvILGZRTnKogYn5k-KgW5eBzpv36pJJut73U7FjGeZjPuZeBA2p30u/pub?output=xlsx'

    dados_vmp = pd.read_excel(link_planilha, sheet_name='VMP')
    dados_vmp = dados_vmp.set_index('Parâmetro').to_dict()['VMP']
    
    dados_coletas = pd.read_excel(link_planilha, sheet_name='ID das amostras')
    dados_coletas = dados_coletas[dados_coletas['Tipo de amostra'] != 'branco de ácido'].reset_index(drop=True)

    # completar valores foward fill
    for i in ['Semana de coleta', 'CRS', 'Município', 'Nome da forma de abastecimento']:
      dados_coletas[i].fillna(method='ffill', inplace=True)
      
    dados = pd.read_excel(link_planilha,
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

    dados_resultados = pd.read_excel(link_planilha, sheet_name='Resultados')
    # Função para definir o valor da nova coluna
    def determinar_tipo(id_amostra):
        if id_amostra.endswith('BT'):
            return 'Bruta'
        elif id_amostra.endswith('TR'):
            return 'Tratada'
        else:
            return 'Indefinido'
    
    # Aplicar a função para criar a nova coluna condicional
    dados_resultados['Tipo de Amostra'] = dados_resultados['ID da Amostra'].apply(determinar_tipo)
    
    # Criar coluna VMP
    dados_resultados['VMP'] = dados_resultados['Ensaio'].map(dados_vmp)
    
    # Criar do indicador de acordo com o VMP
    dados_resultados['Indicador'] = round(dados_resultados['Resultado numerico (mg/L)']/dados_resultados['VMP'],2)
    
    # Merge com a tabela dados
    dados_resultados = dados_resultados.merge(dados_coletas, on='ID da Amostra', how='left')
    dados_resultados = dados_resultados.merge(dados, on='Nome da forma de abastecimento', how='left')

    # Alterar o formato da data DD/MM/AAAA com strftime
    dados_resultados['Data da Coleta'] = dados_resultados['Data da Coleta'].dt.strftime('%d/%m/%Y')
    
    return gdf_pontos, gdf_area_inundada, dados, dados_coletas, dados_resultados

gdf_pontos, gdf_area_inundada, dados, dados_coletas, dados_resultados = read_dados()
dicionario_pontos = dados.set_index('Nome da forma de abastecimento').to_dict()

# Criação das abas
tab_producao, tab_resultados, tab_planejamento = st.tabs(['Pontos escolhidos','Resultados','Metodologia'])

with tab_producao:
    col1_, col2_ = st.columns([1,1])      
    
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
            st.write(f"Município: {dicionario_pontos['Municipio'][selecionado]}")
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

with tab_resultados:
    coluna_grafico, coluna_mapa = st.columns(2)
    with coluna_grafico:
        # Define a paleta de cores
        color_map = {
            'Tratada': 'royalblue',  # Defina as cores desejadas para 'Tratada'
            'Bruta': 'darkslategray'    # Defina as cores desejadas para 'Bruta'
        }
        fig = px.strip(dados_resultados.sort_values('Ensaio'), x="Ensaio", y="Indicador", color='Tipo de Amostra',
                       title = 'Resultados relativos ao VMP',
                       color_discrete_map=color_map,
                       hover_name = 'Nome da forma de abastecimento', 
                       hover_data = [
                           'Município',
                           'Tipo de Amostra',
                           'Conclusão',
                           'Data da Coleta',
                                     ])

        # Adicionar um retângulo para pintar o fundo
        fig.add_shape(
            type="rect",
            x0=-0.5, x1=len(dados_resultados['Ensaio'].unique()) - 0.5,  # Abranger todas as categorias de 'Ensaio'
            y0=0, y1=0.5,  # Definir os limites verticais do retângulo
            fillcolor="forestgreen",
            opacity=0.3,
            layer="below",  # Colocar o retângulo atrás dos dados
            line_width=0
        )
        
        fig.add_shape(
            type="rect",
            x0=-0.5, x1=len(dados_resultados['Ensaio'].unique()) - 0.5,  # Abranger todas as categorias de 'Ensaio'
            y0=0.5, y1=0.75,  # Definir os limites verticais do retângulo
            fillcolor="Gold",
            opacity=0.3,
            layer="below",  # Colocar o retângulo atrás dos dados
            line_width=0
        )
        fig.add_shape(
            type="rect",
            x0=-0.5, x1=len(dados_resultados['Ensaio'].unique()) - 0.5,  # Abranger todas as categorias de 'Ensaio'
            y0=0.75, y1=1,  # Definir os limites verticais do retângulo
            fillcolor="Orange",
            opacity=0.3,
            layer="below",  # Colocar o retângulo atrás dos dados
            line_width=0
        )
        fig.add_shape(
            type="rect",
            x0=-0.5, x1=len(dados_resultados['Ensaio'].unique()) - 0.5,  # Abranger todas as categorias de 'Ensaio'
            y0=1, y1=dados_resultados['Indicador'].max()*1.2,  # Definir os limites verticais do retângulo
            fillcolor="Red",
            opacity=0.3,
            layer="below",  # Colocar o retângulo atrás dos dados
            line_width=0
        )
        # Remover as linhas de grade
        fig.update_layout(
            xaxis=dict(showgrid=False),
            yaxis=dict(showgrid=False),
            xaxis_title='Parâmetro',  # Substitua pelo título desejado para o eixo X
            yaxis_title='Indicador (Resultado/VMP)',  # Substitua pelo título desejado para o eixo Y
        )
        st.plotly_chart(fig)

    with coluna_mapa:
        # Parâmetro selecionado
        parametro_selecionado = st.selectbox('Parâmetro', options=sorted(dados_resultados['Ensaio'].unique()))
        
        # Filtrar os dados com base no parâmetro selecionado
        dados_resultados_mapa = dados_resultados[dados_resultados['Ensaio'] == parametro_selecionado].reset_index(drop=True)
        
        # Cria novas colunas de latitude e longitude com base no 'Tipo de Amostra'
        dados_resultados_mapa['Latitude'] = dados_resultados_mapa.apply(
            lambda row: row['Latitude ETA'] if row['Tipo de Amostra'] == 'Bruta' else row['Latitude ponto captação'], axis=1)
        dados_resultados_mapa['Longitude'] = dados_resultados_mapa.apply(
            lambda row: row['Longitude ETA'] if row['Tipo de Amostra'] == 'tratada' else row['Longitude ponto captação'], axis=1)
        
        # Função para determinar a cor com base no valor do Indicador
        def get_color(indicador):
            if 0 <= indicador <= 0.5:
                return 'forestgreen'
            elif 0.5 < indicador <= 0.75:
                return 'gold'
            elif 0.75 < indicador <= 1:
                return 'orange'
            else:
                return 'red'
        
        # Inicializa o mapa centrado em uma localização média
        mapa = folium.Map(location=[-30.5, -53.5], zoom_start=7)

        # Adiciona a camada OpenStreetMap
        folium.TileLayer(
            tiles='https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
            attr='OpenStreetMap',
            name='OpenStreetMap'
        ).add_to(mapa)
        

        # Adiciona a camada Stadia.AlidadeSatellite
        folium.TileLayer(
            tiles='https://{s}.stadiamaps.com/tiles/alidade_satellite/{z}/{x}/{y}{r}.jpg',
            attr='&copy; CNES, Distribution Airbus DS, © Airbus DS, © PlanetObserver (Contains Copernicus Data) | &copy; <a href="https://www.stadiamaps.com/" target="_blank">Stadia Maps</a> &copy; <a href="https://openmaptiles.org/" target="_blank">OpenMapTiles</a> &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
            name='Alidade Satellite'
        ).add_to(mapa)

        # Adiciona uma camada de controle para alternar entre as camadas
        folium.LayerControl().add_to(mapa)
        
        # Adiciona pontos ao mapa
        for _, row in dados_resultados_mapa.dropna(subset=['Indicador']).iterrows():
            popup_html = f"""
            <div style="width: 400px;">
                <strong>Município:</strong> {row['Município']}<br>
                <strong>Forma de abastecimento:</strong> {row['Nome da forma de abastecimento']}<br>
                <strong>Tipo de amostra:</strong> {row['Tipo de amostra']}<br>
                <strong>Resultado (mg/L):</strong> {row['Resultado (mg/L)']}<br>
                <strong>Indicador:</strong> {row['Indicador']}
            </div>
            """
            iframe = IFrame(html=popup_html, width=430, height=120)
            popup = folium.Popup(iframe, max_width=430)
        
            folium.CircleMarker(
                location=[row['Latitude'], row['Longitude']],
                radius=5,  # Ajusta o tamanho do marcador conforme necessário
                color=get_color(row['Indicador']),
                fill=True,
                fill_opacity=0.7,
                popup=popup
            ).add_to(mapa)
        
        # Salva o mapa em um arquivo HTML
        st_folium(mapa, width=725, returned_objects=[])
