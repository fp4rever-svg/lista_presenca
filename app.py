import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import urllib.parse
import io

# 1. CONFIGURAÇÃO DA PÁGINA
# Começa com a Sidebar fechada para um visual mais profissional
st.set_page_config(
    page_title="Check-in Logística | Grupo SC", 
    layout="centered", 
    initial_sidebar_state="collapsed"
)

# --- ESTILIZAÇÃO CSS (VISUAL LIMPO) ---
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;} /* Esconde menu de 3 pontos */
    footer {visibility: hidden;}    /* Esconde rodapé Streamlit */
    header {background-color: rgba(0,0,0,0);} /* Topo transparente */
    
    /* Garante que o botão da Sidebar continue visível e funcional */
    .st-emotion-cache-zq5wmm {
        visibility: visible !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- CONFIGURAÇÕES DE CONEXÃO ---
SHEET_ID = "1nYm2aRgruykh2YfXTcpCRuHGIqI0TtAFroMEk_p7Ij8"
# Certifique-se de que este link é o da "Nova Versão" implantada no Apps Script
URL_SCRIPT_GOOGLE = "https://script.google.com/macros/s/AKfycbz3J-m4rTKD0Wkr58B2qDsGS81RwZl7-jt3HegpTBI5Fg1mHBJLzoHTvY4D2OW5ZXuClA/exec"
ABAS_LIDERES = ["Carol", "Gabriel / Elisangela","Lais Alves","Leticia","Renato","Thiago"]

def get_sheet_url(aba):
    lider_limpo = urllib.parse.quote(aba)
    return f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={lider_limpo}"

# --- SIDEBAR (PAINEL DO ANALISTA) ---
with st.sidebar:
    st.header("🔐 Painel Administrativo")
    senha = st.text_input("Senha de Acesso", type="password")
    
    if senha == "1234":
        st.success("Acesso Liberado")
        
        # --- MONITORAMENTO DE STATUS DIÁRIO ---
        st.subheader("📅 Status de Hoje")
        data_hoje = datetime.now().strftime("%d/%m") # Procura o dia/mês na coluna D
        
        for l in ABAS_LIDERES:
            try:
                url_check = get_sheet_url(l)
                df_check = pd.read_csv(url_check)
                # Verifica a 4ª coluna (Data/Hora) - índice 3
                coluna_data = df_check.iloc[:, 3].dropna()
                if not coluna_data.empty and data_hoje in str(coluna_data.iloc[-1]):
                    st.write(f"✅ **{l}**: Enviado")
                else:
                    st.write(f"❌ **{l}**: Pendente")
            except:
                st.write(f"⚠️ **{l}**: Erro ao ler aba")
        
        st.markdown("---")
        
        # --- EXPORTAÇÃO UNIFICADA ---
        if st.button("📊 Gerar Excel Unificado"):
            with st.spinner('Consolidando dados...'):
                frames = []
                for l in ABAS_LIDERES:
                    try:
                        d = pd.read_csv(get_sheet_url(l))
                        d.rename(columns={d.columns[0]: 'Colaborador'}, inplace=True)
                        d['Líder Responsável'] = l
                        frames.append(d)
                    except: pass
                
                if frames:
                    full_df = pd.concat(frames, ignore_index=True)
                    output = io.BytesIO()
                    # Requer 'xlsxwriter' no requirements.txt
                    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                        full_df.to_excel(writer, index=False, sheet_name='Consolidado')
                    
                    st.download_button(
                        label="📥 Baixar Excel Geral",
                        data=output.getvalue(),
                        file_name=f"Relatorio_Logistica_{datetime.now().strftime('%d_%m_%Y')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
        
        if st.button("🔍 Ver Pendentes de Inclusão"):
            try:
                df_p = pd.read_csv(get_sheet_url("Pendentes"))
                st.write("### Colaboradores Pendentes")
                st.dataframe(df_p)
            except:
                st.error("Aba 'Pendentes' não encontrada.")

# --- INTERFACE PRINCIPAL ---
st.title("📋 Lista de Presença Digital")
st.caption("Unidade Sumaré | Registro Direto no Google Sheets")

lider_selecionado = st.selectbox("Selecione seu nome (Líder):", ["-- Selecione --"] + ABAS_LIDERES)

if lider_selecionado != "-- Selecione --":
    try:
        url_dados = get_sheet_url(lider_selecionado)
        df_equipe = pd.read_csv(url_dados)
        # Garante que a primeira coluna seja tratada como 'Colaborador'
        df_equipe.rename(columns={df_equipe.columns[0]: 'Colaborador'}, inplace=True)
        
        with st.form("form_chamada"):
            st.write(f"### Equipe: {lider_selecionado}")
            lista_final = []
            
            for i, row in df_equipe.iterrows():
                if pd.isna(row['Colaborador']): continue
                
                col1, col2, col3 = st.columns([3, 1, 3])
                col1.write(f"**{row['Colaborador']}**")
                presente = col2.checkbox("Presença", key=f"check_{i}")
                obs = col3.text_input("Observação", key=f"obs_{i}", placeholder="-")
                
                lista_final.append({
                    "nome": row['Colaborador'],
                    "status": "OK" if presente else "FALTA",
                    "obs": obs
                })
            
            st.markdown("---")
            if st.form_submit_button("✅ ENVIAR CHAMADA"):
                payload = {
                    "tipo": "presenca",
                    "lider": lider_selecionado,
                    "lista": lista_final
                }
                with st.spinner('Salvando dados na planilha...'):
                    try:
                        response = requests.post(URL_SCRIPT_GOOGLE, json=payload)
                        if response.status_code == 200:
                            st.success(f"Chamada de {lider_selecionado} registrada com sucesso!")
                            st.balloons()
                        else:
                            st.error("Erro ao enviar. Verifique o Script do Google.")
                    except:
                        st.error("Falha de conexão com o servidor.")

        # --- ÁREA DE SOLICITAÇÃO ---
        st.markdown("---")
        with st.expander("➕ Solicitar inclusão de novo colaborador"):
            with st.form("form_inc"):
                nome_novo = st.text_input("Nome Completo")
                area_nova = st.text_input("Setor/Área")
                if st.form_submit_button("Enviar para o Analista"):
                    if nome_novo and area_nova:
                        inc_payload = {
                            "tipo": "inclusao",
                            "colaborador": nome_novo,
                            "lider": lider_selecionado,
                            "area": area_nova
                        }
                        requests.post(URL_SCRIPT_GOOGLE, json=inc_payload)
                        st.success("Solicitação enviada para a aba Pendentes!")
                    else:
                        st.warning("Preencha Nome e Área.")

    except Exception as e:
        st.error(f"Erro ao carregar a aba '{lider_selecionado}'.")
        st.info("Verifique se o nome da aba no Sheets está idêntico e se a planilha está compartilhada.")
