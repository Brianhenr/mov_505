# app.py
# Refatoração da aplicação Streamlit
# Principais melhorias:
# - Busca por texto antes do selectbox
# - Filtragem limitada a 50 resultados
# - Código organizado em funções
# - Mantém a lógica original de gravação/cancelamento

import os
from datetime import datetime

import pandas as pd
import streamlit as st

PASTA_BASE = os.path.dirname(os.path.abspath(__file__))
PASTA_DOCUMENTOS = os.path.join(PASTA_BASE, "documentos")
ARQUIVO_SAIDA = os.path.join(PASTA_DOCUMENTOS, "registros_saida.csv")


@st.cache_data
def carregar_dados():
    df_fabrica = pd.read_excel(
        os.path.join(PASTA_DOCUMENTOS, "planilha_fabrica.xlsx"),
        sheet_name="CONTROLE LISTAS",
        header=1,
    )

    df_projetos = df_fabrica[
        df_fabrica["STATUS"].isin(["LISTA ENTREGUE", "LINHA","MONTADO","APONTADO"])
    ].copy()

    df_projetos["PROJETO"] = df_projetos["PROJETO"].astype(str).str.strip()
    df_projetos["LOTE"] = df_projetos["LOTE"].astype(str).str.strip()
    df_projetos["NOME_PROJETO"] = (
        df_projetos["PROJETO"] + " LOTE " + df_projetos["LOTE"]
    )
    df_projetos["BUSCA"] = (
        df_projetos["NOME_PROJETO"].str.upper()
        + " "
        + df_projetos["TAT"].astype(str).str.upper()
    )

    df_produtos = pd.read_excel(
        os.path.join(PASTA_DOCUMENTOS, "produtos.xlsx"),
        header=1,
    )

    df_produtos["Codigo"] = df_produtos["Codigo"].astype(str).str.strip()
    df_produtos["Descricao"] = df_produtos["Descricao"].astype(str).str.strip()

    df_produtos["BUSCA"] = (
        df_produtos["Codigo"] + " " + df_produtos["Descricao"]
    ).str.upper()

    filtrado = df_produtos[
        df_produtos["Codigo"].str.startswith(("10.", "27."))
    ].copy()

    filtrado["EXIBICAO"] = (
        filtrado["Codigo"] + " - " + filtrado["Descricao"]
    )

    return df_projetos, df_produtos, filtrado


def filtrar(df, coluna, texto, limite=50):
    if texto:
        return df[df[coluna].str.contains(texto.upper(), na=False)].head(limite)
    return df.head(limite)


def gravar(registro):
    if os.path.exists(ARQUIVO_SAIDA):
        registro.to_csv(ARQUIVO_SAIDA, mode="a", header=False, index=False)
    else:
        registro.to_csv(ARQUIVO_SAIDA, mode="w", header=True, index=False)


def desfazer():
    if not os.path.exists(ARQUIVO_SAIDA):
        st.info("Nenhum registro encontrado.")
        return

    df = pd.read_csv(ARQUIVO_SAIDA)

    if df.empty:
        st.info("Arquivo vazio.")
        return

    if df.iloc[-1]["STATUS_REGISTRO"] == "ATIVO":
        df.at[df.index[-1], "STATUS_REGISTRO"] = "CANCELADO"
        df.to_csv(ARQUIVO_SAIDA, index=False)
        st.warning("Último registro cancelado.")
    else:
        st.info("Último registro já estava cancelado.")


df_proj, df_prod, df_filtrado = carregar_dados()

st.title("Sistema de Requisição Extra - 505")

busca_proj = st.text_input("Buscar projeto")
proj_df = filtrar(df_proj, "BUSCA", busca_proj)

projeto = st.selectbox(
    "Projeto",
    proj_df["NOME_PROJETO"].tolist(),
    index=None,
)

st.divider()

manual = st.checkbox("⚠ Material fora do padrão")

if manual:
    material = st.text_input("Código do material")
else:
    busca_mat = st.text_input("Buscar material (código ou descrição)")
    mat_df = filtrar(df_filtrado, "BUSCA", busca_mat)
    material = st.selectbox(
        "Material",
        mat_df["EXIBICAO"].tolist(),
        index=None,
    )

st.divider()

resp = st.selectbox(
    "Responsável",
    ["Eduardo", "Chico Louco", "Mairo", "Natan", "Odair", "Outro..."],
    index=None,
)

qtd = st.number_input("Quantidade", min_value=1, step=1)

c1, c2 = st.columns(2)

with c1:
    if st.button("Gravar", use_container_width=True):
        if not (projeto and material and resp):
            st.error("Preencha todos os campos.")
        else:
            if manual:
                codigo = material.strip()
                if codigo not in df_prod["Codigo"].tolist():
                    st.error("Código inexistente.")
                    st.stop()
            else:
                codigo = material.split(" - ")[0]

            projeto_info = df_proj[df_proj["NOME_PROJETO"] == projeto]

            if projeto_info.empty:
                st.error("Projeto não encontrado.")
                st.stop()

            tat = projeto_info.iloc[0]["TAT"]

            reg = pd.DataFrame([{
                "DATA_HORA": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                "TAT": tat,
                "PROJETO_NOME": projeto,
                "CODIGO_MATERIAL": codigo,
                "QUANTIDADE": qtd,
                "RESPONSAVEL": resp,
                "STATUS_REGISTRO": "ATIVO"
            }])

            gravar(reg)
            st.success("Registro salvo.")

with c2:
    if st.button("Desfazer último", use_container_width=True):
        desfazer()
