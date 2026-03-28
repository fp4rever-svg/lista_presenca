import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import urllib.parse
import io
import time

# 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="Check-in Logística | Grupo SC", layout="wide")

# --- IDs E CONFIGURAÇÕES ---
SHEET_ID = "1nYm2aRgruykh2YfXTcpCRuHGIqI0TtAFroMEk_p7Ij8"
# SEU NOVO LINK ATUALIZADO:
URL_SCRIPT_GOOGLE = "https://script.google.com/macros/s/AKfycbwLDpdSgnGTPwciE-25mUel8Zm46zovwoi9o_AnQrkkKUIOfRK6EuPH3YVD0M0TrBJY2Q/exec"

LIDERES = ["Carol", "Elisangela", "Lais Alves", "Leticia", "Renato", "Thiago"]
SENHA_ADMIN = "1234"

# --- FUNÇÕES DE SUPORTE ---
def get_sheet_url(aba):
    # Adicionamos um timestamp para forçar o Google a entregar dados novos (evita cache)
    timestamp = int(time.time())
    lider_limpo = urllib.parse.quote(aba)
    return f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={lider_limpo}&t={timestamp}"

def buscar_senhas_db():
    try:
        r = requests.post(URL_SCRIPT_GOOGLE, json={"tipo": "buscar_senhas"}, timeout=10)
        return r.json() if r.status_code == 200 else {}
    except: return {}

def verificar_liberacao_especial():
    """Lê a aba Config_Geral para validar se H.E. está ativa"""
    try:
        url = get_sheet_url("Config_Geral")
        df = pd.read_csv(url)
        # B1 deve conter ON ou OFF
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
    st.markdown("## 📋 Sistema de Check-in Logística")
    p_tipo = st.radio("Perfil de Acesso:", ["Líder", "Administrador"], horizontal=True)

    if p_tipo == "Líder":
        u_sel = st.selectbox("Selecione seu nome:", ["-- Selecione --"] + LIDERES)
        if u_sel != "-- Selecione --":
            senhas = buscar_senhas_db()
            s_db = senhas.get(u_sel, "")
            
            if not s_db:
                n_s = st.text_input("Defina sua senha de acesso:", type="password")
                if st.button("Cadastrar Senha"):
                    requests.post(URL_SCRIPT_GOOGLE, json={"tipo": "definir_senha", "lider": u_sel, "nova_senha": n_s})
                    st.success("Senha cadastrada! Entre novamente.")
                    st.rerun()
            else:
                s_in = st.text_input("Digite sua senha:", type="password")
                if st.button("Entrar"):
                    if str(s_in) == str(s_db):
                        st.session_state.update({'logado': True, 'usuario': u_sel, 'perfil': "Lider"})
                        st.rerun()
                    else: st.error("Senha incorreta.")
    else:
        s_adm = st.text_input("Senha Administrativa:", type="password")
        if st.button("Acessar Painel"):
            if s_adm == SENHA_ADMIN:
                st.session_state.update({'logado': True, 'usuario': "Administrador", 'perfil': "Admin"})
                st.rerun()

# ==========================================
# ÁREA LOGADA
# ==========================================
else:
    c_header1, c_header2 = st.columns([5, 1])
    c_header1.write(f"Conectado: **{st.session_state.usuario}**")
    if c_header2.button("Sair"):
        st.session_state.logado = False
        st.rerun()

    # --- PERFIL LÍDER ---
    if st.session_state.perfil == "Lider":
        lider = st.session_state.usuario
        # ESSA LINHA É A CHAVE: Ela checa o Sheets em tempo real
        liberado = verificar_liberacao_especial()
        
        try:
            df = pd.read_csv(get_sheet_url(lider))
            df.rename(columns={df.columns[0]: 'Colaborador'}, inplace=True)

            with st.form("f_chamada"):
                st.subheader(f"Chamada - {lider}")
                if liberado:
                    st.success("✅ Campos de Hora Extra e Fretado liberados pela gerência.")
                
                lista_dados = []
                # Layout das colunas
                if liberado:
                    col_layout = [3, 1, 1, 1, 3]
                else:
                    col_layout = [3, 1, 0.1, 0.1, 3] # Minimiza as colunas extras se ocultas

                h = st.columns(col_layout)
                h[0].write("**Nome**")
                h[1].write("**Pres.**")
                if liberado:
                    h[2].write("**H.E.**")
                    h[3].write("**Fret.**")
                h[4].write("**Observação**")

                for i, row in df.iterrows():
                    if pd.isna(row['Colaborador']): continue
                    cols = st.columns(col_layout)
                    
                    cols[0].write(row['Colaborador'])
                    p_ok = cols[1].checkbox("OK", key=f"p_{i}")
                    
                    he_val, fr_val = "Não", "Não"
                    if liberado:
                        he_chk = cols[2].checkbox("⚡", key=f"he_{i}")
                        fr_chk = cols[3].checkbox("🚌", key=f"fr_{i}")
                        he_val = "Sim" if he_chk else "Não"
                        fr_val = "Sim" if fr_chk else "Não"
                    
                    obs_v = cols[4].text_input("", key=f"o_{i}", placeholder="-", label_visibility="collapsed")
                    
                    lista_dados.append({
                        "nome": row['Colaborador'], "status": "OK" if p_ok else "FALTA",
                        "he": he_val, "fretado": fr_val, "obs": obs_v
                    })

                if st.form_submit_button("✅ ENVIAR DADOS"):
                    requests.post(URL_SCRIPT_GOOGLE, json={"tipo": "presenca_completa", "lider": lider, "lista": lista_dados})
                    st.success("Lista enviada com sucesso!")
                    st.balloons()
        except: st.error("Erro ao carregar lista de colaboradores.")

    # --- PERFIL ADMINISTRADOR ---
    elif st.session_state.perfil == "Admin":
        t1, t2 = st.tabs(["Monitoramento Diário", "Ferramentas & Liberação"])

        with t1:
            st.subheader("Status de Envio (Hoje)")
            data_hoje = datetime.now().strftime("%d/%m")
            
            for l in LIDERES:
                try:
                    df_status = pd.read_csv(get_sheet_url(l))
                    # Busca na coluna D (índice 3)
                    enviado = any(data_hoje in str(x) for x in df_status.iloc[:, 3])
                    if enviado:
                        st.success(f"✅ **{l}**: Enviado")
                    else:
                        st.error(f"❌ **{l}**: Pendente")
                except:
                    st.warning(f"⚠️ **{l}**: Erro de conexão")

        with t2:
            st.subheader("🔓 Controle de Visibilidade")
            
            # Forçamos a verificação agora
            status_he = verificar_liberacao_especial()
            
            if status_he:
                st.info("💡 **STATUS:** As colunas H.E. e Fretado estão **VISÍVEIS**.")
                if st.button("🔴 OCULTAR CAMPOS EXTRAS", use_container_width=True):
                    requests.post(URL_SCRIPT_GOOGLE, json={"tipo": "toggle_especial", "status": "OFF"})
                    st.success("Comando enviado! Atualizando...")
                    time.sleep(1) # Espera o Sheets processar
                    st.rerun()
            else:
                st.warning("💡 **STATUS:** As colunas H.E. e Fretado estão **OCULTAS**.")
                if st.button("🟢 MOSTRAR CAMPOS EXTRAS", use_container_width=True):
                    requests.post(URL_SCRIPT_GOOGLE, json={"tipo": "toggle_especial", "status": "ON"})
                    st.success("Comando enviado! Atualizando...")
                    time.sleep(1) # Espera o Sheets processar
                    st.rerun()

            st.divider()
            c_bt1, c_bt2 = st.columns(2)
            with c_bt1:
                if st.button("🔄 Ver Senhas Atuais"):
                    senhas = buscar_senhas_db()
                    if senhas: st.table(pd.DataFrame(list(senhas.items()), columns=['Líder', 'Senha']))
            with c_bt2:
                if st.button("🧹 RESETAR SISTEMA (LIMPAR TURNO)"):
                    requests.post(URL_SCRIPT_GOOGLE, json={"tipo": "limpar_tudo"})
                    st.success("Planilhas resetadas!")
                    st.rerun()
