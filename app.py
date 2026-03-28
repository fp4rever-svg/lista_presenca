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
    # Timestamp para evitar cache do Google
    ts = int(time.time())
    aba_enc = urllib.parse.quote(aba)
    return f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={aba_enc}&t={ts}"

def buscar_senhas_db():
    try:
        r = requests.post(URL_SCRIPT_GOOGLE, json={"tipo": "buscar_senhas"}, timeout=10)
        return r.json() if r.status_code == 200 else {}
    except: return {}

def verificar_liberacao_especial():
    try:
        url = get_sheet_url("Config_Geral")
        # Lemos sem cabeçalho para garantir que pegamos a célula B1 independente do nome
        df = pd.read_csv(url, header=None)
        status = str(df.iloc[0, 1]).strip().upper()
        return True if status == "ON" else False
    except: return False

# --- CONTROLE DE SESSÃO ---
if 'logado' not in st.session_state:
    st.session_state.update({'logado': False, 'usuario': None, 'perfil': None})

# ==========================================
# LOGIN
# ==========================================
if not st.session_state.logado:
    st.title("📋 Sistema de Check-in Logística")
    p_tipo = st.radio("Perfil de Acesso:", ["Líder", "Administrador"], horizontal=True)

    if p_tipo == "Líder":
        u_sel = st.selectbox("Selecione seu nome:", ["-- Selecione --"] + LIDERES)
        if u_sel != "-- Selecione --":
            senhas = buscar_senhas_db()
            s_db = senhas.get(u_sel, "")
            if not s_db:
                n_s = st.text_input("Crie sua senha:", type="password")
                if st.button("Salvar e Entrar"):
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
    c_h1, c_h2 = st.columns([5, 1])
    c_h1.write(f"Conectado: **{st.session_state.usuario}**")
    if c_h2.button("Sair"):
        st.session_state.logado = False
        st.rerun()

    # --- TELA DO LÍDER ---
    if st.session_state.perfil == "Lider":
        lider = st.session_state.usuario
        # Verificação crucial para as colunas extras
        liberado = verificar_liberacao_especial()
        
        try:
            df = pd.read_csv(get_sheet_url(lider))
            df.rename(columns={df.columns[0]: 'Colaborador'}, inplace=True)

            with st.form("f_chamada"):
                st.subheader(f"Chamada - {lider}")
                if liberado:
                    st.success("✅ Campos de Hora Extra e Fretado estão LIBERADOS!")
                
                lista_final = []
                # Define a largura das colunas dinamicamente
                layout = [3, 1, 1, 1, 3] if liberado else [4, 1, 0.1, 0.1, 4]
                
                cols_h = st.columns(layout)
                cols_h[0].write("**Nome**")
                cols_h[1].write("**Pres.**")
                if liberado:
                    cols_h[2].write("**H.E.**")
                    cols_h[3].write("**Fret.**")
                cols_h[4].write("**Observação**")

                for i, row in df.iterrows():
                    if pd.isna(row['Colaborador']): continue
                    c = st.columns(layout)
                    c[0].write(row['Colaborador'])
                    p_ok = c[1].checkbox("OK", key=f"p_{i}")
                    
                    he_v, fr_v = "Não", "Não"
                    if liberado:
                        he_v = "Sim" if c[2].checkbox("⚡", key=f"he_{i}") else "Não"
                        fr_v = "Sim" if c[3].checkbox("🚌", key=f"fr_{i}") else "Não"
                    
                    obs_v = c[4].text_input("", key=f"o_{i}", label_visibility="collapsed")
                    lista_final.append({"nome": row['Colaborador'], "status": "OK" if p_ok else "FALTA", "he": he_v, "fretado": fr_v, "obs": obs_v})

                if st.form_submit_button("✅ ENVIAR CHECK-IN"):
                    requests.post(URL_SCRIPT_GOOGLE, json={"tipo": "presenca_completa", "lider": lider, "lista": lista_final})
                    st.success("Dados enviados com sucesso!")
        except: st.error("Não foi possível carregar a lista. Verifique a internet ou o Sheets.")

    # --- TELA DO ADMINISTRADOR ---
    elif st.session_state.perfil == "Admin":
        t1, t2 = st.tabs(["Monitoramento Diário", "Ferramentas & Exportação"])

        with t1:
            st.subheader("Status de Envio (Hoje)")
            hoje = datetime.now().strftime("%d/%m")
            for l in LIDERES:
                try:
                    df_st = pd.read_csv(get_sheet_url(l))
                    enviado = any(hoje in str(x) for x in df_st.iloc[:, 3])
                    if enviado: st.success(f"✅ {l}: Enviado")
                    else: st.error(f"❌ {l}: Pendente")
                except: st.warning(f"⚠️ {l}: Erro na aba")

        with t2:
            st.subheader("🔓 Liberação de Hora Extra / Fretado")
            status_atual = verificar_liberacao_especial()
            
            if status_atual:
                st.info("STATUS: Campos extras estão VISÍVEIS para os líderes.")
                if st.button("🔴 OCULTAR CAMPOS EXTRAS"):
                    requests.post(URL_SCRIPT_GOOGLE, json={"tipo": "toggle_especial", "status": "OFF"})
                    time.sleep(1)
                    st.rerun()
            else:
                st.warning("STATUS: Campos extras estão OCULTOS.")
                if st.button("🟢 LIBERAR CAMPOS EXTRAS"):
                    requests.post(URL_SCRIPT_GOOGLE, json={"tipo": "toggle_especial", "status": "ON"})
                    time.sleep(1)
                    st.rerun()

            st.divider()
            st.subheader("📥 Exportação de Dados")
            if st.button("📊 Gerar Relatório Excel Unificado"):
                try:
                    all_data = []
                    for l in LIDERES:
                        temp_df = pd.read_csv(get_sheet_url(l))
                        temp_df['Líder'] = l
                        all_data.append(temp_df)
                    
                    final_df = pd.concat(all_data, ignore_index=True)
                    output = io.BytesIO()
                    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                        final_df.to_excel(writer, index=False, sheet_name='Consolidado')
                    
                    st.download_button(
                        label="⬇️ Baixar Planilha Excel",
                        data=output.getvalue(),
                        file_name=f"Checkin_Logistica_{datetime.now().strftime('%d_%m')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                except: st.error("Erro ao consolidar dados. Verifique se as abas estão preenchidas.")

            st.divider()
            if st.button("🧹 RESETAR SISTEMA (LIMPAR TURNO)"):
                requests.post(URL_SCRIPT_GOOGLE, json={"tipo": "limpar_tudo"})
                st.rerun()
