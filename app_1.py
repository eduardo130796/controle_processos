import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import plotly.express as px
import re
from datetime import datetime
import numpy as np
import holidays

st.set_page_config(
    page_title="Controle de Processos",
    page_icon="🧊",
    layout="wide",)
# Carrega os dados
#df = pd.read_parquet("atividades_completas.parquet")

url = "https://github.com/eduardo130796/controle_processos/blob/main/atividades_completas.parquet"

# Carrega o arquivo parquet
df = pd.read_parquet(url)
usuarios_nomes = {
    "adleide.falcao": "Adleide Falcão",
    "amanda.levyski": "Amanda Levyski",
    "celso.cruz": "Celso Cruz",
    "daniela.evangelista": "Daniela Evangelista",
    "dayane.luiz": "Dayane Luiz",
    "diogo.melo": "Diogo Melo",
    "eduardo.junior": "Eduardo Júnior",
    "gabriela.bruno": "Gabriela Bruno",
    "gelvaci.pinto": "Gelvaci Pinto",
    "girlene.alves": "Girlene Alves",
    "isabela.sanches": "Isabela Sanches",
    "isabella.vasconcelos": "Isabella Vasconcelos",
    "izabella.ferreira": "Izabella Ferreira",
    "jerssika.nogueira": "Jerssika Nogueira",
    "jessica.fernandes": "Jéssica Fernandes",
    "jessica.torres": "Jessica Torres",
    "julia.adryenne": "Julia Adryenne",
    "karolina.espezin": "Karolina Espezin",
    "leticia.jesus": "Letícia Jesus",
    "luiza.lacerda": "Luiza Lacerda",
    "maria.furtado": "Maria Furtado",
    "rafaella.fonseca": "Rafaella Fonseca",
    "roberto.rocha": "Roberto Rocha",
    "samuel.novais": "Samuel Novais",
    "sueli.vieira": "Sueli Vieira",
    "vandeir.scheffelt": "Vandeir Scheffelt",
    "vanessa.vaucher": "Vanessa Vaucher"
}

# Substitui os IDs de usuário pelos nomes correspondentes
df['Usuário'] = df['Usuário'].map(usuarios_nomes)

df["Data/Hora"] = pd.to_datetime(df["Data/Hora"], dayfirst=True, errors="coerce")

df_original=df.copy()
# Normaliza datas para o filtro (apenas o filtro, sem alterar o df original)

# Ordena por Processo e Data
df = df.sort_values(by=["Processo", "Data/Hora", "Descrição"], ascending=[True, True, False])

# Agora vem a lógica de rastreamento por passagem
resultados = []

for processo, grupo in df.groupby("Processo"):
    grupo = grupo.reset_index(drop=True)
    processo_aberto = False
    entrada_atual = {}
    responsavel_atribuido = None

    for _, row in grupo.iterrows():
        descricao = str(row["Descrição"]).lower()
        data = row["Data/Hora"]
        usuario = row["Usuário"]
        unidade = row["Unidade"]
        tipo = row["TipoProcesso"]

        if "processo atribuído para" in descricao:
            match = re.search(r"processo atribuído para ([\w\.\-]+)", descricao)
            if match:
                novo_responsavel = match.group(1)
                # Substituindo o nome pelo nome completo usando o dicionário
                if novo_responsavel in usuarios_nomes:
                    novo_responsavel = usuarios_nomes[novo_responsavel]
                
                if processo_aberto:
                    entrada_atual["Responsável"] = novo_responsavel
                else:
                    responsavel_atribuido = novo_responsavel

        elif any(palavra in descricao for palavra in ["recebido na unidade", "reabertura", "processo público gerado"]):
            if not processo_aberto:
                entrada_atual = {
                    "Processo": processo,
                    "Data Recebido": data,
                    "Usuário Recebeu": usuario,
                    "Responsável": responsavel_atribuido or usuario,
                    "Unidade": unidade,
                    "Tipo": tipo,
                    "Data Conclusão": None,
                    "Usuário Concluiu": None
                }
                processo_aberto = True
                responsavel_atribuido = None

        elif "conclusão" in descricao:
            if processo_aberto:
                entrada_atual["Data Conclusão"] = data
                entrada_atual["Usuário Concluiu"] = usuario
                resultados.append(entrada_atual)
                processo_aberto = False
                entrada_atual = {}
                responsavel_atribuido = None

    if processo_aberto and entrada_atual:
        entrada_atual["Data Conclusão"] = None
        entrada_atual["Usuário Concluiu"] = None
        resultados.append(entrada_atual)


feriados = holidays.Brazil(years=datetime.now().year)  # Pega o ano atual
# Processa prazos
for item in resultados:
    data_inicio = pd.to_datetime(item["Data Recebido"], errors="coerce")
    data_fim = pd.to_datetime(item["Data Conclusão"], errors="coerce") if item["Data Conclusão"] else datetime.now()
    # Gerar os feriados do ano de início e do ano de fim (caso atravesse anos diferentes)
    anos = list(range(data_inicio.year, data_fim.year + 1))
    feriados = holidays.Brazil(years=anos, prov="DF")

    # Calcular dias úteis considerando feriados
    dias = np.busday_count(
        data_inicio.date(),
        data_fim.date(),
        holidays=list(feriados.keys())  # Passar só as datas
    )
    status = "Concluído" if item["Data Conclusão"] else "Aberto"

    if dias <= 5:
        cor = "Verde"
        prazo = "0-5"
    elif dias <= 10:
        cor = "Amarelo"
        prazo = "6-10"
    else:
        cor = "Vermelho"
        prazo = "11+"

    item["Status"] = status
    item["Dias de Prazo"] = dias
    item["Faixa de Prazo"] = prazo

# DataFrame final
df_resultado = pd.DataFrame(resultados)
df_resultado = df_resultado.sort_values(by="Responsável", ascending=True)

with st.sidebar:
    st.write("Filtros:")
    data_inicio = st.date_input("Data inicial", value=df_resultado["Data Recebido"].min().date())
    data_fim = st.date_input("Data final", value=df_resultado["Data Recebido"].max().date())
    status = df_resultado["Status"].dropna().unique()
    status_escolhido = st.selectbox("Filtrar por Status (opcional)", options=["Todas"] + list(status))

if status_escolhido != "Todas":
    df_resultado = df_resultado[df_resultado["Status"] == status_escolhido]

filtro_inicio = pd.to_datetime(data_inicio).normalize()
filtro_fim = pd.to_datetime(data_fim).normalize() + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)

# Filtra por data antes de processar os dados
df_resultado = df_resultado[
    (df_resultado["Data Recebido"] >= filtro_inicio) &
    (df_resultado["Data Recebido"] <= filtro_fim)
]

# Filtro por unidade
with st.sidebar:
    unidades = df_resultado["Unidade"].dropna().unique()
    unidade_escolhida = st.selectbox("Filtrar por unidade (opcional)", options=["Todas"] + list(unidades))

if unidade_escolhida != "Todas":
    df_resultado = df_resultado[df_resultado["Unidade"] == unidade_escolhida]

# ==============================
# EXIBIÇÕES
# ==============================

st.subheader("📂 Controle de Processos")

col1, col2, col3, col4 = st.columns(4)
col1.metric("📂 Passagens na Unidade", len(df_resultado))
col2.metric("📁 Processos Únicos", df_resultado["Processo"].nunique())
col3.metric("🟡 Em Aberto", df_resultado[df_resultado["Status"] == "Aberto"].shape[0])
col4.metric("✅ Concluídos", df_resultado[df_resultado["Status"] == "Concluído"].shape[0])

##############################
df_resultado["0-5"] = df_resultado["Faixa de Prazo"].apply(lambda x: 1 if x == "0-5" else 0)
df_resultado["6-10"] = df_resultado["Faixa de Prazo"].apply(lambda x: 1 if x == "6-10" else 0)
df_resultado["11+"] = df_resultado["Faixa de Prazo"].apply(lambda x: 1 if x == "11+" else 0)

#####################################
def grafico_unidade(df_resultado):

    #st.subheader("📉 Gráfico por Unidade e Faixa de Prazo")

    # Categorizar a "Faixa de Prazo"
    df_resultado["Faixa de Prazo"] = pd.Categorical(df_resultado["Faixa de Prazo"], categories=["0-5", "6-10", "11+"], ordered=True)

    # Agrupar os dados por responsável e faixa de prazo
    grafico_df = df_resultado.groupby(["Unidade", "Faixa de Prazo"]).size().reset_index(name="Quantidade")


    # Agrupar agora por responsável para obter a quantidade total de processos por responsável
    grafico_total_df = grafico_df.groupby("Unidade")["Quantidade"].sum().reset_index(name="Quantidade Total")

    # Definir cores mais suaves
    cores = {"0-5": "#1cc88a", "6-10": "#f6c23e", "11+": "#e74a3b"}
    grafico_df = grafico_df.sort_values(by="Unidade", ascending=False)

    # Criar o gráfico de barras horizontais
    fig = px.bar(
        grafico_df,
        x="Quantidade",
        y="Unidade",
        color="Faixa de Prazo",
        color_discrete_map=cores,
        category_orders={"Faixa de Prazo": ["0-5", "6-10", "11+"]},
        barmode="stack",  # Empilhar as barras para facilitar a visualização proporcional
    )

    # Adicionar a quantidade total de processos ao lado das barras
    for i in range(len(grafico_total_df)):
        fig.add_annotation(
            x=grafico_total_df.iloc[i]["Quantidade Total"] + 5,  # Ajuste para colocar o texto ao lado da barra
            y=grafico_total_df.iloc[i]["Unidade"],
            text=str(grafico_total_df.iloc[i]["Quantidade Total"]),
            showarrow=False,
            font=dict(size=12, color="black"),
            align="left",  # Alinhar o texto à esquerda para ficar ao lado da barra
        )

    # Definindo altura com base no número de unidades
    altura_base = 300
    altura_por_unidade = 40
    altura_final = altura_base + (len(grafico_total_df) * altura_por_unidade)

    fig.update_layout(
        title="Quantidade Total de Processos por Unidade e Faixa de Prazo",
        xaxis_title="",
        yaxis_title="Unidade",
        xaxis=dict(showgrid=False, visible=False),
        yaxis=dict(showgrid=False),
        plot_bgcolor="white",
        margin=dict(l=40, r=120, t=40, b=80),
        showlegend=True,
        bargap=0.5,  # novo ajuste
        height=altura_final,  # novo ajuste
        legend_title="Faixa de Prazo",
        legend=dict(
            x=1.05,
            y=1,
            traceorder='normal',
            orientation='v',
            font=dict(size=12)
        ),
    )

    # Remover os valores das barras para deixar o gráfico mais limpo
    fig.update_traces(marker=dict(line=dict(width=1, color="white")))

    # Exibir o gráfico
    st.plotly_chart(fig)


def grafico_media_prazos(df_resultado):

    # 🔵 Agrupa por Unidade e Responsável (caso esteja filtrando, agrupa só responsáveis)
    if unidade_escolhida == "Todas":
        # Calcula média de prazo por Unidade (geral)
        df_media = (
            df_resultado
            .groupby("Unidade")["Dias de Prazo"]
            .mean()
            .reset_index()
            .rename(columns={"Dias de Prazo": "Dias de Prazo Médio"})
        )

        fig = px.bar(
            df_media,
            x="Dias de Prazo Médio",
            y="Unidade",
            orientation="h",
            text="Dias de Prazo Médio",
            title="Média de Dias de Prazo por Unidade"
        )
        fig.update_layout(
            xaxis_title="Média de Dias Úteis",
            yaxis_title="Unidade",
            plot_bgcolor="white",
            margin=dict(l=40, r=20, t=60, b=40)
        )
        fig.update_traces(textposition="outside")

    else:
        # Calcula média de prazo por Responsável dentro da unidade
        df_media = (
            df_resultado
            .groupby("Responsável")["Dias de Prazo"]
            .mean()
            .reset_index()
            .rename(columns={"Dias de Prazo": "Dias de Prazo Médio"})
        )

        fig = px.bar(
            df_media,
            x="Dias de Prazo Médio",
            y="Responsável",
            orientation="h",
            text="Dias de Prazo Médio",
            title=f"Média de Dias de Prazo dos Responsáveis - {unidade_escolhida}"
        )
        fig.update_layout(
            xaxis_title="Média de Dias Úteis",
            yaxis_title="Responsável",
            plot_bgcolor="white",
            margin=dict(l=40, r=20, t=60, b=40)
        )
        fig.update_traces(textposition="outside")

    # 🔵 Exibe o gráfico
    st.plotly_chart(fig)

# --- Exemplo de chamada
col1, col2 = st.columns(2)

with col1:
    grafico_unidade(df_resultado)
with col2:
    grafico_media_prazos(df_resultado)





    ##########################################
def grafico_resposavel_prazo(df_resultado):
    #st.subheader("📉 Gráfico por Responsável e Faixa de Prazo")

    # Categorizar a "Faixa de Prazo"
    df_resultado["Faixa de Prazo"] = pd.Categorical(df_resultado["Faixa de Prazo"], categories=["0-5", "6-10", "11+"], ordered=True)

    # Agrupar os dados por responsável e faixa de prazo
    grafico_df = df_resultado.groupby(["Responsável", "Faixa de Prazo"]).size().reset_index(name="Quantidade")


    # Agrupar agora por responsável para obter a quantidade total de processos por responsável
    grafico_total_df = grafico_df.groupby("Responsável")["Quantidade"].sum().reset_index(name="Quantidade Total")

    # Definir cores mais suaves
    cores = {"0-5": "#1cc88a", "6-10": "#f6c23e", "11+": "#e74a3b"}
    grafico_df = grafico_df.sort_values(by="Responsável", ascending=False)
    # Criar o gráfico de barras horizontais
    fig = px.bar(
        grafico_df,
        x="Quantidade",
        y="Responsável",
        color="Faixa de Prazo",
        color_discrete_map=cores,
        category_orders={"Faixa de Prazo": ["0-5", "6-10", "11+"]},
        barmode="stack",  # Empilhar as barras para facilitar a visualização proporcional
    )

    # Adicionar a quantidade total de processos ao lado das barras
    for i in range(len(grafico_total_df)):
        fig.add_annotation(
            x=grafico_total_df.iloc[i]["Quantidade Total"] + 3,  # Ajuste para colocar o texto ao lado da barra
            y=grafico_total_df.iloc[i]["Responsável"],
            text=str(grafico_total_df.iloc[i]["Quantidade Total"]),
            showarrow=False,
            font=dict(size=12, color="black"),
            align="left",  # Alinhar o texto à esquerda para ficar ao lado da barra
        )


    altura_base = 300
    altura_por_unidade = 40
    altura_final = altura_base + (len(grafico_total_df) * altura_por_unidade)
    # Ajustes de layout para suavizar a estética
    fig.update_layout(
        title="Quantidade Total de Processos por Responsável e Faixa de Prazo",
        xaxis_title="",
        yaxis_title="Responsável",
        xaxis=dict(showgrid=False, visible=False),  # Remover o eixo X
        yaxis=dict(showgrid=False),  # Remover linhas de grade no eixo Y
        plot_bgcolor="white",  # Fundo branco para um visual mais limpo
        barmode="stack",  # Barras empilhadas
        margin=dict(l=40, r=120, t=40, b=80),  # Ajustar margens para melhorar o layout
        showlegend=True,  # Exibir a legenda
        legend_title="Faixa de Prazo",
        legend=dict(
            x=1.05,  # Mover a legenda para fora do gráfico
            y=1,
            traceorder='normal',
            orientation='v',  # Colocar a legenda verticalmente
            font=dict(size=12)
        ),
        height=altura_final,  # Ajuste da altura para um gráfico mais equilibrado
    )

    # Remover os valores das barras para deixar o gráfico mais limpo
    fig.update_traces(marker=dict(line=dict(width=1, color="white")))

    # Exibir o gráfico
    st.plotly_chart(fig)


def exibir_processos(processos, registros_status, df_original, faixa_prazo, prazo):
    """Gera o HTML para exibir os processos de uma faixa de prazo específica."""
    if not processos:
        return ""
    
    html = f"<div class='processo-box'><span class='prazo-{faixa_prazo}'>Prazo {prazo} ({len(processos)} processos):</span></div>"
    html += "<div style='display:flex; flex-wrap: wrap; gap:5px; max-height: 250px; overflow-y: auto;'>"
    for proc in processos:
        tipo_processo = proc["Tipo"]
        numero_processo = proc["Processo"]
        data = proc["Data Recebido"]


        processo_info = registros_status[
            (registros_status["Processo"] == numero_processo) & 
            (registros_status["Data Recebido"] == data)
        ].iloc[0]
        data_entrada = pd.to_datetime(processo_info["Data Recebido"])
        data_conclusao = pd.to_datetime(processo_info["Data Conclusão"])
        status=processo_info["Status"]

        
        if status =="Aberto":
            eventos_no_periodo = df_original[
                (df_original["Processo"] == numero_processo) & 
                (df_original["Data/Hora"] >= data_entrada)& 
                (df_original["Data/Hora"] <= datetime.now())
            ].sort_values(by=["Data/Hora"], ascending=[False])
        else:    
            eventos_no_periodo = df_original[
                (df_original["Processo"] == numero_processo) & 
                (df_original["Data/Hora"] >= data_entrada) & 
                (df_original["Data/Hora"] <= data_conclusao)
            ].sort_values(by=["Data/Hora"], ascending=[False])
        
            

        html += f"""
        <details>
            <summary><span class='badge {faixa_prazo.lower()}' title='{tipo_processo}'> {numero_processo} </span></summary>
            <div style="margin-left:10px; margin-top:5px; font-size:12px;">"""

        if not eventos_no_periodo.empty:
            for _, evento in eventos_no_periodo.iterrows():
                data_formatada = pd.to_datetime(evento["Data/Hora"]).strftime("%d/%m/%Y %H:%M")
                descricao_resumida = evento["Descrição"][:100] + ("..." if len(evento["Descrição"]) > 80 else "")  # Limita o texto
                html += f"<p><strong>{data_formatada}:</strong> ({evento['Usuário']}) - {descricao_resumida}</p>"
        else:
            html += "<p>Sem eventos registrados neste período.</p>"

        html += "</div></details>"
    
    html += "</div>"
    return html

def exibir_cards_por_status(df,df_original, num_colunas=3):

    # CSS apenas para estilizar os cards
    st.markdown("""
    <style>
    .card {
        background-color: #fff;
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 20px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.06);
        height: 100%;
    }
    .card h4 {
        margin-top: 0;
    }
    .badge {
        background-color: #f0f0f0;
        border-radius: 12px;
        padding: 5px 10px;
        font-size: 12px;
        color: #333;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        max-width: 150px;
    }
    .verde {
        background-color: #28a745; /* verde */
        color: white;
    }
    .laranja {
        background-color: #ffc107; /* amarelo */
        color: black;
    }
    .vermelho {
        background-color: #FF0000; /* vermelho */
        color: white;
    }
    .prazo-verde { color: #1cc88a; font-weight: bold; }
    .prazo-laranja { color: #f6c23e; font-weight: bold; }
    .prazo-vermelho { color: #e74a3b; font-weight: bold; }
    .processo-box {
        background-color: #f8f9fc;
        padding: 5px 10px;
        border-radius: 6px;
        font-size: 12px;
        margin: 2px 0;
        border-left: 3px solid #4e73df;
    }
    .barra-status-container {
        height: 30px;
        display: flex;
        position: relative;
        border-radius: 5px; /* Arredondamento do contêiner */
        overflow: hidden; /* Garante que a borda arredondada não será violada */
    }

    .barra-status {
        height: 100%;
        display: flex;
        position: relative;
    }

    .barra-verde {
        background-color: #1cc88a;
    }

    .barra-amarela {
        background-color: #f6c23e;
    }

    .barra-vermelha {
        background-color: #e74a3b;
    }

    /* Lógica de arredondamento de bordas */
    .barra-status-container > .barra-status:first-child {
        border-radius: 5px 0 0 5px; /* Apenas para a primeira barra */
    }

    .barra-status-container > .barra-status:last-child {
        border-radius: 0 5px 5px 0; /* Apenas para a última barra */
    }

    .barra-status-container > .barra-status:nth-child(1):only-child {
        border-radius: 5px; /* Caso seja a única barra */
    }
    .barra-texto {
        position: absolute;
        width: 100%;
        text-align: center;
        color: white;
        font-size: 15px;
        font-weight: bold;
        line-height: 30px;
    }
    </style>
    """, unsafe_allow_html=True)


    
    responsaveis = df["Responsável"].unique()
    colunas = st.columns(num_colunas)

    for i, resp in enumerate(responsaveis):
        registros = df[df["Responsável"] == resp]

        processos_verde = registros.loc[registros["Faixa de Prazo"] == "0-5", ["Processo", "Tipo", "Data Recebido"]].to_dict(orient="records")
        processos_amarelo = registros.loc[registros["Faixa de Prazo"] == "6-10", ["Processo", "Tipo", "Data Recebido"]].to_dict(orient="records")
        processos_vermelho = registros.loc[registros["Faixa de Prazo"] == "11+", ["Processo", "Tipo", "Data Recebido"]].to_dict(orient="records")

        verde = len(processos_verde)
        amarelo = len(processos_amarelo)
        vermelho = len(processos_vermelho)
        total_processos = verde + amarelo + vermelho

        pct_verde = verde / total_processos if total_processos else 0
        pct_amarelo = amarelo / total_processos if total_processos else 0
        pct_vermelho = vermelho / total_processos if total_processos else 0

        barra_texto = []
        if pct_verde > 0:
            barra_texto.append(f"0-5: {int(pct_verde * 100)}%")
        if pct_amarelo > 0:
            barra_texto.append(f"6-10: {int(pct_amarelo * 100)}%")
        if pct_vermelho > 0:
            barra_texto.append(f"11+: {int(pct_vermelho * 100)}%")

        texto_barra = " | ".join(barra_texto)

        
        

        card_html = f"""<div class="card">
                            <h4>{resp}</h4>
                            <div style="display:flex; gap:20px;">
                                <div style="flex:1;">
                                    <div class="barra-status-container">
                                        <div class="barra-status barra-verde" style="width: {pct_verde * 100}%;"></div>
                                        <div class="barra-status barra-amarela" style="width: {pct_amarelo * 100}%;"></div>
                                        <div class="barra-status barra-vermelha" style="width: {pct_vermelho * 100}%;"></div>
                                        <div class="barra-texto">{texto_barra}</div>
                                    </div>
                                    <div style="display: flex; justify-content: space-between; flex-wrap: wrap; gap: 10px; margin-top: 6px;">
                                        <div class="processo-box">
                                            <span class='prazo-verde'>0-5 dias:</span> {verde}
                                        </div>
                                        <div class="processo-box">
                                            <span class='prazo-laranja'>6-10 dias:</span> {amarelo}
                                        </div>
                                        <div class="processo-box">
                                            <span class='prazo-vermelho'>11+ dias:</span> {vermelho}
                                        </div>
                                    </div>
                                    <p><strong>📋 Total de Processos:</strong> {total_processos}</p>
                                </div>
                            </div>
                            <div>
                                <details>
                                    <summary><strong>📜 Processos</strong></summary>
                                    <div style="margin-top: 10px;">
                                       <ul>"""
        
        
        # Chama a função para cada faixa de prazo
        card_html += exibir_processos(processos_verde, df, df_original, "verde", "0-5")
        card_html += exibir_processos(processos_amarelo, df, df_original, "laranja","6-10")
        card_html += exibir_processos(processos_vermelho, df,  df_original, "vermelho", "11+")

        card_html += "</ul></div></details></div></div>"

        # --- Acima você precisa definir os contadores no seu loop, assim:
        

        colunas[i % num_colunas].markdown(card_html, unsafe_allow_html=True)


def lista_geral_prazo(df_resultado):

    # CSS para estilizar a lista e as barras
    st.markdown("""
    <style>
        .container {
            background-color: #fff;
            margin-bottom: 1px;
            display: flex;
            flex-direction: column;
            gap: 5px; /* Espaçamento entre as linhas ajustado */
            box-shadow: 0 4px 10px rgba(0, 0, 0, 0.1);
            border-radius: 10px;
            padding: 4px;
        }
        .lista-item {
            
            border-radius: 8px;
            padding: 4px;
            
            display: flex;
            justify-content: flex-start;
            align-items: center;
            gap: 10px; /* Reduzi o gap entre os itens */
            width: 100%;
            font-size: 10px;
        }
        .lista-item .nome {
            flex: 1;
            text-align: left;
            font-size: 15px; /* Fonte do nome bem menor */
            font-weight: bold;
            overflow: hidden;
            text-overflow: ellipsis;
            padding-left: 5px;
            margin-bottom: 2px; /* Menos espaçamento entre nome e barra */
        }
        .barra-status-container {
            height: 20px; /* Menor altura para a barra */
            display: flex;
            position: relative;
            border-radius: 5px;
            overflow: hidden;
            flex: 10;
            background-color: #e0e0e0;
        }
        .barra-status {
            height: 100%;
        }
        .barra-verde {
            background-color: #1cc88a;
        }
        .barra-amarela {
            background-color: #f6c23e;
        }
        .barra-vermelha {
            background-color: #e74a3b;
        }
        .barra-texto {
            position: absolute;
            width: 100%;
            text-align: center;
            color: white;
            font-size: 12px; /* Texto dentro da barra ajustado */
            font-weight: bold;
            line-height: 20px; /* Alinhamento vertical ajustado */
        }
        .faixa-label {
            position: absolute;
            top: -15px;
            font-size: 10px;
            font-weight: normal;
            color: #333;
        }
        .total-processos {
            flex:1;
            display: flex;
            font-size: 12px;
            color: #555;
            font-weight: bold;
            min-width: 60px;
            text-align: right;
            margin: 0px 1em 0 5px;
            justify-content: center 
        }
    </style>
    """, unsafe_allow_html=True)
    # Exemplo de como os dados seriam filtrados e agrupados
    responsaveis = df_resultado["Responsável"].unique()
    max_processos = df_resultado.groupby("Responsável").size().max()


    # Exibir lista de responsáveis com barras de progresso

    lista_html = """
            <div class="container">
            """
    for resp in responsaveis:
        registros = df_resultado[df_resultado["Responsável"] == resp]

        processos_verde = registros.loc[registros["Faixa de Prazo"] == "0-5", ["Processo", "Tipo", "Data Recebido"]].to_dict(orient="records")
        processos_amarelo = registros.loc[registros["Faixa de Prazo"] == "6-10", ["Processo", "Tipo", "Data Recebido"]].to_dict(orient="records")
        processos_vermelho = registros.loc[registros["Faixa de Prazo"] == "11+", ["Processo", "Tipo", "Data Recebido"]].to_dict(orient="records")

        verde = len(processos_verde)
        amarelo = len(processos_amarelo)
        vermelho = len(processos_vermelho)
        total_processos = verde + amarelo + vermelho

        largura_barra = (total_processos / max_processos) * 100

        pct_verde = verde / max_processos if max_processos else 0
        pct_amarelo = amarelo / max_processos if max_processos else 0
        pct_vermelho = vermelho / max_processos if max_processos else 0
        

        barra_texto = []
        if pct_verde > 0:
            barra_texto.append(f"0-5: {verde}")
        if pct_amarelo > 0:
            barra_texto.append(f"6-10: {amarelo}")
        if pct_vermelho > 0:
            barra_texto.append(f"11+: {vermelho}")

        texto_barra = " | ".join(barra_texto)

        

        lista_html += f"""
        <div class="lista-item">
                <div class="nome">
                    {resp}
                </div>
                <div class="barra-status-container" style="width: {largura_barra}%;">
                    <div class="barra-status barra-verde" style="width: {pct_verde * 100}%;"></div>
                    <div class="barra-status barra-amarela" style="width: {pct_amarelo * 100}%;"></div>
                    <div class="barra-status barra-vermelha" style="width: {pct_vermelho * 100}%;"></div>
                    <div class="barra-texto">{texto_barra}</div>
                </div>
                <div class="total-processos">
                    {total_processos} processos
                </div>
            </div>
        """

        # Fechar o contêiner da lista
    lista_html += "</div>"

    # Exibir a lista no Streamlit
    st.markdown(lista_html, unsafe_allow_html=True)

# Exibindo os cards
st.subheader("👥 Painel de Responsáveis")

grafico_resposavel_prazo(df_resultado)



exibir_cards_por_status(df_resultado,df_original)
lista_geral_prazo(df_resultado)










