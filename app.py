import streamlit as st
import pandas as pd
import requests
from datetime import datetime, date
import urllib.parse
import time
import io

# 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="Check-in Logística | Grupo SC", layout="wide", page_icon="📋")

# --- CSS PARA CORREÇÃO MOBILE (ESSENCIAL PARA NÃO DESCONFIGURAR) ---
st.markdown("""
    <style>
    /* Impede que as colunas empilhem no celular em telas pequenas */
    [data-testid="column"] {
        display: flex;
        flex-direction: column;
        justify-content: center;
    }
    /* Estilização para inputs e checkboxes ficarem alinhados */
    .stCheckbox { margin-bottom: 0px; }
    .stTextInput { margin-top: -10px; }
    /* Reduz padding excessivo no mobile */
    .block-container { padding-top: 1rem; padding-bottom: 1rem; }
    </style>
    """, unsafe_allow_html=True)

# --- CONFIGURAÇÕES ---
SHEET_ID = "1nYm2aRgruykh2YfXTcpCRuHGIqI0TtAFroMEk_p7Ij8"
URL_SCRIPT_GOOGLE = "https://script.google.com/macros/s/AKfycbwLDpdSgnGTPwciE-25mUel8Zm46zovwoi9o_AnQrkkKUIOfRK6EuPH3YVD0M0TrBJY2Q/exec"
LIDERES = ["Carol", "Elisangela", "Lais Alves", "Leticia", "Renato", "Tiago"]
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

# --- INICIALIZAÇÃO DO SESSION STATE ---
if 'logado' not in st.session_state:
    st.session_state.logado = False
if 'usuario' not in st.session_state:
    st.session_state.usuario = None
if 'perfil' not in st.session_state:
    st.session_state.perfil = None
if 'confirmacao_envio' not in st.session_state:
    st.session_state.confirmacao_envio = False

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
    c1.write(f"Usuário: **{st.session_state.usuario}**")
    if c2.button("Sair/Logoff"):
        for key in list(st.session_state.keys()): del st.session_state[key]
        st.rerun()

    # --- PERFIL LÍDER ---
    if st.session_state.perfil == "Lider":
        lider_nome = st.session_state.usuario
        
        if st.session_state.confirmacao_envio:
            st.success("### ✅ DADOS SALVOS COM SUCESSO!")
            if st.button("Fazer Nova Chamada / Atualizar"):
                st.session_state.confirmacao_envio = False
                st.rerun()
            st.stop()

        with st.expander("➕ Solicitar novo colaborador"):
            with st.form("form_novo_colab", clear_on_submit=True):
                nome_novo = st.text_input("Nome Completo:")
                area_nova = st.text_input("Área/Matrícula:")
                if st.form_submit_button("Enviar Solicitação"):
                    if nome_novo:
                        requests.post(URL_SCRIPT_GOOGLE, json={"tipo": "solicitar_inclusao", "lider": lider_nome, "nome": nome_novo, "matricula": area_nova})
                        st.success("Enviado!")

        st.divider()
        is_extra = verificar_liberacao_especial()
        
        try:
            df_lista = pd.read_csv(get_sheet_url(lider_nome))
            
            with st.form("chamada_lider"):
                st.subheader(f"Chamada - {lider_nome} " + ("(EXTRA)" if is_extra else "(NORMAL)"))
                dados_para_envio = []
                
                # Cabeçalho para Mobile
                if not is_extra:
                    h = st.columns([1.5, 4, 1.2]) 
                    h[0].write("**MAT**"); h[1].write("**NOME**"); h[2].write("**OK**")
                else:
                    st.info("📱 Gire o celular para modo horizontal em Hora Extra.")

                for i, row in df_lista.iterrows():
                    if pd.isna(row.iloc[0]) and pd.isna(row.iloc[4]): continue 
                    
                    # REGRA DE FÉRIAS (Coluna J / Índice 9)
                    if len(row) > 9 and pd.notna(row.iloc[9]):
                        if str(row.iloc[9]).strip() != "" and str(row.iloc[9]).lower() != "nan":
                            continue

                    nome_colab = str(row.iloc[0]); matricula = str(row.iloc[4])
                    
                    if not is_extra:
                        ln = st.columns([1.5, 4, 1.2]) # Colunas fixas para Mobile
                        ln[0].write(f"`{matricula}`")
                        # Abreviar nome para não empurrar o checkbox
                        nome_curto = (nome_colab[:16] + '..') if len(nome_colab) > 18 else nome_colab
                        ln[1].write(nome_curto)
                        r_pr = "OK" if ln[2].checkbox("", key=f"pr_{i}", label_visibility="collapsed") else "FALTA"
                        r_obs = st.text_input("Obs:", key=f"ob_{i}", placeholder="Justificativa...", label_visibility="collapsed")
                        r_he, r_fr = "Não", "Não"
                    else:
                        st.markdown(f"**{nome_colab}** ({matricula})")
                        le = st.columns(3)
                        r_he = "Sim" if le[0].checkbox("⚡ HE", key=f"he_{i}") else "Não"
                        r_fr = "Sim" if le[1].checkbox("🚌 FR", key=f"fr_{i}") else "Não"
                        r_obs = st.text_input("Obs", key=f"ob_{i}", label_visibility="collapsed")
                        r_pr = "OK"
                    
                    dados_para_envio.append({"matricula": matricula, "nome": nome_colab, "status": r_pr, "he": r_he, "fretado": r_fr, "obs": r_obs})

                if st.form_submit_button("✅ FINALIZAR"):
                    with st.spinner("Gravando..."):
                        resp = requests.post(URL_SCRIPT_GOOGLE, json={"tipo": "presenca_completa", "lider": lider_nome, "lista": dados_para_envio, "is_extra": is_extra})
                        if resp.status_code == 200:
                            st.session_state.confirmacao_envio = True
                            st.rerun()
        except: st.info("Carregando lista...")

    # --- PERFIL ADMIN ---
    elif st.session_state.perfil == "Admin":
        t1, t2, t3, t4 = st.tabs(["Monitoramento", "Pendentes", "Ferramentas", "📊 Dashboard"])

        with t1:
            st.subheader("Status de Hoje")
            for l in LIDERES:
                try:
                    df_check = pd.read_csv(get_sheet_url(l))
                    h = df_check.iloc[:, 5].dropna().astype(str)
                    h = h[h.str.strip() != ""]
                    if not h.empty: st.success(f"✅ **{l}**: {h.iloc[0]}")
                    else: st.error(f"❌ **{l}**: Pendente")
                except: st.warning(f"⚠️ **{l}**: Erro")

        with t2:
            try: st.dataframe(pd.read_csv(get_sheet_url("Pendentes")), use_container_width=True)
            except: st.info("Sem pendências.")

        with t3:
            st.subheader("Controle")
            lib_status = verificar_liberacao_especial()
            st.write(f"Modo: **{'HORA EXTRA' if lib_status else 'ESCALA NORMAL'}**")
            if st.button("ALTERAR MODO DE OPERAÇÃO"):
                requests.post(URL_SCRIPT_GOOGLE, json={"tipo": "toggle_especial", "status": "OFF" if lib_status else "ON"})
                st.rerun()
            
            st.divider()
            if st.button("📥 Baixar Histórico Geral (Excel)"):
                df_rel = pd.read_csv(get_sheet_url("Historico"))
                out = io.BytesIO()
                with pd.ExcelWriter(out, engine='xlsxwriter') as wr: df_rel.to_excel(wr, index=False)
                st.download_button("⬇️ Salvar Arquivo", out.getvalue(), "Historico.xlsx")

            if st.button("🚀 Baixar Fretado/HE"):
                df_he = pd.read_csv(get_sheet_url("HORA EXTRA"))
                out_he = io.BytesIO()
                with pd.ExcelWriter(out_he, engine='xlsxwriter') as wr: df_he.to_excel(wr, index=False)
                st.download_button("⬇️ Salvar HE", out_he.getvalue(), "Transporte.xlsx")

            if st.button("🧹 Resetar Turno (Limpar Tudo)"):
                requests.post(URL_SCRIPT_GOOGLE, json={"tipo": "limpar_tudo"})
                st.rerun()

        with t4:
            st.subheader("📊 Performance")
            try:
                df_h = pd.read_csv(get_sheet_url("Historico"))
                if not df_h.empty:
                    df_h['Data_DT'] = pd.to_datetime(df_h.iloc[:, 0], dayfirst=True, errors='coerce').dt.date
                    df_h = df_h.dropna(subset=['Data_DT'])
                    c1, c2 = st.columns(2)
                    d_ini = c1.date_input("Início:", df_h['Data_DT'].min())
                    d_fim = c2.date_input("Fim:", date.today())
                    df_f = df_h[(df_h['Data_DT'] >= d_ini) & (df_h['Data_DT'] <= d_fim)]
                    
                    resumo = []
                    for l in LIDERES:
                        df_base = pd.read_csv(get_sheet_url(l))
                        # Remove afastados da base de cálculo
                        if len(df_base.columns) > 9:
                            df_base = df_base[df_base.iloc[:, 9].isna() | (df_base.iloc[:, 9].astype(str).str.strip() == "")]
                        
                        total_base = len(df_base[df_base.iloc[:, 0].notna()])
                        dl = df_f[df_f.iloc[:, 4] == l]
                        dias = dl.iloc[:, 0].nunique()
                        faltas = len(dl[dl.iloc[:, 5] == "FALTA"])
                        
                        if dias > 0 and total_base > 0:
                            perc = (faltas / (total_base * dias)) * 100
                            resumo.append({"Líder": l, "Base": total_base, "Dias": dias, "Faltas": faltas, "% Abs": f"{perc:.2f}%"})
                    
                    if resumo: st.table(pd.DataFrame(resumo))
                    st.dataframe(df_f, use_container_width=True)
            except: st.error("Erro ao gerar gráficos.")
