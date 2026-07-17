import os
import sys
import subprocess
import glob
import time
import pandas as pd
from datetime import datetime
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv

def confirmar_salvamento(pagina):
    print("Aguardando confirmação de salvamento do Protheus...")
    
    # Isola a célula pai (TD) em vez de procurar o input efêmero
    celula_produto = pagina.locator("table").nth(1).locator("tbody tr").nth(0).locator("td[id='0']")
    
    for _ in range(15):
        pagina.wait_for_timeout(1000)
        try:
            # Pega qualquer texto que estiver ali, independentemente da formatação HTML interna
            valor_atual = celula_produto.inner_text()
            
            if valor_atual.strip() == "":
                return True
        except Exception:
            pass 
            
    return False

def recuperar_tela(pagina):
    """
    Tenta fechar pop-ups de erro e abortar o documento atual para destravar o robô.
    """
    print("Tentando recuperar a tela do Protheus...")
    
    # Aperta Esc algumas vezes para fechar possíveis janelas de erro (Help/Atenção)
    for _ in range(3):
        pagina.keyboard.press("Escape")
        pagina.wait_for_timeout(500)
        
    try:
        # Tenta clicar no botão Cancelar da rotina para limpar a sujeira
        pagina.locator('wa-button').filter(has_text="Cancelar").click(timeout=3000)
        pagina.wait_for_timeout(2000)
    except:
        print("Botão cancelar não encontrado ou rotina já fechada.")

PASTA_BASE = os.path.dirname(os.path.abspath(__file__))
CAMINHO_PUXAR_SALDO = os.path.join(PASTA_BASE, "puxar_saldo.py")
PASTA_DOCUMENTOS = os.path.join(PASTA_BASE, "documentos")


def ativar_celula_robustamente(pagina, celula, seletor_input):
    campo_input = pagina.locator(seletor_input)
    for tentativa in range(1, 4):
        try:
            if tentativa == 1:
                celula.dblclick(force=True, timeout=800)
            elif tentativa == 2:
                celula.click(force=True, timeout=800)
                celula.press('Enter', timeout=800)
            elif tentativa == 3:
                pagina.keyboard.press('Escape')
                pagina.wait_for_timeout(250)
                celula.click(force=True)
                celula.press('Enter')
            campo_input.wait_for(state='visible', timeout=2000)
            pagina.wait_for_timeout(300)
            return campo_input
        except Exception:
            if tentativa == 3:
                raise
    return campo_input


def perguntar_puxar_saldo():
    resposta = input("Deseja puxar relatório de saldo? (s/n): ").strip().lower()
    if resposta in ("s", "sim"):
        print("Executando consulta de saldo...")
        subprocess.run([sys.executable, CAMINHO_PUXAR_SALDO], check=True)
    else:
        print("Pulando consulta de saldo, usando último relatório salvo.")


def pegar_ultimo_relatorio():
    arquivos = glob.glob(os.path.join(PASTA_DOCUMENTOS, "Relatorio_saldo_*.xlsx"))
    if not arquivos:
        raise FileNotFoundError("Nenhum relatório de saldo encontrado na pasta 'documentos'.")
    arquivos.sort()
    return arquivos[-1]


load_dotenv()

senha = os.getenv('PASSWORD', '')
web = os.getenv('URL', '')
nome = os.getenv('NOME', '')
caminho_profile = os.getenv('CAMINHO_AUT_50', '')


def planejar_movimentacao(caminho_saldo):
    print("Calculando saldos e frações...")

    try:
        caminho_csv = os.path.join(PASTA_DOCUMENTOS, "registros_saida.csv")
        df_csv = pd.read_csv(caminho_csv)
        df_ativos = df_csv[df_csv["STATUS_REGISTRO"] == "ATIVO"]
        df_saldo = pd.read_excel(caminho_saldo, header=1)
        df_saldo['Armazem'] = df_saldo['Armazem'].astype(str).str.replace(',', '.').str.split('.').str[0].str.zfill(2)

        if df_saldo['Quantidade'].dtype == object:
            df_saldo['Quantidade'] = df_saldo['Quantidade'].astype(str).str.replace('.', '').str.replace(',', '.').astype(float)
        else:
            df_saldo['Quantidade'] = df_saldo['Quantidade'].astype(float)
    except Exception as e:
        print(f"Erro ao ler bases de dados: {e}")
        # Retorna um dicionário vazio em caso de erro
        return {} 

    # ── NOVO: Dicionário que vai agrupar tudo por TAT ──
    plano_por_tat = {}

    for index, req in df_ativos.iterrows():
        codigo_csv = req['CODIGO_MATERIAL']
        qtd_pedida = req['QUANTIDADE']
        tat_csv = req['TAT']

        # Se a TAT ainda não existe no dicionário, cria o grupo dela
        if tat_csv not in plano_por_tat:
            plano_por_tat[tat_csv] = {'linhas': [], 'indices': []}

        saldo_produto = df_saldo[(df_saldo['Produto'] == codigo_csv) & (df_saldo['Armazem'] == '01')]
        total_disp = saldo_produto['Quantidade'].sum()

        if total_disp < qtd_pedida:
            print(f"⚠️ IGNORADO: {codigo_csv} pede {qtd_pedida}, mas só tem {total_disp} no armazém 01.")
            continue
            
        # Salva o índice DENTRO do grupo da TAT atual
        plano_por_tat[tat_csv]['indices'].append(index)
        saldo_produto = saldo_produto.sort_values('Quantidade', ascending=False)
        qtd_faltante = qtd_pedida
        
        for idx_saldo, linha_saldo in saldo_produto.iterrows():
            if qtd_faltante <= 0:
                break

            qtd_end = linha_saldo['Quantidade']
            endereco_local = linha_saldo['Endereco']

            if qtd_end > 0:
                if qtd_end >= qtd_faltante:
                    # Adiciona a linha de digitação DENTRO do grupo da TAT atual
                    plano_por_tat[tat_csv]['linhas'].append({
                        'produto': codigo_csv,
                        'quantidade': qtd_faltante,
                        'endereco': endereco_local,
                        'tat': tat_csv
                    })
                    df_saldo.at[idx_saldo, 'Quantidade'] = qtd_end - qtd_faltante
                    qtd_faltante = 0
                else:
                    plano_por_tat[tat_csv]['linhas'].append({
                        'produto': codigo_csv,
                        'quantidade': qtd_end,
                        'endereco': endereco_local,
                        'tat': tat_csv
                    })
                    df_saldo.at[idx_saldo, 'Quantidade'] = 0 
                    qtd_faltante -= qtd_end

    return plano_por_tat


def executar_pull_saldo(plano_de_movimentacao):
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
                "--start-maximized",
                "--no-sandobox"
            ]
        )
        pagina = context.pages[0] if context.pages else context.new_page()

        try:
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

            print("Acessando Movimentação Múltipla...")
            pagina.locator('span[title="Favoritos"]').click()
            pagina.wait_for_timeout(2000)

            pagina.get_by_title("Movimentação Múltipla").click()
            pagina.wait_for_timeout(10000)

            precisa_clicar_incluir = True

            # ── NOVO: LAÇO MESTRE QUE SEPARA OS DOCUMENTOS POR TAT ──
            for tat_atual, dados_tat in plano_de_movimentacao.items():
                linhas_para_digitar = dados_tat['linhas']
                indices_processados = dados_tat['indices']

                # Se por algum motivo o grupo não tiver linhas (falta de saldo), pula para a próxima TAT
                if not linhas_para_digitar:
                    continue

                print(f"\n--- INICIANDO NOVO DOCUMENTO PARA A TAT: {tat_atual} ---")
                if precisa_clicar_incluir:
                    pagina.get_by_role("button", name="Incluir", exact=True).click()
                    pagina.wait_for_timeout(5500)
                else:
                    print(f"A tela de inclusão ja esta aberta. Pulando click...")

                print("Preenchendo Cabeçalho (505)...")
                locator_tm = pagina.locator("wa-text-input[name='cTm'] input[type='text']")
                locator_tm.fill("505")
                pagina.wait_for_timeout(5000)

                # Laço interno que preenche a grid APENAS com os materiais desta TAT
                for linha_idx, item in enumerate(linhas_para_digitar):
                    print(f"Digitando Linha {linha_idx}: {item['quantidade']} un. de {item['produto']} | End: {item['endereco']} | TAT: {item['tat']}")

                    linha_alvo = pagina.locator("table").nth(1).locator("tbody tr").nth(linha_idx)

                    celula_prod = linha_alvo.locator("td[id='0']")
                    produto = ativar_celula_robustamente(pagina, celula_prod, 'wa-text-input[name="M->D3_COD"] input')
                    produto.fill(item['produto'])
                    pagina.keyboard.press("Enter")
                    pagina.wait_for_timeout(5000)

                    celula_qtd = linha_alvo.locator("td[id='2']")
                    qtd = ativar_celula_robustamente(pagina, celula_qtd, 'wa-text-input[name="M->D3_QUANT"] input')
                    qtd_str = str(item['quantidade']).replace('.', ',') if item['quantidade'] % 1 != 0 else str(int(item['quantidade']))
                    qtd.fill(qtd_str)
                    pagina.keyboard.press("Enter")
                    pagina.wait_for_timeout(5000)

                    # Observacao
                    try: 
                        celula_obs = linha_alvo.locator('td[id="3"]')
                        obs = ativar_celula_robustamente(pagina, celula_obs, 'wa-multi-get[data-advpl="tmultiget"] textarea')
                        obs.fill("REPOSIÇÃO")
                        pagina.get_by_title("Ok").click()
                        pagina.wait_for_timeout(5000)
                    except Exception as e:
                        print(f"Ao marcar observação deu o erro: {e}")

                    # Endereço
                    celula_end = linha_alvo.locator("td[id='8']")
                    endereco = ativar_celula_robustamente(pagina, celula_end, 'wa-text-input[name="M->D3_LOCALIZ"] input')
                    endereco.fill(item['endereco'])
                    pagina.keyboard.press("Enter")
                    pagina.wait_for_timeout(5000)

                    
                     # TAT
                    celula_tat = linha_alvo.locator('td[id="31"]')
                    tat_input = ativar_celula_robustamente(pagina, celula_tat, 'wa-text-input[name="M->D3_CLVL"] input')
                    tat_input.fill(f"TAT {item['tat']}")
                    pagina.keyboard.press("Enter")
                    pagina.wait_for_timeout(1000)

                    # Cria o localizador apontando para o componente pai correto
                    botao_fechar = pagina.locator('wa-button').filter(has_text="Fechar")

                    # Usa o .is_visible() para realmente testar o estado da tela naquele milissegundo
                    if botao_fechar.is_visible():
                        print(f"⚠️ Modal de erro detectado para a TAT {item['tat']}!")
                        botao_fechar.click()
                        pagina.wait_for_timeout(1000)
                        
                        # [LÓGICA DE ABORTO DEVE ENTRAR AQUI]
                        celula_tat = linha_alvo.locator('td[id="31"]')
                        tat_input = ativar_celula_robustamente(pagina, celula_tat, 'wa-text-input[name="M->D3_CLVL"] input')
                        tat_input.fill(f"{item['tat']}")
                        pagina.keyboard.press("Enter")


                    if linha_idx < len(linhas_para_digitar) - 1:
                        pagina.keyboard.press("ArrowDown")
                        nova_linha = pagina.locator("table").nth(1).locator("tbody tr").nth(linha_idx + 1)
                        nova_linha.wait_for(state="attached", timeout=5000)
                        pagina.wait_for_timeout(5000)

                # ── SALVAMENTO DO DOCUMENTO DA TAT ATUAL ──
                print(f"Linhas da TAT {tat_atual} preenchidas. Salvando...")
                pagina.locator('wa-button').filter(has_text="Salvar").click(force=True)
                
                # Valida se ESTE documento salvou com sucesso
                if confirmar_salvamento(pagina):
                    print(f"✓ Movimentação da TAT {tat_atual} confirmada!")
                    caminho_csv = os.path.join(PASTA_DOCUMENTOS, "registros_saida.csv")
                    df_atualizar = pd.read_csv(caminho_csv)
                    df_atualizar.loc[indices_processados, "STATUS_REGISTRO"] = "CONCLUIDO"
                    df_atualizar.to_csv(caminho_csv, index=False)
                    print(f"✓ Itens do CSV atualizados.")

                    precisa_clicar_incluir = False
                else:
                    print(f"⚠ Salvamento da TAT {tat_atual} não confirmado.")
                    recuperar_tela(pagina)

                    precisa_clicar_incluir = True

            print("\nTODOS OS DOCUMENTOS FORAM PROCESSADOS.")

        except Exception as erro:
            print(f"Erro fatal na automação Web: {erro}")
            

if __name__ == '__main__':
    perguntar_puxar_saldo()
    caminho_saldo = pegar_ultimo_relatorio()
    print(f"Usando relatório: {caminho_saldo}")
    
    # Recebe o Dicionário agrupado por TAT
    plano_agrupado = planejar_movimentacao(caminho_saldo) 
    
    # Envia o Dicionário para o robô web processar
    executar_pull_saldo(plano_agrupado)