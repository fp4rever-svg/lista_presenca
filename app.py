import streamlit as st
import pandas as pd
import os
from datetime import datetime

st.set_page_config(page_title="Check-in Logística | Grupo SC", layout="centered")

# --- NOME DO ARQUIVO (DEVE SER IGUAL AO GITHUB) ---
ARQUIVO_EXCEL = "Lista_Colab.xlsx"

# Função para ajudar a gente a debugar se o arquivo sumiu
def verificar_arquivos():
    arquivos_no_servidor = os.listdir('.')
    if ARQUIVO_EXCEL not in arquivos_no_servidor:
        st.error(f"❌ Arquivo '{ARQUIVO_EXCEL}' não encontrado no servidor.")
        st.write("Arquivos detectados no GitHub:", arquivos_no_servidor)
        return False
    return True

@st.cache_data
def carregar_dados():
    if verificar_arquivos():
        try:
            return pd.ExcelFile(ARQUIVO_EXCEL)
        except Exception as e:
            st.error(f"Erro ao ler o Excel: {e}")
            return None
    return None

xls = carregar_dados()

if xls:
    # Filtramos as abas (escondendo a de Pendentes)
    abas_lideres = [s for s in xls.sheet_names if s != 'Pendentes de Inclusão']
    
    st.title("📋 Lista de Presença Digital")
    st.caption("Unidade Sumaré - Grupo SC")

    # --- BARRA LATERAL ---
    st.sidebar.header("Configurações")
    senha_admin = st.sidebar.text_input("Senha do Analista", type="password")
    
    lider = st.selectbox("Selecione seu nome (Líder):", ["-- Selecione --"] + abas_lideres)

    if lider != "-- Selecione --":
        df = pd.read_excel(xls, sheet_name=lider)
        
        with st.form("form_presenca"):
            st.write(f"### Chamada: {lider}")
            dados_finais = []
            
            for i, row in df.iterrows():
                c1, c2, c3 = st.columns([3, 1, 3])
                c1.write(f"**{row['Colaborador']}**")
                presenca = c2.checkbox("Presença", key=f"p_{i}")
                obs = c3.text_input("Justificativa", key=f"o_{i}")
                
                dados_finais.append({
                    "Data": datetime.now().strftime("%d/%m/%Y"),
                    "Lider": lider,
                    "Colaborador": row['Colaborador'],
                    "Presente": "SIM" if presenca else "NÃO",
                    "Observacao": obs
                })
            
            st.markdown("---")
            st.write("#### ➕ Solicitar Inclusão")
            novo_nome = st.text_input("Nome Completo")
            nova_area = st.text_input("Área/Setor")

            if st.form_submit_button("✅ FINALIZAR CHAMADA"):
                resumo = pd.DataFrame(dados_finais)
                if novo_nome:
                    resumo = pd.concat([resumo, pd.DataFrame([{
                        "Data": datetime.now().strftime("%d/%m/%Y"),
                        "Lider": lider,
                        "Colaborador": f"SOLICITAÇÃO: {novo_nome}",
                        "Presente": "PENDENTE",
                        "Observacao": f"Setor: {nova_area}"
                    }])], ignore_index=True)
                
                st.success("Processado!")
                csv = resumo.to_csv(index=False).encode('utf-8-sig')
                st.download_button("📥 Baixar Relatório", csv, f"Chamada_{lider}.csv", "text/csv")

    # --- ÁREA ADMIN ---
    if senha_admin == "1234":
        if st.sidebar.button("Ver Pendentes"):
            df_pendentes = pd.read_excel(xls, sheet_name='Pendentes de Inclusão')
            st.write("### 📂 Aba Pendentes")
            st.dataframe(df_pendentes)
