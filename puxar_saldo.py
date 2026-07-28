import os
import time
import glob
from datetime import datetime
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv

load_dotenv()

senha = os.getenv('PASSWORD', '')
web = os.getenv('URL', '')
nome = os.getenv('NOME', '')
downloads_dir = os.getenv('CAMINHO_DOWNLOAD', '')
caminho_profile= os.getenv('CAMINHO_PROFILE', '')


def executar_pull_saldo():
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=caminho_profile,
            headless=False,
            channel="msedge",
        )
        pagina = context.pages[0] if context.pages else context.new_page()
        pagina.goto(web, wait_until="networkidle", timeout=60000)
        pagina.wait_for_load_state("networkidle")
       
        pagina.bring_to_front()
        pagina.wait_for_timeout(3800)
        pagina.get_by_role("button", name="Ok").click(timeout=5000)
        pagina.wait_for_timeout(2000)
        

        try:
            # ── LOGIN ──
            print("Acessando o Protheus...")
            pagina.goto(web, wait_until="networkidle", timeout=60000)
            pagina.wait_for_load_state("networkidle")


            pagina.bring_to_front()
            pagina.wait_for_timeout(3800)
            pagina.get_by_role("button", name="Ok").click(timeout=5000)
            pagina.wait_for_timeout(2000)
            # input("Clique em Permitir (marcando o checkbox se existir) e pressione Enter aqui...")
            # context.close()
            

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

            # ── NAVEGAÇÃO: Favoritos → Saldo Por Endereço ──
            print("Clicando em Favoritos...")
            pagina.locator('span[title="Favoritos"]').click()
            pagina.wait_for_timeout(2500)

            print("Clicando em Saldo Por Endereço...")
            pagina.locator('span[title="Saldo Por Endereço"]').click()
            pagina.locator('wa-button', has_text="utras Ações").wait_for(state="visible", timeout=20000)
            print("Interface carregada.")


            # ── EXPORTAÇÃO ──

            # 1. Outras Ações
            print("Clicando em Outras Ações...")
            pagina.locator('button:has-text("utras Ações")').click()
            pagina.wait_for_timeout(3500)

            # 2. Imprimir Browse
            print("Clicando em Imprimir Browse...")
            pagina.locator('span.caption:has-text("Browse")').click()
            pagina.wait_for_timeout(3700)

            # 3. Planilha
            print("Selecionando Planilha...")
            pagina.locator('button:has-text("Planilha")').click()
            pagina.wait_for_timeout(2500)

            # 4. Tab 4x até o campo de nome, seleciona tudo e digita
            print("Digitando nome do arquivo...")
            agora = datetime.now().strftime('%Y%m%d_%H%M')
            nome_arquivo = f"Relatorio_saldo_{agora}"

            for _ in range(4):
                pagina.keyboard.press("Tab")
                pagina.wait_for_timeout(200)
            pagina.keyboard.press("Control+a")
            pagina.wait_for_timeout(200)
            pagina.keyboard.type(nome_arquivo, delay=50)
            pagina.wait_for_timeout(500)

            # 5. Mudar Ambiente de Servidor pra Local
            print("Mudando Ambiente pra Local...")
            combo_ambiente = pagina.locator('select:has(option:has-text("Servidor"))').first
            combo_ambiente.evaluate('''el => {
                el.value = "1";
                el.dispatchEvent(new Event("change", { bubbles: true }));
                el.dispatchEvent(new Event("input", { bubbles: true }));
            }''')
            pagina.wait_for_timeout(1000)

            # 6. Formato de Tabela Xlsx (option value="3")
            print("Selecionando formato XLSX...")
            pagina.locator('select:has(option:has-text("Formato de Tabela Xlsx"))').select_option('3')
            pagina.wait_for_timeout(1000)

            # 7. Paisagem
            print("Selecionando Paisagem...")
            pagina.locator('label:has-text("Paisagem")').click()
            pagina.wait_for_timeout(1000)

            try:
                # 8. Desmarcar Preview
                print("Desmarcando Preview...")
                pagina.get_by_role("checkbox", name="check_box Preview").click(force=True)
                pagina.wait_for_timeout(1000)
            except:
                print(f'Erro pois desmarcou o PREVIEW')
            # 9. Imprimir (abre o dialog de salvar)
            print("Clicando em Imprimir...")
            pagina.locator('button:has-text("mprimir")').last.click()
            pagina.wait_for_timeout(3000)

            # 10. Navegar no dialog de salvar arquivo
            print("Navegando no dialog de salvar...")
            pagina.wait_for_timeout(2000)

            # C: [Sistema]
            print("  C: [Sistema]...")
            pagina.locator('label:has-text("C: [Sistema]")').dblclick()
            pagina.wait_for_timeout(1500)

            # Users
            print("  Users...")
            pagina.locator('label:has-text("Users")').dblclick()
            pagina.wait_for_timeout(1500)

        
            print("Selecionando user")
            pagina.locator('label:has-text("brian.santos")').dblclick()
            pagina.wait_for_timeout(1500)

            # Downloads
            print("  Documentos...")
            pagina.locator('label:has-text("Documents")').dblclick()
            pagina.wait_for_timeout(1500)

                
            print("   Abrindo Pasta...")
            pagina.locator('label:has-text("mov_multipla")').dblclick()
            pagina.wait_for_timeout(2000)

            print("Entrando na pasta...")
            pagina.locator("label").get_by_text("documentos", exact=True).dblclick()
            pagina.wait_for_timeout(5000)

            # 11. Abrir (salva no diretório)
            print("Clicando em Abrir...")
            pagina.locator('button:has-text("Abrir")').click()
            pagina.wait_for_timeout(5000)

            # 12. Aguardar e verificar se o arquivo foi salvo
            arquivo_esperado = os.path.join(downloads_dir, f"{nome_arquivo}*")
            print(f"\nAguardando o Protheus processar...")
            print(f"Procurando: {nome_arquivo}* em {downloads_dir}")

            encontrado = False
            for tentativa in range(60):
                time.sleep(10)
                arquivos = glob.glob(arquivo_esperado)
                if arquivos:
                    arquivo_final = max(arquivos, key=os.path.getmtime)
                    print(f"\n✓ Arquivo encontrado: {os.path.basename(arquivo_final)}")
                    print(f"  Tamanho: {os.path.getsize(arquivo_final) / 1024:.1f} KB")
                    encontrado = True
                    return
                if tentativa % 6 == 0:
                    print(f"  Ainda aguardando... ({tentativa * 10}s)")

            if not encontrado:
                print("\n✗ Arquivo não encontrado após 10 minutos.")

            print("\n✓ Processo concluído!")
            

        except Exception as e:
            print(f"\n[ERRO] {e}")
            import traceback
            traceback.print_exc()
            

        finally:
            time.sleep(5)
            context.close()

if __name__ == "__main__":
    executar_pull_saldo()