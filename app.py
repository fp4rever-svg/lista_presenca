import streamlit as st
import pandas as pd
import requests
import urllib.parse
import plotly.express as px
from io import BytesIO
from datetime import datetime

# 1. CONFIGURAÇÕES
st.set_page_config(page_title="Check-in & Performance | Nova Odessa", layout="wide")

# --- IDs DOS ARQUIVOS ---
ID_PLANILHA_PRESENCA = "1nYm2aRgruykh2YfXTcpCRuHGIqI0TtAFroMEk_p7Ij8"
ID_SHEETS_PROD = "1TR5oI_I4C9IA-QfUp0zaMmS4Dni1J8nG75Flxd1yguA" 

URL_SCRIPT_GOOGLE = "https://script.google.com/macros/s/AKfycbz3J-m4rTKD0Wkr58B2qDsGS81RwZl7-jt3HegpTBI5Fg1mHBJLzoHTvY4D2OW5ZXuClA/exec"
LIDERES = ["Carol", "Elisangela", "Lais Alves", "Leticia", "Renato", "Thiago"]
SENHA_ADMIN = "1234"

# --- FUNÇÕES ---
def get_csv_url(file_id, sheet_name):
    name_enc = urllib.parse.quote(sheet_name)
    return f"https://docs.google.com/spreadsheets/d/{file_id}/gviz/tq?tqx=out:csv&sheet={name_enc}"

# --- LÓGICA DE SESSÃO ---
if 'logado' not in st.session_state:
    st.session_state.update({'logado': False, 'usuario': None, 'perfil': None})

# ==========================================
# LOGIN
# ==========================================
if not st.session_state.logado:
    st.title("🔒 Acesso - Grupo SC (Nova Odessa)")
    p_tipo = st.radio("Entrar como:", ["Líder", "Administrador"], horizontal=True)

    if p_tipo == "Líder":
        u_sel = st.selectbox("Selecione seu nome:", ["--"] + LIDERES)
        s_input = st.text_input("Senha:", type="password")
        if st.button("Entrar"):
            # Validação simples para teste ou via DB
            st.session_state.update({'logado': True, 'usuario': u_sel, 'perfil': "Lider"})
            st.rerun()
    else:
        s_adm = st.text_input("Senha Admin:", type="password")
        if st.button("Acessar"):
            if s_adm == SENHA_ADMIN:
                st.session_state.update({'logado': True, 'usuario': "Admin", 'perfil': "Admin"})
                st.rerun()
            else:
                st.error("Senha incorreta.")

# ==========================================
# ÁREA LOGADA
# ==========================================
else:
    # Barra Superior
    c_h1, c_h2 = st.columns([5, 1])
    c_h1.subheader(f"Painel {st.session_state.perfil}: {st.session_state.usuario}")
    if c_h2.button("Sair"):
        st.session_state.logado = False
        st.rerun()

    # --- PERFIL LÍDER ---
    if st.session_state.perfil == "Lider":
        try:
            url_l = get_csv_url(ID_PLANILHA_PRESENCA, st.session_state.usuario)
            df_l = pd.read_csv(url_l)
            with st.form("f_pres"):
                st.write("### Check-in")
                # Lógica de formulário...
                st.form_submit_button("Enviar")
        except: st.error("Erro ao carregar lista.")

    # --- PERFIL ADMINISTRADOR (RESTAURADO) ---
    elif st.session_state.perfil == "Admin":
        t1, t2, t3 = st.tabs(["Monitoramento Diário", "Gestão e Comandos", "Performance"])

        with t1:
            st.write("### Status de Envio")
            try:
                df_c = pd.read_csv(get_csv_url(ID_PLANILHA_PRESENCA, "Controle"))
                df_c.columns = df_c.columns.str.strip()
                for l in LIDERES:
                    check = df_c[df_c['Lider'].astype(str).str.strip() == l]
                    if not check.empty and "Preenchido" in str(check.iloc[0]['Status']):
                        st.write(f"✅ **{l}**: Entregue | {check.iloc[0]['Horario']}")
                    else:
                        st.write(f"⏳ **{l}**: Pendente")
            except: st.info("Sincronizando dados...")

        with t2:
            st.write("### Comandos")
            if st.button("🗑️ Resetar Sistema"):
                requests.post(URL_SCRIPT_GOOGLE, json={"tipo": "reset_presenca"})
                st.warning("Reset solicitado.")

        with t3:
            st.write("### 📈 Produtividade")
            cf1, cf2 = st.columns(2)
            dep_escolhido = cf1.selectbox("Depósito:", ["Todos", "102", "105", "107", "111", "302"])
            op = cf2.radio("Operação:", ["Conferência", "Picking"])
            
            aba = "Conf" if op == "Conferência" else "Pick"
            try:
                df_p = pd.read_csv(get_csv_url(ID_SHEETS_PROD, aba))
                df_p.columns = df_p.columns.str.strip()
                
                # Filtro de Depósito Robusto
                if dep_escolhido != "Todos":
                    # Procura coluna que contenha 'Dep' no nome
                    col_dep = [c for c in df_p.columns if 'Dep' in c][0]
                    df_p[col_dep] = df_p[col_dep].astype(str).str.replace('.0','', regex=False).str.strip()
                    df_p = df_p[df_p[col_dep] == dep_escolhido]

                # Gráficos...
                if not df_p.empty:
                    u_col = df_p.columns[0]
                    st.dataframe(df_p) # Exibe os dados para confirmar o filtro
            except Exception as e:
                st.error(f"Erro na aba {aba}: {e}")
