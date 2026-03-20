import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import urllib.parse

# 1. Configuração da página: Começa fechada (collapsed)
st.set_page_config(
    page_title="Check-in Logística | Grupo SC - Panpharma", 
    layout="centered",
    initial_sidebar_state="collapsed" 
)

# --- CSS: Esconde o desnecessário, mantém o controle da Sidebar ---
hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;} /* Menu de 3 pontos */
            footer {visibility: hidden;}    /* Rodapé do Streamlit */
            
            /* Remove a barra colorida do topo mas mantém o botão da Sidebar */
            header {
                background-color: rgba(0,0,0,0);
                height: 3rem;
            }
            
            /* Ajuste para o botão da Sidebar não sumir no mobile */
            .st-emotion-cache-zq5wmm {
                visibility: visible !important;
            }
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

# --- CONFIGURAÇÕES ---
SHEET_ID = "1nYm2aRgruykh2YfXTcpCRuHGIqI0TtAFroMEk_p7Ij8"
URL_SCRIPT_GOOGLE = "https://script.google.com/macros/s/AKfycbz3J-m4rTKD0Wkr58B2qDsGS81RwZl7-jt3HegpTBI5Fg1mHBJLzoHTvY4D2OW5ZXuClA/exec"
# ... restante do código ...
def get_sheet_url(aba):
    lider_limpo = urllib.parse.quote(aba)
    return f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={lider_limpo}"

ABAS_LIDERES = ["Paula Toledo", "Fabio Santos"]

# --- BARRA LATERAL (PAINEL DO ANALISTA) ---
st.sidebar.header("🔐 Painel Administrativo")
senha_admin = st.sidebar.text_input("Senha de Analista", type="password")

if senha_admin == "1234":
    st.sidebar.success("Acesso Liberado")
    if st.sidebar.button("Verificar Pendentes"):
        try:
            df_p = pd.read_csv(get_sheet_url("Pendentes"))
            st.write("### 📂 Colaboradores Pendentes de Inclusão")
            st.dataframe(df_p)
        except:
            st.error("Aba 'Pendentes' não encontrada na planilha.")

# --- INTERFACE PRINCIPAL ---
st.title("📋 Lista de Presença Digital")
st.caption("Unidade Sumaré | Registro Automático")

lider = st.selectbox("Selecione o Líder:", ["-- Selecione --"] + ABAS_LIDERES)

if lider != "-- Selecione --":
    try:
        # Carrega dados
        df = pd.read_csv(get_sheet_url(lider))
        # Garante que a primeira coluna seja tratada como nome do colaborador
        df.rename(columns={df.columns[0]: 'Colaborador'}, inplace=True)
        
        with st.form("form_chamada"):
            st.write(f"### Equipe: {lider}")
            lista_para_enviar = []
            
            for i, row in df.iterrows():
                if pd.isna(row['Colaborador']): continue
                
                c1, c2, c3 = st.columns([3, 1, 3])
                c1.write(f"**{row['Colaborador']}**")
                presenca = c2.checkbox("Presente", key=f"p_{i}")
                obs = c3.text_input("Observação", key=f"o_{i}", placeholder="Opcional")
                
                lista_para_enviar.append({
                    "nome": row['Colaborador'],
                    "status": "OK" if presenca else "FALTA",
                    "obs": obs
                })
            
            st.markdown("---")
            if st.form_submit_button("✅ ENVIAR"):
                payload = {
                    "tipo": "presenca",
                    "lider": lider,
                    "lista": lista_para_enviar
                }
                with st.spinner('Registrando presença e horário no Sheets...'):
                    response = requests.post(URL_SCRIPT_GOOGLE, json=payload)
                    if response.status_code == 200:
                        st.success(f"Presença e Horário registrados na aba {lider}!")
                    else:
                        st.error("Erro ao salvar. Verifique a conexão com o Script.")

        # --- SOLICITAÇÃO DE INCLUSÃO ---
        st.markdown("---")
        with st.expander("➕ SOLICITAR INCLUSÃO DE NOVO COLABORADOR"):
            with st.form("form_inclusao"):
                nome_n = st.text_input("Nome Completo")
                area_n = st.text_input("Área/Setor")
                if st.form_submit_button("Enviar Solicitação"):
                    if nome_n and area_n:
                        payload_inc = {
                            "tipo": "inclusao", 
                            "colaborador": nome_n, 
                            "lider": lider, 
                            "area": area_n
                        }
                        requests.post(URL_SCRIPT_GOOGLE, json=payload_inc)
                        st.success("Solicitação enviada para a aba Pendentes!")
                    else:
                        st.warning("Preencha todos os campos.")

    except Exception as e:
        st.error("Erro ao carregar a lista. Verifique as abas da planilha.")
