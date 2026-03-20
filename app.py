import streamlit as st
import pandas as pd
import os
from datetime import datetime

st.set_page_config(page_title="Check-in Logística | Grupo SC", layout="centered")

# --- AJUSTE DINÂMICO DE CAMINHO ---
# O comando os.path.join garante que ele procure na mesma pasta do script
diretorio_atual = os.path.dirname(os.path.abspath(__file__))
ARQUIVO_EXCEL = os.path.join(diretorio_atual, "Lista_Colab.xlsx")

@st.cache_data
def carregar_dados():
    if os.path.exists(ARQUIVO_EXCEL):
        try:
            return pd.ExcelFile(ARQUIVO_EXCEL)
        except Exception as e:
            st.error(f"Erro ao ler o arquivo: {e}")
            return None
    else:
        st.error(f"❌ O arquivo '{ARQUIVO_EXCEL}' não foi encontrado.")
        st.info(f"Arquivos na pasta atual: {os.listdir(diretorio_atual)}")
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
                
                st.success("Chamada processada com sucesso!")
                csv = resumo.to_csv(index=False).encode('utf-8-sig')
                st.download_button("📥 Baixar Relatório", csv, f"Chamada_{lider}.csv", "text/csv")

    # --- ÁREA ADMIN ---
    if senha_admin == "1234":
        if st.sidebar.button("Ver Pendentes na Base"):
            df_pendentes = pd.read_excel(xls, sheet_name='Pendentes de Inclusão')
            st.write("### 📂 Colaboradores Pendentes")
            st.dataframe(df_pendentes)
