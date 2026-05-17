import os
from flask import Flask
from .extensions import db, login_manager

def create_app():
    app = Flask(__name__)
    
    # Configurações Básicas e de Banco de Dados
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'chave-secreta-dev-segura')
    
    # No Render, a variável de ambiente será DATABASE_URL (sua URL do Neon)
    # Se não encontrar, tenta criar um sqlite local só para evitar crash no desenvolvimento inicial
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///app.db')
    
    # Ajuste de URL do Postgres (Render às vezes passa 'postgres://' mas o SQLAlchemy exige 'postgresql://')
    if app.config['SQLALCHEMY_DATABASE_URI'] and app.config['SQLALCHEMY_DATABASE_URI'].startswith("postgres://"):
        app.config['SQLALCHEMY_DATABASE_URI'] = app.config['SQLALCHEMY_DATABASE_URI'].replace("postgres://", "postgresql://", 1)
        
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Inicializa Extensões
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'admin.login' # Define para onde mandar quem não está logado

    @login_manager.user_loader
    def load_user(user_id):
        from .models import Usuario
        return Usuario.query.get(int(user_id))

    # Importa e registra os Blueprints
    from .admin.routes import admin_bp
    from .parceiros.routes import parceiros_bp
    from .webhook.routes import webhook_bp

    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(parceiros_bp, url_prefix='/parceiros')
    app.register_blueprint(webhook_bp, url_prefix='/api/webhook')

    # Cria as tabelas automaticamente (Ideal para a nossa fase atual)
    with app.app_context():
        db.create_all()

    return app

