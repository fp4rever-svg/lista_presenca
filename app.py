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
    st.title("📋 Check-in Logística")
    p_tipo = st.radio("Entrar como:", ["Líder", "Administrador"], horizontal=True)

    if p_tipo == "Líder":
        u_sel = st.selectbox("Selecione seu nome:", ["--"] + LIDERES)
        if u_sel != "--":
            s_in = st.text_input("Senha:", type="password")
            if st.button("Entrar"):
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
        liberado = verificar_liberacao_especial()
        
        try:
            df = pd.read_csv(get_sheet_url(lider))
            df.rename(columns={df.columns[0]: 'Colaborador'}, inplace=True)

            with st.form("form_lider"):
                st.subheader(f"Lista de {lider}")
                
                lista_enviar = []
                # Cabeçalho dinâmico
                if liberado:
                    st.info("⏰ MODO HORA EXTRA / FRETADO ATIVO")
                    cols_head = st.columns([3, 1, 1, 3])
                    cols_head[0].write("**Nome**")
                    cols_head[1].write("**H.E.**")
                    cols_head[2].write("**Fret.**")
                    cols_head[3].write("**Observação**")
                else:
                    cols_head = st.columns([3, 1, 3])
                    cols_head[0].write("**Nome**")
                    cols_head[1].write("**Presença**")
                    cols_head[2].write("**Observação**")

                for i, row in df.iterrows():
                    if pd.isna(row['Colaborador']): continue
                    
                    h_val, f_val, p_val = "Não", "Não", "FALTA"
                    
                    if liberado:
                        c = st.columns([3, 1, 1, 3])
                        c[0].write(row['Colaborador'])
                        if c[1].checkbox("⚡", key=f"he_{i}"): h_val = "Sim"
                        if c[2].checkbox("🚌", key=f"fr_{i}"): f_val = "Sim"
                        obs = c[3].text_input("", key=f"o_{i}", label_visibility="collapsed")
                        p_val = "OK" # No modo HE, assume-se presença OK por padrão ou mantém neutro
                    else:
                        c = st.columns([3, 1, 3])
                        c[0].write(row['Colaborador'])
                        if c[1].checkbox("OK", key=f"p_{i}"): p_val = "OK"
                        obs = c[2].text_input("", key=f"o_{i}", label_visibility="collapsed")

                    lista_enviar.append({"nome": row['Colaborador'], "status": p_val, "he": h_val, "fretado": f_val, "obs": obs})

                if st.form_submit_button("✅ ENVIAR DADOS"):
                    requests.post(URL_SCRIPT_GOOGLE, json={"tipo": "presenca_completa", "lider": lider, "lista": lista_enviar})
                    st.success("Dados enviados com sucesso!")
                    st.balloons()

        except Exception as e: st.error(f"Erro ao carregar lista: {e}")

    # --- TELA ADMIN ---
    elif st.session_state.perfil == "Admin":
        t1, t2 = st.tabs(["Monitoramento", "Ferramentas & Acessos"])

        with t1:
            st.subheader("Envios de Hoje")
            hoje = datetime.now().strftime("%d/%m")
            for l in LIDERES:
                try:
                    df_s = pd.read_csv(get_sheet_url(l))
                    if any(hoje in str(x) for x in df_s.iloc[:, 3]):
                        st.success(f"✅ {l}: Enviado")
                    else: st.error(f"❌ {l}: Pendente")
                except: st.warning(f"⚠️ {l}: Erro na aba")

        with t2:
            # 1. Liberação Especial
            st.subheader("⚙️ Controle de Visibilidade")
            at_status = verificar_liberacao_especial()
            if at_status:
                st.success("Status: CAMPOS EXTRAS LIBERADOS")
                if st.button("🔴 BLOQUEAR H.E./FRETADO"):
                    requests.post(URL_SCRIPT_GOOGLE, json={"tipo": "toggle_especial", "status": "OFF"})
                    time.sleep(1)
                    st.rerun()
            else:
                st.warning("Status: CAMPOS EXTRAS OCULTOS")
                if st.button("🟢 LIBERAR H.E./FRETADO"):
                    requests.post(URL_SCRIPT_GOOGLE, json={"tipo": "toggle_especial", "status": "ON"})
                    time.sleep(1)
                    st.rerun()

            st.divider()
            
            # 2. Gestão de Senhas (RESTAURADO)
            st.subheader("🔑 Gestão de Acessos")
            if st.button("🔄 Visualizar Líderes e Senhas"):
                senhas = buscar_senhas_db()
                if senhas:
                    df_acessos = pd.DataFrame(list(senhas.items()), columns=['Líder', 'Senha'])
                    st.table(df_acessos)
                else:
                    st.info("Nenhuma senha encontrada.")

            st.divider()
            
            # 3. Exportação (RESTAURADO)
            st.subheader("📊 Exportação")
            if st.button("📥 Gerar Excel Unificado"):
                try:
                    tabs = []
                    for l in LIDERES:
                        d = pd.read_csv(get_sheet_url(l))
                        d['Lider_Responsavel'] = l
                        tabs.append(d)
                    full_df = pd.concat(tabs)
                    out = io.BytesIO()
                    with pd.ExcelWriter(out, engine='xlsxwriter') as wr:
                        full_df.to_excel(wr, index=False)
                    st.download_button("⬇️ Baixar Arquivo Excel", out.getvalue(), "Relatorio_Checkin.xlsx")
                except: st.error("Erro ao gerar arquivo.")

            if st.button("🧹 RESETAR TUDO (LIMPAR TURNO)"):
                requests.post(URL_SCRIPT_GOOGLE, json={"tipo": "limpar_tudo"})
                st.rerun()
