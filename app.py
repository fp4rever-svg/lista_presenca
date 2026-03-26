import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import urllib.parse
import io

# 1. CONFIGURAÇÕES DE PÁGINA
st.set_page_config(page_title="Check-in & Performance | Grupo SC", layout="wide", initial_sidebar_state="collapsed")

# --- IDs DOS ARQUIVOS (Substitua pelos seus IDs do Google Drive) ---
ID_PLANILHA_PRESENCA = "1nYm2aRgruykh2YfXTcpCRuHGIqI0TtAFroMEk_p7Ij8"
ID_EXCEL_PRODUTIVIDADE = "COLOQUE_AQUI_O_ID_DO_SEU_REPORT_CONF_PICK" # <--- ATENÇÃO AQUI

URL_SCRIPT_GOOGLE = "https://script.google.com/macros/s/AKfycbz3J-m4rTKD0Wkr58B2qDsGS81RwZl7-jt3HegpTBI5Fg1mHBJLzoHTvY4D2OW5ZXuClA/exec"
LIDERES = ["Carol", "Elisangela", "Lais Alves", "Leticia", "Renato", "Thiago"]
SENHA_ADMIN = "1234"

# --- FUNÇÕES AUXILIARES ---
def get_csv_url(aba, file_id):
    aba_enc = urllib.parse.quote(aba)
    return f"https://docs.google.com/spreadsheets/d/{file_id}/gviz/tq?tqx=out:csv&sheet={aba_enc}"

def buscar_senhas_db():
    try:
        r = requests.post(URL_SCRIPT_GOOGLE, json={"tipo": "buscar_senhas"})
        return r.json() if r.status_code == 200 else {}
    except: return {}

# --- INICIALIZAÇÃO DE SESSÃO ---
if 'logado' not in st.session_state:
    st.session_state.logado = False
    st.session_state.usuario = None
    st.session_state.perfil = None

# ==========================================
# TELA DE LOGIN
# ==========================================
if not st.session_state.logado:
    st.title("🔒 Acesso ao Sistema - Nova Odessa")
    p_tipo = st.radio("Entrar como:", ["Líder", "Administrador"], horizontal=True)

    if p_tipo == "Líder":
        u_sel = st.selectbox("Selecione seu nome:", ["--"] + LIDERES)
        if u_sel != "--":
            senhas = buscar_senhas_db()
            s_db = senhas.get(u_sel, "")
            if not s_db:
                s_nova = st.text_input("Defina sua senha de primeiro acesso:", type="password")
                if st.button("Cadastrar Senha"):
                    requests.post(URL_SCRIPT_GOOGLE, json={"tipo": "definir_senha", "lider": u_sel, "nova_senha": s_nova})
                    st.success("Senha salva! Faça login.")
                    st.rerun()
            else:
                s_input = st.text_input("Senha:", type="password")
                if st.button("Entrar"):
                    if str(s_input) == str(s_db):
                        st.session_state.logado, st.session_state.usuario, st.session_state.perfil = True, u_sel, "Lider"
                        st.rerun()
                    else: st.error("Senha incorreta.")
    else:
        s_adm = st.text_input("Senha Admin:", type="password")
        if st.button("Acessar"):
            if s_adm == SENHA_ADMIN:
                st.session_state.logado, st.session_state.usuario, st.session_state.perfil = True, "Admin", "Admin"
                st.rerun()

# ==========================================
# ÁREA LOGADA
# ==========================================
else:
    c1, c2 = st.columns([5, 1])
    c1.subheader(f"Bem-vindo, {st.session_state.usuario}")
    if c2.button("🏠 Sair"):
        st.session_state.logado = False
        st.rerun()

    # --- VISÃO DO LÍDER ---
    if st.session_state.perfil == "Lider":
        try:
            df = pd.read_csv(get_csv_url(st.session_state.usuario, ID_PLANILHA_PRESENCA))
            with st.form("f_presenca"):
                st.write(f"Lista de Equipe")
                envios = []
                for i, r in df.iterrows():
                    col1, col2, col3 = st.columns([3, 1, 3])
                    col1.write(r.iloc[0])
                    ok = col2.checkbox("OK", key=f"c_{i}")
                    obs = col3.text_input("Obs", key=f"o_{i}")
                    envios.append({"nome": r.iloc[0], "status": "OK" if ok else "FALTA", "obs": obs})
                if st.form_submit_button("✅ Enviar Presença"):
                    requests.post(URL_SCRIPT_GOOGLE, json={"tipo": "presenca", "lider": st.session_state.usuario, "lista": envios})
                    st.success("Enviado!")
        except: st.error("Erro ao carregar lista.")

    # --- VISÃO ADMIN ---
    elif st.session_state.perfil == "Admin":
        t1, t2, t3 = st.tabs(["Check-in Diário", "Gestão de Acessos", "Performance Operacional (Dashboard)"])

        with t1:
            st.write("Status das Equipes")
            for l in LIDERES:
                st.write(f"- {l}") # Simplificado para o exemplo

        with t2:
            if st.button("Ver Senhas"):
                st.table(pd.DataFrame(list(buscar_senhas_db().items()), columns=['Líder', 'Senha']))

        with t3:
            st.write("📊 Produtividade em Tempo Real")
            c_f1, c_f2 = st.columns(2)
            dep = c_f1.selectbox("Depósito:", ["Todos", 102, 105, 107, 111, 302])
            op = c_f2.radio("Operação:", ["Conferência", "Picking"], horizontal=True)

            aba = "Dinamica Conf" if op == "Conferência" else "Dinamica Picking"
            try:
                # Link para exportar o .xlsm como Excel comum para o pandas
                url_prod = f"https://docs.google.com/spreadsheets/d/{ID_EXCEL_PRODUTIVIDADE}/export?format=xlsx"
                df_p = pd.read_excel(url_prod, sheet_name=aba)

                # Tratamento de Colunas Dinâmicas (Melt)
                u_col = df_p.columns[0]
                ignorar = [u_col, 'Depósito', 'Total Geral', 'Total', 'Soma de Total']
                h_cols = [c for c in df_p.columns if c not in ignorar]
                
                df_m = df_p.melt(id_vars=[u_col], value_vars=h_cols, var_name='Hora', value_name='Qtd').fillna(0)

                # Gráficos
                g1, g2 = st.columns(2)
                with g1:
                    st.write("**Ranking por Usuário**")
                    rank = df_m.groupby(u_col)['Qtd'].sum().sort_values(ascending=False).reset_index()
                    st.bar_chart(rank, x=u_col, y='Qtd')
                with g2:
                    st.write("**Evolução por Hora**")
                    evol = df_m.groupby('Hora')['Qtd'].sum().reset_index()
                    st.line_chart(evol, x='Hora', y='Qtd')
            except Exception as e:
                st.info(f"Aguardando dados da aba {aba}...")
