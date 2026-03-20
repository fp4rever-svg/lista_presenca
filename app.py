import streamlit as st
import pandas as pd
import os
from datetime import datetime

# Configuração da página
st.set_page_config(page_title="Check-in Logística | Grupo SC", layout="centered")

# --- NOME DO ARQUIVO SIMPLIFICADO ---
ARQUIVO_EXCEL = "lista.xlsx"

@st.cache_data
def carregar_dados():
    # Verifica se o arquivo existe na pasta
    if os.path.exists(ARQUIVO_EXCEL):
        try:
            return pd.ExcelFile(ARQUIVO_EXCEL)
        except Exception as e:
            st.error(f"Erro ao ler o arquivo: {e}")
            return None
    else:
        st.error(f"❌ O arquivo '{ARQUIVO_EXCEL}' não foi encontrado no GitHub.")
        st.info(f"Arquivos detectados: {os.listdir('.')}")
        return None

xls = carregar_dados()

if xls:
    # Filtramos as abas dos líderes (Escondendo a aba de Pendentes)
    # Certifique-se que o nome da aba na planilha seja exatamente 'Pendentes de Inclusão'
    abas_lideres = [s for s in xls.sheet_names if s != 'Pendentes de Inclusão']
    
    st.title("📋 Lista de Presença Digital")
    st.caption("Logística - Unidade Sumaré")

    # --- BARRA LATERAL (ACESSO ANALISTA) ---
    st.sidebar.header("Configurações")
    senha_admin = st.sidebar.text_input("Senha do Analista", type="password")
    
    # --- INTERFACE DO LÍDER ---
    lider = st.selectbox("Selecione seu nome (Líder):", ["-- Selecione --"] + abas_lideres)

    if lider != "-- Selecione --":
        # Lê a aba do líder selecionado
        df = pd.read_excel(xls, sheet_name=lider)
        
        with st.form("form_presenca"):
            st.write(f"### Chamada: {lider}")
            dados_finais = []
            
            for i, row in df.iterrows():
                # Layout em colunas: Nome | Checkbox | Observação
                c1, c2, c3 = st.columns([3, 1, 3])
                c1.write(f"**{row['Colaborador']}**")
                presenca = c2.checkbox("Presente", key=f"p_{i}")
                obs = c3.text_input("Justificativa/Obs", key=f"o_{i}", placeholder="Opcional")
                
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
            novo_nome = st.text_input("Nome Completo do Novo Colaborador")
            nova_area = st.text_input("Área/Setor Destino")

            if st.form_submit_button("✅ FINALIZAR E GERAR RELATÓRIO"):
                resumo = pd.DataFrame(dados_finais)
                
                # Se houver solicitação de inclusão, adiciona ao log
                if novo_nome:
                    nova_linha = {
                        "Data": datetime.now().strftime("%d/%m/%Y"),
                        "Hora": datetime.now().strftime("%H:%M:%S"),
                        "Lider": lider,
                        "Colaborador": f"SOLICITAÇÃO: {novo_nome}",
                        "Presente": "PENDENTE",
                        "Observacao": f"Área: {nova_area}"
                    }
                    resumo = pd.concat([resumo, pd.DataFrame([nova_linha])], ignore_index=True)
                
                st.success("Chamada processada com sucesso!")
                
                # Botão de download para o líder baixar e te enviar
                csv = resumo.to_csv(index=False).encode('utf-8-sig')
                st.download_button(
                    label="📥 Baixar Log de Presença",
                    data=csv,
                    file_name=f"Presenca_{lider}_{datetime.now().strftime('%d%m')}.csv",
                    mime="text/csv"
                )

    # --- ÁREA RESTRITA (PARA VOCÊ) ---
    if senha_admin == "1234": # Sua senha de acesso
        st.sidebar.success("Acesso Analista Liberado!")
        if st.sidebar.button("Ver Pendentes na Base"):
            st.markdown("---")
            st.write("### 📂 Dados da aba 'Pendentes de Inclusão'")
            try:
                df_pendentes = pd.read_excel(xls, sheet_name='Pendentes de Inclusão')
                st.dataframe(df_pendentes)
            except:
                st.warning("Aba 'Pendentes de Inclusão' não encontrada na planilha.")
