import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import urllib.parse
import time
import io

# 1. CONFIGURAÇÃO DA PÁGINA (Visual Moderno)
st.set_page_config(page_title="Check-in Logística | Grupo SC", layout="wide", page_icon="📋")

# Estilização Customizada (CSS)
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; font-weight: bold; }
    .stTabs [data-baseweb="tab-list"] { gap: 24px; }
    .stTabs [data-baseweb="tab"] { height: 50px; white-space: pre-wrap; font-size: 16px; }
    div[data-testid="stMetricValue"] { font-size: 28px; color: #1f77b4; }
    .status-card { padding: 20px; border-radius: 10px; background-color: white; border: 1px solid #e0e0e0; margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- CONFIGURAÇÕES FIXAS ---
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

# --- CONTROLE DE SESSÃO ---
if 'logado' not in st.session_state:
    st.session_state.update({'logado': False, 'usuario': None, 'perfil': None})

# ==========================================
# TELA DE LOGIN
# ==========================================
if not st.session_state.logado:
    st.title("📋 Check-in Logística")
    
    col_login, _ = st.columns([1.5, 2])
    with col_login:
        perfil_escolhido = st.radio("Entrar como:", ["Líder", "Administrador"], horizontal=True)

        if perfil_escolhido == "Líder":
            lider_sel = st.selectbox("Selecione seu nome:", ["--"] + LIDERES)
            if lider_sel != "--":
                senhas_atuais = buscar_senhas_db()
                senha_no_db = senhas_atuais.get(lider_sel)

                if not senha_no_db:
                    st.warning(f"Olá {lider_sel}, defina sua primeira senha.")
                    nova_senha = st.text_input("Nova Senha:", type="password")
                    if st.button("🚀 Cadastrar e Entrar"):
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

# ==========================================
# ÁREA LOGADA
# ==========================================
else:
    # Cabeçalho Superior
    c_user, c_out = st.columns([5, 1])
    c_user.markdown(f"### Bem-vindo, **{st.session_state.usuario}**")
    if c_out.button("Sair 👋"):
        st.session_state.logado = False
        st.rerun()

    # --- 🔵 VISÃO DO LÍDER ---
    if st.session_state.perfil == "Lider":
        lider_nome = st.session_state.usuario
        is_extra = verificar_liberacao_especial()
        
        try:
            df_lista = pd.read_csv(get_sheet_url(lider_nome))
            df_lista.rename(columns={df_lista.columns[0]: 'Colaborador'}, inplace=True)

            with st.form("chamada_lider"):
                st.subheader(f"📋 Chamada de Equipe")
                if is_extra: st.warning("📢 Modo H.E. Ativado (Domingo/Feriado)")
                
                dados_para_envio = []
                cols = [3, 1, 1, 3] if is_extra else [3, 1, 3]
                
                # Cabeçalho da Tabela
                h = st.columns(cols)
                h[0].write("**Nome**")
                if is_extra:
                    h[1].write("**H.E.**"); h[2].write("**Fret.**"); h[3].write("**Observação**")
                else:
                    h[1].write("**Presença**"); h[2].write("**Observação**")

                # Linhas
                for i, row in df_lista.iterrows():
                    if pd.isna(row['Colaborador']): continue
                    ln = st.columns(cols)
                    ln[0].write(row['Colaborador'])
                    r_he, r_fr, r_pr = "Não", "Não", "FALTA"

                    if is_extra:
                        if ln[1].checkbox("⚡", key=f"he_{i}"): r_he = "Sim"
                        if ln[2].checkbox("🚌", key=f"fr_{i}"): r_fr = "Sim"
                        r_obs = ln[3].text_input("", key=f"ob_{i}", label_visibility="collapsed")
                        r_pr = "OK"
                    else:
                        if ln[1].checkbox("Presente", key=f"pr_{i}"): r_pr = "OK"
                        r_obs = ln[2].text_input("", key=f"ob_{i}", label_visibility="collapsed")
                    
                    dados_para_envio.append({"nome": row['Colaborador'], "status": r_pr, "he": r_he, "fretado": r_fr, "obs": r_obs})

                st.markdown("<br>", unsafe_allow_html=True)
                if st.form_submit_button("✅ FINALIZAR E ENVIAR CHECK-IN"):
                    with st.spinner("Gravando no Google Sheets..."):
                        requests.post(URL_SCRIPT_GOOGLE, json={"tipo": "presenca_completa", "lider": lider_nome, "lista": dados_para_envio})
                        st.success("Tudo certo! Presenças enviadas com sucesso.")

            # --- NOVO: SOLICITAÇÃO DE INCLUSÃO ---
            st.divider()
            with st.expander("➕ Solicitar Novo Colaborador na Lista Fixa", expanded=False):
                st.info("Utilize este campo para pedir ao Admin para incluir um novo funcionário na sua aba.")
                with st.form("form_novo_colab"):
                    n_nome = st.text_input("Nome Completo:")
                    n_setor = st.selectbox("Setor de Alocação:", ["Recebimento", "Separação", "Expedição", "Outros"])
                    if st.form_submit_button("Enviar Solicitação"):
                        if n_nome:
                            payload = {"tipo": "solicitar_inclusao", "nome": n_nome, "lider": lider_nome, "area": n_setor}
                            requests.post(URL_SCRIPT_GOOGLE, json=payload)
                            st.success(f"Solicitação de {n_nome} enviada para a aba Pendentes!")
                        else: st.warning("O nome é obrigatório.")

        except Exception as e:
            st.error(f"Erro ao carregar lista de {lider_nome}. Erro: {e}")

    # --- 🔴 VISÃO DO ADMIN ---
    elif st.session_state.perfil == "Admin":
        t1, t2, t3, t4 = st.tabs(["📡 Monitoramento", "📩 Pendentes", "🛠️ Ferramentas", "📊 Dashboard"])

        with t1:
            st.subheader("Envios de Hoje")
            hoje = datetime.now().strftime("%d/%m")
            c_mon1, c_mon2 = st.columns(2)
            for i, l in enumerate(LIDERES):
                col_target = c_mon1 if i % 2 == 0 else c_mon2
                try:
                    d_ch = pd.read_csv(get_sheet_url(l))
                    if not d_ch.empty and d_ch.iloc[:, 3].astype(str).str.contains(hoje).any():
                        col_target.success(f"✅ **{l}**: Enviado")
                    else: col_target.error(f"❌ **{l}**: Pendente")
                except: col_target.warning(f"⚠️ **{l}**: Sem conexão")

        with t2:
            st.subheader("Novas Solicitações dos Líderes")
            try:
                df_p = pd.read_csv(get_sheet_url("Pendentes"))
                if not df_p.empty:
                    st.dataframe(df_p, use_container_width=True)
                    st.caption("⚠️ Cadastre os nomes acima nas abas do Sheets e limpe a aba 'Pendentes' após o processo.")
                else: st.info("Nenhuma solicitação pendente.")
            except: st.info("Sem solicitações pendentes.")

        with t3:
            st.subheader("Configurações do Sistema")
            lib_status = verificar_liberacao_especial()
            
            c_conf1, c_conf2 = st.columns(2)
            with c_conf1:
                st.markdown("**Modo de Operação**")
                if lib_status:
                    st.success("SISTEMA EM MODO H.E. / DOMINGO")
                    if st.button("🔴 DESATIVAR MODO H.E."):
                        requests.post(URL_SCRIPT_GOOGLE, json={"tipo": "toggle_especial", "status": "OFF"})
                        st.rerun()
                else:
                    st.info("SISTEMA EM MODO ESCALA NORMAL")
                    if st.button("🟢 ATIVAR MODO H.E."):
                        requests.post(URL_SCRIPT_GOOGLE, json={"tipo": "toggle_especial", "status": "ON"})
                        st.rerun()
            
            with c_conf2:
                st.markdown("**Relatórios e Backup**")
                if st.button("📥 Gerar Excel Geral"):
                    try:
                        dfs = [pd.read_csv(get_sheet_url(l)).assign(Lider=l) for l in LIDERES]
                        out = io.BytesIO()
                        with pd.ExcelWriter(out, engine='xlsxwriter') as wr:
                            pd.concat(dfs).to_excel(wr, index=False)
                        st.download_button("⬇️ Baixar Arquivo", out.getvalue(), "Checkin_Geral.xlsx")
                    except: st.error("Erro ao gerar Excel.")

            st.divider()
            st.markdown("**Segurança e Dados**")
            col_seg1, col_seg2 = st.columns(2)
            with col_seg1:
                if st.button("🔑 Visualizar Senhas"):
                    s = buscar_senhas_db()
                    if s: st.table(pd.DataFrame(list(s.items()), columns=['Líder', 'Senha']))
            with col_seg2:
                if st.button("🧹 Limpar Turno (Reset de Hoje)"):
                    if st.checkbox("Confirmo a exclusão dos dados de hoje"):
                        requests.post(URL_SCRIPT_GOOGLE, json={"tipo": "limpar_tudo"})
                        st.success("Dados limpos!")
                        st.rerun()

        with t4:
            st.subheader("Análise Histórica")
            try:
                df_h = pd.read_csv(get_sheet_url("Historico"))
                if not df_h.empty:
                    df_h.columns = ["Data", "Hora", "Colaborador", "Lider", "Status", "HE", "Fretado", "Obs"]
                    
                    l_filt = st.multiselect("Filtrar por Líder:", df_h['Lider'].unique(), default=df_h['Lider'].unique())
                    df_f = df_h[df_h['Lider'].isin(l_filt)]
                    
                    m1, m2, m3 = st.columns(3)
                    m1.metric("Total de Registros", len(df_f))
                    m2.metric("Total de Faltas", len(df_f[df_f['Status'] == 'FALTA']), delta_color="inverse")
                    pres_perc = (len(df_f[df_f['Status'] == 'OK'])/len(df_f)*100) if len(df_f)>0 else 0
                    m3.metric("% de Presença", f"{pres_perc:.1f}%")

                    st.markdown("---")
                    st.write("#### Faltas Acumuladas por Líder")
                    df_graf = df_f[df_f['Status'] == 'FALTA'].groupby('Lider').size().reset_index(name='Total')
                    st.bar_chart(df_graf.set_index('Lider'))
                else: st.info("Histórico ainda não possui dados.")
            except Exception as e: st.error(f"Erro ao carregar Dashboard: {e}")
