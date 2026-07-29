import os
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv
from database import db

# Carrega as variáveis de ambiente
load_dotenv()
senha = os.getenv('PASSWORD', '')
web = os.getenv('URL', '')
nome = os.getenv('NOME', '')
caminho_profile = os.getenv('CAMINHO_AUT_50', '')

def confirmar_salvamento(pagina):
    print("Aguardando confirmação de salvamento do Protheus...")
    celula_produto = pagina.locator("table").nth(1).locator("tbody tr").nth(0).locator("td[id='0']")
    for _ in range(15):
        pagina.wait_for_timeout(1000)
        try:
            valor_atual = celula_produto.inner_text()
            if valor_atual.strip() == "":
                return True
        except Exception:
            pass
    return False

def recuperar_tela(pagina):
    print("Tentando recuperar a tela do Protheus...")
    for _ in range(3):
        pagina.keyboard.press("Escape")
        pagina.wait_for_timeout(500)
    try:
        pagina.locator('wa-button').filter(has_text="Cancelar").click(timeout=3000)
        pagina.wait_for_timeout(2000)
    except:
        print("Botão cancelar não encontrado ou rotina já fechada.")

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

def executar_robo_protheus(plano_de_movimentacao):
    if not plano_de_movimentacao:
        print("Nenhuma movimentação lida para ser feita. Robô encerrado.")
        return
        
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=caminho_profile,
            headless=False,
            channel="msedge",
            no_viewport=True,
            permissions=["clipboard-read", "clipboard-write", "notifications"],
            ignore_default_args=["--no-sandbox"],
            args=["--accept-lang=pt-BR,pt", "--start-maximized"]
        )
        pagina = context.pages[0] if context.pages else context.new_page()
        
        pagina.on("dialog", lambda dialog: dialog.accept())
        
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
            pagina.wait_for_timeout(15000)
            
            precisa_clicar_incluir = True
            for tat_atual, dados_tat in plano_de_movimentacao.items():
                linhas_para_digitar = dados_tat['linhas']
                ids_processados = dados_tat['ids_banco']
                
                if not linhas_para_digitar:
                    continue
                
                for id_req in ids_processados:
                    db.table("requisicoes").update({"status_registro": "PROCESSANDO"}).eq("id", id_req).execute()

                print(f"\n--- INICIANDO NOVO DOCUMENTO PARA A TAT: {tat_atual} ---")
                if precisa_clicar_incluir:
                    pagina.get_by_role("button", name="Incluir", exact=True).click()
                    pagina.wait_for_timeout(5500)
                else:
                    print("A tela de inclusão ja esta aberta. Pulando click...")
                    
                print("Preenchendo Cabeçalho (505)...")
                locator_tm = pagina.locator("wa-text-input[name='cTm'] input[type='text']")
                locator_tm.fill("505")
                pagina.wait_for_timeout(5500)
                try:
                    for linha_idx, item in enumerate(linhas_para_digitar):
                        print(f"Digitando Linha {linha_idx}: {item['quantidade']} un. de {item['produto']} | End: {item['endereco']} | TAT: {item['tat']}")
                        linha_alvo = pagina.locator("table").nth(1).locator("tbody tr").nth(linha_idx)
                        
                        celula_prod = linha_alvo.locator("td[id='0']")
                        produto = ativar_celula_robustamente(pagina, celula_prod, 'wa-text-input[name="M->D3_COD"] input')
                        produto.fill(item['produto'])
                        pagina.keyboard.press("Enter")
                        produto.wait_for(state="hidden", timeout=5000)
                        
                        celula_qtd = linha_alvo.locator("td[id='2']")
                        qtd = ativar_celula_robustamente(pagina, celula_qtd, 'wa-text-input[name="M->D3_QUANT"] input')
                        qtd_str = str(item['quantidade']).replace('.', ',') if item['quantidade'] % 1 != 0 else str(int(item['quantidade']))
                        qtd.fill(qtd_str)
                        pagina.keyboard.press("Enter")
                        qtd.wait_for(state="hidden", timeout=5000)
                        
                        try:
                            celula_obs = linha_alvo.locator('td[id="3"]')
                            obs = ativar_celula_robustamente(pagina, celula_obs, 'wa-multi-get[data-advpl="tmultiget"] textarea')
                            obs.fill("REPOSIÇÃO")
                            pagina.get_by_title("Ok").click()
                            pagina.wait_for_timeout(1000)
                        except Exception as e:
                            print(f"Ao marcar observação deu erro: {e}")
                            
                        celula_end = linha_alvo.locator("td[id='8']")
                        endereco = ativar_celula_robustamente(pagina, celula_end, 'wa-text-input[name="M->D3_LOCALIZ"] input')
                        endereco.fill(item['endereco'])
                        pagina.keyboard.press("Enter")
                        endereco.wait_for(state="hidden", timeout=5000)
                        
                        celula_tat = linha_alvo.locator('td[id="31"]')
                        tat_input = ativar_celula_robustamente(pagina, celula_tat, 'wa-text-input[name="M->D3_CLVL"] input')
                        tat_input.fill(f"TAT {item['tat']}")
                        pagina.keyboard.press("Enter")
                        
                        botao_fechar = pagina.locator('wa-button').filter(has_text="Fechar")
                        try:
                            botao_fechar.wait_for(state="visible", timeout=2000)
                            modal_apareceu = True
                        except Exception:
                            modal_apareceu = False
                            
                        if modal_apareceu:
                            print(f"  Modal de erro detectado para a TAT {item['tat']} (com prefixo). Tentando sem prefixo...")
                            botao_fechar.click()
                            pagina.wait_for_timeout(1000)
                            celula_tat = linha_alvo.locator('td[id="31"]')
                            tat_input = ativar_celula_robustamente(pagina, celula_tat, 'wa-text-input[name="M->D3_CLVL"] input')
                            tat_input.fill(f"{item['tat']}")
                            pagina.keyboard.press("Enter")
                            try:
                                botao_fechar.wait_for(state="visible", timeout=2000)
                                segunda_falha = True
                            except Exception:
                                segunda_falha = False
                                
                            if segunda_falha:
                                print(f"  ABORTANDO documento: TAT {item['tat']} rejeitada.")
                                botao_fechar.click()
                                pagina.wait_for_timeout(1000)
                                recuperar_tela(pagina)
                                raise RuntimeError(f"TAT inválida no Protheus: {item['tat']}")
                                
                        if linha_idx < len(linhas_para_digitar) - 1:
                            pagina.keyboard.press("ArrowDown")
                            nova_linha = pagina.locator("table").nth(1).locator("tbody tr").nth(linha_idx + 1)
                            nova_linha.wait_for(state="attached", timeout=5000)
                            pagina.wait_for_timeout(5000)
                            
                    print(f"Linhas da TAT {tat_atual} preenchidas. Salvando...")
                    pagina.locator('wa-button').filter(has_text="Salvar").click()
                    pagina.wait_for_timeout(5000)
                    
                    if confirmar_salvamento(pagina):
                        print(f"  Movimentação da TAT {tat_atual} confirmada!")
                        for id_req in ids_processados:
                            db.table("requisicoes").update({"status_registro": "CONCLUIDO"}).eq("id", id_req).execute()
                        print("  Banco de dados atualizado (CONCLUIDO).")
                        precisa_clicar_incluir = False
                    else:
                        print(f"  Salvamento da TAT {tat_atual} não confirmado.")
                        recuperar_tela(pagina)
                        precisa_clicar_incluir = True
                        for id_req in ids_processados:
                            db.table("requisicoes").update({
                                "status_registro": "ERRO",
                                "motivo_erro": "Salvamento não confirmado no Protheus"
                            }).eq("id", id_req).execute()
                            
                except RuntimeError as erro_tat:
                    print(f"  Documento da TAT {tat_atual} abortado: {erro_tat}")
                    precisa_clicar_incluir = True
                    for id_req in ids_processados:
                        db.table("requisicoes").update({
                            "status_registro": "ERRO",
                            "motivo_erro": str(erro_tat)
                        }).eq("id", id_req).execute()
                        
            print("\nTODOS OS DOCUMENTOS FORAM PROCESSADOS.")
        except Exception as erro:
            print(f"Erro fatal na automação Web: {erro}")
        finally:
            if 'context' in locals():
                print("Salvando perfil e encerrando o navegador...")
                context.close()