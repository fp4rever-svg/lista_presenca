import streamlit as st
import pandas as pd
import requests
import urllib.parse
import plotly.express as px
import plotly.graph_objects as go
from io import BytesIO
from datetime import datetime

# 1. CONFIGURAÇÕES
st.set_page_config(page_title="Check-in & Performance | Nova Odessa", layout="wide")

# --- IDs DOS ARQUIVOS ---
ID_PLANILHA_PRESENCA = "1nYm2aRgruykh2YfXTcpCRuHGIqI0TtAFroMEk_p7Ij8"
ID_SHEETS_PROD = "1TR5oI_I4C9IA-QfUp0zaMmS4Dni1J8nG75Flxd1yguA" 

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

else:
    c_h1, c_h2 = st.columns([5, 1])
    c_h1.subheader(f"Bem-vindo, {st.session_state.usuario}")
    if c_h2.button("Sair"):
        st.session_state.logado = False
        st.rerun()

    if st.session_state.perfil == "Lider":
        try:
            df = pd.read_csv(get_csv_url(ID_PLANILHA_PRESENCA, st.session_state.usuario))
            with st.form("f_pres"):
                st.write("### Check-in da Equipe")
                envios = []
                for i, r in df.iterrows():
                    col1, col2, col3 = st.columns([3, 1, 3])
                    col1.write(r.iloc[0])
                    ok = col2.checkbox("Presença", key=f"c{i}")
                    obs = col3.text_input("Obs", key=f"o{i}")
                    envios.append({"nome": r.iloc[0], "status": "OK" if ok else "FALTA", "obs": obs})
                if st.form_submit_button("✅ Finalizar Envio"):
                    requests.post(URL_SCRIPT_GOOGLE, json={"tipo": "presenca", "lider": st.session_state.usuario, "lista": envios})
                    st.success("Dados enviados!")
        except: st.error("Erro na lista.")

    elif st.session_state.perfil == "Admin":
        t1, t2, t3 = st.tabs(["Monitoramento Diário", "Gestão e Comandos", "Performance"])

        with t1:
            st.write("### Status de Envio por Líder")
            try:
                df_c = pd.read_csv(get_csv_url(ID_PLANILHA_PRESENCA, "Controle"))
                for lider_nome in LIDERES:
                    info = df_c[df_c['Lider'] == lider_nome]
                    if not info.empty and info.iloc[0]['Status'] == "Preenchido":
                        st.write(f"✅ **{lider_nome}**: Entregue | {info.iloc[0]['Horario']}")
                    else:
                        st.write(f"⏳ **{lider_nome}**: Pendente | -")
            except: st.info("Erro ao carregar monitoramento.")

        with t2:
            st.write("### Comandos do Sistema")
            c1, c2 = st.columns(2)
            with c1:
                if st.button("🗑️ Resetar Presenças"):
                    requests.post(URL_SCRIPT_GOOGLE, json={"tipo": "reset_presenca"})
                    st.warning("Comando de reset enviado!")
            with c2:
                if st.button("📂 Gerar Relatório"):
                    try:
                        df_rel = pd.read_csv(get_csv_url(ID_PLANILHA_PRESENCA, "Base_Geral"))
                        output = BytesIO()
                        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                            df_rel.to_excel(writer, index=False)
                        st.download_button(label="⬇️ Baixar Excel", data=output.getvalue(), file_name="Relatorio.xlsx")
                    except: st.error("Erro ao gerar arquivo.")

        with t3:
            st.write("### 📈 Produtividade com Metas")
            cf1, cf2 = st.columns(2)
            dep_escolhido = cf1.selectbox("Filtrar Depósito:", ["Todos", "102", "105", "107", "111", "302"])
            op = cf2.radio("Operação:", ["Conferência", "Picking"], horizontal=True)

            aba = "Conf" if op == "Conferência" else "Pick"
            meta_valor = 2000 if op == "Conferência" else 150
            
            try:
                url = get_csv_url(ID_SHEETS_PROD, aba)
                df_p = pd.read_csv(url)

                if not df_p.empty:
                    # Normalização da coluna Depósito para evitar erro de filtro
                    if 'Depósito' in df_p.columns:
                        df_p['Depósito'] = df_p['Depósito'].astype(str).str.replace('.0', '', regex=False).str.strip()
                    
                    if dep_escolhido != "Todos":
                        df_p = df_p[df_p['Depósito'] == dep_escolhido]

                    u_col = df_p.columns[0]
                    ignorar = [u_col, 'Depósito', 'Total Geral', 'Total', 'Soma de Total']
                    h_cols = [c for c in df_p.columns if c not in ignorar and not str(c).startswith('Unnamed')]

                    if h_cols:
                        df_m = df_p.melt(id_vars=[u_col], value_vars=h_cols, var_name='Hora', value_name='Qtd')
                        df_m['Qtd'] = pd.to_numeric(df_m['Qtd'], errors='coerce').fillna(0)

                        # GRÁFICO 1: RANKING INDIVIDUAL (PLOTLY)
                        fig_rank = px.bar(
                            df_m.groupby(u_col)['Qtd'].sum().reset_index(),
                            x=u_col, y='Qtd', text_auto='.0f',
                            title=f"Ranking {op} (Meta: {meta_valor})"
                        )
                        fig_rank.update_traces(textposition="outside")
                        st.plotly_chart(fig_rank, use_container_width=True)

                        # GRÁFICO 2: FLUXO POR HORA COM LINHA DE META
                        fluxo = df_m.groupby('Hora')['Qtd'].sum().reset_index()
                        fig_fluxo = px.line(fluxo, x='Hora', y='Qtd', title=f"Fluxo por Hora - Meta {meta_valor}/h", markers=True)
                        fig_fluxo.add_hline(y=meta_valor, line_dash="dash", line_color="red", annotation_text=f"Meta: {meta_valor}")
                        st.plotly_chart(fig_fluxo, use_container_width=True)

                    else: st.info("Sem dados de horários.")
                else: st.warning(f"A aba '{aba}' está vazia.")
            except Exception as e:
                st.error(f"Erro ao processar dados da aba {aba}. Verifique a estrutura da planilha.")
