from flask import Flask
from .extensions import db
from flask_login import LoginManager
import os

def create_app():
    app = Flask(__name__)
    
    # Configurações de Segurança e Banco de Dados
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'chave-secreta-ellic-producao')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # SOLUÇÃO DO ERRO SSL NEON: Força o Flask a testar a conexão antes de executar comandos
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
    }

    # Inicializa os plugins
    db.init_app(app)
    
    login_manager = LoginManager()
    login_manager.login_view = 'admin.login'
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        from .models import Usuario
        return Usuario.query.get(int(user_id))

    # Registra as Rotas (Blueprints)
    from .admin.routes import admin_bp
    from .parceiros.routes import parceiros_bp
    from .webhook.routes import webhook_bp

    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(parceiros_bp, url_prefix='/parceiros')
    app.register_blueprint(webhook_bp, url_prefix='/api/webhook')

    # Configuração de Banco de Dados Automática
    with app.app_context():
        # Recria as tabelas limpas no Neon
        db.create_all()
        
        # Garante a recriação do Administrador caso o banco tenha sido resetado
        from .models import Usuario
        admin_existente = Usuario.query.filter_by(email='admin@ellic.com.br').first()
        
        if not admin_existente:
            novo_admin = Usuario(
                email='admin@ellic.com.br',
                role='admin',
                senha_temporaria=False
            )
            novo_admin.set_senha('admin123')
            db.session.add(novo_admin)
            db.session.commit()

    return app

