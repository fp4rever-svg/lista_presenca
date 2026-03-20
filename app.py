import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Check-in Logística | Grupo SC", layout="centered")

# --- CONFIGURAÇÃO GOOGLE SHEETS ---
# Substitua pelo ID da sua planilha (está entre o /d/ e o /edit no link)
SHEET_ID = "1nYm2aRgruykh2YfXTcpCRuHGIqI0TtAFroMEk_p7Ij8"

def get_sheet_url(aba):
    return f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={aba}"

# Lista das abas exatamente como estão no seu Sheets
# (Você pode atualizar essa lista aqui sempre que criar um líder novo)
ABAS_LIDERES = ["Paula Toledo", "Fabio Santos"] 

st.title("📋 Lista de Presença Digital")
st.caption("Conectado via Google Sheets")

# --- BARRA LATERAL ---
st.sidebar.header("Painel Analista")
senha = st.sidebar.text_input("Senha", type="password")

# --- SELEÇÃO DO LÍDER ---
lider = st.selectbox("Selecione o Líder:", ["-- Selecione --"] + ABAS_LIDERES)

if lider != "-- Selecione --":
    try:
        # Lê os nomes direto do Google Sheets
        url = get_sheet_url(lider)
        df = pd.read_csv(url)
        
        with st.form("chamada_sheets"):
            st.write(f"### Equipe: {lider}")
            dados_sessao = []
            
            for i, row in df.iterrows():
                col1, col2, col3 = st.columns([3, 1, 3])
                col1.write(f"**{row['Colaborador']}**")
                presenca = col2.checkbox("Presença", key=f"check_{i}")
                obs = col3.text_input("Observação", key=f"obs_{i}")
                
                dados_sessao.append({
                    "Data": datetime.now().strftime("%d/%m/%Y"),
                    "Lider": lider,
                    "Colaborador": row['Colaborador'],
                    "Status": "PRESENTE" if presenca else "FALTA",
                    "Obs": obs
                })
            
            st.markdown("---")
            st.write("#### ➕ Inclusão Pendente")
            novo = st.text_input("Nome do Colaborador")
            setor = st.text_input("Setor")

            if st.form_submit_button("✅ FINALIZAR"):
                df_resultado = pd.DataFrame(dados_sessao)
                if novo:
                    df_resultado = pd.concat([df_resultado, pd.DataFrame([{"Colaborador": f"SOLIC: {novo}", "Status": "PENDENTE", "Obs": setor}])])
                
                st.success("Chamada processada!")
                # Por enquanto, mantemos o download para segurança
                csv = df_resultado.to_csv(index=False).encode('utf-8-sig')
                st.download_button("📥 Baixar Relatório do Turno", csv, f"Chamada_{lider}.csv")

    except Exception as e:
        st.error("Erro ao conectar com o Google Sheets. Verifique o compartilhamento.")

# --- ÁREA DO ANALISTA ---
if senha == "1234":
    if st.sidebar.button("Ver Pendentes (Base)"):
        url_pendentes = get_sheet_url("Pendetes de Inclusão") # Note o erro de digitação do nome da aba se houver
        df_p = pd.read_csv(url_pendentes)
        st.write("### Colaboradores na Fila de Inclusão")
        st.dataframe(df_p)