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
        if r.status_code == 200:
            return r.json()
        return {}
    except:
        return {}

def verificar_liberacao_especial():
    try:
        url = get_sheet_url("Config_Geral")
        df = pd.read_csv(url, header=None)
        status = str(df.iloc[0, 1]).strip().upper()
        return True if status == "ON" else False
    except:
        return False

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
                st.warning(f"Olá {lider_sel}, define a tua primeira senha de acesso.")
                nova_senha = st.text_input("Nova Senha:", type="password")
                if st.button("Cadastrar e Entrar"):
                    if nova_senha:
                        requests.post(URL_SCRIPT_GOOGLE, json={"tipo": "definir_senha", "lider": lider_sel, "nova_senha": nova_senha})
                        st.session_state.update({'logado': True, 'usuario': lider_sel, 'perfil': "Lider"})
                        st.rerun()
            else:
                senha_input = st.text_input("Senha de Acesso:", type="password")
                if st.button("Entrar"):
                    if str(senha_input) == str(senha_no_db):
                        st.session_state.update({'logado': True, 'usuario': lider_sel, 'perfil': "Lider"})
                        st.rerun()
                    else:
                        st.error("Senha incorreta.")

    elif perfil_escolhido == "Administrador":
        senha_adm_input = st.text_input("Senha Administrativa:", type="password")
        if st.button("Acessar Painel Admin"):
            if senha_adm_input == SENHA_ADMIN:
                st.session_state.update({'logado': True, 'usuario': "Administrador", 'perfil': "Admin"})
                st.rerun()
            else:
                st.error("Acesso Negado.")

# ==========================================
# SISTEMA PÓS-LOGIN
# ==========================================
else:
    c1, c2 = st.columns([5, 1])
    c1.write(f"Usuário: **{st.session_state.usuario}**")
    if c2.button("Sair/Logoff"):
        st.session_state.logado = False
        st.rerun()

    # --- VISÃO DO LÍDER ---
    if st.session_state.perfil == "Lider":
        lider_nome = st.session_state.usuario
        is_extra_ativo = verificar_liberacao_especial()
        
        try:
            df_lista = pd.read_csv(get_sheet_url(lider_nome))
            df_lista.rename(columns={df_lista.columns[0]: 'Colaborador'}, inplace=True)

            with st.form("chamada_lider"):
                st.subheader(f"Chamada - {lider_nome}")
                dados_para_envio = []

                if is_extra_ativo:
                    st.success("⚡ MODO H.E. / FRETADO (Presença Automática)")
                    cols = [3, 1, 1, 3]
                    h = st.columns(cols)
                    h[0].write("**Nome**"); h[1].write("**H.E.**"); h[2].write("**Fret.**"); h[3].write("**Obs**")
                else:
                    cols = [3, 1, 3]
                    h = st.columns(cols)
                    h[0].write("**Nome**"); h[1].write("**Presença**"); h[2].write("**Obs**")

                for i, row in df_lista.iterrows():
                    if pd.isna(row['Colaborador']): continue
                    r_he, r_fr, r_pr = "Não", "Não", "FALTA"
                    ln = st.columns(cols)
                    ln[0].write(row['Colaborador'])

                    if is_extra_ativo:
                        if ln[1].checkbox("⚡", key=f"he_{i}"): r_he = "Sim"
                        if ln[2].checkbox("🚌", key=f"fr_{i}"): r_fr = "Sim"
                        r_obs = ln[3].text_input("", key=f"ob_{i}", label_visibility="collapsed")
                        r_pr = "OK"
                    else:
                        if ln[1].checkbox("OK", key=f"pr_{i}"): r_pr = "OK"
                        r_obs = ln[2].text_input("", key=f"ob_{i}", label_visibility="collapsed")
                    
                    dados_para_envio.append({"nome": row['Colaborador'], "status": r_pr, "he": r_he, "fretado": r_fr, "obs": r_obs})

                if st.form_submit_button("✅ FINALIZAR E ENVIAR"):
                    requests.post(URL_SCRIPT_GOOGLE, json={"tipo": "presenca_completa", "lider": lider_nome, "lista": dados_para_envio})
                    st.success("Check-in enviado com sucesso!")

            st.divider()
            with st.expander("➕ Solicitar Inclusão de Colaborador (Para Admin)"):
                with st.form("solicita_novo"):
                    n_nome = st.text_input("Nome Completo:")
                    n_area = st.selectbox("Área:", ["Recebimento", "Separação", "Expedição", "Outros"])
                    if st.form_submit_button("Enviar Solicitação"):
                        if n_nome:
                            requests.post(URL_SCRIPT_GOOGLE, json={"tipo": "solicitar_inclusao", "nome": n_nome, "lider": lider_nome, "area": n_area})
                            st.success("Solicitação enviada!")

        except: st.error("Erro ao carregar lista.")

    # --- VISÃO DO ADMIN ---
    elif st.session_state.perfil == "Admin":
        t1, t2, t3, t4 = st.tabs(["Monitoramento", "Pendentes", "Ferramentas", "📊 Dashboard Mensal"])

        with t1:
            st.subheader("Envios de Hoje")
            # Pega a data de hoje no formato dia/mês (ex: 01/04)
            hoje = datetime.now().strftime("%d/%m")
            
            for l in LIDERES:
                try:
                    url_lider = get_sheet_url(l)
                    d_ch = pd.read_csv(url_lider)
                    
                    # Se a planilha estiver vazia ou não tiver colunas suficientes
                    if d_ch.empty:
                        st.error(f"❌ {l}: Planilha Vazia")
                        continue

                    # TESTE DINÂMICO: Procura o 'hoje' em todas as colunas de texto
                    # Isso evita erro se você moveu a coluna de data de lugar
                    encontrou_envio = False
                    for col in d_ch.columns:
                        if d_ch[col].astype(str).str.contains(hoje).any():
                            encontrou_envio = True
                            break
                    
                    if encontrou_envio:
                        st.success(f"✅ {l}: Concluído")
                    else:
                        st.error(f"❌ {l}: Pendente")
                        
                except Exception as e:
                    st.warning(f"⚠️ {l}: Erro na leitura")

        with t2:
            st.subheader("Novos Colaboradores Solicitados")
            try:
                df_p = pd.read_csv(get_sheet_url("Pendentes"))
                st.dataframe(df_p, use_container_width=True)
            except: st.info("Nenhuma solicitação pendente.")

        with t3:
            st.subheader("Configurações")
            lib_status = verificar_liberacao_especial()
            if lib_status:
                st.success("CAMPOS EXTRAS: ATIVOS")
                if st.button("🔴 DESATIVAR H.E./FRETADO"):
                    requests.post(URL_SCRIPT_GOOGLE, json={"tipo": "toggle_especial", "status": "OFF"})
                    time.sleep(1); st.rerun()
            else:
                st.warning("CAMPOS EXTRAS: OCULTOS")
                if st.button("🟢 ATIVAR H.E./FRETADO"):
                    requests.post(URL_SCRIPT_GOOGLE, json={"tipo": "toggle_especial", "status": "ON"})
                    time.sleep(1); st.rerun()

            st.divider()
            if st.button("🔑 Ver Senhas dos Líderes"):
                senhas = buscar_senhas_db()
                if senhas: st.table(pd.DataFrame(list(senhas.items()), columns=['Líder', 'Senha']))

            st.divider()
            if st.button("📥 Baixar Excel Geral"):
                try:
                    all_dfs = [pd.read_csv(get_sheet_url(l)).assign(Lider=l) for l in LIDERES]
                    f_df = pd.concat(all_dfs)
                    output = io.BytesIO()
                    with pd.ExcelWriter(output, engine='xlsxwriter') as wr:
                        f_df.to_excel(wr, index=False)
                    st.download_button("⬇️ Download Excel", output.getvalue(), "Consolidado_Logistica.xlsx")
                except: st.error("Erro ao gerar arquivo.")

            if st.button("🧹 Limpar Turno (Reset)"):
                requests.post(URL_SCRIPT_GOOGLE, json={"tipo": "limpar_tudo"})
                st.rerun()

        with t4:
            st.subheader("Análise de Presença e Produtividade")
            try:
                url_hist = get_sheet_url("Historico")
                df_h = pd.read_csv(url_hist)
                
                if not df_h.empty:
                    col_f1, col_f2 = st.columns(2)
                    lider_f = col_f1.multiselect("Filtrar Líder:", df_h['Lider'].unique(), default=df_h['Lider'].unique())
                    df_f = df_h[df_h['Lider'].isin(lider_f)]

                    m1, m2, m3 = st.columns(3)
                    total = len(df_f)
                    presencas = len(df_f[df_f['Status'] == 'OK'])
                    faltas = len(df_f[df_f['Status'] == 'FALTA'])
                    
                    m1.metric("Total de Registros", total)
                    m2.metric("Presenças ✅", presencas)
                    m3.metric("Faltas ❌", faltas, delta=f"{(faltas/total)*100:.1f}% Absenteísmo" if total > 0 else "0%", delta_color="inverse")

                    st.write("### Faltas por Líder no Período")
                    df_grafico = df_f[df_f['Status'] == 'FALTA'].groupby('Lider').size().reset_index(name='Total Faltas')
                    st.bar_chart(df_grafico.set_index('Lider'))

                    st.write("### Colaboradores com mais H.E.")
                    he_count = df_f[df_f['HE'] == 'Sim'].groupby('Colaborador').size().reset_index(name='Qtd HE').sort_values(by='Qtd HE', ascending=False)
                    st.dataframe(he_count, use_container_width=True)
                else:
                    st.info("O histórico ainda está vazio.")
            except:
                st.warning("Aba 'Historico' não encontrada.")
