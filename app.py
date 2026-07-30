import os
import uuid
import pandas as pd
import streamlit as st
from database import db

# ==========================================
# SOLUÇÃO 3: ACESSIBILIDADE E LAYOUT MOBILE
# ==========================================
st.set_page_config(
    page_title="Sistema 505", 
    layout="centered", # Mantém a interface ideal para telas de celular/coletor
    initial_sidebar_state="collapsed"
)

# Injeção de CSS para aumentar legibilidade para PCDs e facilitar o toque em mobile
st.markdown("""
    <style>
    /* Aumenta a fonte geral do aplicativo */
    html, body, [class*="css"] {
        font-size: 18px !important;
    }
    /* Aumenta a altura dos botões para facilitar o toque na tela */
    .stButton>button {
        min-height: 60px;
        font-weight: bold;
        font-size: 18px !important;
    }
    /* Aumenta o tamanho das caixas de seleção */
    div[data-baseweb="select"] {
        font-size: 18px !important;
    }
    </style>
""", unsafe_allow_html=True)


# Cache ajustado para leitura rápida do banco de dados na nuvem
@st.cache_data(ttl=600) 
def carregar_dados():
    # 1. Carrega e filtra os projetos (Mantido como estava)
    try:
        res_proj = db.table("projetos").select("*").execute()
        df_fabrica = pd.DataFrame(res_proj.data)
        
        if not df_fabrica.empty:
            df_fabrica = df_fabrica.rename(columns={
                "projeto": "PROJETO", "lote": "LOTE", "nome_projeto": "NOME_PROJETO", 
                "tat": "TAT", "status": "STATUS"
            })
            
            df_projetos = df_fabrica[df_fabrica["STATUS"].isin(["LISTA ENTREGUE", "LINHA", "MONTADO", "APONTADO"])].copy()
            df_projetos["PROJETO"] = df_projetos["PROJETO"].astype(str).str.strip()
            df_projetos["LOTE"] = df_projetos["LOTE"].astype(str).str.strip()
            df_projetos["NOME_PROJETO"] = df_projetos["PROJETO"] + " LOTE " + df_projetos["LOTE"]
            df_projetos["BUSCA"] = df_projetos["NOME_PROJETO"].str.upper() + " " + df_projetos["TAT"].astype(str).str.upper()
        else:
            df_projetos = pd.DataFrame(columns=["PROJETO", "LOTE", "NOME_PROJETO", "BUSCA", "TAT"])
    except Exception as e:
        st.error(f"Erro ao carregar projetos do banco: {e}")
        df_projetos = pd.DataFrame(columns=["PROJETO", "LOTE", "NOME_PROJETO", "BUSCA", "TAT"])

    # ==========================================
    # SOLUÇÃO 2: PAGINAÇÃO PARA LER OS 77.000 PRODUTOS
    # ==========================================
    try:
        todos_produtos = []
        inicio = 0
        tamanho_bloco = 1000
        
        # Loop para baixar toda a base da nuvem contornando o limite de 1000 da API
        while True:
            res_prod = db.table("produtos").select("*").range(inicio, inicio + tamanho_bloco - 1).execute()
            dados = res_prod.data
            
            if not dados: # Se vier vazio, acabou a tabela
                break
                
            todos_produtos.extend(dados)
            
            if len(dados) < tamanho_bloco: # Se vier menos que 1000, chegou no fim
                break
                
            inicio += tamanho_bloco
            
        df_produtos_nuvem = pd.DataFrame(todos_produtos)
        
        if not df_produtos_nuvem.empty:
            df_produtos_nuvem = df_produtos_nuvem.rename(columns={
                "codigo": "Codigo", "descricao": "Descricao"
            })
            
            df_produtos = df_produtos_nuvem.copy()
            df_produtos["Codigo"] = df_produtos["Codigo"].astype(str).str.strip()
            df_produtos["Descricao"] = df_produtos["Descricao"].astype(str).str.strip()
            df_produtos["BUSCA"] = (df_produtos["Codigo"] + " " + df_produtos["Descricao"]).str.upper()
            
            # Filtro de exibição padrão INTACTO (Sua Regra de Negócio)
            filtrado = df_produtos[df_produtos["Codigo"].str.startswith(("10.", "27."))].copy()
            filtrado["EXIBICAO"] = filtrado["Codigo"] + " - " + filtrado["Descricao"]
        else:
            df_produtos = pd.DataFrame(columns=["Codigo", "Descricao", "BUSCA"])
            filtrado = pd.DataFrame(columns=["Codigo", "Descricao", "BUSCA", "EXIBICAO"])
    except Exception as e:
        st.error(f"Erro ao carregar produtos do banco: {e}")
        df_produtos = pd.DataFrame(columns=["Codigo", "Descricao", "BUSCA"])
        filtrado = pd.DataFrame(columns=["Codigo", "Descricao", "BUSCA", "EXIBICAO"])
        
    return df_projetos, df_produtos, filtrado

def filtrar(df, coluna, texto, limite=50):
    if df.empty:
        return df
    if texto:
        return df[df[coluna].str.contains(texto.upper(), na=False)].head(limite)
    return df.head(limite)

def gravar(projeto_nome, codigo, qtd, resp, tat):
    novo_id = str(uuid.uuid4())
    
    dados = {
        "id": novo_id,
        "tat": tat,
        "projeto_nome": projeto_nome,
        "codigo_material": codigo,
        "quantidade": qtd,
        "responsavel": resp,
        "status_registro": "ATIVO"
    }
    
    db.table("requisicoes").insert(dados).execute()
    st.session_state['ultimo_id'] = novo_id

def desfazer():
    if 'ultimo_id' in st.session_state:
        id_para_cancelar = st.session_state['ultimo_id']
        db.table("requisicoes").update({"status_registro": "CANCELADO"}).eq("id", id_para_cancelar).execute()
        st.warning("Último registro cancelado com sucesso.")
        del st.session_state['ultimo_id'] 
    else:
        st.info("Nenhum registro recente nesta sessão para cancelar.")

df_proj, df_prod, df_filtrado = carregar_dados()

st.title("Sistema de Requisição Extra - 505")

busca_proj = st.text_input("Buscar projeto")
proj_df = filtrar(df_proj, "BUSCA", busca_proj)
projeto = st.selectbox(
    "Projeto",
    proj_df["NOME_PROJETO"].tolist() if not proj_df.empty else [],
    index=None,
)

st.divider()

manual = st.checkbox("Material fora do padrão")

if manual:
    material = st.text_input("Código do material")
else:
    busca_mat = st.text_input("Buscar material (código ou descrição)")
    mat_df = filtrar(df_filtrado, "BUSCA", busca_mat)
    material = st.selectbox(
        "Material",
        mat_df["EXIBICAO"].tolist() if not mat_df.empty else [],
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
                if not df_prod.empty and codigo not in df_prod["Codigo"].tolist():
                    st.error("Código inexistente.")
                    st.stop()
            else:
                codigo = material.split(" - ")[0]

            projeto_info = df_proj[df_proj["NOME_PROJETO"] == projeto]
            if projeto_info.empty:
                st.error("Projeto não encontrado.")
                st.stop()

            tat = projeto_info.iloc[0]["TAT"]
            
            gravar(projeto, codigo, qtd, resp, tat)
            st.success("Registro salvo na fila com sucesso!")

with c2:
    if st.button("Desfazer Último", use_container_width=True):
        desfazer()

st.divider()
st.subheader("📋 Status das Requisições Recentes")

def mostrar_status_recentes():
    res = db.table("requisicoes").select("projeto_nome, codigo_material, quantidade, status_registro, motivo_erro").order("data_hora", desc=True).limit(10).execute()
    df_status = pd.DataFrame(res.data)
    
    if not df_status.empty:
        for index, row in df_status.iterrows():
            texto_base = f"**{int(row['quantidade'])}x {row['codigo_material']}** para {row['projeto_nome']}"
            if row['status_registro'] == 'CONCLUIDO':
                st.success(f"✅ Concluído: {texto_base}")
            elif row['status_registro'] == 'ERRO':
                st.error(f"❌ Erro: {texto_base} - Motivo: {row['motivo_erro']}")
            elif row['status_registro'] == 'PROCESSANDO':
                st.info(f"⏳ O Robô está digitando agora: {texto_base}")
            else:
                st.warning(f"📝 Na fila (Aguardando robô): {texto_base}")
    else:
        st.info("Nenhuma requisição recente encontrada no banco de dados.")

mostrar_status_recentes()