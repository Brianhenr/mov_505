import streamlit as st
import pandas as pd
import uuid
from datetime import datetime

# Conexão com o banco de dados via Supabase
from database import db

# 1. CONFIGURAÇÃO DA PÁGINA (Anônima e Profissional)
st.set_page_config(
    page_title="Portal de Requisições - Almoxarifado", 
    page_icon="📦", 
    layout="wide"
)

# 2. CARREGAMENTO DE DADOS DA NUVEM (Substituindo leitura de Excel local)
@st.cache_data(ttl=300)
def carregar_produtos():
    try:
        res = db.table("produtos").select("codigo, descricao").execute()
        if res.data:
            return pd.DataFrame(res.data)
        return pd.DataFrame(columns=["codigo", "descricao"])
    except Exception as e:
        st.error(f"Erro ao carregar produtos: {e}")
        return pd.DataFrame(columns=["codigo", "descricao"])

@st.cache_data(ttl=300)
def carregar_projetos():
    try:
        res = db.table("projetos").select("projeto, lote, nome_projeto, tat, status").execute()
        if res.data:
            return pd.DataFrame(res.data)
        return pd.DataFrame(columns=["projeto", "lote", "nome_projeto", "tat", "status"])
    except Exception as e:
        st.error(f"Erro ao carregar projetos: {e}")
        return pd.DataFrame(columns=["projeto", "lote", "nome_projeto", "tat", "status"])

# Carrega os DataFrames em memória
df_produtos = carregar_produtos()
df_projetos = carregar_projetos()

# 3. INTERFACE PRINCIPAL
st.title("📦 Sistema de Requisição Múltipla")
st.markdown("---")

# 4. FORMULÁRIO DE REQUISIÇÃO (Com limpeza automática após envio)
with st.container():
    # Prepara as listas para os menus suspensos
    opcoes_projetos = df_projetos['nome_projeto'].tolist() if not df_projetos.empty else []
    opcoes_produtos = (df_produtos['codigo'] + " - " + df_produtos['descricao']).tolist() if not df_produtos.empty else []

    with st.form("form_requisicao", clear_on_submit=True):
        st.subheader("Nova Requisição")
        
        col1, col2 = st.columns(2)
        with col1:
            projeto_selecionado = st.selectbox("Selecione o Projeto e Lote", [""] + opcoes_projetos)
        with col2:
            produto_selecionado = st.selectbox("Selecione o Material", [""] + opcoes_produtos)
            
        quantidade = st.number_input("Quantidade Necessária", min_value=1.0, step=1.0)
        
        # Botão de envio dentro do form
        enviado = st.form_submit_button("Enviar Requisição", type="primary", use_container_width=True)
        
        if enviado:
            if not projeto_selecionado or not produto_selecionado:
                st.warning("⚠️ Por favor, selecione o projeto e o material antes de enviar.")
            else:
                try:
                    # Regras de Negócio Preservadas: Extração de código e identificação do TAT
                    codigo_material = produto_selecionado.split(" - ")[0]
                    
                    linha_projeto = df_projetos[df_projetos['nome_projeto'] == projeto_selecionado].iloc[0]
                    tat_projeto = linha_projeto['tat']
                    
                    req_id = str(uuid.uuid4())
                    
                    # Montando o pacote de dados para o banco na nuvem
                    dados_requisicao = {
                        "id": req_id,
                        "codigo_material": codigo_material,
                        "quantidade": quantidade,
                        "tat": tat_projeto,
                        "projeto_lote": projeto_selecionado,
                        "status_registro": "ATIVO",
                        "data_solicitacao": datetime.now().isoformat()
                    }
                    
                    # Inserção no Supabase
                    db.table("requisicoes").insert(dados_requisicao).execute()
                    
                    st.success(f"✅ Requisição enviada com sucesso! Código: {codigo_material} | Qtd: {quantidade}")
                except Exception as e:
                    st.error(f"❌ Erro ao enviar requisição: {e}")

st.markdown("---")

# 5. PAINEL DE STATUS EM TEMPO REAL
st.subheader("📊 Status das Requisições Recentes")

if st.button("🔄 Atualizar Painel"):
    # Limpa o cache para forçar a leitura mais recente do banco, caso necessário
    st.rerun()

try:
    # Busca apenas os últimos 50 registros para manter o app leve
    res_req = db.table("requisicoes").select("*").order("data_solicitacao", desc=True).limit(50).execute()
    
    if res_req.data:
        df_status = pd.DataFrame(res_req.data)
        
        # Mapeamento e organização das colunas para uma visualização limpa
        colunas_exibicao = {
            "codigo_material": "Material",
            "quantidade": "Qtd",
            "tat": "TAT",
            "projeto_lote": "Projeto",
            "status_registro": "Status",
            "motivo_erro": "Observação"
        }
        
        df_exibicao = df_status[[col for col in colunas_exibicao.keys() if col in df_status.columns]].rename(columns=colunas_exibicao)
        
        # Destaca a tabela no frontend
        st.dataframe(df_exibicao, use_container_width=True, hide_index=True)
    else:
        st.info("Nenhuma requisição pendente ou processada hoje.")
        
except Exception as e:
    st.error(f"Erro ao carregar painel de status: {e}")