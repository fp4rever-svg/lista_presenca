import streamlit as st
import pandas as pd
import requests
from datetime import datetime, date
import urllib.parse
import time
import io

# 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="Check-in Logística | Grupo SC", layout="wide", page_icon="📋")

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
        
        # Carregamento da lista
        try:
            url_lista = get_sheet_url(lider_nome)
            df_lista = pd.read_csv(url_lista)
            
            with st.form("chamada_lider"):
                st.subheader(f"Chamada - {lider_nome} " + ("(MODO HORA EXTRA)" if is_extra else "(NORMAL)"))
                dados_para_envio = []
                cols = [1, 3, 1, 1, 2] if is_extra else [1, 3, 1, 2]
                
                h = st.columns(cols)
                h[0].write("**MAT**"); h[1].write("**NOME**")
                if is_extra: h[2].write("**HE**"); h[3].write("**FRT**"); h[4].write("**OBS**")
                else: h[2].write("**PRES**"); h[3].write("**OBS**")

                for i, row in df_lista.iterrows():
                    if pd.isna(row.iloc[0]) and pd.isna(row.iloc[4]): continue 
                    
                    # --- NOVA REGRA: FÉRIAS/AFASTAMENTO ---
                    # Verifica se a Coluna J (índice 9) existe e se tem algo escrito nela
                    if len(row) > 9 and pd.notna(row.iloc[9]):
                        status_afastamento = str(row.iloc[9]).strip()
                        if status_afastamento != "" and status_afastamento.lower() != "nan":
                            continue # Pula este colaborador (fica invisível na chamada)
                    # --------------------------------------

                    nome_colab = str(row.iloc[0]); matricula = str(row.iloc[4])
                    ln = st.columns(cols)
                    ln[0].write(f"`{matricula}`"); ln[1].write(nome_colab)
                    r_he, r_fr, r_pr = "Não", "Não", "FALTA"

                    if is_extra:
                        if ln[2].checkbox("⚡", key=f"he_{i}"): r_he = "Sim"
                        if ln[3].checkbox("🚌", key=f"fr_{i}"): r_fr = "Sim"
                        r_obs = ln[4].text_input("", key=f"ob_{i}", label_visibility="collapsed")
                        r_pr = "OK"
                    else:
                        if ln[2].checkbox("OK", key=f"pr_{i}"): r_pr = "OK"
                        r_obs = ln[3].text_input("", key=f"ob_{i}", label_visibility="collapsed")
                    
                    dados_para_envio.append({"matricula": matricula, "nome": nome_colab, "status": r_pr, "he": r_he, "fretado": r_fr, "obs": r_obs})

                if st.form_submit_button("✅ FINALIZAR E ENVIAR"):
                    with st.spinner("Enviando para o Google Sheets..."):
                        resp = requests.post(URL_SCRIPT_GOOGLE, json={
                            "tipo": "presenca_completa", 
                            "lider": lider_nome, 
                            "lista": dados_para_envio,
                            "is_extra": is_extra 
                        })
                        if resp.status_code == 200:
                            st.session_state.confirmacao_envio = True
                            st.rerun()
                        else:
                            st.error("Erro ao conectar com o servidor.")
        except Exception as e:
            st.info("Aguardando carregamento da lista...")

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
                    if not horarios.empty:
                        st.success(f"✅ **{l}**: Concluído às {horarios.iloc[0]}")
                    else: st.error(f"❌ **{l}**: Pendente")
                except: st.warning(f"⚠️ **{l}**: Sem dados.")

        with t2:
            st.subheader("Solicitações Pendentes")
            try: st.dataframe(pd.read_csv(get_sheet_url("Pendentes")), use_container_width=True)
            except: st.info("Sem solicitações.")

        with t3:
            st.subheader("Controle de Operação")
            lib_status = verificar_liberacao_especial()
            st.info(f"Modo atual: **{'HORA EXTRA/FRETADO' if lib_status else 'ESCALA NORMAL'}**")
            if st.button("ALTERAR OPERAÇÃO"):
                requests.post(URL_SCRIPT_GOOGLE, json={"tipo": "toggle_especial", "status": "OFF" if lib_status else "ON"})
                st.rerun()
            
            st.divider()
            if st.button("📥 Baixar Histórico Geral"):
                try:
                    df_rel = pd.read_csv(get_sheet_url("Historico"))
                    out = io.BytesIO()
                    with pd.ExcelWriter(out, engine='xlsxwriter') as wr: df_rel.to_excel(wr, index=False)
                    st.download_button("⬇️ Salvar Excel", out.getvalue(), "Historico.xlsx")
                except: st.error("Erro ao gerar histórico.")

            if st.button("🚀 Baixar HORA EXTRA Atual"):
                try:
                    df_he = pd.read_csv(get_sheet_url("HORA EXTRA"))
                    out_he = io.BytesIO()
                    with pd.ExcelWriter(out_he, engine='xlsxwriter') as wr: df_he.to_excel(wr, index=False)
                    st.download_button("⬇️ Salvar Excel HE", out_he.getvalue(), "Transporte_HE.xlsx")
                except: st.error("Aba HORA EXTRA vazia.")

            st.divider()
            if st.button("🧹 Limpar Turno (Reset)"):
                requests.post(URL_SCRIPT_GOOGLE, json={"tipo": "limpar_tudo"})
                st.rerun()

        with t4:
            st.subheader("📊 Dashboard de Performance")
            try:
                df_h = pd.read_csv(get_sheet_url("Historico"))
                if not df_h.empty:
                    # Correção de Datas
                    df_h['Data_DT'] = pd.to_datetime(df_h.iloc[:, 0], dayfirst=True, errors='coerce').dt.date
                    df_h = df_h.dropna(subset=['Data_DT'])
                    
                    c1, c2 = st.columns(2)
                    d_ini = c1.date_input("Início:", df_h['Data_DT'].min())
                    d_fim = c2.date_input("Fim:", date.today())
                    
                    df_f = df_h[(df_h['Data_DT'] >= d_ini) & (df_h['Data_DT'] <= d_fim)]
                    
                    if not df_f.empty:
                        resumo_lideres = []
                        for l in LIDERES:
                            try:
                                # Pega a base total do líder
                                df_base = pd.read_csv(get_sheet_url(l))
                                
                                # --- NOVA REGRA: Remover Férias/Afastados do cálculo base ---
                                if len(df_base.columns) > 9:
                                    # Mantém na base apenas quem está com a Coluna J (índice 9) vazia
                                    df_base = df_base[df_base.iloc[:, 9].isna() | (df_base.iloc[:, 9].astype(str).str.strip() == "") | (df_base.iloc[:, 9].astype(str).str.lower() == "nan")]
                                # -----------------------------------------------------------
                                
                                total_colab_base = len(df_base[df_base.iloc[:, 0].notna()])
                                
                                # Filtra histórico desse líder
                                dados_lider = df_f[df_f.iloc[:, 4] == l]
                                dias_chamada = dados_lider.iloc[:, 0].nunique()
                                total_faltas = len(dados_lider[dados_lider.iloc[:, 5] == "FALTA"])
                                total_presencas = len(dados_lider[dados_lider.iloc[:, 5] == "OK"])
                                
                                if dias_chamada > 0 and total_colab_base > 0:
                                    # Cálculo: Faltas / (Total Colaboradores Ativos * Dias de Chamada)
                                    perc_abs = (total_faltas / (total_colab_base * dias_chamada)) * 100
                                    resumo_lideres.append({
                                        "Líder": l,
                                        "Colab_Base": total_colab_base,
                                        "Dias": dias_chamada,
                                        "Faltas": total_faltas,
                                        "Presenças": total_presencas,
                                        "% Absenteísmo": f"{perc_abs:.2f}%"
                                    })
                            except: continue
                        
                        if resumo_lideres:
                            st.table(pd.DataFrame(resumo_lideres))
                        
                        st.subheader("🔍 Histórico Detalhado")
                        st.dataframe(df_f, use_container_width=True)
                else:
                    st.info("Sem registros no histórico.")
            except Exception as e:
                st.error(f"Erro no Dashboard: {e}")
