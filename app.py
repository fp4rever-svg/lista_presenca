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
        r = requests.post(URL_SCRIPT_GOOGLE, json={"tipo": "buscar_senhas"}, timeout=15)
        return r.json() if r.status_code == 200 else {}
    except: return {}

def verificar_liberacao_especial():
    try:
        url = get_sheet_url("Config_Geral")
        df = pd.read_csv(url, header=None)
        return True if str(df.iloc[0, 1]).strip().upper() == "ON" else False
    except: return False

if 'logado' not in st.session_state:
    st.session_state.update({'logado': False, 'usuario': None, 'perfil': None})

# ==========================================
# LOGIN
# ==========================================
if not st.session_state.logado:
    st.title("📋 Check-in Logística")
    perfil = st.radio("Entrar como:", ["Líder", "Administrador"], horizontal=True)

    if perfil == "Líder":
        u_sel = st.selectbox("Selecione seu nome:", ["--"] + LIDERES)
        if u_sel != "--":
            s_db = buscar_senhas_db().get(u_sel)
            if not s_db:
                n_s = st.text_input("Defina sua senha:", type="password")
                if st.button("Cadastrar"):
                    requests.post(URL_SCRIPT_GOOGLE, json={"tipo":"definir_senha","lider":u_sel,"nova_senha":n_s})
                    st.session_state.update({'logado':True,'usuario':u_sel,'perfil':"Lider"})
                    st.rerun()
            else:
                s_in = st.text_input("Senha:", type="password")
                if st.button("Entrar"):
                    if str(s_in) == str(s_db):
                        st.session_state.update({'logado':True,'usuario':u_sel,'perfil':"Lider"})
                        st.rerun()
                    else: st.error("Senha incorreta.")
    else:
        s_adm = st.text_input("Senha Admin:", type="password")
        if st.button("Acessar Admin"):
            if s_adm == SENHA_ADMIN:
                st.session_state.update({'logado':True,'usuario':"Admin",'perfil':"Admin"})
                st.rerun()

# ==========================================
# ÁREA LOGADA
# ==========================================
else:
    c1, c2 = st.columns([5, 1])
    c1.write(f"Usuário: **{st.session_state.usuario}**")
    if c2.button("Sair"):
        st.session_state.logado = False
        st.rerun()

    if st.session_state.perfil == "Lider":
        lider = st.session_state.usuario
        extra = verificar_liberacao_especial()
        try:
            df = pd.read_csv(get_sheet_url(lider))
            with st.form("f_lider"):
                st.subheader(f"Chamada - {lider}")
                lista = []
                cols_sz = [3, 1, 1, 3] if extra else [3, 1, 3]
                for i, row in df.iterrows():
                    if pd.isna(row.iloc[0]): continue
                    ln = st.columns(cols_sz)
                    ln[0].write(row.iloc[0])
                    h_v, f_v, p_v = "Não", "Não", "FALTA"
                    if extra:
                        if ln[1].checkbox("⚡", key=f"h_{i}"): h_v = "Sim"
                        if ln[2].checkbox("🚌", key=f"f_{i}"): f_v = "Sim"
                        obs = ln[3].text_input("", key=f"o_{i}", label_visibility="collapsed")
                        p_v = "OK"
                    else:
                        if ln[1].checkbox("OK", key=f"p_{i}"): p_v = "OK"
                        obs = ln[2].text_input("", key=f"o_{i}", label_visibility="collapsed")
                    lista.append({"nome": row.iloc[0], "status": p_v, "he": h_v, "fretado": f_v, "obs": obs})
                if st.form_submit_button("✅ ENVIAR"):
                    requests.post(URL_SCRIPT_GOOGLE, json={"tipo":"presenca_completa","lider":lider,"lista":lista})
                    st.success("Enviado!")
        except: st.error("Erro ao carregar.")

    elif st.session_state.perfil == "Admin":
        t1, t2, t3, t4 = st.tabs(["Monitoramento", "Pendentes", "Ferramentas", "📊 Dashboard"])

        with t1:
            st.subheader("Envios de Hoje")
            hoje = datetime.now().strftime("%d/%m")
            for l in LIDERES:
                try:
                    # Lê a aba do líder e verifica a COLUNA 4 (Índice 3 - Data)
                    d_ch = pd.read_csv(get_sheet_url(l))
                    # .iloc[:, 3] garante que estamos olhando para a coluna da DATA
                    if d_ch.iloc[:, 3].astype(str).str.contains(hoje).any():
                        st.success(f"✅ {l}: Concluído")
                    else: st.error(f"❌ {l}: Pendente")
                except: st.warning(f"⚠️ {l}: Sem dados")

        with t2:
            try: st.dataframe(pd.read_csv(get_sheet_url("Pendentes")), use_container_width=True)
            except: st.info("Sem solicitações.")

        with t3:
            # Botões de ON/OFF, Senhas, etc (Mantenha o que já tinha)
            if st.button("🔑 Ver Senhas"): st.table(pd.DataFrame(list(buscar_senhas_db().items()), columns=['Líder', 'Senha']))
            if st.button("🧹 Resetar Turno"): requests.post(URL_SCRIPT_GOOGLE, json={"tipo":"limpar_tudo"}); st.rerun()

        with t4:
            st.subheader("Análise Mensal")
            try:
                df_h = pd.read_csv(get_sheet_url("Historico"))
                if not df_h.empty:
                    # FORÇANDO NOMES DE COLUNAS PARA EVITAR ERRO DE POSIÇÃO
                    # Baseado no seu Code.gs: ["Data", "Hora", "Colaborador", "Lider", "Status", "HE", "Fretado", "Obs"]
                    df_h.columns = ["Data", "Hora", "Colaborador", "Lider", "Status", "HE", "Fretado", "Obs"]

                    l_sel = st.multiselect("Filtrar Líder:", df_h['Lider'].unique(), default=df_h['Lider'].unique())
                    df_f = df_h[df_h['Lider'].isin(l_sel)]

                    m1, m2, m3 = st.columns(3)
                    faltas = len(df_f[df_f['Status'] == 'FALTA'])
                    m1.metric("Registros", len(df_f))
                    m2.metric("Faltas", faltas)
                    m3.metric("% Absenteísmo", f"{(faltas/len(df_f))*100:.1f}%" if len(df_f)>0 else "0%")

                    st.write("### Faltas por Líder")
                    graf = df_f[df_f['Status'] == 'FALTA'].groupby('Lider').size().reset_index(name='Total')
                    st.bar_chart(graf.set_index('Lider'))

                    st.write("### Ranking de Horas Extras")
                    he = df_f[df_f['HE'] == 'Sim'].groupby('Colaborador').size().reset_index(name='Qtd').sort_values('Qtd', ascending=False)
                    st.table(he.head(10))
                else: st.info("Histórico vazio.")
            except Exception as e: st.error(f"Erro no histórico: {e}")
