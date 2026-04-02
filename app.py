import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import urllib.parse
import time
import io

# 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="Check-in Logística | Grupo SC", layout="wide", page_icon="📋")

# Estilização Customizada
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stButton>button { width: 100%; border-radius: 5px; font-weight: bold; }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .status-card { padding: 15px; border-radius: 8px; background-color: white; border: 1px solid #ddd; }
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
# ACESSO (LOGIN)
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
    c_head1, c_head2 = st.columns([5, 1])
    c_head1.subheader(f"👤 Usuário: {st.session_state.usuario}")
    if c_head2.button("Sair/Logoff"):
        st.session_state.logado = False
        st.rerun()

    # --- 🔵 VISÃO DO LÍDER ---
    if st.session_state.perfil == "Lider":
        lider_nome = st.session_state.usuario
        is_extra = verificar_liberacao_especial()
        
        try:
            # Carrega a aba do líder para pegar a lista e a matrícula (Coluna E se existir)
            df_lista = pd.read_csv(get_sheet_url(lider_nome))
            # Padronização de colunas para garantir que a matrícula seja capturada
            df_lista.columns = [c.strip() for c in df_lista.columns]
            
            with st.form("chamada_lider"):
                st.subheader(f"Chamada - {lider_nome}")
                if is_extra: st.warning("📢 MODO HORA EXTRA ATIVO: Registros de Presença ficarão em branco.")
                else: st.info("📅 ESCALA NORMAL: Registros de H.E./Fretado ficarão em branco.")

                dados_para_envio = []
                cols = [3, 1, 1, 3] if is_extra else [3, 1, 3]
                
                h = st.columns(cols)
                h[0].write("**Nome**")
                if is_extra:
                    h[1].write("**H.E.**"); h[2].write("**Fret.**"); h[3].write("**Obs**")
                else:
                    h[1].write("**Presença**"); h[2].write("**Obs**")

                for i, row in df_lista.iterrows():
                    if pd.isna(row.iloc[1]): continue # Pula se o nome estiver vazio
                    
                    ln = st.columns(cols)
                    nome_colab = str(row.iloc[1])
                    matricula = str(row.iloc[0]) # Assume que matrícula é a primeira coluna (A)
                    ln[0].write(nome_colab)
                    
                    r_he, r_fr, r_pr = "", "", ""

                    if is_extra:
                        # Em modo Extra, Presença fica em branco ("")
                        if ln[1].checkbox("⚡", key=f"he_{i}"): r_he = "Sim"
                        else: r_he = "Não"
                        if ln[2].checkbox("🚌", key=f"fr_{i}"): r_fr = "Sim"
                        else: r_fr = "Não"
                        r_obs = ln[3].text_input("", key=f"ob_{i}", label_visibility="collapsed")
                    else:
                        # Em modo Normal, HE e Fretado ficam em branco ("")
                        if ln[1].checkbox("OK", key=f"pr_{i}"): r_pr = "OK"
                        else: r_pr = "FALTA"
                        r_obs = ln[2].text_input("", key=f"ob_{i}", label_visibility="collapsed")
                    
                    dados_para_envio.append({
                        "matricula": matricula,
                        "nome": nome_colab, 
                        "status": r_pr, 
                        "he": r_he, 
                        "fretado": r_fr, 
                        "obs": r_obs
                    })

                if st.form_submit_button("✅ ENVIAR CHECK-IN"):
                    requests.post(URL_SCRIPT_GOOGLE, json={"tipo": "presenca_completa", "lider": lider_nome, "lista": dados_para_envio})
                    st.success("Enviado com sucesso!")

            # Solicitação de Inclusão
            with st.expander("➕ Solicitar Novo Colaborador"):
                with st.form("add_colab"):
                    n_nome = st.text_input("Nome:")
                    n_mat = st.text_input("Matrícula:")
                    if st.form_submit_button("Solicitar"):
                        requests.post(URL_SCRIPT_GOOGLE, json={"tipo": "solicitar_inclusao", "nome": n_nome, "matricula": n_mat, "lider": lider_nome})
                        st.success("Solicitação enviada!")

        except Exception as e: st.error(f"Erro ao carregar lista: {e}")

    # --- 🔴 VISÃO DO ADMIN ---
    elif st.session_state.perfil == "Admin":
        t1, t2, t3, t4, t5 = st.tabs(["Monitoramento", "Pendentes", "Ferramentas", "📊 Dashboard", "📑 Tabela Geral"])

        with t1:
            st.subheader("Envios de Hoje")
            hoje = datetime.now().strftime("%d/%m")
            for l in LIDERES:
                try:
                    d_ch = pd.read_csv(get_sheet_url(l))
                    # Verifica coluna D (índice 3) para data
                    if not d_ch.empty and d_ch.iloc[:, 3].astype(str).str.contains(hoje).any():
                        st.success(f"✅ {l}: Concluído")
                    else: st.error(f"❌ {l}: Pendente")
                except: st.warning(f"⚠️ {l}: Sem conexão")

        with t2:
            st.subheader("Novas Solicitações")
            try:
                st.dataframe(pd.read_csv(get_sheet_url("Pendentes")), use_container_width=True)
            except: st.info("Sem solicitações.")

        with t3:
            st.subheader("Gestão do Sistema")
            lib_status = verificar_liberacao_especial()
            
            # Botão de Toggle H.E.
            if st.button("🔄 ALTERAR MODO (NORMAL / EXTRA)"):
                novo_status = "OFF" if lib_status else "ON"
                requests.post(URL_SCRIPT_GOOGLE, json={"tipo": "toggle_especial", "status": novo_status})
                st.rerun()
            
            st.divider()
            
            if st.button("🔑 Ver Senhas"):
                s = buscar_senhas_db()
                if s: st.table(pd.DataFrame(list(s.items()), columns=['Líder', 'Senha']))

            if st.button("📥 Baixar Relatório Atual"):
                dfs = [pd.read_csv(get_sheet_url(l)).assign(Lider=l) for l in LIDERES]
                out = io.BytesIO()
                with pd.ExcelWriter(out, engine='xlsxwriter') as wr:
                    pd.concat(dfs).to_excel(wr, index=False)
                st.download_button("Download .xlsx", out.getvalue(), "Relatorio.xlsx")

            # --- CORREÇÃO DO RESET ---
            st.divider()
            st.warning("Área Crítica")
            if st.button("🧹 LIMPAR TURNO (RESET TOTAL)"):
                r_reset = requests.post(URL_SCRIPT_GOOGLE, json={"tipo": "limpar_tudo"})
                if r_reset.status_code == 200:
                    st.success("Sistema resetado para o próximo turno!")
                    time.sleep(1)
                    st.rerun()
                else: st.error("Erro ao resetar.")

        with t4:
            st.subheader("Gráficos de Desempenho")
            try:
                df_h = pd.read_csv(get_sheet_url("Historico"))
                if not df_h.empty:
                    df_h.columns = ["Data", "Hora", "Matricula", "Colaborador", "Lider", "Status", "HE", "Fretado", "Obs"]
                    df_graf = df_h[df_h['Status'] == 'FALTA'].groupby('Lider').size().reset_index(name='Faltas')
                    st.bar_chart(df_graf.set_index('Lider'))
                else: st.info("Sem dados no histórico.")
            except: st.error("Erro ao carregar gráficos.")

        with t5:
            st.subheader("📑 Tabela Geral e Absenteísmo")
            try:
                df_tab = pd.read_csv(get_sheet_url("Historico"))
                if not df_tab.empty:
                    df_tab.columns = ["Data", "Hora", "Matricula", "Colaborador", "Lider", "Status", "HE", "Fretado", "Obs"]
                    df_tab['Data'] = pd.to_datetime(df_tab['Data'], dayfirst=True).dt.date
                    
                    # Filtros de Data
                    c_f1, c_f2, c_f3 = st.columns(3)
                    d_ini = c_f1.date_input("Data Início", value=df_tab['Data'].min())
                    d_fim = c_f2.date_input("Data Fim", value=df_tab['Data'].max())
                    busca = c_f3.text_input("Filtrar Nome ou Matrícula")

                    # Aplicação dos Filtros
                    mask = (df_tab['Data'] >= d_ini) & (df_tab['Data'] <= d_fim)
                    df_filtrado = df_tab[mask]
                    if busca:
                        df_filtrado = df_filtrado[df_filtrado['Colaborador'].str.contains(busca, case=False) | 
                                                  df_filtrado['Matricula'].astype(str).str.contains(busca)]

                    # Cálculo de Absenteísmo por Colaborador
                    # Filtramos apenas registros onde 'Status' não é vazio (Escala Normal)
                    df_abs = df_filtrado[df_filtrado['Status'].isin(['OK', 'FALTA'])]
                    
                    if not df_abs.empty:
                        total_dias = df_abs.groupby(['Matricula', 'Colaborador']).size().reset_index(name='Dias_Totais')
                        faltas = df_abs[df_abs['Status'] == 'FALTA'].groupby(['Matricula', 'Colaborador']).size().reset_index(name='Total_Faltas')
                        
                        relatorio_final = pd.merge(total_dias, faltas, on=['Matricula', 'Colaborador'], how='left').fillna(0)
                        relatorio_final['Absenteísmo (%)'] = (relatorio_final['Total_Faltas'] / relatorio_final['Dias_Totais'] * 100).round(2)
                        
                        st.write("### Relatório de Frequência")
                        st.dataframe(relatorio_final, use_container_width=True)
                        
                        st.write("### Detalhes dos Lançamentos")
                        st.dataframe(df_filtrado.sort_values(by='Data', ascending=False), use_container_width=True)
                    else:
                        st.info("Nenhum dado de presença (Escala Normal) no período selecionado.")
                else:
                    st.info("O histórico está vazio.")
            except Exception as e:
                st.error(f"Erro ao processar tabela: {e}")
