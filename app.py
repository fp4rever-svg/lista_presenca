import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import urllib.parse
import io

# 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="Check-in Logística | Grupo SC", layout="centered", initial_sidebar_state="collapsed")

# --- ESTILO VISUAL ---
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {background-color: rgba(0,0,0,0);}
    .main-title {text-align: center; color: #1E3A8A; margin-bottom: 2rem;}
    </style>
""", unsafe_allow_html=True)

# --- CONFIGURAÇÕES ---
SHEET_ID = "1nYm2aRgruykh2YfXTcpCRuHGIqI0TtAFroMEk_p7Ij8"
URL_SCRIPT_GOOGLE = "https://script.google.com/macros/s/AKfycbz3J-m4rTKD0Wkr58B2qDsGS81RwZl7-jt3HegpTBI5Fg1mHBJLzoHTvY4D2OW5ZXuClA/exec"
LIDERES = ["Carol", "Gabriel / Elisangela", "Lais Alves", "Leticia", "Renato", "Thiago"]
SENHA_LIDER = "123"  # Senha para todos os líderes (você pode personalizar depois)
SENHA_ADMIN = "1234" # Sua senha de administrador

def get_sheet_url(aba):
    lider_limpo = urllib.parse.quote(aba)
    return f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={lider_limpo}"

# --- CONTROLE DE SESSÃO (LOGIN) ---
if 'logado' not in st.session_state:
    st.session_state.logado = False
    st.session_state.usuario = None
    st.session_state.perfil = None

# --- TELA DE LOGIN ---
if not st.session_state.logado:
    st.markdown("<h1 class='main-title'>🔒 Acesso ao Sistema</h1>", unsafe_allow_html=True)
    
    with st.container():
        tipo_login = st.radio("Selecione o perfil:", ["Líder", "Administrador"], horizontal=True)
        
        if tipo_login == "Líder":
            usuario = st.selectbox("Selecione seu nome:", ["--"] + LIDERES)
            senha = st.text_input("Senha de acesso:", type="password")
            
            if st.button("Entrar"):
                if usuario != "--" and senha == SENHA_LIDER:
                    st.session_state.logado = True
                    st.session_state.usuario = usuario
                    st.session_state.perfil = "Lider"
                    st.rerun()
                else:
                    st.error("Usuário ou Senha incorretos.")
                    
        else: # Admin
            senha_adm = st.text_input("Senha Admin:", type="password")
            if st.button("Acessar Painel"):
                if senha_adm == SENHA_ADMIN:
                    st.session_state.logado = True
                    st.session_state.usuario = "Administrador"
                    st.session_state.perfil = "Admin"
                    st.rerun()
                else:
                    st.error("Senha administrativa incorreta.")

# --- TELA PÓS-LOGIN ---
else:
    # BOTÃO VOLTAR / SAIR (HOME)
    if st.button("🏠 Sair / Tela Inicial"):
        st.session_state.logado = False
        st.session_state.usuario = None
        st.session_state.perfil = None
        st.rerun()

    st.write(f"Bem-vindo, **{st.session_state.usuario}**")
    st.markdown("---")

    # --- VISÃO DO LÍDER ---
    if st.session_state.perfil == "Lider":
        lider = st.session_state.usuario
        try:
            url = get_sheet_url(lider)
            df = pd.read_csv(url)
            df.rename(columns={df.columns[0]: 'Colaborador'}, inplace=True)
            
            with st.form("chamada"):
                st.subheader(f"Lista de Presença - {lider}")
                lista_envio = []
                for i, row in df.iterrows():
                    if pd.isna(row['Colaborador']): continue
                    c1, c2, c3 = st.columns([3, 1, 3])
                    c1.write(f"**{row['Colaborador']}**")
                    presenca = c2.checkbox("OK", key=f"p_{i}")
                    obs = c3.text_input("Obs", key=f"o_{i}", placeholder="-")
                    lista_envio.append({"nome": row['Colaborador'], "status": "OK" if presenca else "FALTA", "obs": obs})
                
                if st.form_submit_button("✅ ENVIAR REGISTRO"):
                    requests.post(URL_SCRIPT_GOOGLE, json={"tipo": "presenca", "lider": lider, "lista": lista_envio})
                    st.success("Enviado com sucesso!")
                    st.balloons()
        except:
            st.error("Erro ao carregar sua lista. Verifique a planilha.")

    # --- VISÃO DO ADMIN ---
    elif st.session_state.perfil == "Admin":
        st.subheader("📊 Painel de Controle Geral")
        
        # Monitoramento de Status
        col1, col2 = st.columns(2)
        data_hoje = datetime.now().strftime("%d/%m/%Y")
        
        with col1:
            st.write("**Status de Envio (Hoje):**")
            for l in LIDERES:
                try:
                    df_check = pd.read_csv(get_sheet_url(l), dtype=str)
                    if not df_check.empty and data_hoje in df_check.iloc[:, 3].astype(str).values:
                        st.write(f"✅ {l}")
                    else:
                        st.write(f"❌ {l}")
                except: st.write(f"⚠️ {l} (Erro)")

        with col2:
            st.write("**Ações Rápidas:**")
            if st.button("📥 Baixar Excel Unificado"):
                frames = []
                for l in LIDERES:
                    try:
                        d = pd.read_csv(get_sheet_url(l))
                        d.rename(columns={d.columns[0]: 'Colaborador'}, inplace=True)
                        d['Líder'] = l
                        frames.append(d)
                    except: pass
                if frames:
                    full_df = pd.concat(frames, ignore_index=True)
                    towrite = io.BytesIO()
                    full_df.to_excel(towrite, index=False, engine='xlsxwriter')
                    st.download_button("Clique para Baixar", towrite.getvalue(), "Relatorio_Geral.xlsx")

            if st.button("🧹 Limpar Dados (Reset)"):
                requests.post(URL_SCRIPT_GOOGLE, json={"tipo": "limpar_tudo"})
                st.success("Planilhas resetadas!")
                st.rerun()
