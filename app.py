import streamlit as st
import pandas as pd
from datetime import datetime

# Configuração visual
st.set_page_config(page_title="Check-in Logística | Grupo SC", layout="centered")

# Nome do arquivo que está no seu GitHub
ARQUIVO_EXCEL = "Lista Presença.xlsx"

def carregar_dados():
    try:
        return pd.ExcelFile(ARQUIVO_EXCEL)
    except Exception as e:
        st.error(f"Erro ao carregar a planilha '{ARQUIVO_EXCEL}'. Verifique se o nome está correto no GitHub.")
        return None

xls = carregar_dados()

if xls:
    abas_lideres = [s for s in xls.sheet_names if s != 'Pendentes de Inclusão']
    
    st.title("📋 Lista de Presença Digital")
    st.subheader("Logística - Terceiro Turno")

    lider = st.selectbox("Selecione seu nome:", ["-- Selecione --"] + abas_lideres)

    if lider != "-- Selecione --":
        df = pd.read_excel(xls, sheet_name=lider)
        
        with st.form("form_presenca"):
            st.write(f"### Equipe: {lider}")
            dados_finais = []
            
            for i, row in df.iterrows():
                c1, c2, c3 = st.columns([3, 1, 3])
                c1.write(f"**{row['Colaborador']}**")
                presenca = c2.checkbox("Presença", key=f"p_{i}")
                obs = c3.text_input("Obs/Justificativa", key=f"o_{i}")
                
                dados_finais.append({
                    "Data": datetime.now().strftime("%d/%m/%Y"),
                    "Lider": lider,
                    "Colaborador": row['Colaborador'],
                    "Presente": "SIM" if presenca else "NÃO",
                    "Observacao": obs
                })
            
            st.markdown("---")
            st.write("#### ➕ Solicitar Inclusão")
            novo_nome = st.text_input("Nome do novo colaborador")
            nova_area = st.text_input("Área")

            if st.form_submit_button("✅ SALVAR CHAMADA"):
                resumo = pd.DataFrame(dados_finais)
                st.success("Presença registrada com sucesso!")
                
                if novo_nome:
                    st.warning(f"Solicitação para {novo_nome} enviada!")
                
                # Botão para você baixar o log do dia
                csv = resumo.to_csv(index=False).encode('utf-8-sig')
                st.download_button("📥 Baixar Relatório (Admin)", csv, f"Chamada_{lider}.csv", "text/csv")