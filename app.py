import streamlit as st
import pandas as pd
from datetime import datetime

# Configuração da página
st.set_page_config(page_title="Check-in Logística | Grupo SC", layout="centered")

# --- AJUSTE DO NOME DO ARQUIVO ---
# Certifique-se de que no GitHub o arquivo se chama exatamente Lista_Colab.xlsx
ARQUIVO_EXCEL = "Lista_Colab.xlsx"

@st.cache_data
def carregar_dados():
    try:
        return pd.ExcelFile(ARQUIVO_EXCEL)
    except Exception as e:
        st.error(f"Erro: Não encontrei o arquivo '{ARQUIVO_EXCEL}' no GitHub.")
        st.info("Verifique se o arquivo foi enviado para a mesma pasta do app.py")
        return None

xls = carregar_dados()

if xls:
    # Filtramos as abas dos líderes (Escondendo a aba de Pendentes)
    abas_lideres = [s for s in xls.sheet_names if s != 'Pendentes de Inclusão']
    
    st.title("📋 Lista de Presença Digital")
    st.caption("Logística - Grupo SC")

    # --- BARRA LATERAL (ACESSO ANALISTA) ---
    st.sidebar.header("Configurações")
    senha_admin = st.sidebar.text_input("Senha do Analista", type="password")
    
    # --- INTERFACE DO LÍDER ---
    lider = st.selectbox("Selecione seu nome (Líder):", ["-- Selecione --"] + abas_lideres)

    if lider != "-- Selecione --":
        df = pd.read_excel(xls, sheet_name=lider)
        
        with st.form("form_presenca"):
            st.write(f"### Chamada: {lider}")
            dados_finais = []
            
            for i, row in df.iterrows():
                # Criamos colunas para o layout ficar organizado
                c1, c2, c3 = st.columns([3, 1, 3])
                c1.write(f"**{row['Colaborador']}**")
                presenca = c2.checkbox("Presença", key=f"p_{i}")
                obs = c3.text_input("Justificativa", key=f"o_{i}", placeholder="Se houver falta...")
                
                dados_finais.append({
                    "Data": datetime.now().strftime("%d/%m/%Y"),
                    "Hora": datetime.now().strftime("%H:%M:%S"),
                    "Lider": lider,
                    "Colaborador": row['Colaborador'],
                    "Presente": "SIM" if presenca else "NÃO",
                    "Observacao": obs
                })
            
            st.markdown("---")
            st.write("#### ➕ Solicitar Inclusão de Colaborador")
            novo_nome = st.text_input("Nome Completo")
            nova_area = st.text_input("Área/Setor")

            if st.form_submit_button("✅ FINALIZAR CHAMADA"):
                resumo = pd.DataFrame(dados_finais)
                
                # Adiciona a solicitação no log se houver
                if novo_nome:
                    nova_linha = {
                        "Data": datetime.now().strftime("%d/%m/%Y"),
                        "Hora": datetime.now().strftime("%H:%M:%S"),
                        "Lider": lider,
                        "Colaborador": f"SOLICITAÇÃO: {novo_nome}",
                        "Presente": "PENDENTE",
                        "Observacao": f"Setor: {nova_area}"
                    }
                    resumo = pd.concat([resumo, pd.DataFrame([nova_linha])], ignore_index=True)
                
                st.success("Chamada processada!")
                
                # Download do CSV para o líder te enviar
                csv = resumo.to_csv(index=False).encode('utf-8-sig')
                st.download_button(
                    label="📥 Baixar Log de Presença",
                    data=csv,
                    file_name=f"Chamada_{lider}_{datetime.now().strftime('%d_%m')}.csv",
                    mime="text/csv"
                )

    # --- ÁREA RESTRITA (PARA VOCÊ) ---
    if senha_admin == "1234": # Pode mudar essa senha aqui
        st.sidebar.success("Acesso Liberado!")
        if st.sidebar.button("Ver Pendentes na Base"):
            st.markdown("---")
            st.write("### 📂 Colaboradores na aba 'Pendentes de Inclusão'")
            df_pendentes = pd.read_excel(xls, sheet_name='Pendentes de Inclusão')
            st.dataframe(df_pendentes)