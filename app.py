import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import urllib.parse
import io

# 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(
    page_title="Check-in Logística | Grupo SC", 
    layout="centered", 
    initial_sidebar_state="collapsed"
)

# --- ESTILIZAÇÃO CSS (VISUAL LIMPO) ---
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
# ATENÇÃO: Substitua pela URL da sua última implantação do Apps Script
URL_SCRIPT_GOOGLE = "https://script.google.com/macros/s/AKfycbz3J-m4rTKD0Wkr58B2qDsGS81RwZl7-jt3HegpTBI5Fg1mHBJLzoHTvY4D2OW5ZXuClA/exec"

LIDERES = ["Carol", "Elisangela", "Lais Alves", "Leticia", "Renato", "Thiago"]
SENHA_ADMIN = "1234"

# --- FUNÇÕES DE SUPORTE ---
def get_sheet_url(aba):
    lider_limpo = urllib.parse.quote(aba)
    return f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={lider_limpo}"

def buscar_senhas_db():
    try:
        response = requests.post(URL_SCRIPT_GOOGLE, json={"tipo": "buscar_senhas"})
        if response.status_code == 200:
            return response.json()
        return {}
    except:
        return {}

# --- CONTROLE DE SESSÃO ---
if 'logado' not in st.session_state:
    st.session_state.logado = False
    st.session_state.usuario = None
    st.session_state.perfil = None

# ==========================================
# TELA DE LOGIN / TELA INICIAL
# ==========================================
if not st.session_state.logado:
    st.markdown("<h1 class='main-title'>📋 Sistema de Check-in Logística</h1>", unsafe_allow_html=True)
    st.markdown("---")
    
    col_login, _ = st.columns([2, 1])
    with col_login:
        perfil_tipo = st.radio("Selecione o perfil de acesso:", ["Líder", "Administrador"], horizontal=True)

    if perfil_tipo == "Líder":
        user_select = st.selectbox("Selecione seu nome:", ["-- Selecione --"] + LIDERES)
        
        if user_select != "-- Selecione --":
            # Busca senhas na aba Config_Acesso
            dict_senhas = buscar_senhas_db()
            senha_cadastrada = dict_senhas.get(user_select, "")

            # CASO 1: LÍDER NÃO TEM SENHA (CRIAÇÃO)
            if not senha_cadastrada or str(senha_cadastrada).strip() == "":
                st.warning(f"Olá {user_select}, você ainda não possui uma senha cadastrada.")
                nova_senha = st.text_input("Crie uma senha agora:", type="password")
                if st.button("Confirmar e Salvar Senha"):
                    if len(nova_senha) >= 3:
                        requests.post(URL_SCRIPT_GOOGLE, json={"tipo": "definir_senha", "lider": user_select, "nova_senha": nova_senha})
                        st.success("Senha cadastrada com sucesso! Faça login agora.")
                        st.rerun()
                    else:
                        st.error("A senha deve ter no mínimo 3 caracteres.")
            
            # CASO 2: LÍDER JÁ TEM SENHA (LOGIN)
            else:
                senha_input = st.text_input("Digite sua senha:", type="password")
                if st.button("Entrar"):
                    if str(senha_input) == str(senha_cadastrada):
                        st.session_state.logado = True
                        st.session_state.usuario = user_select
                        st.session_state.perfil = "Lider"
                        st.rerun()
                    else:
                        st.error("Senha incorreta. Tente novamente.")

    else: # Perfil Administrador
        senha_adm_input = st.text_input("Senha Administrativa:", type="password")
        if st.button("Acessar Painel"):
            if senha_adm_input == SENHA_ADMIN:
                st.session_state.logado = True
                st.session_state.usuario = "Administrador"
                st.session_state.perfil = "Admin"
                st.rerun()
            else:
                st.error("Acesso negado.")

# ==========================================
# ÁREA LOGADA
# ==========================================
else:
    # Cabeçalho com Botão Sair
    c1, c2 = st.columns([5, 1])
    c1.write(f"Conectado como: **{st.session_state.usuario}**")
    if c2.button("🏠 Sair"):
        st.session_state.logado = False
        st.session_state.usuario = None
        st.rerun()
    
    st.markdown("---")

    # --- TELA DO LÍDER (FORMULÁRIO DE PRESENÇA) ---
    if st.session_state.perfil == "Lider":
        lider = st.session_state.usuario
        try:
            url_lider = get_sheet_url(lider)
            df_equipe = pd.read_csv(url_lider)
            df_equipe.rename(columns={df_equipe.columns[0]: 'Colaborador'}, inplace=True)
            
            with st.form("form_lider"):
                st.subheader(f"Chamada: {lider}")
                lista_dados = []
                for i, row in df_equipe.iterrows():
                    if pd.isna(row['Colaborador']): continue
                    col_nome, col_pres, col_obs = st.columns([3, 1, 3])
                    col_nome.write(f"{row['Colaborador']}")
                    pres = col_pres.checkbox("OK", key=f"check_{i}")
                    obs_text = col_obs.text_input("Obs", key=f"obs_{i}", placeholder="-")
                    lista_dados.append({"nome": row['Colaborador'], "status": "OK" if pres else "FALTA", "obs": obs_text})
                
                if st.form_submit_button("✅ ENVIAR PARA LOGÍSTICA"):
                    with st.spinner('Gravando...'):
                        requests.post(URL_SCRIPT_GOOGLE, json={"tipo": "presenca", "lider": lider, "lista": lista_dados})
                        st.success("Lista enviada com sucesso!")
                        st.balloons()
            
            # Solicitação de Inclusão
            with st.expander("➕ Solicitar Novo Colaborador"):
                with st.form("inc_colab"):
                    nome_n = st.text_input("Nome Completo")
                    area_n = st.text_input("Setor")
                    if st.form_submit_button("Enviar Solicitação"):
                        requests.post(URL_SCRIPT_GOOGLE, json={"tipo": "inclusao", "colaborador": nome_n, "lider": lider, "area": area_n})
                        st.success("Solicitação enviada!")

        except:
            st.error("Não foi possível carregar sua equipe. Verifique o Google Sheets.")

    # --- TELA DO ADMINISTRADOR (PAINEL DE CONTROLE) ---
    elif st.session_state.perfil == "Admin":
        st.subheader("📊 Painel de Controle Administrativo")
        
        tab1, tab2 = st.tabs(["Monitoramento Diário", "Ferramentas"])
        
        with tab1:
            st.write(f"Status de Envio - **{datetime.now().strftime('%d/%m/%Y')}**")
            data_hoje_str = datetime.now().strftime("%d/%m")
            
            for l in LIDERES:
                try:
                    df_status = pd.read_csv(get_sheet_url(l), dtype=str).fillna("")
                    enviado = False
                    if not df_status.empty and df_status.shape[1] >= 4:
                        # Varre coluna D em busca do dia de hoje
                        if any(data_hoje_str in str(d) for d in df_status.iloc[:, 3]):
                            enviado = True
                    
                    if enviado:
                        st.success(f"✅ {l}: Lista Enviada")
                    else:
                        st.error(f"❌ {l}: Pendente")
                except:
                    st.warning(f"⚠️ {l}: Erro na leitura da aba")

        with tab2:
            st.write("### Ações Globais")
            if st.button("📥 Gerar Excel Unificado (Todas as Equipes)"):
                frames = []
                for l in LIDERES:
                    try:
                        temp = pd.read_csv(get_sheet_url(l))
                        temp.rename(columns={temp.columns[0]: 'Colaborador'}, inplace=True)
                        temp['Líder'] = l
                        frames.append(temp)
                    except: pass
                if frames:
                    final_df = pd.concat(frames, ignore_index=True)
                    buffer = io.BytesIO()
                    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                        final_df.to_excel(writer, index=False)
                    st.download_button("Baixar Arquivo Excel", buffer.getvalue(), "Consolidado_Logistica.xlsx")

            st.markdown("---")
            st.warning("Atenção: O reset apaga as colunas B, C, D e F de todos os líderes.")
            if st.button("🧹 RESETAR PLANILHAS (Limpar Turno)"):
                requests.post(URL_SCRIPT_GOOGLE, json={"tipo": "limpar_tudo"})
                st.success("Planilhas resetadas com sucesso!")
                st.rerun()
