import streamlit as st
import pandas as pd
import requests
import urllib.parse
import plotly.express as px
from io import BytesIO
from datetime import datetime

# 1. CONFIGURAÇÕES
st.set_page_config(page_title="Check-in & Performance | Nova Odessa", layout="wide")

# --- IDs DOS ARQUIVOS ---
ID_PLANILHA_PRESENCA = "1nYm2aRgruykh2YfXTcpCRuHGIqI0TtAFroMEk_p7Ij8"
ID_SHEETS_PROD = "1mKZxkhEjrJN5hidKG4pXNcMDhbgc5Z5C" 

URL_SCRIPT_GOOGLE = "https://script.google.com/macros/s/AKfycbz3J-m4rTKD0Wkr58B2qDsGS81RwZl7-jt3HegpTBI5Fg1mHBJLzoHTvY4D2OW5ZXuClA/exec"
LIDERES = ["Carol", "Gabriel / Elisangela", "Lais Alves", "Leticia", "Renato", "Thiago"]
SENHA_ADMIN = "1234"

# --- FUNÇÃO DE URL ---
def get_csv_url(file_id, sheet_name):
    name_enc = urllib.parse.quote(sheet_name)
    return f"https://docs.google.com/spreadsheets/d/{file_id}/gviz/tq?tqx=out:csv&sheet={name_enc}"

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
        s_input = st.text_input("Senha:", type="password")
        if st.button("Entrar"):
            st.session_state.update({'logado': True, 'usuario': u_sel, 'perfil': "Lider"})
            st.rerun()
    else:
        s_adm = st.text_input("Senha Admin:", type="password")
        if st.button("Acessar"):
            if s_adm == SENHA_ADMIN:
                st.session_state.update({'logado': True, 'usuario': "Admin", 'perfil': "Admin"})
                st.rerun()
            else:
                st.error("Senha incorreta.")

# ==========================================
# ÁREA LOGADA
# ==========================================
else:
    c_h1, c_h2 = st.columns([5, 1])
    c_h1.subheader(f"Painel {st.session_state.perfil}: {st.session_state.usuario}")
    if c_h2.button("Sair"):
        st.session_state.logado = False
        st.rerun()

    # --- ABA ADMIN ---
    if st.session_state.perfil == "Admin":
        t1, t2, t3 = st.tabs(["Monitoramento Diário", "Gestão e Comandos", "Performance"])

        with t1:
            st.write("### Status de Envio por Líder")
            try:
                df_c = pd.read_csv(get_csv_url(ID_PLANILHA_PRESENCA, "Controle"))
                df_c.columns = df_c.columns.str.strip() # Limpa colunas
                for l in LIDERES:
                    # Busca flexível (ignora espaços)
                    match = df_c[df_c['Lider'].astype(str).str.strip().str.upper() == l.strip().upper()]
                    if not match.empty and "Preenchido" in str(match.iloc[0]['Status']):
                        st.write(f"✅ **{l}**: Entregue | {match.iloc[0]['Horario']}")
                    else:
                        st.write(f"⏳ **{l}**: Pendente | -")
            except:
                st.info("Aguardando sincronização inicial da planilha...")

        with t2:
            st.write("### Comandos Administrativos")
            c1, c2 = st.columns(2)
            with c1:
                if st.button("🗑️ Resetar Presenças"):
                    requests.post(URL_SCRIPT_GOOGLE, json={"tipo": "reset_presenca"})
                    st.warning("Reset solicitado!")
            with c2:
                if st.button("📂 Exportar Presença (Excel)"):
                    try:
                        df_rel = pd.read_csv(get_csv_url(ID_PLANILHA_PRESENCA, "Base_Geral"))
                        out = BytesIO()
                        with pd.ExcelWriter(out, engine='xlsxwriter') as wr:
                            df_rel.to_excel(wr, index=False)
                        st.download_button("⬇️ Download", out.getvalue(), "Relatorio.xlsx")
                    except: st.error("Erro ao gerar arquivo.")

        with t3:
            st.write("### 📈 Performance (Metas)")
            cf1, cf2 = st.columns(2)
            dep_f = cf1.selectbox("Depósito:", ["Todos", "102", "105", "107", "111", "302"])
            op = cf2.radio("Operação:", ["Conferência", "Picking"], horizontal=True)

            aba = "Conf" if op == "Conferência" else "Pick"
            meta = 2000 if op == "Conferência" else 150
            
            try:
                df_p = pd.read_csv(get_csv_url(ID_SHEETS_PROD, aba))
                df_p.columns = df_p.columns.str.strip()
                
                # Filtro de Depósito corrigido (Lógica Robusta)
                col_dep = [c for c in df_p.columns if 'Dep' in c]
                if col_dep and dep_f != "Todos":
                    c_n = col_dep[0]
                    # Converte para string e limpa decimais (ex: 105.0 -> 105)
                    df_p[c_n] = df_p[c_n].astype(str).str.split('.').str[0].str.strip()
                    df_p = df_p[df_p[c_n] == dep_f]

                if not df_p.empty:
                    u_col = df_p.columns[0]
                    ignorar = [u_col, 'Depósito', 'Total Geral', 'Total']
                    h_cols = [c for c in df_p.columns if c not in ignorar and not str(c).startswith('Unnamed')]

                    if h_cols:
                        df_m = df_p.melt(id_vars=[u_col], value_vars=h_cols, var_name='Hora', value_name='Qtd')
                        df_m['Qtd'] = pd.to_numeric(df_m['Qtd'], errors='coerce').fillna(0)

                        # Gráfico Ranking Individual
                        rank_df = df_m.groupby(u_col)['Qtd'].sum().reset_index().sort_values('Qtd', ascending=False)
                        fig_r = px.bar(rank_df, x=u_col, y='Qtd', text_auto='.0f', title=f"Ranking {op}")
                        fig_r.update_traces(textposition='outside')
                        st.plotly_chart(fig_r, use_container_width=True)

                        # Gráfico Fluxo por Hora
                        fluxo_df = df_m.groupby('Hora')['Qtd'].sum().reset_index()
                        fig_f = px.line(fluxo_df, x='Hora', y='Qtd', markers=True, title=f"Fluxo Horário (Meta: {meta})")
                        fig_f.add_hline(y=meta, line_dash="dash", line_color="red", annotation_text=f"Meta {meta}")
                        st.plotly_chart(fig_f, use_container_width=True)
                    else: st.info("Selecione um filtro válido para ver os dados.")
                else: st.warning("Nenhum dado encontrado para este filtro.")
            except Exception as e:
                st.error(f"Erro ao carregar aba '{aba}'.")
