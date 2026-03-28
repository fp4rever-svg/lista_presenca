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
        r = requests.post(URL_SCRIPT_GOOGLE, json={"tipo": "buscar_senhas"}, timeout=10)
        return r.json() if r.status_code == 200 else {}
    except: return {}

def verificar_liberacao_especial():
    try:
        url = get_sheet_url("Config_Geral")
        df = pd.read_csv(url, header=None)
        status = str(df.iloc[0, 1]).strip().upper()
        return True if status == "ON" else False
    except: return False

# --- CONTROLE DE SESSÃO ---
if 'logado' not in st.session_state:
    st.session_state.update({'logado': False, 'usuario': None, 'perfil': None})

# ==========================================
# LOGIN
# ==========================================
if not st.session_state.logado:
    st.title("📋 Check-in Logística")
    p_tipo = st.radio("Entrar como:", ["Líder", "Administrador"], horizontal=True)

    if p_tipo == "Líder":
        u_sel = st.selectbox("Selecione seu nome:", ["--"] + LIDERES)
        if u_sel != "--":
            # Busca as senhas direto no banco de dados do Sheets
            dicionario_senhas = buscar_senhas_db()
            senha_registrada = dicionario_senhas.get(u_sel)
            
            if not senha_registrada:
                st.warning(f"Olá {u_sel}, você ainda não tem uma senha.")
                nova_s = st.text_input("Crie uma senha de acesso:", type="password", key="new_pass")
                if st.button("Cadastrar Senha"):
                    if nova_s:
                        payload = {"tipo": "definir_senha", "lider": u_sel, "nova_senha": nova_s}
                        requests.post(URL_SCRIPT_GOOGLE, json=payload)
                        st.success("Senha cadastrada com sucesso! Clique em Entrar.")
                        time.sleep(1)
                        st.rerun()
            else:
                senha_input = st.text_input("Digite sua senha:", type="password", key="login_pass")
                if st.button("Entrar"):
                    if str(senha_input) == str(senha_registrada):
                        st.session_state.update({'logado': True, 'usuario': u_sel, 'perfil': "Lider"})
                        st.rerun()
                    else:
                        st.error("Senha incorreta. Tente novamente.")

# ==========================================
# ÁREA LOGADA
# ==========================================
else:
    c_h1, c_h2 = st.columns([5, 1])
    c_h1.write(f"Usuário: **{st.session_state.usuario}**")
    if c_h2.button("Sair"):
        st.session_state.logado = False
        st.rerun()

    # --- TELA LIDER ---
    if st.session_state.perfil == "Lider":
        lider = st.session_state.usuario
        liberado = verificar_liberacao_especial()
        
        try:
            df = pd.read_csv(get_sheet_url(lider))
            df.rename(columns={df.columns[0]: 'Colaborador'}, inplace=True)

            # --- FORMULÁRIO DE CHAMADA ---
            with st.form("form_lider"):
                st.subheader(f"Lista de {lider}")
                lista_enviar = []
                
                if liberado:
                    st.info("⏰ MODO HORA EXTRA / FRETADO ATIVO (Presença Oculta)")
                    cols_layout = [3, 1, 1, 3]
                    h = st.columns(cols_layout)
                    h[0].write("**Nome**")
                    h[1].write("**H.E.**")
                    h[2].write("**Fret.**")
                    h[3].write("**Observação**")
                else:
                    cols_layout = [3, 1, 3]
                    h = st.columns(cols_layout)
                    h[0].write("**Nome**")
                    h[1].write("**Presença**")
                    h[2].write("**Observação**")

                for i, row in df.iterrows():
                    if pd.isna(row['Colaborador']): continue
                    h_val, f_val, p_val = "Não", "Não", "FALTA"
                    
                    if liberado:
                        c = st.columns(cols_layout)
                        c[0].write(row['Colaborador'])
                        if c[1].checkbox("⚡", key=f"he_{i}"): h_val = "Sim"
                        if c[2].checkbox("🚌", key=f"fr_{i}"): f_val = "Sim"
                        obs = c[3].text_input("", key=f"o_{i}", label_visibility="collapsed")
                        p_val = "OK"
                    else:
                        c = st.columns(cols_layout)
                        c[0].write(row['Colaborador'])
                        if c[1].checkbox("OK", key=f"p_{i}"): p_val = "OK"
                        obs = c[2].text_input("", key=f"o_{i}", label_visibility="collapsed")

                    lista_enviar.append({"nome": row['Colaborador'], "status": p_val, "he": h_val, "fretado": f_val, "obs": obs})

                if st.form_submit_button("✅ ENVIAR CHECK-IN"):
                    requests.post(URL_SCRIPT_GOOGLE, json={"tipo": "presenca_completa", "lider": lider, "lista": lista_enviar})
                    st.success("Dados enviados!")
                    st.balloons()

            # --- SEÇÃO DE SOLICITAÇÃO (PARA O ADMIN) ---
            st.divider()
            with st.expander("➕ Solicitar Inclusão de Novo Colaborador"):
                st.write("Esta solicitação será enviada para aprovação do Administrador.")
                with st.form("form_solicitacao"):
                    nome_novo = st.text_input("Nome Completo:")
                    area_nova = st.selectbox("Área/Setor:", ["Recebimento", "Separação", "Expedição", "Devolução", "Inventário", "Outros"])
                    
                    if st.form_submit_button("Enviar para Administrador"):
                        if nome_novo:
                            payload = {
                                "tipo": "solicitar_inclusao",
                                "nome": nome_novo,
                                "lider": lider,
                                "area": area_nova
                            }
                            requests.post(URL_SCRIPT_GOOGLE, json=payload)
                            st.success(f"Solicitação de {nome_novo} enviada com sucesso!")
                        else:
                            st.error("Por favor, preencha o nome.")

        except Exception as e: st.error(f"Erro: {e}")

    # --- TELA ADMIN ---
    elif st.session_state.perfil == "Admin":
        t1, t2, t3 = st.tabs(["Monitoramento", "Solicitações Pendentes", "Ferramentas"])

        with t1:
            st.subheader("Envios de Hoje")
            hoje = datetime.now().strftime("%d/%m")
            for l in LIDERES:
                try:
                    df_s = pd.read_csv(get_sheet_url(l))
                    if any(hoje in str(x) for x in df_s.iloc[:, 3]):
                        st.success(f"✅ {l}: Enviado")
                    else: st.error(f"❌ {l}: Pendente")
                except: st.warning(f"⚠️ {l}")

        with t2:
            st.subheader("📝 Novos Colaboradores Aguardando Inclusão")
            try:
                df_pendentes = pd.read_csv(get_sheet_url("Pendentes"))
                if not df_pendentes.empty:
                    st.dataframe(df_pendentes, use_container_width=True)
                    st.info("Consulte a aba 'Pendentes' na sua planilha para realizar as inclusões fixas.")
                else:
                    st.write("Nenhuma solicitação pendente.")
            except:
                st.write("Aba 'Pendentes' não encontrada ou vazia.")

        with t3:
            st.subheader("⚙️ Configurações de Visibilidade")
            at_status = verificar_liberacao_especial()
            if at_status:
                st.success("CAMPOS EXTRAS LIBERADOS")
                if st.button("🔴 BLOQUEAR H.E./FRETADO"):
                    requests.post(URL_SCRIPT_GOOGLE, json={"tipo": "toggle_especial", "status": "OFF"})
                    time.sleep(1); st.rerun()
            else:
                st.warning("CAMPOS EXTRAS OCULTOS")
                if st.button("🟢 LIBERAR H.E./FRETADO"):
                    requests.post(URL_SCRIPT_GOOGLE, json={"tipo": "toggle_especial", "status": "ON"})
                    time.sleep(1); st.rerun()

            st.divider()
            if st.button("🔄 Ver Senhas"):
                senhas = buscar_senhas_db()
                if senhas: st.table(pd.DataFrame(list(senhas.items()), columns=['Líder', 'Senha']))

            st.divider()
            if st.button("📥 Gerar Excel Unificado"):
                try:
                    tabs = [pd.read_csv(get_sheet_url(l)).assign(Lider=l) for l in LIDERES]
                    full_df = pd.concat(tabs)
                    out = io.BytesIO()
                    with pd.ExcelWriter(out, engine='xlsxwriter') as wr:
                        full_df.to_excel(wr, index=False)
                    st.download_button("⬇️ Baixar Excel", out.getvalue(), "Relatorio.xlsx")
                except: st.error("Erro ao gerar Excel.")

            if st.button("🧹 RESETAR TUDO"):
                requests.post(URL_SCRIPT_GOOGLE, json={"tipo": "limpar_tudo"})
                st.rerun()
