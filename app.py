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
        # Usamos um timestamp na URL para evitar cache de senhas antigas
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
    
    # IMPORTANTE: O seletor de perfil deve estar fora de qualquer outro IF
    perfil_escolhido = st.radio("Entrar como:", ["Líder", "Administrador"], horizontal=True)

    if perfil_escolhido == "Líder":
        lider_sel = st.selectbox("Selecione seu nome:", ["--"] + LIDERES)
        if lider_sel != "--":
            # Busca senhas reais do Sheets
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
    # Cabeçalho de Logout
    c1, c2 = st.columns([5, 1])
    c1.write(f"Sessão Ativa: **{st.session_state.usuario}**")
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
                    cols = [3, 1, 1, 3] # Nome, HE, Fret, Obs
                    h = st.columns(cols)
                    h[0].write("**Nome**"); h[1].write("**H.E.**"); h[2].write("**Fret.**"); h[3].write("**Obs**")
                else:
                    cols = [3, 1, 3] # Nome, Presenca, Obs
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

            # --- SOLICITAÇÃO DE NOVO ---
            st.divider()
            with st.expander("➕ Solicitar Inclusão de Colaborador (Para Admin)"):
                with st.form("solicita_novo"):
                    n_nome = st.text_input("Nome Completo:")
                    n_area = st.selectbox("Área:", ["Recebimento", "Separação", "Expedição", "Outros"])
                    if st.form_submit_button("Enviar Solicitação"):
                        if n_nome:
                            requests.post(URL_SCRIPT_GOOGLE, json={"tipo": "solicitar_inclusao", "nome": n_nome, "lider": lider_nome, "area": n_area})
                            st.success("Solicitação enviada para a aba Pendentes!")

        except: st.error("Erro ao carregar lista.")

    # --- VISÃO DO ADMIN ---
    elif st.session_state.perfil == "Admin":
        t1, t2, t3 = st.tabs(["Monitoramento", "Pendentes", "Ferramentas"])

        with t1:
            st.subheader("Envios de Hoje")
            hoje = datetime.now().strftime("%d/%m")
            for l in LIDERES:
                try:
                    d_ch = pd.read_csv(get_sheet_url(l))
                    if any(hoje in str(x) for x in d_ch.iloc[:, 3]):
                        st.success(f"✅ {l}: Concluído")
                    else: st.error(f"❌ {l}: Pendente")
                except: st.warning(f"⚠️ {l}: Sem dados")

        with t2:
            st.subheader("Novos Colaboradores Solicitados")
            try:
                df_p = pd.read_csv(get_sheet_url("Pendentes"))
                st.dataframe(df_p, use_container_width=True)
            except: st.info("Nenhuma solicitação pendente encontrada.")

        with t3:
            st.subheader("Configurações")
            # Liberação HE
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
                else: st.write("Nenhuma senha cadastrada.")

            st.divider()
            if st.button("📥 Baixar Excel Geral"):
                try:
                    all_dfs = [pd.read_csv(get_sheet_url(l)).assign(Lider=l) for l in LIDERES]
                    f_df = pd.concat(all_dfs)
                    output = io.BytesIO()
                    with pd.ExcelWriter(output, engine='xlsxwriter') as wr:
                        f_df.to_excel(wr, index=False)
                    st.download_button("⬇️ Download Excel", output.getvalue(), "Relatorio.xlsx")
                except: st.error("Erro ao gerar arquivo.")

            if st.button("🧹 Limpar Turno (Reset)"):
                requests.post(URL_SCRIPT_GOOGLE, json={"tipo": "limpar_tudo"})
                st.rerun()
