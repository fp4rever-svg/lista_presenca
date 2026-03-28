import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import urllib.parse
import io

# 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(
    page_title="Check-in Logística | Grupo SC", 
    layout="wide", 
    initial_sidebar_state="collapsed"
)

# --- ESTILIZAÇÃO CSS ---
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {background-color: rgba(0,0,0,0);}
    .stButton>button {width: 100%; border-radius: 5px; height: 3em; background-color: #1E3A8A; color: white;}
    .main-title {text-align: center; color: #1E3A8A; font-weight: bold;}
    </style>
""", unsafe_allow_html=True)

# --- CONFIGURAÇÕES ---
SHEET_ID = "1nYm2aRgruykh2YfXTcpCRuHGIqI0TtAFroMEk_p7Ij8"
URL_SCRIPT_GOOGLE = "https://script.google.com/macros/s/AKfycbwLDpdSgnGTPwciE-25mUel8Zm46zovwoi9o_AnQrkkKUIOfRK6EuPH3YVD0M0TrBJY2Q/exec"

LIDERES = ["Carol", "Elisangela", "Lais Alves", "Leticia", "Renato", "Thiago"]
SENHA_ADMIN = "1234"

# --- FUNÇÕES DE SUPORTE ---
def get_sheet_url(aba):
    lider_limpo = urllib.parse.quote(aba)
    return f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={lider_limpo}"

def buscar_senhas_db():
    try:
        response = requests.post(URL_SCRIPT_GOOGLE, json={"tipo": "buscar_senhas"})
        return response.json() if response.status_code == 200 else {}
    except: return {}

def verificar_liberacao_especial():
    try:
        # Tenta ler a aba de controle de funções
        url_config = get_sheet_url("Config_Geral")
        df_config = pd.read_csv(url_config)
        if not df_config.empty and str(df_config.iloc[0, 1]).strip().upper() == "ON":
            return True
        return False
    except: return False

# --- CONTROLE DE SESSÃO ---
if 'logado' not in st.session_state:
    st.session_state.update({'logado': False, 'usuario': None, 'perfil': None})

# ==========================================
# TELA DE LOGIN
# ==========================================
if not st.session_state.logado:
    st.markdown("<h1 class='main-title'>📋 Sistema de Check-in Logística</h1>", unsafe_allow_html=True)
    st.markdown("---")
    
    perfil_tipo = st.radio("Perfil:", ["Líder", "Administrador"], horizontal=True)

    if perfil_tipo == "Líder":
        user_select = st.selectbox("Líder:", ["-- Selecione --"] + LIDERES)
        if user_select != "-- Selecione --":
            senhas = buscar_senhas_db()
            senha_db = senhas.get(user_select, "")
            
            if not senha_db:
                nova_s = st.text_input("Crie uma senha:", type="password")
                if st.button("Salvar Senha"):
                    requests.post(URL_SCRIPT_GOOGLE, json={"tipo": "definir_senha", "lider": user_select, "nova_senha": nova_s})
                    st.rerun()
            else:
                s_input = st.text_input("Senha:", type="password")
                if st.button("Entrar"):
                    if str(s_input) == str(senha_db):
                        st.session_state.update({'logado': True, 'usuario': user_select, 'perfil': "Lider"})
                        st.rerun()
                    else: st.error("Senha incorreta.")
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
    c1, c2 = st.columns([5, 1])
    c1.write(f"Usuário: **{st.session_state.usuario}**")
    if c2.button("🏠 Sair"):
        st.session_state.logado = False
        st.rerun()

    # --- TELA DO LÍDER ---
    if st.session_state.perfil == "Lider":
        lider = st.session_state.usuario
        try:
            df_equipe = pd.read_csv(get_sheet_url(lider))
            df_equipe.rename(columns={df_equipe.columns[0]: 'Colaborador'}, inplace=True)
            
            # Checa se o Admin liberou os campos extras
            liberado = verificar_liberacao_especial()

            with st.form("form_chamada"):
                st.subheader(f"Chamada - {lider}")
                lista_final = []
                
                # Cabeçalho da Tabela
                cols_head = st.columns([3, 1, 1, 1, 3])
                cols_head[0].write("**Nome**")
                cols_head[1].write("**Pres.**")
                if liberado:
                    cols_head[2].write("**H.E.**")
                    cols_head[3].write("**Fret.**")
                cols_head[4].write("**Observação**")
                
                for i, row in df_equipe.iterrows():
                    if pd.isna(row['Colaborador']): continue
                    
                    c_nome, c_pres, c_he, c_fret, c_obs = st.columns([3, 1, 1, 1, 3])
                    
                    c_nome.write(row['Colaborador'])
                    pres = c_pres.checkbox("OK", key=f"p_{i}")
                    
                    he_val = "Não"
                    fret_val = "Não"
                    
                    if liberado:
                        he_check = c_he.checkbox("⚡", key=f"he_{i}")
                        fret_check = c_fret.checkbox("🚌", key=f"fr_{i}")
                        he_val = "Sim" if he_check else "Não"
                        fret_val = "Sim" if fret_check else "Não"
                    
                    obs = c_obs.text_input("", key=f"o_{i}", placeholder="-", label_visibility="collapsed")
                    
                    lista_final.append({
                        "nome": row['Colaborador'],
                        "status": "OK" if pres else "FALTA",
                        "he": he_val,
                        "fretado": fret_val,
                        "obs": obs
                    })

                if st.form_submit_button("✅ ENVIAR CHECK-IN"):
                    requests.post(URL_SCRIPT_GOOGLE, json={
                        "tipo": "presenca_completa", 
                        "lider": lider, 
                        "lista": lista_final
                    })
                    st.success("Dados enviados!")
                    st.balloons()
        except: st.error("Erro ao carregar equipe.")

    # --- TELA DO ADMINISTRADOR ---
        elif st.session_state.perfil == "Admin":
        st.subheader("📊 Painel de Controle Administrativo")

        tab1, tab2 = st.tabs(["Monitoramento Diário", "Ferramentas & Liberação"])

        with tab1:
            st.write(f"Status - {datetime.now().strftime('%d/%m')}")
            # ... (seu código de monitoramento de líderes aqui)

        with tab2:
            st.write("### 🔓 Controle de Campos Extras")
            
            # 1. Busca o status atual no Sheets
            status_he = verificar_liberacao_especial()
            
            # 2. Mostra o status e o botão dinâmico
            if status_he:
                st.info("💡 **Status Atual:** HORA EXTRA e FRETADO estão **ATIVOS** para os líderes.")
                if st.button("🔴 BLOQUEAR CAMPOS EXTRAS", use_container_width=True):
                    requests.post(URL_SCRIPT_GOOGLE, json={"tipo": "toggle_especial", "status": "OFF"})
                    st.success("Campos bloqueados com sucesso!")
                    st.rerun()
            else:
                st.warning("💡 **Status Atual:** Campos de Hora Extra/Fretado estão **OCULTOS**.")
                if st.button("🟢 LIBERAR HORA EXTRA / FRETADO", use_container_width=True):
                    requests.post(URL_SCRIPT_GOOGLE, json={"tipo": "toggle_especial", "status": "ON"})
                    st.success("Campos liberados com sucesso!")
                    st.rerun()

            st.divider()
            
            st.write("### 🛠️ Ações de Sistema")
            col_a, col_b = st.columns(2)
            
            with col_a:
                if st.button("🔄 Ver Senhas"):
                    s = buscar_senhas_db()
                    if s: st.table(pd.DataFrame(list(s.items()), columns=['Líder', 'Senha']))
            
            with col_b:
                if st.button("🧹 RESETAR PLANILHAS"):
                    requests.post(URL_SCRIPT_GOOGLE, json={"tipo": "limpar_tudo"})
                    st.success("Dados limpos!")
                    st.rerun()
