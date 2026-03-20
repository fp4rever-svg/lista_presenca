import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import urllib.parse

# Configuração da página
st.set_page_config(page_title="Check-in Logística | Grupo SC", layout="centered")

# --- CONFIGURAÇÕES ---
SHEET_ID = "1nYm2aRgruykh2YfXTcpCRuHGIqI0TtAFroMEk_p7Ij8"
# Seu link oficial do Apps Script para salvar na aba Pendentes
URL_SCRIPT_GOOGLE = "https://script.google.com/macros/s/AKfycbz3J-m4rTKD0Wkr58B2qDsGS81RwZl7-jt3HegpTBI5Fg1mHBJLzoHTvY4D2OW5ZXuClA/exec"

def get_sheet_url(aba):
    lider_limpo = urllib.parse.quote(aba)
    return f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={lider_limpo}"

# Lista de líderes (Verifique se os nomes batem com as abas do Sheets)
ABAS_LIDERES = ["Paula Toledo", "Fabio Santos"]

st.title("📋 Lista de Presença Digital")
st.caption("Unidade Sumaré - Conexão Direta via Google Sheets")

# --- SELEÇÃO DO LÍDER ---
lider = st.selectbox("Selecione seu nome (Líder):", ["-- Selecione --"] + ABAS_LIDERES)

if lider != "-- Selecione --":
    try:
        # Carrega os dados da aba do líder
        df = pd.read_csv(get_sheet_url(lider))
        
        with st.form("form_chamada"):
            st.write(f"### Equipe: {lider}")
            dados_turno = []
            
            for i, row in df.iterrows():
                col1, col2, col3 = st.columns([3, 1, 3])
                col1.write(f"**{row['Colaborador']}**")
                presenca = col2.checkbox("Presente", key=f"p_{i}")
                obs = col3.text_input("Obs/Justificativa", key=f"o_{i}", placeholder="Opcional")
                
                dados_turno.append({
                    "Data": datetime.now().strftime("%d/%m/%Y"),
                    "Lider": lider,
                    "Colaborador": row['Colaborador'],
                    "Status": "SIM" if presenca else "NÃO",
                    "Observacao": obs
                })
            
            st.markdown("---")
            # Botão renomeado para ENVIAR conforme solicitado
            if st.form_submit_button("✅ ENVIAR"):
                st.success("Presença processada! O relatório CSV está pronto para baixar.")
                csv = pd.DataFrame(dados_turno).to_csv(index=False).encode('utf-8-sig')
                st.download_button(
                    label="📥 Baixar Relatório (CSV)",
                    data=csv,
                    file_name=f"Presenca_{lider.replace(' ', '_')}.csv",
                    mime="text/csv"
                )

        # --- ÁREA DE SOLICITAÇÃO DE INCLUSÃO ---
        st.markdown("---")
        with st.expander("➕ SOLICITAR INCLUSÃO DE NOVO COLABORADOR"):
            st.info("Use este campo para adicionar alguém que ainda não está na sua lista.")
            with st.form("form_inclusao"):
                nome_novo = st.text_input("Nome Completo do Colaborador")
                area_nova = st.text_input("Área ou Setor")
                
                # Botão Salvar que aciona o Google Apps Script
                if st.form_submit_button("Salvar Solicitação"):
                    if nome_novo and area_nova:
                        # Prepara o pacote de dados para o Script
                        payload = {
                            "colaborador": nome_novo,
                            "lider": lider,
                            "area": area_nova
                        }
                        
                        # Envia via POST para o Google Sheets (Gratuito)
                        try:
                            response = requests.post(URL_SCRIPT_GOOGLE, json=payload)
                            if response.status_code == 200:
                                st.success(f"Solicitação de {nome_novo} salva com sucesso na aba Pendentes!")
                            else:
                                st.error("Erro na comunicação com o Google Script.")
                        except:
                            st.error("Falha ao conectar. Verifique se o Script está publicado corretamente.")
                    else:
                        st.warning("Por favor, preencha o nome e a área do colaborador.")
                        
    except Exception as e:
        st.error("Não foi possível carregar a lista desta aba.")
        st.info("Verifique se o nome da aba no Sheets está idêntico ao selecionado.")

# --- BARRA LATERAL (ADMIN) ---
st.sidebar.header("Painel Analista")
senha = st.sidebar.text_input("Senha", type="password")
if senha == "1234":
    if st.sidebar.button("Verificar Fila de Pendentes"):
        try:
            df_p = pd.read_csv(get_sheet_url("Pendentes"))
            st.write("### 📂 Colaboradores Aguardando Inclusão")
            st.dataframe(df_p)
        except:
            st.sidebar.error("Aba 'Pendentes' não encontrada.")