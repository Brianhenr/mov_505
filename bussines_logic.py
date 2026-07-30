import pandas as pd
from database import db

def recuperar_pendencias_travadas():
    print("Verificando se há requisições travadas em 'PROCESSANDO'...")
    try:
        res = db.table("requisicoes").select("id, codigo_material, tat").eq("status_registro", "PROCESSANDO").execute()
        travados = res.data
        if travados:
            print(f"Encontrados {len(travados)} registros travados. Revertendo para ATIVO...")
            for item in (travados or []):
                id_travado = item.get("id") if isinstance(item, dict) else None
                if id_travado:
                    db.table("requisicoes").update({
                        "status_registro": "ATIVO",
                        "motivo_erro": "Revertido automaticamente por interrupção inesperada do robô"
                    }).eq("id", id_travado).execute()
            print("Requisições travadas recuperadas com sucesso.")
        else:
            print("Nenhuma requisição travada encontrada.")
    except Exception as e:
        print(f"Erro ao tentar recuperar pendências travadas: {e}")

def planejar_movimentacao(caminho_saldo):
    print("Calculando saldos e frações...")
    try:
        res = db.table("requisicoes").select("*").eq("status_registro", "ATIVO").execute()
        df_ativos = pd.DataFrame(res.data)
        
        if df_ativos.empty:
            print("Nenhuma requisição ATIVA encontrada no banco.")
            return {}

        df_saldo = pd.read_excel(caminho_saldo, header=1)
        df_saldo['Armazem'] = df_saldo['Armazem'].astype(str).str.replace(',', '.').str.split('.').str[0].str.zfill(2)
        if df_saldo['Quantidade'].dtype == object:
            df_saldo['Quantidade'] = df_saldo['Quantidade'].astype(str).str.replace('.', '').str.replace(',', '.').astype(float)
        else:
            df_saldo['Quantidade'] = df_saldo['Quantidade'].astype(float)
    except Exception as e:
        print(f"Erro ao ler bases de dados: {e}")
        return {}

    plano_por_tat = {}
    for index, req in df_ativos.iterrows():
        id_banco = req.get('id') if isinstance(req, dict) else str(req.get('id', ''))
        codigo_req = str(req.get('codigo_material') if isinstance(req, dict) else req.get('codigo_material', ''))
        
        raw_qtd = req.get('quantidade') if isinstance(req, dict) else req.get('quantidade')
        qtd_pedida = float(raw_qtd) if raw_qtd is not None else 0.0
        
        tat_req = str(req.get('tat') if isinstance(req, dict) else req.get('tat', ''))
        
        if not tat_req or tat_req == 'nan':
            continue
            
        if tat_req not in plano_por_tat:
            plano_por_tat[tat_req] = {'linhas': [], 'ids_banco': []}
            
        saldo_produto = df_saldo[(df_saldo['Produto'] == codigo_req) & (df_saldo['Armazem'] == '01')]
        total_disp = saldo_produto['Quantidade'].sum()
        
        if total_disp < qtd_pedida:
            print(f"  IGNORADO: {codigo_req} pede {qtd_pedida}, mas só tem {total_disp} no armazém 01.")
            db.table("requisicoes").update({
                "status_registro": "ERRO",
                "motivo_erro": f"Falta de saldo. Pedido: {qtd_pedida}, Disponivel: {total_disp}"
            }).eq("id", id_banco).execute()
            continue
            
        plano_por_tat[tat_req]['ids_banco'].append(id_banco)
        saldo_produto = saldo_produto.sort_values('Quantidade', ascending=False)
        qtd_faltante = qtd_pedida
        
        for idx_saldo, linha_saldo in saldo_produto.iterrows():
            if qtd_faltante <= 0:
                break
            qtd_end = linha_saldo['Quantidade']
            endereco_local = linha_saldo['Endereco']
            if qtd_end > 0:
                if qtd_end >= qtd_faltante:
                    plano_por_tat[tat_req]['linhas'].append({
                        'produto': codigo_req,
                        'quantidade': qtd_faltante,
                        'endereco': endereco_local,
                        'tat': tat_req
                    })
                    df_saldo.at[idx_saldo, 'Quantidade'] = qtd_end - qtd_faltante
                    qtd_faltante = 0
                else:
                    plano_por_tat[tat_req]['linhas'].append({
                        'produto': codigo_req,
                        'quantidade': qtd_end,
                        'endereco': endereco_local,
                        'tat': tat_req
                    })
                    df_saldo.at[idx_saldo, 'Quantidade'] = 0 
                    qtd_faltante -= qtd_end
                    
    return plano_por_tat