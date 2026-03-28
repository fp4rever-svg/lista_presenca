import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import urllib.parse
import time

# 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="Check-in Logística | Grupo SC", layout="wide")

# --- CONFIGURAÇÕES ---
SHEET_ID = "1nYm2aRgruykh2YfXTcpCRuHGIqI0TtAFroMEk_p7Ij8"
URL_SCRIPT_GOOGLE = "https://script.google.com/macros/s/AKfycbwLDpdSgnGTPwciE-25mUel8Zm46zovwoi9o_AnQrkkKUIOfRK6EuPH3YVD0M0TrBJY2Q/exec"

LIDERES = ["Carol", "Elisangela", "Lais Alves", "Leticia", "Renato", "Thiago"]
SENHA_ADMIN = "1234"

# --- FUNÇÕES DE SUPORTE ---
def get_sheet_url(aba):
    ts = int(time.time())
    aba_enc = urllib.parse.quote(aba)
    return f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={aba_enc}&t={ts}"

def buscar_senhas_db():
    try:
        r = requests.post(URL_SCRIPT_GOOGLE, json={"tipo": "buscar_senhas"}, timeout=10)
        return r.json() if r.status_code == 200 else {}
    except:
        return {}

def verificar_liberacao_especial():
    try:
        url = get_sheet_url("Config_Geral")
        df = pd.read_csv(url)
        # Lê a célula B1 (segunda coluna da primeira linha)
        status = str(df.iloc[0, 1]).strip().upper()
        return True if status == "ON" else False
    except:
        return False

# --- SESSÃO ---
if 'logado' not in st.session_state:
    st.session_state.update({'logado': False, 'usuario': None, 'perfil': None})

# ==========================================
# LOGIN
# ==========================================
if not st.session_state.logado:
    st.title("📋 Sistema de Check-in Logística")
    p_tipo = st.radio("Perfil:", ["Líder", "Administrador"], horizontal=True)

    if p_tipo == "Líder":
        u_sel = st.selectbox("Líder:", ["-- Selecione --"] + LIDERES)
        if u_sel != "-- Selecione --":
            senhas = buscar_senhas_db()
            s_db = senhas.get(u_sel, "")
            if not s_db:
                n_s = st.text_input("Defina sua senha:", type="password")
                if st.button("Cadastrar"):
                    requests.post(URL_SCRIPT_GOOGLE, json={"tipo": "definir_senha", "lider": u_sel, "nova_senha": n_s})
                    st.rerun()
            else:
                s_in = st.text_input("Senha:", type="password")
                if st.button("Entrar"):
                    if str(s_in) == str(s_db):
                        st.session_state.update({'logado': True, 'usuario': u_sel, 'perfil': "Lider"})
                        st.rerun()
                    else: st.error("Incorreta.")
    else:
        s_adm = st.text_input("Senha Admin:", type="password")
        if st.button("Acessar Painel"):
            if s_adm == SENHA_ADMIN:
                st.session_state.update({'logado': True, 'usuario': "Administrador", 'perfil': "Admin"})
                st.rerun()

# ==========================================
# ÁREA LOGADA
# ==========================================
else:
    c_h1, c_h2 = st.columns([5, 1])
    c_h1.write(f"Conectado: **{st.session_state.usuario}**")
    if c_h2.button("Sair"):
        st.session_state.logado = False
        st.rerun()

    # --- VISÃO LÍDER ---
    if st.session_state.perfil == "Lider":
        lider = st.session_state.usuario
        liberado = verificar_liberacao_especial()
        
        try:
            df = pd.read_csv(get_sheet_url(lider))
            df.rename(columns={df.columns[0]: 'Colaborador'}, inplace=True)

            with st.form("f_chamada"):
                st.subheader(f"Chamada - {lider}")
                if liberado:
                    st.success("✅ Campos de Hora Extra e Fretado LIBERADOS")
                
                lista_final = []
                col_dim = [3, 1, 1, 1, 3] if liberado else [3, 1, 0.1, 0.1, 3]
                
                h = st.columns(col_dim)
                h[0].write("**Nome**")
                h[1].write("**Pres.**")
                if liberado:
                    h[2].write("**H.E.**")
                    h[3].write("**Fret.**")
                h[4].write("**Obs**")

                for i, row in df.iterrows():
                    if pd.isna(row['Colaborador']): continue
                    cols = st.columns(col_dim)
                    cols[0].write(row['Colaborador'])
                    p_ok = cols[1].checkbox("OK", key=f"p_{i}")
                    
                    he_v, fr_v = "Não", "Não"
                    if liberado:
                        he_chk = cols[2].checkbox("⚡", key=f"he_{i}")
                        fr_chk = cols[3].checkbox("🚌", key=f"fr_{i}")
                        he_v = "Sim" if he_chk else "Não"
                        fr_v = "Sim" if fr_chk else "Não"
                    
                    obs_v = cols[4].text_input("", key=f"o_{i}", label_visibility="collapsed")
                    lista_final.append({"nome": row['Colaborador'], "status": "OK" if p_ok else "FALTA", "he": he_v, "fretado": fr_v, "obs": obs_v})

                if st.form_submit_button("ENVIAR"):
                    requests.post(URL_SCRIPT_GOOGLE, json={"tipo": "presenca_completa", "lider": lider, "lista": lista_final})
                    st.success("Enviado!")
        except: st.error("Erro ao carregar dados.")

    # --- VISÃO ADMIN ---
    elif st.session_state.perfil == "Admin":
        t1, t2 = st.tabs(["Monitoramento Diário", "Ferramentas"])

        with t1:
            st.subheader("Status de Envio (Hoje)")
            dt_hoje = datetime.now().strftime("%d/%m")
            for l in LIDERES:
                try:
                    df_st = pd.read_csv(get_sheet_url(l))
                    # Varre a coluna D (índice 3) para achar a data de hoje
                    foi = any(dt_hoje in str(x) for x in df_st.iloc[:, 3])
                    if foi: st.success(f"✅ {l}")
                    else: st.error(f"❌ {l}")
                except: st.warning(f"⚠️ {l}")

        with t2:
            st.subheader("🔓 Liberação Especial")
            status_agora = verificar_liberacao_especial()
            
            if status_agora:
                st.info("Status: CAMPOS EXTRAS VISÍVEIS")
                if st.button("🔴 OCULTAR CAMPOS"):
                    requests.post(URL_SCRIPT_GOOGLE, json={"tipo": "toggle_especial", "status": "OFF"})
                    time.sleep(1)
                    st.rerun()
            else:
                st.warning("Status: CAMPOS EXTRAS OCULTOS")
                if st.button("🟢 LIBERAR CAMPOS"):
                    requests.post(URL_SCRIPT_GOOGLE, json={"tipo": "toggle_especial", "status": "ON"})
                    time.sleep(1)
                    st.rerun()

            if st.button("🧹 RESETAR TUDO"):
                requests.post(URL_SCRIPT_GOOGLE, json={"tipo": "limpar_tudo"})
                st.rerun()
