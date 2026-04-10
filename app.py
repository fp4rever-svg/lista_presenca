import streamlit as st
import pandas as pd
import requests
from datetime import datetime, date
import urllib.parse
import time
import io

# 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="Check-in Logística | Grupo SC", layout="wide", page_icon="📋")

# --- CSS PARA CORREÇÃO MOBILE ---
st.markdown("""
    <style>
    /* Força as colunas a manterem o alinhamento horizontal no mobile */
    [data-testid="column"] {
        display: flex;
        flex-direction: column;
        justify-content: center;
    }
    /* Diminui o espaçamento entre elementos para caber mais coisa */
    .stCheckbox { margin-bottom: 0px; }
    .stTextInput { margin-top: -10px; }
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
            st.info("A planilha foi atualizada com a data e hora do envio.")
            if st.button("Fazer Nova Chamada / Atualizar"):
                st.session_state.confirmacao_envio = False
                st.rerun()
            st.stop()

        with st.expander("➕ Solicitar inclusão de novo colaborador"):
            with st.form("form_novo_colab", clear_on_submit=True):
                nome_novo = st.text_input("Nome Completo:")
                area_nova = st.text_input("Área/Matrícula:")
                if st.form_submit_button("Enviar Solicitação"):
                    if nome_novo:
                        requests.post(URL_SCRIPT_GOOGLE, json={"tipo": "solicitar_inclusao", "lider": lider_nome, "nome": nome_novo, "matricula": area_nova})
                        st.success("Solicitação enviada!")
                    else: st.warning("Digite o nome.")

        st.divider()
        is_extra = verificar_liberacao_especial()
        
        try:
            url_lista = get_sheet_url(lider_nome)
            df_lista = pd.read_csv(url_lista)
            
            with st.form("chamada_lider"):
                st.subheader(f"Chamada - {lider_nome} " + ("(MODO HORA EXTRA)" if is_extra else "(NORMAL)"))
                dados_para_envio = []
                
                # Cabeçalho Fixo para Mobile (Apenas Escala Normal)
                if not is_extra:
                    h = st.columns([1.5, 4, 1.2]) 
                    h[0].write("**MAT**"); h[1].write("**NOME**"); h[2].write("**OK**")
                else:
                    st.info("📱 Use o celular deitado (horizontal) para melhor visualização em Hora Extra.")

                for i, row in df_lista.iterrows():
                    if pd.isna(row.iloc[0]) and pd.isna(row.iloc[4]): continue 
                    
                    # REGRA DE FÉRIAS (Pula se Coluna J tiver algo)
                    if len(row) > 9 and pd.notna(row.iloc[9]):
                        if str(row.iloc[9]).strip() != "": continue

                    nome_colab = str(row.iloc[0])
                    matricula = str(row.iloc[4])
                    
                    if not is_extra:
                        # Layout Escala Normal: MAT | NOME (Abreviado) | CHECKBOX
                        ln = st.columns([1.5, 4, 1.2])
                        ln[0].write(f"`{matricula}`")
                        
                        # Abreviação para não quebrar a linha no celular
                        nome_curto = (nome_colab[:16] + '..') if len(nome_colab) > 18 else nome_colab
                        ln[1].write(nome_curto)
                        
                        # Checkbox sem label para economizar espaço
                        r_pr = "OK" if ln[2].checkbox("", key=f"pr_{i}", label_visibility="collapsed") else "FALTA"
                        
                        # Campo de OBS logo abaixo da linha para não apertar as colunas
                        r_obs = st.text_input("Obs:", key=f"ob_{i}", placeholder="Justificativa se falta...", label_visibility="collapsed")
                        r_he, r_fr = "Não", "Não"
                    else:
                        # Layout Hora Extra
                        st.markdown(f"**{nome_colab}** ({matricula})")
                        le = st.columns(3)
                        r_he = "Sim" if le[0].checkbox("⚡ HE", key=f"he_{i}") else "Não"
                        r_fr = "Sim" if le[1].checkbox("🚌 FR", key=f"fr_{i}") else "Não"
                        r_pr = "OK"
                        r_obs = st.text_input("Obs", key=f"ob_{i}", label_visibility="collapsed")
                    
                    dados_para_envio.append({"matricula": matricula, "nome": nome_colab, "status": r_pr, "he": r_he, "fretado": r_fr, "obs": r_obs})

                if st.form_submit_button("✅ FINALIZAR E ENVIAR"):
                    with st.spinner("Enviando..."):
                        resp = requests.post(URL_SCRIPT_GOOGLE, json={
                            "tipo": "presenca_completa", "lider": lider_nome, "lista": dados_para_envio, "is_extra": is_extra 
                        })
                        if resp.status_code == 200:
                            st.session_state.confirmacao_envio = True
                            st.rerun()
                        else: st.error("Erro ao conectar.")
        except:
            st.info("Aguardando lista...")

    # --- PERFIL ADMIN ---
    elif st.session_state.perfil == "Admin":
        t1, t2, t3, t4 = st.tabs(["Monitoramento", "Pendentes", "Ferramentas", "📊 Dashboard"])

        with t1:
            st.subheader("Envios de Hoje")
            for l in LIDERES:
                try:
                    df_check = pd.read_csv(get_sheet_url(l))
                    horarios = df_check.iloc[:, 5].dropna().astype(str)
                    horarios = horarios[horarios.str.strip() != ""]
                    if not horarios.empty: st.success(f"✅ **{l}**: {horarios.iloc[0]}")
                    else: st.error(f"❌ **{l}**: Pendente")
                except: st.warning(f"⚠️ **{l}**: Sem dados.")

        with t2:
            st.subheader("Solicitações")
            try: st.dataframe(pd.read_csv(get_sheet_url("Pendentes")), use_container_width=True)
            except: st.info("Sem solicitações.")

        with t3:
            st.subheader("Ferramentas")
            lib_status = verificar_liberacao_especial()
            if st.button(f"MUDAR PARA {'ESCALA NORMAL' if lib_status else 'HORA EXTRA'}"):
                requests.post(URL_SCRIPT_GOOGLE, json={"tipo": "toggle_especial", "status": "OFF" if lib_status else "ON"})
                st.rerun()
            
            st.divider()
            if st.button("📥 Baixar Histórico"):
                df_rel = pd.read_csv(get_sheet_url("Historico"))
                out = io.BytesIO()
                with pd.ExcelWriter(out, engine='xlsxwriter') as wr: df_rel.to_excel(wr, index=False)
                st.download_button("⬇️ Salvar Excel", out.getvalue(), "Historico.xlsx")

        with t4:
            st.subheader("📊 Performance")
            try:
                df_h = pd.read_csv(get_sheet_url("Historico"))
                if not df_h.empty:
                    df_h['Data_DT'] = pd.to_datetime(df_h.iloc[:, 0], dayfirst=True, errors='coerce').dt.date
                    df_h = df_h.dropna(subset=['Data_DT'])
                    d_ini = st.date_input("Início:", df_h['Data_DT'].min())
                    d_fim = st.date_input("Fim:", date.today())
                    df_f = df_h[(df_h['Data_DT'] >= d_ini) & (df_h['Data_DT'] <= d_fim)]
                    
                    resumo = []
                    for l in LIDERES:
                        df_base = pd.read_csv(get_sheet_url(l))
                        # Desconta férias da base do dashboard
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
            except: st.error("Erro no dashboard.")
