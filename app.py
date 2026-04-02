import streamlit as st
import pd as pd
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

    if st.session_state.perfil == "Lider":
        lider_nome = st.session_state.usuario
        with st.expander("➕ Solicitar inclusão de novo colaborador"):
            with st.form("form_novo_colab"):
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
            df_lista = pd.read_csv(get_sheet_url(lider_nome))
            with st.form("chamada_lider"):
                st.subheader(f"Chamada - {lider_nome}")
                dados_para_envio = []
                cols = [1, 3, 1, 1, 2] if is_extra else [1, 3, 1, 2]
                
                h = st.columns(cols)
                h[0].write("**MAT**"); h[1].write("**NOME**")
                if is_extra: h[2].write("**HE**"); h[3].write("**FRT**"); h[4].write("**OBS**")
                else: h[2].write("**PRES**"); h[3].write("**OBS**")

                for i, row in df_lista.iterrows():
                    if pd.isna(row.iloc[0]): continue 
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
                    requests.post(URL_SCRIPT_GOOGLE, json={"tipo": "presenca_completa", "lider": lider_nome, "lista": dados_para_envio})
                    st.success("Check-in enviado!")
                    time.sleep(1); st.rerun()
        except: st.error("Erro ao carregar lista.")

    elif st.session_state.perfil == "Admin":
        t1, t2, t3, t4 = st.tabs(["Monitoramento", "Pendentes", "Ferramentas", "📊 Dashboard"])

        with t1:
            st.subheader("Envios de Hoje (Monitoramento por Aba do Líder)")
            for l in LIDERES:
                try:
                    df_check = pd.read_csv(get_sheet_url(l))
                    horarios = df_check.iloc[:, 5].dropna().astype(str)
                    horarios = horarios[horarios.str.strip() != ""]
                    if not horarios.empty:
                        st.success(f"✅ **{l}**: Concluído às {horarios.iloc[0]}")
                    else: st.error(f"❌ **{l}**: Pendente")
                except: st.warning(f"⚠️ **{l}**: Erro de leitura.")

        with t2:
            st.subheader("Solicitações Pendentes")
            try: st.dataframe(pd.read_csv(get_sheet_url("Pendentes")), use_container_width=True)
            except: st.info("Sem solicitações.")

        with t3:
            st.subheader("Ferramentas")
            lib_status = verificar_liberacao_especial()
            if st.button("🔴 DESATIVAR H.E./FRETADO" if lib_status else "🟢 ATIVAR H.E./FRETADO"):
                requests.post(URL_SCRIPT_GOOGLE, json={"tipo": "toggle_especial", "status": "OFF" if lib_status else "ON"})
                st.rerun()
            st.divider()
            if st.button("📥 Gerar Relatório Excel"):
                try:
                    df_rel = pd.read_csv(get_sheet_url("Historico"))
                    out = io.BytesIO()
                    with pd.ExcelWriter(out, engine='xlsxwriter') as wr: df_rel.to_excel(wr, index=False)
                    st.download_button("⬇️ Baixar", out.getvalue(), "Relatorio.xlsx")
                except: st.error("Erro ao gerar.")
            if st.button("🧹 Limpar Turno (Reset)"):
                requests.post(URL_SCRIPT_GOOGLE, json={"tipo": "limpar_tudo"})
                st.rerun()

        with t4:
            st.subheader("📊 Dashboard de Performance")
            try:
                df_h = pd.read_csv(get_sheet_url("Historico"))
                if not df_h.empty:
                    df_h.columns = ["Data", "Hora", "Matricula", "Colaborador", "Lider", "Status", "HE", "Fretado", "Obs"]
                    df_h['Data_DT'] = pd.to_datetime(df_h['Data'], format='%d/%m/%Y').dt.date
                    c1, c2 = st.columns(2)
                    d_ini = c1.date_input("Início:", df_h['Data_DT'].min())
                    d_fim = c2.date_input("Fim:", date.today())
                    df_f = df_h[(df_h['Data_DT'] >= d_ini) & (df_h['Data_DT'] <= d_fim)]

                    if not df_f.empty:
                        resumo_lideres = []
                        for l in LIDERES:
                            try:
                                # Pega a quantidade REAL de colaboradores na aba do líder
                                df_base = pd.read_csv(get_sheet_url(l))
                                qtd_real_colab = len(df_base.dropna(subset=[df_base.columns[0]]))
                                
                                # Filtra histórico do período para este líder
                                hist_lider = df_f[df_f['Lider'] == l]
                                dias_enviados = hist_lider['Data'].nunique()
                                total_faltas = (hist_lider['Status'] == 'FALTA').sum()
                                
                                if dias_enviados > 0:
                                    absent = (total_faltas / (qtd_real_colab * dias_enviados)) * 100
                                    resumo_lideres.append({
                                        "Lider": l,
                                        "Qtd Colab (Base)": qtd_real_colab,
                                        "Dias Enviados": dias_enviados,
                                        "Total Faltas": total_faltas,
                                        "% Absenteísmo": round(absent, 2)
                                    })
                            except: continue
                        
                        st.write("### Resumo por Equipe")
                        st.dataframe(pd.DataFrame(resumo_lideres), use_container_width=True)
                        
                        st.write("### Frequência Individual")
                        dash_c = df_f.groupby(['Matricula', 'Colaborador', 'Lider']).agg(Pres=('Status', lambda x: (x == 'OK').sum()), Faltas=('Status', lambda x: (x == 'FALTA').sum())).reset_index()
                        st.dataframe(dash_c.sort_values('Faltas', ascending=False), use_container_width=True)
                else: st.info("Sem dados.")
            except Exception as e: st.error(f"Erro: {e}")
