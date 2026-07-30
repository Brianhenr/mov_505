import os
import pandas as pd
from database import db

PASTA_BASE = os.path.dirname(os.path.abspath(__file__))
PASTA_DOCUMENTOS = os.path.join(PASTA_BASE, "documentos")

def sincronizar_produtos():
    print("Sincronizando Produtos...")
    caminho = os.path.join(PASTA_DOCUMENTOS, "produtos.xlsx")
    df = pd.read_excel(caminho, header=1)
    
    registros = []
    for _, row in df.iterrows():
        if pd.notna(row["Codigo"]) and str(row["Codigo"]).strip() != 'nan':
            registros.append({
                "codigo": str(row["Codigo"]).strip(),
                "descricao": str(row["Descricao"]).strip() if pd.notna(row["Descricao"]) else ""
            })
    
    # Envio em lotes de 1000 para evitar bloqueios de payload no Supabase
    for i in range(0, len(registros), 1000):
        db.table("produtos").upsert(registros[i:i+1000]).execute()
    print(f"{len(registros)} produtos enviados.")

def sincronizar_projetos():
    print("Sincronizando Projetos...")
    caminho = os.path.join(PASTA_DOCUMENTOS, "planilha_fabrica.xlsx")
    df = pd.read_excel(caminho, sheet_name="CONTROLE LISTAS", header=1)
    df = df[df["STATUS"].isin(["LISTA ENTREGUE", "LINHA", "MONTADO", "APONTADO"])].copy()
    
    # Limpa a tabela antiga para evitar dados obsoletos
    db.table("projetos").delete().neq("id", -1).execute()
    
    registros = []
    for _, row in df.iterrows():
        projeto = str(row["PROJETO"]).strip() if pd.notna(row["PROJETO"]) else ""
        lote = str(row["LOTE"]).strip() if pd.notna(row["LOTE"]) else ""
        
        if projeto and projeto != 'nan':
            registros.append({
                "projeto": projeto,
                "lote": lote,
                "nome_projeto": f"{projeto} LOTE {lote}",
                "tat": str(row["TAT"]).strip() if pd.notna(row["TAT"]) else "",
                "status": str(row["STATUS"]).strip() if pd.notna(row["STATUS"]) else ""
            })
            
    # Envio em lotes de 1000
    for i in range(0, len(registros), 1000):
        db.table("projetos").insert(registros[i:i+1000]).execute()
    print(f"{len(registros)} projetos enviados.")

if __name__ == "__main__":
    print("--- INICIANDO SINCRONIZAÇÃO COM A NUVEM ---")
    sincronizar_produtos()
    sincronizar_projetos()
    print("--- SINCRONIZAÇÃO CONCLUÍDA ---")