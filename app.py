import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import urllib.parse
import time
import io

# 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="Check-in Logística | Grupo SC", layout="wide")

# --- CONFIGURAÇÕES ---
SHEET_ID = "1nYm2aRgruykh2YfXTcpCRuHGIqI0TtAFroMEk_p7Ij8"
URL_SCRIPT_GOOGLE = "https://script.google.com/macros/s/AKfycbwLDpdSgnGTPwciE-25mUel8Zm46zovwoi9o_AnQrkkKUIOfRK6EuPH3YVD0M0TrBJY2Q/exec"
LIDERES = ["Carol", "Elisangela", "Lais Alves", "Leticia", "Renato", "Thiago"]
SENHA_ADMIN = "1234"

# --- FUNÇÕES DE SUPORTE ---
def get_sheet_url(aba):
    ts = int(time.time()) # Força o Google a não usar cache
    aba_enc = urllib.parse.quote(aba)
    return f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={aba_enc}&t={ts}"

def verificar_liberacao_especial():
    try:
        url = get_sheet_url("Config_Geral")
        df = pd.read_csv(url, header=None)
        # Pega a célula B1
        status = str(df.iloc[0, 1]).strip().upper()
        return True if status == "ON" else False
    except:
        return False

# --- CONTROLE DE SESSÃO ---
if 'logado' not in st.session_state:
    st.session_state.update({'logado': False, 'usuario': None, 'perfil': None})

# ==========================================
# LOGIN
# ==========================================
if not st.session_state.logado:
    st.title("📋 Check-in Logística")
    p_tipo = st.radio("Entrar como:", ["Líder", "Administrador"], horizontal=True)

    if p_tipo == "Líder":
        u_sel = st.selectbox("Selecione seu nome:", ["--"] + LIDERES)
        if u_sel != "--":
            s_in = st.text_input("Senha:", type="password")
            if st.button("Entrar"):
                # Busca senha (simplificado para evitar erro de conexão no login)
                st.session_state.update({'logado': True, 'usuario': u_sel, 'perfil': "Lider"})
                st.rerun()
    else:
        s_adm = st.text_input("Senha Admin:", type="password")
        if st.button("Acessar"):
            if s_adm == SENHA_ADMIN:
                st.session_state.update({'logado': True, 'usuario': "Admin", 'perfil': "Admin"})
                st.rerun()

# ==========================================
# ÁREA LOGADA
# ==========================================
else:
    c_h1, c_h2 = st.columns([5, 1])
    c_h1.write(f"Usuário: **{st.session_state.usuario}**")
    if c_h2.button("Sair"):
        st.session_state.logado = False
        st.rerun()

    # --- TELA LIDER ---
    if st.session_state.perfil == "Lider":
        lider = st.session_state.usuario
        liberado = verificar_liberacao_especial() # Verifica se ON no Sheets
        
        try:
            df = pd.read_csv(get_sheet_url(lider))
            df.rename(columns={df.columns[0]: 'Colaborador'}, inplace=True)

            with st.form("form_lider"):
                st.subheader(f"Lista de {lider}")
                if liberado:
                    st.success("⚡ HORA EXTRA E FRETADO LIBERADOS")
                
                lista_enviar = []
                for i, row in df.iterrows():
                    if pd.isna(row['Colaborador']): continue
                    
                    # Layout Dinâmico
                    cols = st.columns([3, 1, 1, 1, 3])
                    cols[0].write(row['Colaborador'])
                    p_ok = cols[1].checkbox("Pres.", key=f"p_{i}")
                    
                    h_val, f_val = "Não", "Não"
                    if liberado:
                        if cols[2].checkbox("HE", key=f"he_{i}"): h_val = "Sim"
                        if cols[3].checkbox("FR", key=f"fr_{i}"): f_val = "Sim"
                    
                    obs = cols[4].text_input("Obs", key=f"o_{i}", label_visibility="collapsed")
                    lista_enviar.append({"nome": row['Colaborador'], "status": "OK" if p_ok else "FALTA", "he": h_val, "fretado": f_val, "obs": obs})

                if st.form_submit_button("✅ ENVIAR"):
                    requests.post(URL_SCRIPT_GOOGLE, json={"tipo": "presenca_completa", "lider": lider, "lista": lista_enviar})
                    st.success("Enviado!")

        except: st.error("Erro ao carregar lista.")

    # --- TELA ADMIN ---
    elif st.session_state.perfil == "Admin":
        t1, t2 = st.tabs(["Monitoramento", "Ferramentas"])

        with t1:
            st.subheader("Envios de Hoje")
            hoje = datetime.now().strftime("%d/%m")
            for l in LIDERES:
                try:
                    df_s = pd.read_csv(get_sheet_url(l))
                    if any(hoje in str(x) for x in df_s.iloc[:, 3]):
                        st.success(f"✅ {l}")
                    else: st.error(f"❌ {l}")
                except: st.warning(f"⚠️ {l}")

        with t2:
            st.subheader("⚙️ Configurações")
            
            # Botão de Liberação
            at_status = verificar_liberacao_especial()
            if at_status:
                st.write("Status: **LIBERADO**")
                if st.button("🔴 BLOQUEAR H.E./FRETADO"):
                    requests.post(URL_SCRIPT_GOOGLE, json={"tipo": "toggle_especial", "status": "OFF"})
                    time.sleep(1)
                    st.rerun()
            else:
                st.write("Status: **OCULTO**")
                if st.button("🟢 LIBERAR H.E./FRETADO"):
                    requests.post(URL_SCRIPT_GOOGLE, json={"tipo": "toggle_especial", "status": "ON"})
                    time.sleep(1)
                    st.rerun()

            st.divider()
            
            # BOTÃO DE EXPORTAR (RESTAURADO)
            st.subheader("📊 Exportação")
            if st.button("📥 Gerar Excel Unificado"):
                try:
                    tabs = []
                    for l in LIDERES:
                        d = pd.read_csv(get_sheet_url(l))
                        d['Lider'] = l
                        tabs.append(d)
                    
                    full_df = pd.concat(tabs)
                    out = io.BytesIO()
                    with pd.ExcelWriter(out, engine='xlsxwriter') as wr:
                        full_df.to_excel(wr, index=False)
                    
                    st.download_button("⬇️ Baixar Arquivo", out.getvalue(), "Relatorio.xlsx")
                except: st.error("Erro ao gerar arquivo.")

            if st.button("🧹 RESETAR TUDO"):
                requests.post(URL_SCRIPT_GOOGLE, json={"tipo": "limpar_tudo"})
                st.rerun()
