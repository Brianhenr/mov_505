import os
import uuid
import re
import pandas as pd
import streamlit as st
from database import db

# ==========================================
# ACESSIBILIDADE E LAYOUT MOBILE (PCD)
# ==========================================
st.set_page_config(
    page_title="Sistema 505", 
    layout="centered", 
    initial_sidebar_state="collapsed"
)

st.markdown("""
    <style>
    html, body, [class*="css"] {
        font-size: 18px !important;
    }
    .stButton>button {
        min-height: 60px;
        font-weight: bold;
        font-size: 18px !important;
    }
    div[data-baseweb="select"] {
        font-size: 18px !important;
    }
    </style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=600) 
def carregar_dados():
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

    try:
        todos_produtos = []
        inicio = 0
        tamanho_bloco = 1000
        
        while True:
            res_prod = db.table("produtos").select("*").range(inicio, inicio + tamanho_bloco - 1).execute()
            dados = res_prod.data
            if not dados:
                break
            todos_produtos.extend(dados)
            if len(dados) < tamanho_bloco:
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

def desfazer(responsavel_atual):
    id_para_cancelar = st.session_state.get('ultimo_id')
    
    if not id_para_cancelar and responsavel_atual:
        res_busca = db.table("requisicoes").select("id").eq("responsavel", responsavel_atual).eq("status_registro", "ATIVO").order("data_hora", desc=True).limit(1).execute()
        data = getattr(res_busca, 'data', None)
        if data and isinstance(data, list) and len(data) > 0:
            primeiro_item = data[0]
            if isinstance(primeiro_item, dict):
                id_para_cancelar = primeiro_item.get('id')

    if id_para_cancelar:
        db.table("requisicoes").update({"status_registro": "CANCELADO"}).eq("id", id_para_cancelar).execute()
        st.warning("Último registro cancelado com sucesso.")
        if 'ultimo_id' in st.session_state:
            del st.session_state['ultimo_id']
        st.rerun()
    else:
        st.info("Nenhum registro recente encontrado para cancelar.")

df_proj, df_prod, df_filtrado = carregar_dados()

st.title("Sistema de Requisição Extra - 505")

# Campos de Projeto com controle de estado
busca_proj = st.text_input("Buscar projeto", key="busca_proj")
proj_df = filtrar(df_proj, "BUSCA", busca_proj)
projeto = st.selectbox(
    "Projeto",
    proj_df["NOME_PROJETO"].tolist() if not proj_df.empty else [],
    index=None,
    key="projeto_selecionado"
)

st.divider()

manual = st.checkbox("Material fora do padrão", key="manual_check")

if manual:
    material = st.text_input("Código do material", key="material_manual")
else:
    busca_mat = st.text_input("Buscar material (código ou descrição)", key="busca_mat")
    mat_df = filtrar(df_filtrado, "BUSCA", busca_mat)
    material = st.selectbox(
        "Material",
        mat_df["EXIBICAO"].tolist() if not mat_df.empty else [],
        index=None,
        key="material_select"
    )

st.divider()

resp = st.selectbox(
    "Responsável",
    ["Eduardo", "Chico Louco", "Mairo", "Natan", "Odair", "Outro..."],
    index=None,
    key="resp_select"
)

qtd = st.number_input("Quantidade", min_value=1, step=1, key="qtd_input")

# ==========================================
# FUNÇÃO DE PROCESSAMENTO E VALIDAÇÃO (CALLBACK)
# ==========================================
def processar_gravacao():
    st.session_state['mensagem_erro'] = None
    st.session_state['mensagem_sucesso'] = None
    
    proj_atual = st.session_state.get('projeto_selecionado')
    is_manual = st.session_state.get('manual_check', False)
    resp_atual = st.session_state.get('resp_select')
    qtd_atual = st.session_state.get('qtd_input', 1)
    
    if is_manual:
        mat_atual = st.session_state.get('material_manual', '')
    else:
        mat_atual = st.session_state.get('material_select')

    if not (proj_atual and mat_atual and resp_atual):
        st.session_state['mensagem_erro'] = "Preencha todos os campos."
        return

    if is_manual:
        codigo = mat_atual.strip()
        if df_prod.empty:
            st.session_state['mensagem_erro'] = "Não foi possível validar o código: base de produtos indisponível no momento. Tente novamente em instantes."
            return
        if codigo not in df_prod["Codigo"].tolist():
            st.session_state['mensagem_erro'] = "Código inexistente."
            return
    else:
        codigo = mat_atual.split(" - ")[0]

    projeto_info = df_proj[df_proj["NOME_PROJETO"] == proj_atual]
    if projeto_info.empty:
        st.session_state['mensagem_erro'] = "Projeto não encontrado."
        return

    tat = projeto_info.iloc[0]["TAT"]
    
    # Grava no banco de dados
    gravar(proj_atual, codigo, qtd_atual, resp_atual, tat)
    
    # Limpa os campos após o sucesso, mantendo o projeto selecionado
    st.session_state['manual_check'] = False
    st.session_state['busca_mat'] = ""
    st.session_state['material_manual'] = ""
    st.session_state['material_select'] = None
    st.session_state['resp_select'] = None
    st.session_state['qtd_input'] = 1
    
    st.session_state['mensagem_sucesso'] = "Registro salvo na fila com sucesso!"

c1, c2 = st.columns(2)

with c1:
    st.button("Gravar", use_container_width=True, on_click=processar_gravacao)

with c2:
    if st.button("Desfazer Último", use_container_width=True):
        desfazer(resp)

# Exibe mensagens de feedback armazenadas no estado
if st.session_state.get('mensagem_erro'):
    st.error(st.session_state['mensagem_erro'])
    st.session_state['mensagem_erro'] = None

if st.session_state.get('mensagem_sucesso'):
    st.success(st.session_state['mensagem_sucesso'])
    st.session_state['mensagem_sucesso'] = None

st.divider()
st.subheader("📋 Status das Requisições Recentes")

def mostrar_status_recentes():
    res = db.table("requisicoes").select("id, tat, projeto_nome, codigo_material, quantidade, responsavel, status_registro, motivo_erro").order("data_hora", desc=True).limit(10).execute()
    df_status = pd.DataFrame(res.data)
    
    if not df_status.empty:
        for index, row in df_status.iterrows():
            texto_base = f"**{int(row['quantidade']) if pd.notna(row['quantidade']) else row['quantidade']}x {row['codigo_material']}** para {row['projeto_nome']}"
            
            if row['status_registro'] == 'CONCLUIDO':
                st.success(f"✅ Concluído: {texto_base}")
            elif row['status_registro'] == 'CANCELADO':
                st.warning(f"🚫 Cancelado: {texto_base}")
            elif row['status_registro'] == 'ERRO':
                motivo = str(row.get('motivo_erro', ''))
                st.error(f"❌ Erro: {texto_base} - Motivo: {motivo}")
                
                if "saldo" in motivo.lower():
                    try:
                        match = re.search(r"dispon[ií]vel[:\s]*([\d\.]+)", motivo, re.IGNORECASE)
                        if match:
                            qtd_disponivel = float(match.group(1))
                            if qtd_disponivel > 0:
                                row_id = row.get('id', index)
                                btn_key = f"btn_saldo_{row_id}_{index}"
                                qtd_formatada = int(qtd_disponivel) if qtd_disponivel.is_integer() else qtd_disponivel
                                
                                if st.button(f"📦 Movimentar saldo disponível ({qtd_formatada}x)", key=btn_key, use_container_width=True):
                                    if row.get('id'):
                                        db.table("requisicoes").update({"status_registro": "CANCELADO"}).eq("id", row['id']).execute()
                                    
                                    novo_id = str(uuid.uuid4())
                                    dados_novo = {
                                        "id": novo_id,
                                        "tat": row.get('tat', ''),
                                        "projeto_nome": row.get('projeto_nome', ''),
                                        "codigo_material": row.get('codigo_material', ''),
                                        "quantidade": qtd_disponivel,
                                        "responsavel": row.get('responsavel') if row.get('responsavel') else "Sistema",
                                        "status_registro": "ATIVO"
                                    }
                                    db.table("requisicoes").insert(dados_novo).execute()
                                    
                                    st.success(f"Nova requisição criada com sucesso para o saldo disponível ({qtd_formatada}x)!")
                                    st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao processar saldo disponível: {e}")

            elif row['status_registro'] == 'PROCESSANDO':
                st.info(f"⏳ O Robô está digitando agora: {texto_base}")
            else:
                st.warning(f"📝 Na fila (Aguardando robô): {texto_base}")
    else:
        st.info("Nenhuma requisição recente encontrada no banco de dados.")

mostrar_status_recentes()