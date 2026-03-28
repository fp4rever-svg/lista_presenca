import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import urllib.parse
import io

# 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="Check-in Logística | Grupo SC", layout="wide")

# --- IDs E CONFIGURAÇÕES ---
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
        r = requests.post(URL_SCRIPT_GOOGLE, json={"tipo": "buscar_senhas"}, timeout=5)
        return r.json() if r.status_code == 200 else {}
    except: return {}

def verificar_liberacao_especial():
    """Verifica na aba Config_Geral se a Coluna B está como ON"""
    try:
        url = get_sheet_url("Config_Geral")
        df = pd.read_csv(url)
        # Forçamos a leitura da primeira linha, segunda coluna (B1)
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
    st.title("📋 Sistema de Check-in Logística")
    p_tipo = st.radio("Perfil:", ["Líder", "Administrador"], horizontal=True)

    if p_tipo == "Líder":
        u_sel = st.selectbox("Líder:", ["-- Selecione --"] + LIDERES)
        if u_sel != "-- Selecione --":
            senhas = buscar_senhas_db()
            s_db = senhas.get(u_sel, "")
            if not s_db:
                n_s = st.text_input("Defina sua senha:", type="password")
                if st.button("Salvar Senha"):
                    requests.post(URL_SCRIPT_GOOGLE, json={"tipo": "definir_senha", "lider": u_sel, "nova_senha": n_s})
                    st.rerun()
            else:
                s_in = st.text_input("Senha:", type="password")
                if st.button("Entrar"):
                    if str(s_in) == str(s_db):
                        st.session_state.update({'logado': True, 'usuario': u_sel, 'perfil': "Lider"})
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
    c1.write(f"Conectado como: **{st.session_state.usuario}**")
    if c2.button("🏠 Sair"):
        st.session_state.logado = False
        st.rerun()

    # --- VISÃO LÍDER ---
    if st.session_state.perfil == "Lider":
        lider = st.session_state.usuario
        liberado = verificar_liberacao_especial() # Checa se mostra HE/Fretado
        
        try:
            df = pd.read_csv(get_sheet_url(lider))
            df.rename(columns={df.columns[0]: 'Colaborador'}, inplace=True)

            with st.form("f_chamada"):
                st.subheader(f"Chamada - {lider}")
                if liberado:
                    st.info("⚠️ Atenção: Campos de Hora Extra e Fretado liberados!")
                
                lista_final = []
                # Cabeçalho manual para melhor visualização
                h1, h2, h3, h4, h5 = st.columns([3, 1, 1, 1, 3])
                h1.write("**Nome**")
                h2.write("**Pres.**")
                if liberado:
                    h3.write("**H.E.**")
                    h4.write("**Fret.**")
                h5.write("**Obs**")

                for i, row in df.iterrows():
                    if pd.isna(row['Colaborador']): continue
                    col1, col2, col3, col4, col5 = st.columns([3, 1, 1, 1, 3])
                    
                    col1.write(row['Colaborador'])
                    pres_ok = col2.checkbox("OK", key=f"p_{i}")
                    
                    he_v, fr_v = "Não", "Não"
                    if liberado:
                        he_chk = col3.checkbox("⚡", key=f"he_{i}")
                        fr_chk = col4.checkbox("🚌", key=f"fr_{i}")
                        he_v = "Sim" if he_chk else "Não"
                        fr_v = "Sim" if fr_chk else "Não"
                    
                    obs_v = col5.text_input("", key=f"o_{i}", placeholder="-", label_visibility="collapsed")
                    
                    lista_final.append({
                        "nome": row['Colaborador'], "status": "OK" if pres_ok else "FALTA",
                        "he": he_v, "fretado": fr_v, "obs": obs_v
                    })

                if st.form_submit_button("✅ ENVIAR CHECK-IN"):
                    requests.post(URL_SCRIPT_GOOGLE, json={"tipo": "presenca_completa", "lider": lider, "lista": lista_final})
                    st.success("Enviado com sucesso!")
                    st.balloons()
        except: st.error("Erro ao carregar sua lista no Sheets.")

    # --- VISÃO ADMIN ---
    elif st.session_state.perfil == "Admin":
        t1, t2 = st.tabs(["Monitoramento Diário", "Ferramentas & Liberação"])

        with t1:
            st.subheader("Status de Envio (Hoje)")
            data_hoje = datetime.now().strftime("%d/%m")
            
            for l in LIDERES:
                try:
                    # Lógica de monitoramento restaurada
                    df_s = pd.read_csv(get_sheet_url(l))
                    # Varre a coluna D (índice 3) buscando a data de hoje
                    enviado = any(data_hoje in str(x) for x in df_s.iloc[:, 3])
                    if enviado:
                        st.success(f"✅ **{l}**: Enviado")
                    else:
                        st.error(f"❌ **{l}**: Pendente")
                except:
                    st.warning(f"⚠️ **{l}**: Erro na leitura")

        with t2:
            st.subheader("🔓 Controle de Hora Extra / Fretado")
            status_atual = verificar_liberacao_especial()
            
            if status_atual:
                st.info("🔓 **STATUS:** Campos Extras estão VISÍVEIS para os líderes.")
                if st.button("🔴 BLOQUEAR CAMPOS (OCULTAR)", use_container_width=True):
                    requests.post(URL_SCRIPT_GOOGLE, json={"tipo": "toggle_especial", "status": "OFF"})
                    st.rerun()
            else:
                st.warning("🔒 **STATUS:** Campos Extras estão OCULTOS para os líderes.")
                if st.button("🟢 LIBERAR CAMPOS (MOSTRAR)", use_container_width=True):
                    requests.post(URL_SCRIPT_GOOGLE, json={"tipo": "toggle_especial", "status": "ON"})
                    st.rerun()

            st.divider()
            col_bt1, col_bt2 = st.columns(2)
            with col_bt1:
                if st.button("🔄 Ver Senhas"):
                    s = buscar_senhas_db()
                    if s: st.table(pd.DataFrame(list(s.items()), columns=['Líder', 'Senha']))
            with col_bt2:
                if st.button("🧹 RESETAR TUDO"):
                    requests.post(URL_SCRIPT_GOOGLE, json={"tipo": "limpar_tudo"})
                    st.success("Sistema limpo para o próximo turno!")
                    st.rerun()
