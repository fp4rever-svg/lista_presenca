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

# --- CONTROLE DE SESSÃO ---
if 'logado' not in st.session_state:
    st.session_state.update({'logado': False, 'usuario': None, 'perfil': None})

# ==========================================
# ÁREA DE ACESSO (LOGIN)
# ==========================================
if not st.session_state.logado:
    st.title("📋 Check-in Logística")
    perfil_escolhido = st.radio("Entrar como:", ["Líder", "Administrador"], horizontal=True)

    if perfil_escolhido == "Líder":
        lider_sel = st.selectbox("Selecione seu nome:", ["--"] + LIDERES)
        if lider_sel != "--":
            senhas_atuais = buscar_senhas_db()
            senha_no_db = senhas_atuais.get(lider_sel)

            if not senha_no_db:
                st.warning(f"Olá {lider_sel}, defina sua primeira senha.")
                nova_senha = st.text_input("Nova Senha:", type="password")
                if st.button("Cadastrar e Entrar"):
                    requests.post(URL_SCRIPT_GOOGLE, json={"tipo": "definir_senha", "lider": l_sel, "nova_senha": nova_senha})
                    st.session_state.update({'logado': True, 'usuario': lider_sel, 'perfil': "Lider"})
                    st.rerun()
            else:
                senha_input = st.text_input("Senha de Acesso:", type="password")
                if st.button("Entrar"):
                    if str(senha_input) == str(senha_no_db):
                        st.session_state.update({'logado': True, 'usuario': l_sel, 'perfil': "Lider"})
                        st.rerun()
                    else: st.error("Senha incorreta.")
    else:
        s_adm = st.text_input("Senha Administrativa:", type="password")
        if st.button("Acessar Painel Admin"):
            if s_adm == SENHA_ADMIN:
                st.session_state.update({'logado': True, 'usuario': "Administrador", 'perfil': "Admin"})
                st.rerun()
            else: st.error("Acesso Negado.")

# ==========================================
# SISTEMA PÓS-LOGIN
# ==========================================
else:
    c1, c2 = st.columns([5, 1])
    c1.write(f"Sessão: **{st.session_state.usuario}**")
    if c2.button("Sair/Logoff"):
        st.session_state.logado = False
        st.rerun()

    # --- VISÃO DO LÍDER ---
    # --- PARTE DO CÓDIGO DO LÍDER ---
if st.session_state.perfil == "Lider":
    lider_nome = st.session_state.usuario
    is_extra = verificar_liberacao_especial()
    
    try:
        # Busca a lista da aba com o nome do Líder
        df_lista = pd.read_csv(get_sheet_url(lider_nome))
        df_lista.rename(columns={df_lista.columns[0]: 'Colaborador'}, inplace=True)

        # 1. FORMULÁRIO DE CHAMADA
        with st.form("chamada_lider"):
            st.subheader(f"📋 Chamada - {lider_nome}")
            dados_para_envio = []
            cols = [3, 1, 1, 3] if is_extra else [3, 1, 3]
            
            # ... (lógica de repetição dos colaboradores aqui) ...
            # [Mantenha o loop 'for i, row in df_lista.iterrows()' que você já tem]

            if st.form_submit_button("✅ FINALIZAR E ENVIAR"):
                requests.post(URL_SCRIPT_GOOGLE, json={"tipo": "presenca_completa", "lider": lider_nome, "lista": dados_para_envio})
                st.success("Check-in enviado com sucesso!")

        # 2. ÁREA DE SOLICITAÇÃO (ISOLADA DO FORMULÁRIO ACIMA)
        st.markdown("---") # Linha divisória visual
        st.subheader("🚀 Gestão de Equipe")
        
        with st.expander("➕ SOLICITAR INCLUSÃO DE NOVO COLABORADOR", expanded=False):
            st.write("Preencha os dados abaixo para enviar ao Administrador:")
            with st.form("form_solicitacao_novo"):
                n_nome = st.text_input("Nome Completo do Colaborador:")
                n_setor = st.selectbox("Setor de Alocação:", ["Recebimento", "Separação", "Expedição", "Outros"])
                
                enviar_sol = st.form_submit_button("Enviar Solicitação")
                
                if enviar_sol:
                    if n_nome:
                        # Chama o script para gravar na aba 'Pendentes'
                        payload = {"tipo": "solicitar_inclusao", "nome": n_nome, "lider": lider_nome, "area": n_setor}
                        requests.post(URL_SCRIPT_GOOGLE, json=payload)
                        st.success(f"Solicitação de {n_nome} enviada para a aba Pendentes!")
                    else:
                        st.error("Por favor, preencha o nome do colaborador.")

    except Exception as e:
        st.error(f"Erro ao carregar lista de {lider_nome}. Verifique a aba no Sheets.")

    # --- VISÃO DO ADMIN ---
    elif st.session_state.perfil == "Admin":
        t1, t2, t3, t4 = st.tabs(["Monitoramento", "Pendentes", "Ferramentas", "📊 Dashboard"])

        with t1:
            st.subheader("Envios de Hoje")
            hoje = datetime.now().strftime("%d/%m")
            for l in LIDERES:
                try:
                    d_ch = pd.read_csv(get_sheet_url(l))
                    # Verifica na Coluna D (índice 3)
                    if not d_ch.empty and d_ch.iloc[:, 3].astype(str).str.contains(hoje).any():
                        st.success(f"✅ {l}: Concluído")
                    else: st.error(f"❌ {l}: Pendente")
                except: st.warning(f"⚠️ {l}: Sem conexão")

        with t2:
            st.subheader("Novas Solicitações dos Líderes")
            try:
                df_p = pd.read_csv(get_sheet_url("Pendentes"))
                st.dataframe(df_p, use_container_width=True)
            except: st.info("Nenhuma pendência.")

        with t3:
            st.subheader("Ações Administrativas")
            lib = verificar_liberacao_especial()
            if lib:
                st.success("MODO H.E.: ATIVO")
                if st.button("🔴 DESATIVAR"):
                    requests.post(URL_SCRIPT_GOOGLE, json={"tipo": "toggle_especial", "status": "OFF"})
                    time.sleep(1); st.rerun()
            else:
                st.warning("MODO H.E.: OCULTO")
                if st.button("🟢 ATIVAR"):
                    requests.post(URL_SCRIPT_GOOGLE, json={"tipo": "toggle_especial", "status": "ON"})
                    time.sleep(1); st.rerun()
            
            st.divider()
            if st.button("🔑 Ver Senhas"):
                senhas = buscar_senhas_db()
                if senhas: st.table(pd.DataFrame(list(senhas.items()), columns=['Líder', 'Senha']))

            if st.button("📥 Baixar Excel"):
                try:
                    all_dfs = [pd.read_csv(get_sheet_url(l)).assign(Lider=l) for l in LIDERES]
                    out = io.BytesIO()
                    with pd.ExcelWriter(out, engine='xlsxwriter') as wr:
                        pd.concat(all_dfs).to_excel(wr, index=False)
                    st.download_button("⬇️ Download", out.getvalue(), "Relatorio.xlsx")
                except: st.error("Erro ao exportar.")

            if st.button("🧹 Resetar Turno"):
                requests.post(URL_SCRIPT_GOOGLE, json={"tipo": "limpar_tudo"})
                st.rerun()

        with t4:
            st.subheader("Análise Mensal")
            try:
                df_h = pd.read_csv(get_sheet_url("Historico"))
                if not df_h.empty:
                    df_h.columns = ["Data", "Hora", "Colaborador", "Lider", "Status", "HE", "Fretado", "Obs"]
                    l_sel = st.multiselect("Líder:", df_h['Lider'].unique(), default=df_h['Lider'].unique())
                    df_f = df_h[df_h['Lider'].isin(l_sel)]
                    st.metric("Faltas Totais", len(df_f[df_f['Status'] == 'FALTA']))
                    df_g = df_f[df_f['Status'] == 'FALTA'].groupby('Lider').size().reset_index(name='Qtd')
                    st.bar_chart(df_g.set_index('Lider'))
                else: st.info("Histórico vazio.")
            except: st.warning("Aba 'Historico' não encontrada.")
