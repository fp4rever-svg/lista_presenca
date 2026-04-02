import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import urllib.parse
import time
import io

# 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="Check-in Logística | Grupo SC", layout="wide", page_icon="📋")

# --- CONFIGURAÇÕES FIXAS ---
SHEET_ID = "1nYm2aRgruykh2YfXTcpCRuHGIqI0TtAFroMEk_p7Ij8"
URL_SCRIPT_GOOGLE = "https://script.google.com/macros/s/AKfycbwLDpdSgnGTPwciE-25mUel8Zm46zovwoi9o_AnQrkkKUIOfRK6EuPH3YVD0M0TrBJY2Q/exec"
LIDERES = ["Carol", "Elisangela", "Lais Alves", "Leticia", "Renato", "Thiago"]

def get_sheet_url(aba):
    ts = int(time.time())
    aba_enc = urllib.parse.quote(aba)
    return f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={aba_enc}&t={ts}"

def verificar_liberacao_especial():
    try:
        url = get_sheet_url("Config_Geral")
        df = pd.read_csv(url, header=None)
        return True if str(df.iloc[0, 1]).strip().upper() == "ON" else False
    except: return False

if 'logado' not in st.session_state:
    st.session_state.update({'logado': False, 'usuario': None, 'perfil': None})

# --- INTERFACE DE LOGIN ---
if not st.session_state.logado:
    st.title("📋 Check-in Logística")
    perfil = st.radio("Perfil:", ["Líder", "Administrador"], horizontal=True)
    if perfil == "Líder":
        user = st.selectbox("Líder:", ["--"] + LIDERES)
        if st.button("Entrar"):
            st.session_state.update({'logado': True, 'usuario': user, 'perfil': "Lider"})
            st.rerun()
    else:
        senha = st.text_input("Senha ADM:", type="password")
        if st.button("Acessar"):
            if senha == "1234":
                st.session_state.update({'logado': True, 'usuario': "Admin", 'perfil': "Admin"})
                st.rerun()

# --- SISTEMA ---
else:
    st.sidebar.write(f"Usuário: {st.session_state.usuario}")
    if st.sidebar.button("Sair"):
        st.session_state.logado = False
        st.rerun()

    if st.session_state.perfil == "Lider":
        lider_nome = st.session_state.usuario
        is_extra = verificar_liberacao_especial()
        
        try:
            # Carrega a aba do líder
            df = pd.read_csv(get_sheet_url(lider_nome))
            
            st.subheader(f"Chamada: {lider_nome}")
            if is_extra: st.warning("MODO H.E. / FRETADO ATIVO")
            
            with st.form("form_chamada"):
                dados_envio = []
                # Definição das colunas da tabela no Streamlit
                c_size = [1, 3, 1, 1, 2] if is_extra else [1, 3, 1, 2]
                h = st.columns(c_size)
                h[0].write("**Matrícula**")
                h[1].write("**Colaborador**")
                
                if is_extra:
                    h[2].write("**HE**"); h[3].write("**FRT**"); h[4].write("**OBS**")
                else:
                    h[2].write("**PRES**"); h[3].write("**OBS**")

                for i, row in df.iterrows():
                    # Lógica de colunas conforme sua planilha:
                    # NOME na Coluna A (index 0) e MATRICULA na Coluna E (index 4)
                    if pd.isna(row.iloc[0]): continue # Pula se o nome estiver vazio
                    
                    nome_colab = str(row.iloc[0])
                    matricula = str(row.iloc[4])
                    
                    ln = st.columns(c_size)
                    ln[0].write(f"`{matricula}`")
                    ln[1].write(nome_colab)
                    
                    r_he, r_fr, r_pr, r_obs = "", "", "", ""

                    if is_extra:
                        if ln[2].checkbox("HE", key=f"he_{i}"): r_he = "Sim"
                        if ln[3].checkbox("FR", key=f"fr_{i}"): r_fr = "Sim"
                        r_obs = ln[4].text_input("Obs", key=f"ob_{i}", label_visibility="collapsed")
                    else:
                        if ln[2].checkbox("OK", key=f"pr_{i}"): r_pr = "OK"
                        else: r_pr = "FALTA"
                        r_obs = ln[3].text_input("Obs", key=f"ob_{i}", label_visibility="collapsed")
                    
                    dados_envio.append({
                        "matricula": matricula, "nome": nome_colab, 
                        "status": r_pr, "he": r_he, "fretado": r_fr, "obs": r_obs
                    })

                if st.form_submit_button("✅ ENVIAR CHECK-LIST"):
                    resp = requests.post(URL_SCRIPT_GOOGLE, json={"tipo": "presenca_completa", "lider": lider_nome, "lista": dados_envio})
                    st.success("Check-list enviado com sucesso!")

        except Exception as e:
            st.error(f"Erro ao carregar aba {lider_nome}. Verifique as colunas A e E.")

    elif st.session_state.perfil == "Admin":
        t1, t2 = st.tabs(["Painel de Controle", "📊 Tabela Geral (Absenteísmo)"])
        
        with t1:
            if st.button("🔄 ALTERAR MODO (NORMAL / EXTRA)"):
                status_atual = verificar_liberacao_especial()
                requests.post(URL_SCRIPT_GOOGLE, json={"tipo": "toggle_especial", "status": "OFF" if status_atual else "ON"})
                st.rerun()
            
            if st.button("🧹 RESETAR SISTEMA (LIMPAR CAMPOS)"):
                requests.post(URL_SCRIPT_GOOGLE, json={"tipo": "limpar_tudo"})
                st.success("Reset concluído!")

        with t2:
            try:
                df_h = pd.read_csv(get_sheet_url("Historico"))
                if not df_h.empty:
                    df_h.columns = ["Data", "Hora", "Matricula", "Nome", "Lider", "Presenca", "HE", "Fretado", "Obs"]
                    
                    # Filtro de Busca
                    busca = st.text_input("Pesquisar Matrícula ou Nome:")
                    if busca:
                        df_h = df_h[df_h['Nome'].str.contains(busca, case=False) | df_h['Matricula'].astype(str).str.contains(busca)]
                    
                    # Cálculo de Absenteísmo (apenas modo normal)
                    df_abs = df_h[df_h['Presenca'].isin(['OK', 'FALTA'])]
                    if not df_abs.empty:
                        total = df_abs.groupby(['Matricula', 'Nome']).size().reset_index(name='Total')
                        faltas = df_abs[df_abs['Presenca'] == 'FALTA'].groupby(['Matricula', 'Nome']).size().reset_index(name='Faltas')
                        relat = pd.merge(total, faltas, on=['Matricula', 'Nome'], how='left').fillna(0)
                        relat['% Abs'] = (relat['Faltas'] / relat['Total'] * 100).round(2)
                        st.write("### Relatório de Absenteísmo")
                        st.dataframe(relat, use_container_width=True)
                    
                    st.write("### Todos os Lançamentos")
                    st.dataframe(df_h, use_container_width=True)
                else: st.info("Aguardando primeiros lançamentos...")
            except: st.info("Aba 'Historico' ainda não foi criada.")
