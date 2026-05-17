from app import create_app
from app.extensions import db
from app.models import Usuario, ParceiroConfig

# Inicializa o app para ter acesso às configurações do banco
app = create_app()

with app.app_context():
    print("Verificando banco de dados...")
    
    # 1. Criação do Admin (Dona da loja)
    admin_email = 'admin@lojadacliente.com.br'
    if not Usuario.query.filter_by(email=admin_email).first():
        print("Criando usuário Admin...")
        admin = Usuario(email=admin_email, role='admin')
        admin.set_senha('admin123') # Senha de teste
        db.session.add(admin)
    else:
        print("Usuário Admin já existe.")

    # 2. Criação do Parceiro de Teste
    parceiro_email = 'parceiro@teste.com'
    parceiro_existente = Usuario.query.filter_by(email=parceiro_email).first()
    
    if not parceiro_existente:
        print("Criando usuário Parceiro...")
        parceiro = Usuario(email=parceiro_email, role='parceiro')
        parceiro.set_senha('parceiro123') # Senha de teste
        db.session.add(parceiro)
        db.session.flush() # Gera o ID do parceiro sem comitar ainda
        
        print("Criando configuração e link UTM do Parceiro...")
        config = ParceiroConfig(
            usuario_id=parceiro.id,
            nome='João Parceiro',
            codigo_utm='PRC-7777',
            taxa_comissao=15.0, # 15% de comissão
            chave_pix='11999999999'
        )
        db.session.add(config)
    else:
        print("Usuário Parceiro já existe.")

    # Salva tudo no banco de dados
    db.session.commit()
    print("\n✅ Processo finalizado!")
    print("--------------------------------------------------")
    print("DADOS DE ACESSO PARA TESTE:")
    print(f"Admin    -> Email: {admin_email} | Senha: admin123")
    print(f"Parceiro -> Email: {parceiro_email}      | Senha: parceiro123")
    print("--------------------------------------------------")

