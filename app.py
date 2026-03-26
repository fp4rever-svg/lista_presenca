import streamlit as st
import pandas as pd
import requests
import urllib.parse

# 1. CONFIGURAÇÕES
st.set_page_config(page_title="Check-in & Performance | Nova Odessa", layout="wide")

# --- IDs DOS ARQUIVOS ---
ID_PLANILHA_PRESENCA = "1nYm2aRgruykh2YfXTcpCRuHGIqI0TtAFroMEk_p7Ij8"
# SUBSTITUA ABAIXO PELO ID DA SUA NOVA PLANILHA GOOGLE SHEETS (A QUE TEM AS DINÂMICAS)
ID_SHEETS_PROD = "1mKZxkhEjrJN5hidKG4pXNcMDhbgc5Z5C" 

URL_SCRIPT_GOOGLE = "https://script.google.com/macros/s/AKfycbz3J-m4rTKD0Wkr58B2qDsGS81RwZl7-jt3HegpTBI5Fg1mHBJLzoHTvY4D2OW5ZXuClA/exec"
LIDERES = ["Carol", "Elisangela", "Lais Alves", "Leticia", "Renato", "Thiago"]
SENHA_ADMIN = "1234"

# --- FUNÇÕES ---
def get_csv_url(file_id, sheet_name):
    name_enc = urllib.parse.quote(sheet_name)
    return f"https://docs.google.com/spreadsheets/d/{file_id}/gviz/tq?tqx=out:csv&sheet={name_enc}"

def buscar_senhas_db():
    try:
        r = requests.post(URL_SCRIPT_GOOGLE, json={"tipo": "buscar_senhas"}, timeout=5)
        return r.json() if r.status_code == 200 else {}
    except: return {}

# --- LÓGICA DE SESSÃO ---
if 'logado' not in st.session_state:
    st.session_state.update({'logado': False, 'usuario': None, 'perfil': None})

# ==========================================
# LOGIN
# ==========================================
if not st.session_state.logado:
    st.title("🔒 Acesso - Grupo SC (Nova Odessa)")
    p_tipo = st.radio("Entrar como:", ["Líder", "Administrador"], horizontal=True)

    if p_tipo == "Líder":
        u_sel = st.selectbox("Selecione seu nome:", ["--"] + LIDERES)
        if u_sel != "--":
            senhas = buscar_senhas_db()
            s_db = senhas.get(u_sel, "")
            if not s_db:
                s_nova = st.text_input("Defina sua senha:", type="password")
                if st.button("Cadastrar"):
                    requests.post(URL_SCRIPT_GOOGLE, json={"tipo": "definir_senha", "lider": u_sel, "nova_senha": s_nova})
                    st.success("Senha cadastrada!")
                    st.rerun()
            else:
                s_input = st.text_input("Senha:", type="password")
                if st.button("Entrar"):
                    if str(s_input) == str(s_db):
                        st.session_state.update({'logado': True, 'usuario': u_sel, 'perfil': "Lider"})
                        st.rerun()
                    else: st.error("Incorreta.")
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
    c_h1.subheader(f"Usuário: {st.session_state.usuario}")
    if c_h2.button("Sair"):
        st.session_state.logado = False
        st.rerun()

    if st.session_state.perfil == "Lider":
        try:
            df = pd.read_csv(get_csv_url(ID_PLANILHA_PRESENCA, st.session_state.usuario))
            with st.form("f_pres"):
                envios = []
                for i, r in df.iterrows():
                    col1, col2, col3 = st.columns([3, 1, 3])
                    col1.write(r.iloc[0])
                    ok = col2.checkbox("OK", key=f"c{i}")
                    obs = col3.text_input("Obs", key=f"o{i}")
                    envios.append({"nome": r.iloc[0], "status": "OK" if ok else "FALTA", "obs": obs})
                if st.form_submit_button("Enviar"):
                    requests.post(URL_SCRIPT_GOOGLE, json={"tipo": "presenca", "lider": st.session_state.usuario, "lista": envios})
                    st.success("Enviado!")
        except: st.error("Erro na lista.")

    elif st.session_state.perfil == "Admin":
        t1, t2, t3 = st.tabs(["Check-in", "Senhas", "Performance"])

        with t1:
            st.write("Acompanhamento de Equipes")

        with t2:
            if st.button("Ver Senhas"):
                st.table(pd.DataFrame(list(buscar_senhas_db().items()), columns=['Líder', 'Senha']))

        with t3:
            st.write("### 📈 Produtividade (Sheets)")
            col_f1, col_f2 = st.columns(2)
            dep = col_f1.selectbox("Depósito:", ["Todos", 102, 105, 107, 111, 302])
            op = col_f2.radio("Operação:", ["Conferência", "Picking"], horizontal=True)

            aba = "Dinamica Conf" if op == "Conferência" else "Dinamica Picking"
            
            try:
                # Leitura simplificada via CSV (Zero conflito de bibliotecas)
                df_p = pd.read_csv(get_csv_url(ID_SHEETS_PROD, aba))
                
                u_col = df_p.columns[0]
                ignorar = [u_col, 'Depósito', 'Total Geral', 'Total']
                h_cols = [c for c in df_p.columns if c not in ignorar]
                
                if dep != "Todos" and 'Depósito' in df_p.columns:
                    df_p = df_p[df_p['Depósito'] == dep]

                if h_cols:
                    df_m = df_p.melt(id_vars=[u_col], value_vars=h_cols, var_name='Hora', value_name='Qtd').fillna(0)
                    g1, g2 = st.columns(2)
                    with g1:
                        st.write("**Ranking Individual**")
                        st.bar_chart(df_m.groupby(u_col)['Qtd'].sum())
                    with g2:
                        st.write("**Fluxo por Hora**")
                        st.line_chart(df_m.groupby('Hora')['Qtd'].sum())
                else:
                    st.info("Sem dados de horários.")
            except:
                st.warning(f"Certifique-se que a aba '{aba}' existe no Sheets.")
