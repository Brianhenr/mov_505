import os
import time
import pandas as pd
from datetime import datetime
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv

# Importação da sua função de clique/foco na célula (certifique-se de que o main.py está na mesma pasta)
from main import ativar_celula_robustamente

load_dotenv()

senha = os.getenv('PASSWORD', '')
web = os.getenv('URL', '')
nome = os.getenv('NOME', '')
caminho_profile = os.getenv('CAMINHO_AUT_50', '')

def planejar_movimentacao():
    """
    Fase 1: Lê os arquivos, verifica saldo e quebra as frações de endereço.
    Retorna uma lista exata de linhas para o robô digitar.
    """
    print("Calculando saldos e frações...")
    
    try:
        # 1. Carrega os arquivos
        df_csv = pd.read_csv("registros_saida.csv")
        df_ativos = df_csv[df_csv["STATUS_REGISTRO"] == "ATIVO"]
        
        # header=1 ignora a primeira linha vazia do Excel de saldos
        df_saldo = pd.read_excel('saldo_endereco.xlsx', header=1) 
        
        # 2. Limpeza brutal dos dados do Excel de Saldo
        df_saldo['Armazen'] = df_saldo['Armazen'].astype(str).str.replace(',', '.').str.split('.').str[0].str.zfill(2)
        
        if df_saldo['Quantidade'].dtype == object:
            df_saldo['Quantidade'] = df_saldo['Quantidade'].astype(str).str.replace('.', '').str.replace(',', '.').astype(float)
        else:
            df_saldo['Quantidade'] = df_saldo['Quantidade'].astype(float)
            
    except Exception as e:
        print(f"Erro ao ler bases de dados: {e}")
        return []

    linhas_para_digitar = []

    # 3. Cruzamento de Dados e Matemática de Fração
    for index, req in df_ativos.iterrows():
        codigo_csv = req['CODIGO_MATERIAL']
        qtd_pedida = req['QUANTIDADE']
        tat_csv = req['TAT']
        
        # Puxa o saldo do código atual no armazém 01
        saldo_produto = df_saldo[(df_saldo['Produto'] == codigo_csv) & (df_saldo['Armazen'] == '01')]
        total_disp = saldo_produto['Quantidade'].sum()
        
        # Bloqueio: Se pedir mais do que tem, ignora e avisa
        if total_disp < qtd_pedida:
            print(f"⚠️ IGNORADO: {codigo_csv} pede {qtd_pedida}, mas só tem {total_disp} no armazém 01.")
            continue 
            
        # Lógica de distribuição pelos endereços
        qtd_faltante = qtd_pedida
        for _, linha_saldo in saldo_produto.iterrows():
            if qtd_faltante <= 0:
                break
                
            qtd_end = linha_saldo['Quantidade']
            endereco_local = linha_saldo['Endereco']
            
            if qtd_end > 0:
                if qtd_end >= qtd_faltante:
                    linhas_para_digitar.append({
                        'produto': codigo_csv, 
                        'quantidade': qtd_faltante, 
                        'endereco': endereco_local,
                        'tat': tat_csv
                    })
                    qtd_faltante = 0
                else:
                    linhas_para_digitar.append({
                        'produto': codigo_csv, 
                        'quantidade': qtd_end, 
                        'endereco': endereco_local,
                        'tat': tat_csv
                    })
                    qtd_faltante -= qtd_end
                    
    return linhas_para_digitar


def executar_pull_saldo(plano_de_movimentacao):
    """
    Fase 2: Automação Web via Playwright para injetar os dados no Protheus.
    """
    if not plano_de_movimentacao:
        print("Nenhuma movimentação válida para ser feita. Robô encerrado.")
        return

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=caminho_profile,
            headless=False,
            channel="msedge",
            no_viewport=True, 
            args=[
                "--disable-extensions",
                "--accept-lang=pt-BR,pt",
                "--start-maximized" 
            ]
        )
        pagina = context.pages[0] if context.pages else context.new_page()

        try:
            # ── LOGIN E AMBIENTE ──
            print("Acessando o Protheus...")
            pagina.goto(web, wait_until="networkidle", timeout=60000)
            pagina.wait_for_load_state("networkidle")

           
            # ── LOGIN E AMBIENTE ──
            print("Acessando o Protheus...")
            pagina.goto(web, wait_until="networkidle", timeout=60000)
            pagina.wait_for_load_state("networkidle")

            try:
                pagina.get_by_role("button", name="Permitir").click(timeout=3000)
                pagina.wait_for_timeout(1000)
            except Exception:
                pass

            pagina.bring_to_front()
            pagina.wait_for_timeout(3800)
            pagina.get_by_role("button", name="Ok").click(timeout=5000)
            pagina.wait_for_timeout(2000)

            # O login continua no iframe, senão o Playwright não acha os campos de senha
            iframe = pagina.frame_locator("iframe")
            iframe.get_by_role("textbox", name="Insira seu usuário").wait_for(timeout=30000)
            pagina.wait_for_timeout(1000)
            iframe.get_by_role("textbox", name="Insira seu usuário").fill(nome)
            iframe.get_by_role("textbox", name="Insira sua senha").fill(senha)
            pagina.wait_for_timeout(500)
            iframe.get_by_role("button", name="Entrar").click()
            pagina.wait_for_timeout(2500)

            iframe.get_by_role("textbox", name="Grupo").fill("01")
            iframe.get_by_role("textbox", name="Filial").fill("0102")
            iframe.get_by_role("textbox", name="Ambiente").fill("4")
            iframe.get_by_role("textbox", name="Papel de trabalho").fill("04")
            pagina.wait_for_timeout(800)
            iframe.locator("div").filter(has_text="Linha Protheus Boas-vindas,").nth(1).click()
            pagina.wait_for_timeout(500)
            iframe.get_by_role("button", name="Entrar").click()

            pagina.wait_for_load_state("networkidle")
            pagina.wait_for_timeout(6000)
            print("Login OK.")

            # ── NAVEGAÇÃO INTERNA RESTAURADA ──
            print("Acessando Movimentação Múltipla...")
            
            # Voltando para os seletores originais da página principal
            pagina.locator('span[title="Favoritos"]').click()
            pagina.wait_for_timeout(2000)
            
            pagina.get_by_title("Movimentação Múltipla").click()
            pagina.wait_for_timeout(4000) 
            
            pagina.get_by_role("button", name="Incluir", exact=True).click()
            pagina.wait_for_timeout(4000)

            print("Preenchendo Cabeçalho (505)...")
            # Aqui volta para o iframe porque os campos do grid estão dentro da rotina
            locator_tm = iframe.locator("wa-text-input[name='cTm'] input[type='text']")
            locator_tm.fill("505")
            pagina.wait_for_timeout(1500)
            
            # ... (AQUI CONTINUA O LOOP DINÂMICO DE PREENCHIMENTO DO GRID QUE FIZEMOS) ...

            # ── PREENCHIMENTO DO GRID (LOOP) ──
            for linha_idx, item in enumerate(plano_de_movimentacao):
                print(f"Digitando Linha {linha_idx}: {item['quantidade']} un. de {item['produto']} | End: {item['endereco']} | TAT: {item['tat']}")
                
                linha_alvo = iframe.locator("table").nth(1).locator("tbody tr").nth(linha_idx)
                
                # 1. Produto (ID 0)
                celula_prod = linha_alvo.locator("td[id='0']")
                produto = ativar_celula_robustamente(pagina, celula_prod, 'wa-text-input[name="M->D3_COD"] input')
                produto.fill(item['produto'])
                pagina.keyboard.press("Enter")
                pagina.wait_for_timeout(500)
                
                # 2. Quantidade (ID 2)
                celula_qtd = linha_alvo.locator("td[id='2']")
                qtd = ativar_celula_robustamente(pagina, celula_qtd, 'wa-text-input[name="M->D3_QUANT"] input')
                qtd_str = str(item['quantidade']).replace('.', ',') if item['quantidade'] % 1 != 0 else str(int(item['quantidade']))
                qtd.fill(qtd_str)
                pagina.keyboard.press("Enter")
                pagina.wait_for_timeout(500)
                
                # 3. Endereço (ID 8)
                celula_end = linha_alvo.locator("td[id='8']")
                endereco = ativar_celula_robustamente(pagina, celula_end, 'wa-text-input[name="M->D3_LOCALIZ"] input')
                endereco.fill(item['endereco'])
                pagina.keyboard.press("Enter")
                pagina.wait_for_timeout(500)
                
                # 4. Observação (ID 3)
                celula_obs = linha_alvo.locator('td[id="3"]')
                obs = ativar_celula_robustamente(pagina, celula_obs, 'wa-multi-get[data-advpl="tmultiget"] textarea')
                obs.fill("REPOSIÇÃO")
                pagina.keyboard.press("Enter")
                pagina.wait_for_timeout(500)
                
                # 5. Classe de Valor / TAT (ID 31)
                celula_tat = linha_alvo.locator('td[id="31"]')
                tat_input = ativar_celula_robustamente(pagina, celula_tat, 'wa-text-input[name="M->D3_CLVL"] input')
                tat_input.fill(item['tat'])
                pagina.keyboard.press("Enter")
                pagina.wait_for_timeout(500)
                
                # Seta para baixo se não for a última linha
                if linha_idx < len(plano_de_movimentacao) - 1:
                    pagina.keyboard.press("ArrowDown")
                    nova_linha = iframe.locator("table").nth(1).locator("tbody tr").nth(linha_idx + 1)
                    nova_linha.wait_for(state="attached", timeout=5000)
                    pagina.wait_for_timeout(1000)
            
            # ── SALVAMENTO FINAL ──
            print("Todas as linhas preenchidas. Salvando movimentação...")
            iframe.locator('wa-button').filter(has_text="Salvar").click()
            pagina.wait_for_timeout(5000)
            
        except Exception as erro:
            print(f'Falha na automação Web: {erro}')
            
        input('Pressione Enter para fechar o navegador...')

if __name__ == '__main__':
    plano_final = planejar_movimentacao()
    executar_pull_saldo(plano_final)