import streamlit as st
import pandas as pd
import requests
import urllib.parse
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
                # Mescla com a lista fixa de líderes para garantir que todos apareçam
                status_lideres = pd.DataFrame({"Lider": LIDERES})
                df_c = pd.merge(status_lideres, df_c, on="Lider", how="left").fillna({"Status": "Pendente", "Horario": "-"})
                
                for _, row in df_c.iterrows():
                    icone = "✅" if row['Status'] == "Preenchido" else "⏳"
                    status_txt = "Entregue" if row['Status'] == "Preenchido" else "Pendente"
                    st.write(f"{icone} **{row['Lider']}**: {status_txt} | {row['Horario']}")
            except: 
                for l in LIDERES: st.write(f"⏳ **{l}**: Pendente | -")

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
            st.write("### 📈 Produtividade (Metas)")
            cf1, cf2 = st.columns(2)
            dep_escolhido = cf1.selectbox("Filtrar Depósito:", ["Todos", 102, 105, 107, 111, 302])
            op = cf2.radio("Operação:", ["Conferência", "Picking"], horizontal=True)

            aba = "Conf" if op == "Conferência" else "Pick"
            meta = 2000 if op == "Conferência" else 150
            
            try:
                url = f"https://docs.google.com/spreadsheets/d/{ID_SHEETS_PROD}/gviz/tq?tqx=out:csv&sheet={urllib.parse.quote(aba)}"
                df_p = pd.read_csv(url)

                if not df_p.empty:
                    # Forçar colunas numéricas
                    if 'Depósito' in df_p.columns:
                        df_p['Depósito'] = pd.to_numeric(df_p['Depósito'], errors='coerce')
                    
                    u_col = df_p.columns[0]
                    ignorar = [u_col, 'Depósito', 'Total Geral', 'Total', 'Soma de Total']
                    h_cols = [c for c in df_p.columns if c not in ignorar and not str(c).startswith('Unnamed')]
                    
                    # Filtro de Depósito corrigido
                    if dep_escolhido != "Todos":
                        df_p = df_p[df_p['Depósito'] == int(dep_escolhido)]

                    if h_cols:
                        df_m = df_p.melt(id_vars=[u_col], value_vars=h_cols, var_name='Hora', value_name='Qtd')
                        df_m['Qtd'] = pd.to_numeric(df_m['Qtd'], errors='coerce').fillna(0)

                        g1, g2 = st.columns(2)
                        with g1:
                            st.write(f"**Ranking Individual (Meta: {meta})**")
                            rank = df_m.groupby(u_col)['Qtd'].sum().sort_values(ascending=False)
                            st.bar_chart(rank)
                            # Exibe tabela com valores para conferência rápida
                            st.dataframe(rank, use_container_width=True)
                        
                        with g2:
                            st.write(f"**Fluxo por Hora (Meta Horária: {meta})**")
                            fluxo = df_m.groupby('Hora')['Qtd'].sum()
                            st.line_chart(fluxo)
                            # Adiciona linha de meta visualmente
                            st.info(f"Produção Total: {int(fluxo.sum())} unidades")
                    else: st.info("Sem colunas de horários.")
            except: st.error(f"Erro ao ler aba '{aba}'.")
