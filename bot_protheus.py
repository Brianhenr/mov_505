import os
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv
from database import db
import time

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
        botao_cancelar = pagina.locator('wa-button').filter(has_text="Cancelar")
        botao_cancelar.wait_for(state="visible", timeout=3000)
        botao_cancelar.click()
        pagina.wait_for_timeout(1000)
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
            args=["--start-maximized"]
        )
        pagina = context.pages[0] if context.pages else context.new_page()
        
        pagina.on("dialog", lambda dialog: dialog.accept())
        
        try:
            print("Acessando o Protheus...")
            pagina.goto(web, wait_until="networkidle", timeout=60000)
            
            # Modal de permissão inicial (se houver)
            try:
                botao_permitir = pagina.get_by_role("button", name="Permitir")
                botao_permitir.wait_for(state="visible", timeout=3000)
                botao_permitir.click()
            except Exception:
                pass
                
            pagina.bring_to_front()
            
            # Botão OK de Boas-vindas
            botao_ok = pagina.get_by_role("button", name="Ok")
            botao_ok.wait_for(state="visible", timeout=15000)
            botao_ok.click()
            botao_ok.wait_for(state="hidden", timeout=10000)
            
            iframe = pagina.frame_locator("iframe")
            
            # Preenchimento do Login
            input_usuario = iframe.get_by_role("textbox", name="Insira seu usuário")
            input_usuario.wait_for(state="visible", timeout=30000)
            input_usuario.fill(nome)
            
            iframe.get_by_role("textbox", name="Insira sua senha").fill(senha)
            botao_entrar_login = iframe.get_by_role("button", name="Entrar")
            botao_entrar_login.click()
            
            input_usuario.wait_for(state="hidden", timeout=15000)
            
            # Preenchimento de Grupo/Filial
            input_grupo = iframe.get_by_role("textbox", name="Grupo")
            input_grupo.wait_for(state="visible", timeout=15000)
            input_grupo.fill("01")
            
            iframe.get_by_role("textbox", name="Filial").fill("0102")
            iframe.get_by_role("textbox", name="Ambiente").fill("4")
            iframe.get_by_role("textbox", name="Papel de trabalho").fill("04")
            
            iframe.locator("div").filter(has_text="Linha Protheus Boas-vindas,").nth(1).click()
            
            botao_entrar_modulo = iframe.get_by_role("button", name="Entrar")
            botao_entrar_modulo.click()
            botao_entrar_modulo.wait_for(state="hidden", timeout=30000)
            
            print("Aguardando carregamento completo da interface...")
            pagina.wait_for_load_state("networkidle", timeout=30000)
            
            # Tela Principal
            botao_favoritos = pagina.locator('span[title="Favoritos"]')
            botao_favoritos.wait_for(state="visible", timeout=30000)

            
            print("Login OK. Acessando Movimentação Múltipla...")
            botao_favoritos.click()

            time.sleep(5)
            
            # Correção do erro de sintaxe: removido o filter(state="visible")
            botao_mov = pagina.get_by_title("Movimentação Múltipla").first
            botao_mov.wait_for(state="visible", timeout=15000)
            
            botao_mov.hover()
            pagina.wait_for_timeout(800) 
            botao_mov.click()
            time.sleep(10)
            pagina.wait_for_load_state("networkidle", timeout=30000)
            
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
                    time.sleep(4)
                    botao_incluir = pagina.get_by_role("button", name="Incluir", exact=True)
                    botao_incluir.wait_for(state="visible", timeout=30000)
                    botao_incluir.click()
                else:
                    print("A tela de inclusão ja esta aberta. Pulando click...")
                    
                print("Preenchendo Cabeçalho (505)...")
                locator_tm = pagina.locator("wa-text-input[name='cTm'] input[type='text']")
                locator_tm.wait_for(state="visible", timeout=30000)
                locator_tm.fill("505")
                pagina.keyboard.press("Enter")
                
                primeira_linha = pagina.locator("table").nth(1).locator("tbody tr").nth(0)
                primeira_linha.locator("td[id='0']").wait_for(state="visible", timeout=15000)
                pagina.wait_for_timeout(500) 
                
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
                            
                            # Correção do erro de sintaxe: removido o filter(state="visible")
                            botao_ok_obs = pagina.get_by_title("Ok").first
                            # Só executamos essa espera se o botão ainda estiver na tela
                            try:
                                botao_ok_obs.wait_for(state="hidden", timeout=5000)
                            except Exception:
                                pass # Se o botão sumiu instantaneamente, ignora o erro
                            
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
                            botao_fechar.first.wait_for(state="visible", timeout=2000)
                            modal_apareceu = True
                        except Exception:
                            modal_apareceu = False
                            
                        if modal_apareceu:
                            print(f"  Modal de erro detectado para a TAT {item['tat']} (com prefixo). Tentando sem prefixo...")
                            botao_fechar.first.click()
                            pagina.wait_for_timeout(500)
                            celula_tat = linha_alvo.locator('td[id="31"]')
                            tat_input = ativar_celula_robustamente(pagina, celula_tat, 'wa-text-input[name="M->D3_CLVL"] input')
                            tat_input.fill(f"{item['tat']}")
                            pagina.keyboard.press("Enter")
                            try:
                                botao_fechar.first.wait_for(state="visible", timeout=2000)
                                segunda_falha = True
                            except Exception:
                                segunda_falha = False
                                
                            if segunda_falha:
                                print(f"  ABORTANDO documento: TAT {item['tat']} rejeitada.")
                                botao_fechar.first.click()
                                pagina.wait_for_timeout(500)
                                recuperar_tela(pagina)
                                raise RuntimeError(f"TAT inválida no Protheus: {item['tat']}")
                                
                        if linha_idx < len(linhas_para_digitar) - 1:
                            pagina.keyboard.press("ArrowDown")
                            nova_linha = pagina.locator("table").nth(1).locator("tbody tr").nth(linha_idx + 1)
                            nova_linha.wait_for(state="attached", timeout=5000)
                            pagina.wait_for_timeout(300) 
                            
                    print(f"Linhas da TAT {tat_atual} preenchidas. Salvando...")
                    botao_salvar = pagina.locator('wa-button').filter(has_text="Salvar")
                    botao_salvar.wait_for(state="visible", timeout=5000)
                    botao_salvar.click()
                    
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