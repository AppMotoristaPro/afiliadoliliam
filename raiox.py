import os
from pathlib import Path

# Configurações
projeto_dir = os.getcwd()  # Pasta atual
saida_txt = "/sdcard/Download/backup_projeto_completo.txt"

def listar_estrutura(diretorio, prefixo=""):
    estrutura = ""
    itens = sorted(os.listdir(diretorio))
    # Ignora pastas de ambiente virtual e git
    itens = [i for i in itens if i not in ['.git', '.venv', 'venv', '__pycache__', '.env']]
    
    for i, item in enumerate(itens):
        caminho = os.path.join(diretorio, item)
        conector = "└── " if i == len(itens) - 1 else "├── "
        estrutura += f"{prefixo}{conector}{item}\n"
        if os.path.isdir(caminho):
            novo_prefixo = prefixo + ("    " if i == len(itens) - 1 else "│   ")
            estrutura += listar_estrutura(caminho, novo_prefixo)
    return estrutura

def coletar_arquivos(diretorio, arquivo_saida):
    with open(arquivo_saida, "w", encoding="utf-8") as f:
        f.write("=== ESTRUTURA DO PROJETO ===\n")
        f.write(listar_estrutura(diretorio))
        f.write("\n\n" + "="*50 + "\n\n")
        
        for root, dirs, files in os.walk(diretorio):
            # Ignora pastas desnecessárias
            if any(ignorar in root for ignorar in ['.git', '.venv', 'venv', '__pycache__']):
                continue
                
            for file in files:
                if file.endswith(('.py', '.html', '.css', '.js', '.json', '.txt')):
                    caminho_completo = os.path.join(root, file)
                    relativo = os.path.relpath(caminho_completo, diretorio)
                    
                    f.write(f"\n--- ARQUIVO: {relativo} ---\n")
                    try:
                        with open(caminho_completo, "r", encoding="utf-8") as f_in:
                            f.write(f_in.read())
                    except Exception as e:
                        f.write(f"Erro ao ler arquivo: {e}")
                    f.write("\n\n" + "-"*30 + "\n")

if __name__ == "__main__":
    coletar_arquivos(projeto_dir, saida_txt)
    print(f"Sucesso! Backup salvo em: {saida_txt}")

