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
SENHA_ADMIN = "1234"

# --- FUNÇÕES DE UTILIDADE ---
def get_sheet_url(aba):
    """Gera URL de exportação CSV para uma aba específica do Google Sheets"""
    ts = int(time.time())
    aba_enc = urllib.parse.quote(aba)
    return f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={aba_enc}&t={ts}"

def buscar_senhas_db():
    try:
        r = requests.post(URL_SCRIPT_GOOGLE, json={"tipo": "buscar_senhas"}, timeout=15)
        return r.json() if r.status_code == 200 else {}
    except:
        return {}

def verificar_liberacao_especial():
    try:
        url = get_sheet_url("Config_Geral")
        df = pd.read_csv(url, header=None)
        return True if str(df.iloc[0, 1]).strip().upper() == "ON" else False
    except:
        return False

# --- INICIALIZAÇÃO DE SESSÃO ---
if 'logado' not in st.session_state:
    st.session_state.update({'logado': False, 'usuario': None, 'perfil': None})

# ==========================================
# TELA DE LOGIN
# ==========================================
if not st.session_state.logado:
    st.title("📋 Sistema de Check-in Logística")
    st.info("Acesse com seu usuário de Líder ou Painel Administrativo.")
    
    perfil_escolhido = st.radio("Selecione o Perfil:", ["Líder", "Administrador"], horizontal=True)

    if perfil_escolhido == "Líder":
        l_sel = st.selectbox("Selecione seu nome:", ["-- SELECIONE --"] + LIDERES)
        if l_sel != "-- SELECIONE --":
            senhas = buscar_senhas_db()
            senha_gravada = senhas.get(l_sel)

            if not senha_gravada:
                st.warning(f"Primeiro acesso de {l_sel}. Defina uma senha:")
                nova_s = st.text_input("Definir Senha:", type="password")
                if st.button("Cadastrar e Acessar"):
                    if nova_s:
                        requests.post(URL_SCRIPT_GOOGLE, json={"tipo": "definir_senha", "lider": l_sel, "nova_senha": nova_s})
                        st.session_state.update({'logado': True, 'usuario': l_sel, 'perfil': "Lider"})
                        st.rerun()
            else:
                senha_in = st.text_input("Senha:", type="password")
                if st.button("Entrar"):
                    if str(senha_in) == str(senha_gravada):
                        st.session_state.update({'logado': True, 'usuario': l_sel, 'perfil': "Lider"})
                        st.rerun()
                    else:
                        st.error("Senha incorreta.")
    else:
        s_adm = st.text_input("Senha Mestra:", type="password")
        if st.button("Acessar Admin"):
            if s_adm == SENHA_ADMIN:
                st.session_state.update({'logado': True, 'usuario': "Admin", 'perfil': "Admin"})
                st.rerun()
            else:
                st.error("Senha Administrativa Inválida.")

# ==========================================
# ÁREA LOGADA
# ==========================================
else:
    # Cabeçalho de Usuário
    cab1, cab2 = st.columns([5, 1])
    cab1.write(f"Conectado como: **{st.session_state.usuario}**")
    if cab2.button("Sair"):
        st.session_state.logado = False
        st.rerun()

    # ------------------------------------------
    # VISÃO DO LÍDER
    # ------------------------------------------
    if st.session_state.perfil == "Lider":
        lider_atual = st.session_state.usuario
        modo_he = verificar_liberacao_especial()
        
        st.header(f"Lista de Chamada - {lider_atual}")
        
        try:
            # Carrega a lista de colaboradores da aba do líder
            url_lider = get_sheet_url(lider_atual)
            df_lista = pd.read_csv(url_lider)
            # Normaliza a primeira coluna para 'Colaborador'
            df_lista.rename(columns={df_lista.columns[0]: 'Colaborador'}, inplace=True)

            # Formulário Principal de Presença
            with st.form("form_presenca"):
                st.write("Marque a presença e clique no botão ao final.")
                lista_envio = []
                
                # Cabeçalho da Tabela
                h = st.columns([3, 1, 1, 3]) if modo_he else st.columns([3, 1, 3])
                h[0].write("**Nome**")
                if modo_he:
                    h[1].write("**HE**")
                    h[2].write("**Fret**")
                    h[3].write("**Observação**")
                else:
                    h[1].write("**Status**")
                    h[2].write("**Observação**")
                
                # Linhas de Colaboradores
                for idx, row in df_lista.iterrows():
                    if pd.isna(row['Colaborador']): continue
                    
                    ln = st.columns([3, 1, 1, 3]) if modo_he else st.columns([3, 1, 3])
                    ln[0].write(row['Colaborador'])
                    
                    status_final = "FALTA"
                    he_final = "Não"
                    fr_final = "Não"
                    
                    if modo_he:
                        if ln[1].checkbox("Sim", key=f"he_{idx}"): he_final = "Sim"
                        if ln[2].checkbox("Sim", key=f"fr_{idx}"): fr_final = "Sim"
                        obs_final = ln[3].text_input("Obs", key=f"obs_{idx}", label_visibility="collapsed")
                        status_final = "OK" # No modo HE, assume-se presença se estiver na lista
                    else:
                        if ln[1].checkbox("Pres.", key=f"pr_{idx}"): status_final = "OK"
                        obs_final = ln[2].text_input("Obs", key=f"obs_{idx}", label_visibility="collapsed")
                    
                    lista_envio.append({
                        "nome": row['Colaborador'],
                        "status": status_final,
                        "he": he_final,
                        "fretado": fr_final,
                        "obs": obs_final
                    })

                enviar_chamada = st.form_submit_button("✅ SALVAR PRESENÇAS")
                if enviar_chamada:
                    with st.spinner("Enviando..."):
                        res = requests.post(URL_SCRIPT_GOOGLE, json={
                            "tipo": "presenca_completa", 
                            "lider": lider_atual, 
                            "lista": lista_envio
                        })
                        if res.status_code == 200:
                            st.success("Presenças registradas com sucesso!")
                        else:
                            st.error("Erro ao comunicar com o servidor.")

            # --- ÁREA DE SOLICITAÇÃO DE NOVOS MEMBROS ---
            st.markdown("---")
            st.subheader("🚀 Gestão de Equipe")
            with st.expander("➕ SOLICITAR INCLUSÃO DE NOVO COLABORADOR", expanded=False):
                st.write("Use este campo para pedir ao Admin que adicione alguém à sua lista fixa.")
                with st.form("form_solicitacao"):
                    novo_nome = st.text_input("Nome Completo do Colaborador:")
                    novo_setor = st.selectbox("Setor:", ["Recebimento", "Separação", "Expedição", "Inventário", "Outros"])
                    
                    if st.form_submit_button("Enviar Pedido"):
                        if novo_nome:
                            payload = {
                                "tipo": "solicitar_inclusao",
                                "nome": novo_nome,
                                "lider": lider_atual,
                                "area": novo_setor
                            }
                            requests.post(URL_SCRIPT_GOOGLE, json=payload)
                            st.success(f"Solicitação para '{novo_nome}' enviada para análise!")
                        else:
                            st.warning("Preencha o nome do colaborador.")

        except Exception as e:
            st.error(f"Erro ao carregar sua lista de equipe: {e}")

    # ------------------------------------------
    # VISÃO DO ADMINISTRADOR
    # ------------------------------------------
    elif st.session_state.perfil == "Admin":
        t1, t2, t3, t4 = st.tabs(["📊 Monitoramento", "📩 Pendentes", "⚙️ Configurações", "📈 Histórico"])

        with t1:
            st.subheader("Status de Envio (Hoje)")
            hoje = datetime.now().strftime("%d/%m")
            for l in LIDERES:
                try:
                    df_check = pd.read_csv(get_sheet_url(l))
                    # Verifica data na Coluna D (índice 3)
                    if not df_check.empty and df_check.iloc[:, 3].astype(str).str.contains(hoje).any():
                        st.success(f"✅ {l}: Já enviou hoje.")
                    else:
                        st.error(f"❌ {l}: Ainda não enviou.")
                except:
                    st.warning(f"⚠️ {l}: Erro ao acessar aba.")

        with t2:
            st.subheader("Solicitações de Inclusão")
            try:
                df_p = pd.read_csv(get_sheet_url("Pendentes"))
                if not df_p.empty:
                    st.dataframe(df_p, use_container_width=True)
                    st.caption("Cadastre estes nomes nas abas correspondentes do Sheets e limpe esta lista no Sheets após concluir.")
                else:
                    st.info("Nenhuma solicitação pendente.")
            except:
                st.info("Aba 'Pendentes' não encontrada ou vazia.")

        with t3:
            st.subheader("Controle de Sistema")
            lib = verificar_liberacao_especial()
            if lib:
                st.success("O sistema está em MODO HORA EXTRA (Domingo/Feriado)")
                if st.button("Mudar para Modo Normal (Escala)"):
                    requests.post(URL_SCRIPT_GOOGLE, json={"tipo": "toggle_especial", "status": "OFF"})
                    st.rerun()
            else:
                st.info("O sistema está em MODO NORMAL (Escala Diária)")
                if st.button("Mudar para Modo Hora Extra"):
                    requests.post(URL_SCRIPT_GOOGLE, json={"tipo": "toggle_especial", "status": "ON"})
                    st.rerun()
            
            st.divider()
            if st.button("🗑️ Resetar Presenças do Turno"):
                if st.checkbox("Confirmo que quero apagar as datas/status de hoje"):
                    requests.post(URL_SCRIPT_GOOGLE, json={"tipo": "limpar_tudo"})
                    st.success("Dados limpos!")

        with t4:
            st.subheader("Relatório Geral de Faltas")
            try:
                df_h = pd.read_csv(get_sheet_url("Historico"))
                if not df_h.empty:
                    df_h.columns = ["Data", "Hora", "Nome", "Lider", "Status", "HE", "Fretado", "Obs"]
                    faltas = df_h[df_h['Status'] == 'FALTA']
                    st.metric("Total de Faltas Acumuladas", len(faltas))
                    st.bar_chart(faltas['Lider'].value_counts())
                else:
                    st.info("Histórico ainda não possui registros.")
            except:
                st.warning("Aba 'Historico' não configurada.")
