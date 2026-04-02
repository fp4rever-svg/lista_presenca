import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import urllib.parse
import time
import io

# 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="Check-in Logística | Grupo SC", layout="wide", page_icon="📋")

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
# SISTEMA PÓS-LOGIN
# ==========================================
else:
    c1, c2 = st.columns([5, 1])
    c1.write(f"Sessão: **{st.session_state.usuario}**")
    if c2.button("Sair/Logoff"):
        st.session_state.logado = False
        st.rerun()

    # --- VISÃO DO LÍDER ---
    if st.session_state.perfil == "Lider":
        lider_nome = st.session_state.usuario
        
        # --- NOVO: SEÇÃO DE SOLICITAÇÃO DE INCLUSÃO ---
        with st.expander("➕ Solicitar inclusão de novo colaborador"):
            with st.form("form_novo_colab"):
                nome_novo = st.text_input("Nome Completo:")
                mat_nova = st.text_input("Matrícula (opcional):")
                if st.form_submit_button("Enviar Solicitação"):
                    if nome_novo:
                        # Envia para a aba 'Pendentes' via Script
                        requests.post(URL_SCRIPT_GOOGLE, json={
                            "tipo": "solicitar_inclusao", 
                            "lider": lider_nome, 
                            "nome": nome_novo, 
                            "matricula": mat_nova
                        })
                        st.success("Solicitação enviada ao Administrador!")
                    else: st.warning("Digite o nome do colaborador.")

        st.divider()

        is_extra = verificar_liberacao_especial()
        try:
            df_lista = pd.read_csv(get_sheet_url(lider_nome))
            
            with st.form("chamada_lider"):
                st.subheader(f"Chamada - {lider_nome}")
                dados_para_envio = []
                cols = [1, 3, 1, 1, 2] if is_extra else [1, 3, 1, 2]
                
                h = st.columns(cols)
                h[0].write("**MAT**"); h[1].write("**NOME**")
                if is_extra:
                    h[2].write("**HE**"); h[3].write("**FRT**"); h[4].write("**OBS**")
                else:
                    h[2].write("**PRES**"); h[3].write("**OBS**")

                for i, row in df_lista.iterrows():
                    if pd.isna(row.iloc[0]): continue 
                    nome_colab = str(row.iloc[0]); matricula = str(row.iloc[4])
                    
                    ln = st.columns(cols)
                    ln[0].write(f"`{matricula}`"); ln[1].write(nome_colab)
                    r_he, r_fr, r_pr = "Não", "Não", "FALTA"

                    if is_extra:
                        if ln[2].checkbox("⚡", key=f"he_{i}"): r_he = "Sim"
                        if ln[2].checkbox("🚌", key=f"fr_{i}"): r_fr = "Sim"
                        r_obs = ln[4].text_input("", key=f"ob_{i}", label_visibility="collapsed")
                        r_pr = "OK"
                    else:
                        if ln[2].checkbox("OK", key=f"pr_{i}"): r_pr = "OK"
                        r_obs = ln[3].text_input("", key=f"ob_{i}", label_visibility="collapsed")
                    
                    dados_para_envio.append({"matricula": matricula, "nome": nome_colab, "status": r_pr, "he": r_he, "fretado": r_fr, "obs": r_obs})

                if st.form_submit_button("✅ FINALIZAR E ENVIAR"):
                    requests.post(URL_SCRIPT_GOOGLE, json={"tipo": "presenca_completa", "lider": lider_nome, "lista": dados_para_envio})
                    st.success("Check-in enviado!")
        except: st.error("Erro ao carregar lista.")

    # --- VISÃO DO ADMIN ---
    elif st.session_state.perfil == "Admin":
        t1, t2, t3, t4 = st.tabs(["Monitoramento", "Pendentes", "Ferramentas", "📊 Dashboard"])

        with t1:
            st.subheader("Envios de Hoje")
            hoje = datetime.now().strftime("%d/%m")
            for l in LIDERES:
                try:
                    d_ch = pd.read_csv(get_sheet_url(l))
                    if not d_ch.empty and d_ch.iloc[:, 3].astype(str).str.contains(hoje).any():
                        st.success(f"✅ {l}: Concluído")
                    else: st.error(f"❌ {l}: Pendente")
                except: st.warning(f"⚠️ {l}: Sem conexão")

        with t2:
            st.subheader("Novas Solicitações de Inclusão")
            try:
                st.dataframe(pd.read_csv(get_sheet_url("Pendentes")), use_container_width=True)
            except: st.info("Sem solicitações pendentes.")

        with t3:
            st.subheader("Ferramentas de Gestão")
            lib_status = verificar_liberacao_especial()
            if st.button("🔴 DESATIVAR H.E./FRETADO" if lib_status else "🟢 ATIVAR H.E./FRETADO"):
                requests.post(URL_SCRIPT_GOOGLE, json={"tipo": "toggle_especial", "status": "OFF" if lib_status else "ON"})
                st.rerun()
            
            st.divider()
            
            # --- RESTAURADO: FERRAMENTA DE DOWNLOAD ---
            st.write("### Exportar Dados")
            if st.button("📥 Gerar Relatório Consolidado (Excel)"):
                try:
                    with st.spinner("Compilando dados..."):
                        # Tenta baixar o histórico consolidado
                        df_relatorio = pd.read_csv(get_sheet_url("Historico"))
                        output = io.BytesIO()
                        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                            df_relatorio.to_excel(writer, index=False, sheet_name='Historico_Geral')
                        st.download_button(
                            label="⬇️ Clique para Baixar Excel",
                            data=output.getvalue(),
                            file_name=f"Relatorio_Logistica_{datetime.now().strftime('%d_%m_%Y')}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                except: st.error("Erro ao gerar arquivo. Verifique se a aba 'Historico' possui dados.")

            if st.button("🧹 Limpar Turno (Reset)"):
                requests.post(URL_SCRIPT_GOOGLE, json={"tipo": "limpar_tudo"})
                st.rerun()

        with t4:
            st.subheader("📊 Dashboard de Performance e Absenteísmo")
            try:
                df_h = pd.read_csv(get_sheet_url("Historico"))
                if not df_h.empty:
                    # Padronização de Colunas
                    df_h.columns = ["Data", "Hora", "Matricula", "Colaborador", "Lider", "Status", "HE", "Fretado", "Obs"]
                    
                    # Filtro de Data Global para o Dash
                    datas_disponiveis = df_h['Data'].unique()
                    data_sel = st.multiselect("Filtrar por Data:", datas_disponiveis, default=datas_disponiveis)
                    df_f = df_h[df_h['Data'].isin(data_sel)]

                    # --- VISÃO 1: POR LÍDER (Métricas de Gestão) ---
                    st.markdown("### 👥 Visão por Líder")
                    
                    # Agrupamento por Líder
                    dash_lider = df_f.groupby('Lider').agg(
                        Total=('Status', 'count'),
                        Presencas=('Status', lambda x: (x == 'OK').sum()),
                        Faltas=('Status', lambda x: (x == 'FALTA').sum())
                    ).reset_index()
                    
                    # Cálculo de Absenteísmo por Líder
                    dash_lider['% Absenteísmo'] = (dash_lider['Faltas'] / dash_lider['Total'] * 100).round(2)
                    
                    # Exibição em Colunas de Métricas (Top Líderes com mais faltas ou maior absenteísmo)
                    col_l1, col_l2 = st.columns([2, 1])
                    with col_l1:
                        st.dataframe(dash_lider.sort_values('% Absenteísmo', ascending=False), use_container_width=True)
                    with col_l2:
                        st.bar_chart(dash_lider.set_index('Lider')['% Absenteísmo'])

                    st.divider()

                    # --- VISÃO 2: POR COLABORADOR (Frequência Individual) ---
                    st.markdown("### 👤 Visão Geral de Colaboradores")
                    
                    search_colab = st.text_input("🔍 Pesquisar colaborador específico:")
                    
                    # Agrupamento por Colaborador
                    dash_colab = df_f.groupby(['Matricula', 'Colaborador', 'Lider']).agg(
                        Dias_Monitorados=('Status', 'count'),
                        Total_Faltas=('Status', lambda x: (x == 'FALTA').sum()),
                        Total_HE=('HE', lambda x: (x == 'Sim').sum())
                    ).reset_index()
                    
                    # Filtro de busca
                    if search_colab:
                        dash_colab = dash_colab[dash_colab['Colaborador'].str.contains(search_colab, case=False)]

                    # Ranking de quem mais falta (importante para o RH)
                    st.write("Ranking de Absenteísmo Individual (Colaboradores com mais faltas):")
                    st.dataframe(dash_colab.sort_values('Total_Faltas', ascending=False), use_container_width=True)

                else:
                    st.info("Aguardando dados no histórico para gerar indicadores.")
            except Exception as e:
                st.error(f"Erro ao processar indicadores: {e}")
