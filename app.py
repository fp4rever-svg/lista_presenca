import streamlit as st
import pandas as pd
import gspread
from datetime import datetime

st.set_page_config(page_title="Check-in Logística | Grupo SC", layout="centered")

# --- CONEXÃO DINÂMICA ---
SHEET_ID = "1nYm2aRgruykh2YfXTcpCRuHGIqI0TtAFroMEk_p7Ij8"

# Função para listar todas as abas do seu Google Sheets automaticamente
@st.cache_data(ttl=600) # Atualiza a lista a cada 10 minutos
def listar_abas_automaticamente():
    try:
        # Formato de URL para exportar metadados das abas (técnica avançada)
        url_abas = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=xlsx"
        xls = pd.ExcelFile(url_abas)
        # Retorna todas as abas exceto a 'Pendentes'
        return [sheet for sheet in xls.sheet_names if sheet != 'Pendentes']
    except:
        return ["Paula Toledo", "Fabio Santos"] # Fallback caso falhe

abas_disponiveis = listar_abas_automaticamente()

st.title("📋 Lista de Presença Digital")
st.caption("Sincronizado em tempo real com Google Sheets")

# O menu agora usa a lista que veio direto do Sheets!
lider = st.selectbox("Selecione seu nome (Líder):", ["-- Selecione --"] + abas_disponiveis)

if lider != "-- Selecione --":
    # Daqui para baixo o código segue igual...
    url_dados = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={lider}"
    df = pd.read_csv(url_dados)
    
    with st.form("form_v2"):
        st.write(f"### Chamada: {lider}")
        # ... (resto do código de marcação de presença)
        if st.form_submit_button("✅ FINALIZAR"):
            st.success("Processado!")