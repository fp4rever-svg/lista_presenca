import streamlit as st
import pandas as pd
from datetime import datetime
import urllib.parse  # Biblioteca para limpar o link

st.set_page_config(page_title="Check-in Logística | Grupo SC", layout="centered")

# --- CONFIGURAÇÃO GOOGLE SHEETS ---
SHEET_ID = "1nYm2aRgruykh2YfXTcpCRuHGIqI0TtAFroMEk_p7Ij8"

# Lista das abas (mantenha exatamente como no Sheets)
ABAS_LIDERES = ["Paula Toledo", "Fabio Santos"] 

st.title("📋 Lista de Presença Digital")
st.caption("Conectado via Google Sheets - Unidade Sumaré")

# --- BARRA LATERAL ---
st.sidebar.header("Painel Analista")
senha = st.sidebar.text_input("Senha de Acesso", type="password")

# --- SELEÇÃO DO LÍDER ---
lider = st.selectbox("Selecione seu nome (Líder):", ["-- Selecione --"] + ABAS_LIDERES)

if lider != "-- Selecione --":
    try:
        # 🟢 AQUI ESTÁ A CORREÇÃO:
        # O quote() limpa o nome do líder para não dar erro de URL
        lider_limpo = urllib.parse.quote(lider)
        url_dados = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={lider_limpo}"
        
        # Lê os dados
        df = pd.read_csv(url_dados)
        
        with st.form("form_chamada"):
            st.write(f"### Equipe: {lider}")
            dados_finais = []
            
            for i, row in df.iterrows():
                c1, c2, c3 = st.columns([3, 1, 3])
                c1.write(f"**{row['Colaborador']}**")
                presenca = c2.checkbox("Presente", key=f"p_{i}")
                obs = c3.text_input("Obs/Justificativa", key=f"o_{i}", placeholder="Opcional")
                
                dados_finais.append({
                    "Data": datetime.now().strftime("%d/%m/%Y"),
                    "Hora": datetime.now().strftime("%H:%M:%S"),
                    "Lider": lider,
                    "Colaborador": row['Colaborador'],
                    "Status": "PRESENTE" if presenca else "FALTA",
                    "Observacao": obs
                })
            
            st.markdown("---")
            if st.form_submit_button("✅ FINALIZAR CHAMADA"):
                df_resumo = pd.DataFrame(dados_finais)
                st.success(f"Chamada de {lider} processada!")
                
                csv = df_resumo.to_csv(index=False).encode('utf-8-sig')
                st.download_button(
                    label="📥 Baixar Log e Enviar ao Analista",
                    data=csv,
                    file_name=f"Presenca_{lider.replace(' ', '_')}_{datetime.now().strftime('%d_%m')}.csv",
                    mime="text/csv"
                )

    except Exception as e:
        st.error(f"Erro ao carregar os dados de {lider}.")
        st.info("Dica: Verifique se o nome da aba no Sheets é EXATAMENTE igual ao nome na lista do código.")

# --- VISÃO DO ANALISTA ---
if senha == "1234":
    if st.sidebar.button("Ver Aba Pendentes"):
        try:
            url_p = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Pendentes"
            df_p = pd.read_csv(url_p)
            st.write("### 📂 Colaboradores Pendentes")
            st.dataframe(df_p)
        except:
            st.error("Aba 'Pendentes' não encontrada.")
