import streamlit as st
import pandas as pd
import os
from datetime import datetime

PASTA_BASE = os.path.dirname(os.path.abspath(__file__))
PASTA_DOCUMENTOS = os.path.join(PASTA_BASE, "documentos")

ARQUIVO_SAIDA = os.path.join(PASTA_DOCUMENTOS, "registros_saida.csv")

@st.cache_data
def carregar_dados():
    try:
        # 1. Carrega Fábrica
        df_fabrica = pd.read_excel(os.path.join(PASTA_DOCUMENTOS, "planilha_fabrica.xlsx"), sheet_name="CONTROLE LISTAS", header=1)
        df_ativos = df_fabrica[df_fabrica["STATUS"].isin(["LISTA ENTREGUE", "LINHA"])].copy()
        df_ativos["NOME_PROJETO"] = df_ativos["PROJETO"].astype(str) + " LOTE " + df_ativos["LOTE"].astype(str)
        
        # 2. Carrega Produtos (Base Completa para validação)
        df_produtos_completo = pd.read_excel(os.path.join(PASTA_DOCUMENTOS, "produtos.xlsx"), header=1)
        
        # 3. Cria a Base Filtrada (Apenas 10. e 27. para o Dropdown rápido)
        filtro_codigo = df_produtos_completo["Codigo"].astype(str).str.startswith(("10.", "27."))
        df_produtos_filtrado = df_produtos_completo[filtro_codigo].copy()
        df_produtos_filtrado["EXIBICAO"] = df_produtos_filtrado["Codigo"].astype(str) + " - " + df_produtos_filtrado["Descricao"].astype(str)
        
        return df_ativos, df_produtos_completo, df_produtos_filtrado

    except Exception as e:
        st.error(f"Erro estrutural ao carregar bases: {e}")
        st.stop()

df_projetos, df_produtos_completo, df_produtos_filtrado = carregar_dados()

st.title("Sistema de Requisição Extra")

projeto_selecionado = st.selectbox(
    "1. Projeto:", 
    df_projetos["NOME_PROJETO"].tolist(), 
    index=None, 
    placeholder="Clique ou digite para buscar o projeto..."
)

st.write("---")
usar_urgencia = st.checkbox("⚠️ Material fora do padrão (Digitação Manual)")

if usar_urgencia:
    material_selecionado = st.text_input("2. Digite o código EXATO do material:")
else:
    material_selecionado = st.selectbox(
        "2. Material (Somente 10. e 27.):", 
        df_produtos_filtrado["EXIBICAO"].tolist(), 
        index=None, 
        placeholder="Digite o código ou a descrição..."
    )
st.write("---")

lista_responsaveis = ["Eduardo", "Chico Louco", "Mairo", "Natan", "Odair", "Outro..."]
responsavel_selecionado = st.selectbox(
    "3. Responsável pela retirada:", 
    lista_responsaveis, 
    index=None, 
    placeholder="Quem está retirando o material?"
)

quantidade = st.number_input("4. Quantidade:", min_value=1, step=1)

col1, col2 = st.columns(2)

with col1:
    if st.button("Gravar Saída", use_container_width=True):
        if not projeto_selecionado or not material_selecionado or not responsavel_selecionado:
            st.error("Bloqueado: Preencha todos os campos antes de gravar.")
        else:
            if usar_urgencia:
                codigo_final = material_selecionado.strip() 
                codigos_validos = df_produtos_completo["Codigo"].astype(str).tolist()
                if codigo_final not in codigos_validos:
                    st.error(f"ERRO: O código '{codigo_final}' não existe no Protheus. Verifique a digitação.")
                    st.stop()
            else:
                codigo_final = material_selecionado.split(" - ")[0]
            
            tat_exata = df_projetos[df_projetos["NOME_PROJETO"] == projeto_selecionado]["TAT"].values[0]
            
            novo_registro = pd.DataFrame([{
                "DATA_HORA": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                "TAT": tat_exata,
                "PROJETO_NOME": projeto_selecionado,
                "CODIGO_MATERIAL": codigo_final,
                "QUANTIDADE": quantidade,
                "RESPONSAVEL": responsavel_selecionado,
                "STATUS_REGISTRO": "ATIVO" 
            }])
            
            if os.path.exists(ARQUIVO_SAIDA):
                novo_registro.to_csv(ARQUIVO_SAIDA, mode='a', header=False, index=False)
            else:
                novo_registro.to_csv(ARQUIVO_SAIDA, mode='w', header=True, index=False)
                
            st.success(f"Salvo! (Material: {codigo_final})")

with col2:
    if st.button("Desfazer Último Registro", use_container_width=True):
        if os.path.exists(ARQUIVO_SAIDA):
            df_saida = pd.read_csv(ARQUIVO_SAIDA)
            if not df_saida.empty:
                if df_saida.iloc[-1]["STATUS_REGISTRO"] == "ATIVO":
                    df_saida.at[df_saida.index[-1], "STATUS_REGISTRO"] = "CANCELADO"
                    df_saida.to_csv(ARQUIVO_SAIDA, index=False)
                    st.warning("O último registro foi marcado como CANCELADO.")
                else:
                    st.info("O último registro já estava cancelado.")
            else:
                st.info("A base de registros está vazia.")
        else:
            st.info("Nenhum arquivo de registro encontrado.")