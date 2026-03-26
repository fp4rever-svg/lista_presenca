import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import urllib.parse
import io

# 1. CONFIGURAÇÕES DE PÁGINA
st.set_page_config(page_title="Check-in & Performance | Grupo SC", layout="wide", initial_sidebar_state="collapsed")

# --- IDs DOS ARQUIVOS ---
ID_PLANILHA_PRESENCA = "1nYm2aRgruykh2YfXTcpCRuHGIqI0TtAFroMEk_p7Ij8"
ID_EXCEL_PRODUTIVIDADE = "1mKZxkhEjrJN5hidKG4pXNcMDhbgc5Z5C"

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
    except:
        return {}

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
                        st.session_state.logado = True
                        st.session_state.usuario = u_sel
                        st.session_state.perfil = "Lider"
                        st.rerun()
                    else:
                        st.error("Senha incorreta.")
    else:
        s_adm = st.text_input("Senha Admin:", type="password")
        if st.button("Acessar"):
            if s_adm == SENHA_ADMIN:
                st.session_state.logado = True
                st.session_state.usuario = "Admin"
                st.session_state.perfil = "Admin"
                st.rerun()

# ==========================================
# ÁREA LOGADA
# ==========================================
else:
    col_h1, col_h2 = st.columns([5, 1])
    col_h1.subheader(f"Bem-vindo, {st.session_state.usuario}")
    if col_h2.button("🏠 Sair"):
        st.session_state.logado = False
        st.rerun()

    # --- VISÃO DO LÍDER ---
    if st.session_state.perfil == "Lider":
        try:
            url_lider = get_csv_url(st.session_state.usuario, ID_PLANILHA_PRESENCA)
            df = pd.read_csv(url_lider)
            with st.form("f_presenca"):
                st.write("### Lista de Presença da Equipe")
                envios = []
                for i, r in df.iterrows():
                    c1, c2, c3 = st.columns([3, 1, 3])
                    nome_colab = r.iloc[0]
                    c1.write(nome_colab)
                    ok = c2.checkbox("Presença", key=f"check_{i}")
                    obs = c3.text_input("Observação", key=f"obs_{i}")
                    envios.append({"nome": nome_colab, "status": "OK" if ok else "FALTA", "obs": obs})
                
                if st.form_submit_button("✅ Enviar Dados"):
                    payload = {"tipo": "presenca", "lider": st.session_state.usuario, "lista": envios}
                    requests.post(URL_SCRIPT_GOOGLE, json=payload)
                    st.success("Presença enviada com sucesso!")
        except:
            st.error("Erro ao carregar a lista de colaboradores.")

    # --- VISÃO DO ADMINISTRADOR ---
    elif st.session_state.perfil == "Admin":
        t1, t2, t3 = st.tabs(["Monitoramento Diário", "Gestão de Acessos", "Performance Operacional"])

        with t1:
            st.write("### Status de Presença por Líder")
            for lider in LIDERES:
                st.write(f"📍 Equipe: {lider}")

        with t2:
            st.write("### Configurações de Acesso")
            if st.button("🔄 Visualizar Líderes e Senhas"):
                dados_senhas = buscar_senhas_db()
                if dados_senhas:
                    df_acesso = pd.DataFrame(list(dados_senhas.items()), columns=['Líder', 'Senha'])
                    st.table(df_acesso)
                else:
                    st.info("Nenhuma senha cadastrada.")

        with t3:
            st.write("### 📊 Produtividade: Conferência & Picking")
            
            col_f1, col_f2 = st.columns(2)
            dep_escolhido = col_f1.selectbox("Filtrar Depósito:", ["Todos", 102, 105, 107, 111, 302])
            op_escolhida = col_f2.radio("Tipo de Operação:", ["Conferência", "Picking"], horizontal=True)

            aba_alvo = "Dinamica Conf" if op_escolhida == "Conferência" else "Dinamica Picking"
            
            try:
                # Carregamento do arquivo Excel via link de exportação do Drive
                url_excel = f"https://docs.google.com/spreadsheets/d/{ID_EXCEL_PRODUTIVIDADE}/export?format=xlsx"
                df_prod = pd.read_excel(url_excel, sheet_name=aba_alvo)

                # Tratamento de dados dinâmicos
                col_usu = df_prod.columns[0]
                cols_para_pular = [col_usu, 'Depósito', 'Total Geral', 'Total', 'Soma de Total', 'Soma de Total Geral']
                colunas_de_hora = [c for c in df_prod.columns if c not in cols_para_pular]

                # Filtro de depósito se existir a coluna
                if dep_escolhido != "Todos" and 'Depósito' in df_prod.columns:
                    df_prod = df_prod[df_prod['Depósito'] == dep_escolhido]

                if len(colunas_de_hora) > 0:
                    # Ajuste da tabela (Melt) para visualização em gráficos
                    df_melt = df_prod.melt(id_vars=[col_usu], value_vars=colunas_de_hora, var_name='Hora', value_name='Qtd').fillna(0)

                    graf_1, graf_2 = st.columns(2)
                    with graf_1:
                        st.write(f"**Ranking Individual ({op_escolhida})**")
                        df_rank = df_melt.groupby(col_usu)['Qtd'].sum().sort_values(ascending=False).reset_index()
                        st.bar_chart(df_rank, x=col_usu, y='Qtd')
                    
                    with graf_2:
                        st.write("**Desempenho por Faixa Horária**")
                        df_hora = df_melt.groupby('Hora')['Qtd'].sum().reset_index()
                        st.line_chart(df_hora, x='Hora', y='Qtd')
                else:
                    st.info("Aguardando preenchimento de dados de horários no Excel.")

            except Exception as e:
                st.warning(f"Não foi possível carregar a aba '{aba_alvo}'.")
                st.info("Certifique-se de que o arquivo está compartilhado no Drive como 'Qualquer pessoa com o link'.")
