import os
import sys
import subprocess
import glob

# Importando os módulos do nosso sistema
from bussines_logic import recuperar_pendencias_travadas, planejar_movimentacao
from bot_protheus import executar_robo_protheus

PASTA_BASE = os.path.dirname(os.path.abspath(__file__))
CAMINHO_PUXAR_SALDO = os.path.join(PASTA_BASE, "puxar_saldo.py")
PASTA_DOCUMENTOS = os.path.join(PASTA_BASE, "documentos")

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

if __name__ == '__main__':
    print("--- INICIANDO SISTEMA DE REQUISIÇÃO EXTRA ---")
    
    # Etapa 1: Limpeza do Banco de Dados
    recuperar_pendencias_travadas()
    
    # Etapa 2: Atualização do Saldo
    perguntar_puxar_saldo()
    caminho_saldo = pegar_ultimo_relatorio()
    print(f"Usando relatório de saldo: {caminho_saldo}")
    
    # Etapa 3: Regra de Negócio (Matemática e Quebra de Endereços)
    plano_agrupado = planejar_movimentacao(caminho_saldo)
    
    # Etapa 4: Robô Playwright (Automação Visual)
    executar_robo_protheus(plano_agrupado)
    
    print("--- EXECUÇÃO FINALIZADA ---")