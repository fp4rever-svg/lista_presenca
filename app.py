import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import urllib.parse

st.set_page_config(page_title="Check-in Logística | Grupo SC", layout="centered")

SHEET_ID = "1nYm2aRgruykh2YfXTcpCRuHGIqI0TtAFroMEk_p7Ij8"
URL_SCRIPT_GOOGLE = "https://script.google.com/macros/s/AKfycbz3J-m4rTKD0Wkr58B2qDsGS81RwZl7-jt3HegpTBI5Fg1mHBJLzoHTvY4D2OW5ZXuClA/exec"

def get_sheet_url(aba):
    lider_limpo = urllib.parse.quote(aba)
    return f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={lider_limpo}"

ABAS_LIDERES = ["Paula Toledo", "Fabio Santos"]

st.title("📋 Lista de Presença Digital")

lider = st.selectbox("Selecione o Líder:", ["-- Selecione --"] + ABAS_LIDERES)

if lider != "-- Selecione --":
    try:
        # Carrega dados (A coluna 'Status' será lida mas não mostrada no loop do form)
        df = pd.read_csv(get_sheet_url(lider))
        df.rename(columns={df.columns[0]: 'Colaborador'}, inplace=True)
        
        with st.form("form_chamada"):
            st.write(f"### Equipe: {lider}")
            lista_para_enviar = []
            
            for i, row in df.iterrows():
                c1, c2, c3 = st.columns([3, 1, 3])
                c1.write(f"**{row['Colaborador']}**")
                # A coluna B (Status) do Sheets não aparece aqui
                presenca = c2.checkbox("Presente", key=f"p_{i}")
                obs = c3.text_input("Observação", key=f"o_{i}", placeholder="Opcional")
                
                lista_para_enviar.append({
                    "nome": row['Colaborador'],
                    "status": "OK" if presenca else "FALTA",
                    "obs": obs
                })
            
            if st.form_submit_button("✅ ENVIAR"):
                payload = {
                    "tipo": "presenca",
                    "lider": lider,
                    "lista": lista_para_enviar
                }
                with st.spinner('Salvando no Google Sheets...'):
                    response = requests.post(URL_SCRIPT_GOOGLE, json=payload)
                    if response.status_code == 200:
                        st.success("Status atualizado diretamente na planilha!")
                    else:
                        st.error("Erro ao salvar. Verifique o Script.")

        # --- ÁREA DE SOLICITAÇÃO ---
        st.markdown("---")
        with st.expander("➕ SOLICITAR INCLUSÃO"):
            with st.form("form_inclusao"):
                nome_n = st.text_input("Nome")
                area_n = st.text_input("Área")
                if st.form_submit_button("Salvar na Aba Pendentes"):
                    payload_inc = {"tipo": "inclusao", "colaborador": nome_n, "lider": lider, "area": area_n}
                    requests.post(URL_SCRIPT_GOOGLE, json=payload_inc)
                    st.success("Enviado para análise!")

    except Exception as e:
        st.error("Erro ao carregar lista.")