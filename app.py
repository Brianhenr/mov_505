import streamlit as st
import pandas as pd
from database import db

# Usamos o cache do Streamlit (ttl=300 significa 5 minutos) 
# Isso evita que o site faça milhares de consultas no banco a cada clique
@st.cache_data(ttl=300)
def carregar_produtos():
    try:
        res = db.table("produtos").select("codigo, descricao").execute()
        if res.data:
            return pd.DataFrame(res.data)
        return pd.DataFrame(columns=["codigo", "descricao"])
    except Exception as e:
        st.error(f"Erro ao carregar produtos do banco: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=300)
def carregar_projetos():
    try:
        res = db.table("projetos").select("projeto, lote, nome_projeto, tat, status").execute()
        if res.data:
            return pd.DataFrame(res.data)
        return pd.DataFrame(columns=["projeto", "lote", "nome_projeto", "tat", "status"])
    except Exception as e:
        st.error(f"Erro ao carregar projetos do banco: {e}")
        return pd.DataFrame()

# Carregando as bases de dados da NUVEM em vez dos arquivos locais
df_produtos = carregar_produtos()
df_projetos = carregar_projetos()