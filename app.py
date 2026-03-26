import streamlit as st
import pandas as pd
import requests
import urllib.parse
import plotly.express as px
from io import BytesIO
from datetime import datetime

# 1. CONFIGURAÇÕES
st.set_page_config(page_title="Check-in & Performance | Nova Odessa", layout="wide")

# --- IDs DOS ARQUIVOS ---
ID_PLANILHA_PRESENCA = "1nYm2aRgruykh2YfXTcpCRuHGIqI0TtAFroMEk_p7Ij8"
ID_SHEETS_PROD = "1TR5oI_I4C9IA-QfUp0zaMmS4Dni1J8nG75Flxd1yguA" 

URL_SCRIPT_GOOGLE = "https://script.google.com/macros/s/AKfycbz3J-m4rTKD0Wkr58B2qDsGS81RwZl7-jt3HegpTBI5Fg1mHBJLzoHTvY4D2OW5ZXuClA/exec"
LIDERES = ["Carol", "Elisangela", "Lais Alves", "Leticia", "Renato", "Thiago"]
SENHA_ADMIN = "1234"

# --- FUNÇÕES ---
def get_csv_url(file_id, sheet_name):
    name_enc = urllib.parse.quote(sheet_name)
    return f"https://docs.google.com/spreadsheets/d/{file_id}/gviz/tq?tqx=out:csv&sheet={name_enc}"

# --- LÓGICA DE SESSÃO ---
if 'logado' not in st.session_state:
    st.session_state.update({'logado': False, 'usuario': None, 'perfil': None})

if not st.session_state.logado:
    st.title("🔒 Acesso - Grupo SC (Nova Odessa)")
    # ... (bloco de login omitido para brevidade, mantenha o seu atual)
    # [Login permanece igual ao anterior]
    u_sel = st.selectbox("Selecione seu nome:", ["--"] + LIDERES)
    if st.button("Entrar"): # Simplificado para teste
        st.session_state.update({'logado': True, 'usuario': "Admin", 'perfil': "Admin"})
        st.rerun()

else:
    # --- VISÃO ADMINISTRADOR ---
    if st.session_state.perfil == "Admin":
        t1, t2, t3 = st.tabs(["Monitoramento Diário", "Gestão e Comandos", "Performance"])

        with t1:
            st.write("### Status de Envio por Líder")
            try:
                url_c = get_csv_url(ID_PLANILHA_PRESENCA, "Controle")
                df_c = pd.read_csv(url_c)
                # Limpa nomes das colunas
                df_c.columns = df_c.columns.str.strip()
                
                for lider_nome in LIDERES:
                    # Busca ignorando espaços
                    info = df_c[df_c['Lider'].astype(str).str.strip() == lider_nome]
                    if not info.empty and "Preenchido" in str(info.iloc[0]['Status']):
                        st.write(f"✅ **{lider_nome}**: Entregue | {info.iloc[0]['Horario']}")
                    else:
                        st.write(f"⏳ **{lider_nome}**: Pendente | -")
            except Exception as e:
                st.info("Aguardando sincronização da planilha de controle...")

        with t2:
            # [Botões de Reset e Relatório permanecem iguais]
            st.write("### Comandos do Sistema")
            if st.button("🗑️ Resetar Presenças"):
                requests.post(URL_SCRIPT_GOOGLE, json={"tipo": "reset_presenca"})
                st.warning("Comando enviado!")

        with t3:
            st.write("### 📈 Produtividade com Metas")
            cf1, cf2 = st.columns(2)
            dep_escolhido = cf1.selectbox("Filtrar Depósito:", ["Todos", "102", "105", "107", "111", "302"])
            op = cf2.radio("Operação:", ["Conferência", "Picking"], horizontal=True)

            aba = "Conf" if op == "Conferência" else "Pick"
            meta_valor = 2000 if op == "Conferência" else 150
            
            try:
                url_p = get_csv_url(ID_SHEETS_PROD, aba)
                df_p = pd.read_csv(url_p)
                
                # --- LIMPEZA CRÍTICA ---
                df_p.columns = df_p.columns.str.strip() # Remove espaços dos títulos
                
                if not df_p.empty:
                    # Localiza a coluna de Depósito independente de como o Sheets a nomeou
                    col_dep = [c for c in df_p.columns if 'Dep' in c]
                    
                    if col_dep and dep_escolhido != "Todos":
                        c_name = col_dep[0]
                        # Converte coluna e filtro para string pura e limpa
                        df_p[c_name] = df_p[c_name].astype(str).str.replace('.0', '', regex=False).str.strip()
                        df_p = df_p[df_p[c_name] == str(dep_escolhido)]

                    u_col = df_p.columns[0]
                    ignorar = [u_col, 'Depósito', 'Total Geral', 'Total', 'Soma de Total']
                    h_cols = [c for c in df_p.columns if c not in ignorar and not str(c).startswith('Unnamed')]

                    if h_cols:
                        df_m = df_p.melt(id_vars=[u_col], value_vars=h_cols, var_name='Hora', value_name='Qtd')
                        df_m['Qtd'] = pd.to_numeric(df_m['Qtd'], errors='coerce').fillna(0)

                        # Gráfico Ranking
                        resumo = df_m.groupby(u_col)['Qtd'].sum().reset_index()
                        fig_rank = px.bar(resumo, x=u_col, y='Qtd', text_auto='.0f', title=f"Performance {op}")
                        fig_rank.update_traces(textposition="outside")
                        st.plotly_chart(fig_rank, use_container_width=True)

                        # Gráfico Fluxo com Meta
                        fluxo = df_m.groupby('Hora')['Qtd'].sum().reset_index()
                        fig_fluxo = px.line(fluxo, x='Hora', y='Qtd', markers=True, title=f"Fluxo Horário (Meta: {meta_valor})")
                        fig_fluxo.add_hline(y=meta_valor, line_dash="dash", line_color="red")
                        st.plotly_chart(fig_fluxo, use_container_width=True)
                    else:
                        st.info("Dados filtrados, mas sem colunas de horários para exibir.")
                else:
                    st.warning("Nenhum dado encontrado para os filtros selecionados.")
            except Exception as e:
                st.error(f"Erro ao processar aba {aba}. Verifique se a planilha está aberta.")
