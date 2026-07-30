import os
from dotenv import load_dotenv
from supabase import create_client, Client

# Carrega as variáveis do arquivo .env
load_dotenv()

# Busca as credenciais de ambiente
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

def conectar_banco() -> Client:
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise ValueError("Credenciais do Supabase não encontradas no arquivo .env")
    
    return create_client(SUPABASE_URL, SUPABASE_KEY)

# Instância única exportada para uso no sistema
db = conectar_banco()