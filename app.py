import streamlit as st
import pandas as pd
import requests
from datetime import datetime, date
import urllib.parse
import time
import io

# 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="Check-in Logística | Grupo SC", layout="wide", page_icon="📋")

# Custom CSS para melhorar o visual mobile e reduzir espaçamentos
st.markdown("""
    <style>
    [data-testid="stCheckbox"] { margin-bottom: -15px; }
    .stTextInput { margin-top: -10px; }
    hr { margin: 10px 0px; }
    </style>
    """, unsafe_allow_html=True)

# --- CONFIGURAÇÕES ---
SHEET_ID = "1nYm2aRgruykh2YfXTcpCRuHGIqI0TtAFroMEk_p7Ij8"
URL_SCRIPT_GOOGLE = "https://script.google.com/macros/s/AKfycbwLDpdSgnGTPwciE-25mUel8Zm46zovwoi9o_AnQrkkKUIOfRK6EuPH3YVD0M0TrBJY2Q/exec"
LIDERES = ["Carol", "Elisangela", "Lais Alves", "Leticia", "Renato", "Tiago"]
SENHA_ADMIN = "1234"

# --- FUNÇÕES DE SUPORTE ---
def get_sheet_url(aba):
    ts = int(time.time())
    aba_enc = urllib.parse.quote(aba)
    return f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={aba_enc}&t={ts}"

def buscar_senhas_db():
    try:
        r = requests.post(URL_SCRIPT_GOOGLE, json={"tipo": "buscar_senhas"}, timeout=15)
        return r.json() if r.status_code == 200 else {}
    except: return {}

def verificar_liberacao_especial():
    try:
        url = get_sheet_url("Config_Geral")
        df = pd.read_csv(url, header=None)
        return True if str(df.iloc[0, 1]).strip().upper() == "ON" else False
    except: return False

def formatar_nome_curto(nome):
    partes = str(nome).split()
    return " ".join(partes[:2]) if len(partes) > 1 else nome

# --- INICIALIZAÇÃO DO SESSION STATE ---
if 'logado' not in st.session_state: st.session_state.logado = False
if 'usuario' not in st.session_state: st.session_state.usuario = None
if 'perfil' not in st.session_state: st.session_state.perfil = None
if 'confirmacao_envio' not in st.session_state: st.session_state.confirmacao_envio = False

# ==========================================
# ÁREA DE ACESSO (LOGIN)
# ==========================================
if not st.session_state.logado:
    st.title("📋 Check-in Logística")
    perfil_escolhido = st.radio("Entrar como:", ["Líder", "Administrador"], horizontal=True)

    if perfil_escolhido == "Líder":
        lider_sel = st.selectbox("Selecione seu nome:", ["--"] + LIDERES)
        if lider_sel != "--":
            senhas_atuais = buscar_senhas_db()
            senha_no_db = senhas_atuais.get(lider_sel)

            if not senha_no_db:
                st.warning(f"Olá {lider_sel}, defina sua primeira senha.")
                nova_senha = st.text_input("Nova Senha:", type="password")
                if st.button("Cadastrar e Entrar"):
                    requests.post(URL_SCRIPT_GOOGLE, json={"tipo": "definir_senha", "lider": lider_sel, "nova_senha": nova_senha})
                    st.session_state.update({'logado': True, 'usuario': lider_sel, 'perfil': "Lider"})
                    st.rerun()
            else:
                senha_input = st.text_input("Senha de Acesso:", type="password")
                if st.button("Entrar"):
                    if str(senha_input) == str(senha_no_db):
                        st.session_state.update({'logado': True, 'usuario': lider_sel, 'perfil': "Lider"})
                        st.rerun()
                    else: st.error("Senha incorreta.")

    elif perfil_escolhido == "Administrador":
        senha_adm_input = st.text_input("Senha Administrativa:", type="password")
        if st.button("Acessar Painel Admin"):
            if senha_adm_input == SENHA_ADMIN:
                st.session_state.update({'logado': True, 'usuario': "Administrador", 'perfil': "Admin"})
                st.rerun()
            else: st.error("Acesso Negado.")

else:
    c1, c2 = st.columns([5, 1])
    c1.write(f"Usuário: **{st.session_state.usuario}**")
    if c2.button("Sair/Logoff"):
        for key in list(st.session_state.keys()): del st.session_state[key]
        st.rerun()

    # --- PERFIL LÍDER ---
    if st.session_state.perfil == "Lider":
        lider_nome = st.session_state.usuario
        
        if st.session_state.confirmacao_envio:
            st.success("### ✅ DADOS SALVOS COM SUCESSO!")
            if st.button("Fazer Nova Chamada / Atualizar"):
                st.session_state.confirmacao_envio = False
                st.rerun()
            st.stop()

        st.divider()
        is_extra = verificar_liberacao_especial()
        
        try:
            url_lista = get_sheet_url(lider_nome)
            df_lista = pd.read_csv(url_lista)
            
            with st.form("chamada_lider"):
                st.subheader(f"Chamada - {lider_nome} " + ("(EXTRA)" if is_extra else "(NORMAL)"))
                dados_para_envio = []

                for i, row in df_lista.iterrows():
                    if pd.isna(row.iloc[0]) and pd.isna(row.iloc[4]): continue 
                    
                    # Filtro Afastamento (Coluna J)
                    if len(row) > 9 and pd.notna(row.iloc[9]):
                        if str(row.iloc[9]).strip() != "" and str(row.iloc[9]).lower() != "nan":
                            continue

                    nome_completo = str(row.iloc[0])
                    nome_curto = formatar_nome_curto(nome_completo)
                    matricula = str(row.iloc[4])
                    
                    # Layout Mobile: Nome e Checkbox na mesma linha
                    col_nome, col_check = st.columns([3, 1])
                    col_nome.write(f"**{nome_curto}** `{matricula}`")
                    
                    r_he, r_fr, r_pr = "Não", "Não", "FALTA"

                    if is_extra:
                        with col_check:
                            if st.checkbox("⚡", key=f"he_{i}"): r_he = "Sim"
                            if st.checkbox("🚌", key=f"fr_{i}"): r_fr = "Sim"
                            r_pr = "OK"
                    else:
                        if col_check.checkbox("OK", key=f"pr_{i}"): r_pr = "OK"

                    # Observação logo abaixo
                    r_obs = st.text_input("Obs:", key=f"ob_{i}", label_visibility="collapsed", placeholder="Observação...")
                    st.markdown("---")
                    
                    dados_para_envio.append({"matricula": matricula, "nome": nome_completo, "status": r_pr, "he": r_he, "fretado": r_fr, "obs": r_obs})

                if st.form_submit_button("✅ FINALIZAR E ENVIAR", use_container_width=True):
                    with st.spinner("Enviando..."):
                        resp = requests.post(URL_SCRIPT_GOOGLE, json={
                            "tipo": "presenca_completa", 
                            "lider": lider_nome, 
                            "lista": dados_para_envio,
                            "is_extra": is_extra 
                        })
                        if resp.status_code == 200:
                            st.session_state.confirmacao_envio = True
                            st.rerun()
                        else: st.error("Erro ao salvar.")
        except: st.info("Carregando lista...")

    # --- PERFIL ADMIN ---
    elif st.session_state.perfil == "Admin":
        t1, t2, t3, t4 = st.tabs(["Monitoramento", "Pendentes", "Ferramentas", "📊 Dashboard"])

        with t1:
            st.subheader("Envios de Hoje")
            for l in LIDERES:
                try:
                    df_check = pd.read_csv(get_sheet_url(l))
                    horarios = df_check.iloc[:, 5].dropna().astype(str)
                    horarios = horarios[horarios.str.strip() != ""]
                    if not horarios.empty: st.success(f"✅ **{l}**: {horarios.iloc[0]}")
                    else: st.error(f"❌ **{l}**: Pendente")
                except: st.warning(f"⚠️ **{l}**: Sem dados.")

        with t3:
            lib_status = verificar_liberacao_especial()
            if st.button(f"MUDAR PARA {'NORMAL' if lib_status else 'HORA EXTRA'}"):
                requests.post(URL_SCRIPT_GOOGLE, json={"tipo": "toggle_especial", "status": "OFF" if lib_status else "ON"})
                st.rerun()

        with t4:
            st.subheader("📊 Dashboard")
            try:
                df_h = pd.read_csv(get_sheet_url("Historico"))
                if not df_h.empty:
                    # CORREÇÃO: Tratamento robusto para a coluna de data (geralmente a primeira)
                    coluna_data = df_h.columns[0]
                    df_h['Data_DT'] = pd.to_datetime(df_h[coluna_data], dayfirst=True, errors='coerce').dt.date
                    df_h = df_h.dropna(subset=['Data_DT'])
                    
                    c1, c2 = st.columns(2)
                    d_ini = c1.date_input("Início:", df_h['Data_DT'].min())
                    d_fim = c2.date_input("Fim:", date.today())
                    
                    df_f = df_h[(df_h['Data_DT'] >= d_ini) & (df_h['Data_DT'] <= d_fim)]
                    st.dataframe(df_f, use_container_width=True)
                else: st.info("Histórico vazio.")
            except Exception as e: st.error(f"Erro ao processar Dashboard: {e}")
