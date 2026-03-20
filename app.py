import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Check-in Logística | Grupo SC", layout="centered")

ARQUIVO_EXCEL = "Lista Presença.xlsx"

# Função para carregar a planilha
@st.cache_data
def carregar_dados():
    try:
        return pd.ExcelFile(ARQUIVO_EXCEL)
    except:
        return None

xls = carregar_dados()

if xls:
    # 1. Filtramos apenas as abas dos líderes (Escondemos 'Pendentes de Inclusão')
    abas_lideres = [s for s in xls.sheet_names if s != 'Pendentes de Inclusão']
    
    st.title("📋 Lista de Presença Digital")
    st.caption("Distribuição Farmacêutica - Terceiro Turno")

    # --- BARRA LATERAL (MODO ADMIN) ---
    st.sidebar.header("Configurações")
    senha_admin = st.sidebar.text_input("Acesso Analista (Senha)", type="password")
    
    # --- INTERFACE DO LÍDER ---
    lider = st.selectbox("Selecione seu nome (Líder):", ["-- Selecione --"] + abas_lideres)

    if lider != "-- Selecione --":
        df = pd.read_excel(xls, sheet_name=lider)
        
        with st.form("form_presenca"):
            st.write(f"### Chamada: {lider}")
            dados_finais = []
            
            for i, row in df.iterrows():
                c1, c2, c3 = st.columns([3, 1, 3])
                c1.write(f"**{row['Colaborador']}**")
                presenca = c2.checkbox("Presente", key=f"p_{i}")
                obs = c3.text_input("Justificativa", key=f"o_{i}", placeholder="Opcional")
                
                dados_finais.append({
                    "Data": datetime.now().strftime("%d/%m/%Y"),
                    "Hora": datetime.now().strftime("%H:%M:%S"),
                    "Lider": lider,
                    "Colaborador": row['Colaborador'],
                    "Presente": "SIM" if presenca else "NÃO",
                    "Observacao": obs
                })
            
            # Seção de inclusão (O líder vê, mas os dados só aparecem no log final)
            st.markdown("---")
            st.write("#### ➕ Solicitar Inclusão de Colaborador")
            novo_nome = st.text_input("Nome do novo colaborador")
            nova_area = st.text_input("Área/Setor")

            if st.form_submit_button("✅ FINALIZAR E GERAR RELATÓRIO"):
                resumo = pd.DataFrame(dados_finais)
                
                # Se houver solicitação de inclusão, adicionamos uma linha extra no log
                if novo_nome:
                    resumo = pd.concat([resumo, pd.DataFrame([{
                        "Data": datetime.now().strftime("%d/%m/%Y"),
                        "Hora": datetime.now().strftime("%H:%M:%S"),
                        "Lider": lider,
                        "Colaborador": f"SOLICITAÇÃO: {novo_nome}",
                        "Presente": "PENDENTE",
                        "Observacao": f"Área: {nova_area}"
                    }])], ignore_index=True)
                
                st.success("Chamada processada com sucesso!")
                
                # O líder baixa o arquivo e te envia
                csv = resumo.to_csv(index=False).encode('utf-8-sig')
                st.download_button(
                    label="📥 Clique aqui para baixar o Log e enviar ao Analista",
                    data=csv,
                    file_name=f"Presenca_{lider}_{datetime.now().strftime('%d%m')}.csv",
                    mime="text/csv"
                )

    # --- VISÃO DO ADMINISTRADOR (VOCÊ) ---
    # Só aparece se você digitar a senha correta (ex: 'admin123')
    if senha_admin == "1234": # Altere para a senha que desejar
        st.sidebar.markdown("---")
        st.sidebar.subheader("Área do Analista")
        
        if st.sidebar.button("Visualizar Pendentes"):
            df_pendentes = pd.read_excel(xls, sheet_name='Pendentes de Inclusão')
            st.write("### 📂 Colaboradores Pendentes de Inclusão (Base)")
            st.dataframe(df_pendentes)