import os
from flask import Flask
from .extensions import db, login_manager

def create_app():
    app = Flask(__name__)
    
    # Configurações de Segurança e Ambiente
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'chave-secreta-dev-segura')
    
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        database_url = 'sqlite:///fallback.db'
        
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
        
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Inicializa as extensões
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'admin.login'

    @login_manager.user_loader
    def load_user(user_id):
        from .models import Usuario
        return Usuario.query.get(int(user_id))

    # Registro de Blueprints
    from .admin.routes import admin_bp
    from .parceiros.routes import parceiros_bp
    from .webhook.routes import webhook_bp

    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(parceiros_bp, url_prefix='/parceiros')
    app.register_blueprint(webhook_bp, url_prefix='/api/webhook')

    # Criação de tabelas e população automática do banco de dados em nuvem
    with app.app_context():
        db.create_all()
        
        from .models import Usuario, ParceiroConfig
        
        # Injeta automaticamente o Admin de teste no Neon caso não exista
        admin_email = 'admin@lojadacliente.com.br'
        if not Usuario.query.filter_by(email=admin_email).first():
            admin = Usuario(email=admin_email, role='admin')
            admin.set_senha('admin123')
            db.session.add(admin)
            
        # Injeta automaticamente o Parceiro de teste no Neon caso não exista
        parceiro_email = 'parceiro@teste.com'
        if not Usuario.query.filter_by(email=parceiro_email).first():
            parceiro = Usuario(email=parceiro_email, role='parceiro')
            parceiro.set_senha('parceiro123')
            db.session.add(parceiro)
            db.session.flush()
            
            config = ParceiroConfig(
                usuario_id=parceiro.id,
                nome='João Parceiro',
                codigo_utm='PRC-7777',
                taxa_comissao=15.0,
                chave_pix='11999999999'
            )
            db.session.add(config)
            
        db.session.commit()

    return app

