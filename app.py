import streamlit as st
import pandas as pd
import requests
from datetime import datetime, date
import urllib.parse
import time
import io

# ... (Mantenha as funções get_sheet_url, buscar_senhas_db e verificar_liberacao_especial iguais)

# --- DENTRO DA VISÃO DO ADMIN ---
elif st.session_state.perfil == "Admin":
    t1, t2, t3, t4 = st.tabs(["Monitoramento", "Pendentes", "Ferramentas", "📊 Dashboard"])

    with t1:
        st.subheader("Envios de Hoje")
        hoje = datetime.now().strftime("%d/%m/%Y")
        
        try:
            # Carrega o histórico para verificar os horários de envio
            df_h_mon = pd.read_csv(get_sheet_url("Historico"))
            df_h_mon.columns = ["Data", "Hora", "Matricula", "Colaborador", "Lider", "Status", "HE", "Fretado", "Obs"]
            
            for l in LIDERES:
                # Filtra envios do líder no dia de hoje
                envios_lider = df_h_mon[(df_h_mon['Lider'] == l) & (df_h_mon['Data'] == hoje)]
                
                if not envios_lider.empty:
                    # Pega o horário do último registro enviado
                    ultimo_horario = envios_lider['Hora'].max()
                    st.success(f"✅ **{l}**: Concluído às {ultimo_horario}")
                else:
                    st.error(f"❌ **{l}**: Pendente")
        except:
            st.warning("⚠️ Sem dados no Histórico para monitoramento hoje.")

    # ... (Mantenha t2 e t3 iguais)

    with t4:
        st.subheader("📊 Dashboard de Performance e Absenteísmo")
        try:
            df_h = pd.read_csv(get_sheet_url("Historico"))
            if not df_h.empty:
                df_h.columns = ["Data", "Hora", "Matricula", "Colaborador", "Lider", "Status", "HE", "Fretado", "Obs"]
                
                # Converte a coluna Data para formato datetime para o filtro funcionar
                df_h['Data_DT'] = pd.to_datetime(df_h['Data'], format='%d/%m/%Y').dt.date

                # --- NOVO FILTRO DE PERÍODO ---
                col_f1, col_f2 = st.columns(2)
                with col_f1:
                    data_inicio = st.date_input("Data Início:", value=df_h['Data_DT'].min())
                with col_f2:
                    data_fim = st.date_input("Data Fim:", value=date.today())

                # Filtragem do DataFrame pelo período selecionado
                df_f = df_h[(df_h['Data_DT'] >= data_inicio) & (df_h['Data_DT'] <= data_fim)]

                if not df_f.empty:
                    # --- VISÃO POR LÍDER (Cálculo Corrigido por Dia) ---
                    daily_metrics = df_f.groupby(['Data', 'Lider']).agg(
                        Total_Colab=('Status', 'count'),
                        Faltas=('Status', lambda x: (x == 'FALTA').sum())
                    ).reset_index()
                    
                    dash_lider = daily_metrics.groupby('Lider').agg(
                        Media_Colaboradores=('Total_Colab', 'mean'),
                        Total_Faltas_Acumuladas=('Faltas', 'sum'),
                        Dias_Registrados=('Data', 'count')
                    ).reset_index()

                    dash_lider['% Absenteísmo'] = (dash_lider['Total_Faltas_Acumuladas'] / (dash_lider['Media_Colaboradores'] * dash_lider['Dias_Registrados']) * 100).round(2)

                    st.markdown(f"### 👥 Performance por Equipe ({data_inicio.strftime('%d/%m')} a {data_fim.strftime('%d/%m')})")
                    st.dataframe(dash_lider[['Lider', 'Media_Colaboradores', 'Total_Faltas_Acumuladas', '% Absenteísmo']], use_container_width=True)

                    st.divider()

                    # --- VISÃO POR COLABORADOR ---
                    st.markdown("### 👤 Assiduidade Individual no Período")
                    dash_colab = df_f.groupby(['Matricula', 'Colaborador', 'Lider']).agg(
                        Presencas=('Status', lambda x: (x == 'OK').sum()),
                        Faltas=('Status', lambda x: (x == 'FALTA').sum()),
                        HE_Total=('HE', lambda x: (x == 'Sim').sum())
                    ).reset_index()
                    
                    st.dataframe(dash_colab.sort_values('Faltas', ascending=False), use_container_width=True)
                else:
                    st.warning("Não há registros para o período selecionado.")
            else:
                st.info("Histórico vazio.")
        except Exception as e:
            st.error(f"Erro no Dashboard: {e}")
