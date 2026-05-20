import os
from PIL import Image

def gerar_icones_pwa(app):
    # Caminhos das pastas
    static_dir = os.path.join(app.root_path, 'static')
    icons_dir = os.path.join(static_dir, 'icons')
    
    # Cria a pasta 'icons' dentro de static se ela não existir
    if not os.path.exists(icons_dir):
        os.makedirs(icons_dir)
        
    # O script vai procurar por uma imagem chamada 'logo_base.png'
    logo_path = os.path.join(static_dir, 'logo_base.png')
    
    # Se a logo não existir, o sistema não crasha, apenas avisa
    if not os.path.exists(logo_path):
        print("Aviso: 'logo_base.png' não encontrada na pasta static. Ícones PWA ignorados.")
        return

    try:
        with Image.open(logo_path) as img:
            # Converte para RGBA para garantir que a transparência (fundo) é mantida
            img = img.convert("RGBA")
            
            # Transforma a imagem num quadrado perfeito (crop centralizado)
            width, height = img.size
            if width != height:
                new_size = min(width, height)
                left = (width - new_size) / 2
                top = (height - new_size) / 2
                right = (width + new_size) / 2
                bottom = (height + new_size) / 2
                img = img.crop((left, top, right, bottom))
            
            # Tamanhos estritos exigidos pelo manifesto do PWA
            sizes = [(192, 192), (512, 512)]
            
            for size in sizes:
                icon_path = os.path.join(icons_dir, f'icon-{size[0]}x{size[0]}.png')
                # Gera o ícone apenas se ele ainda não existir, para não atrasar o servidor
                if not os.path.exists(icon_path):
                    resized_img = img.resize(size, Image.Resampling.LANCZOS)
                    resized_img.save(icon_path, "PNG")
                    print(f"Sucesso: Ícone PWA {size[0]}x{size[0]} gerado!")
                    
    except Exception as e:
        print(f"Erro ao processar ícones da aplicação: {e}")

