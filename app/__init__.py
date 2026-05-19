from flask import Flask, redirect, url_for, request
from .extensions import db
from flask_login import LoginManager, current_user
import os

def create_app():
    app = Flask(__name__)
    
    # Configurações do Banco de Dados e Segurança
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'chave-secreta-ellic-producao')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    db.init_app(app)
    
    # Configuração de Autenticação
    login_manager = LoginManager()
    login_manager.login_view = 'admin.login'
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        from .models import Usuario
        return Usuario.query.get(int(user_id))

    # Registo de Rotas
    from .admin.routes import admin_bp
    from .parceiros.routes import parceiros_bp
    from .webhook.routes import webhook_bp

    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(parceiros_bp, url_prefix='/parceiros')
    app.register_blueprint(webhook_bp, url_prefix='/api/webhook')

    # Validação Global do Onboarding
    @app.before_request
    def check_senha_temporaria():
        if request.endpoint and 'static' not in request.endpoint and request.endpoint != 'admin.nova_senha' and request.endpoint != 'admin.logout':
            if current_user.is_authenticated and getattr(current_user, 'senha_temporaria', False):
                return redirect(url_for('admin.nova_senha'))

    # Criação Automática das Tabelas e do Acesso Master
    with app.app_context():
        db.create_all()
        from .models import Usuario
        
        admin = Usuario.query.filter_by(email='admin@ellic.com.br').first()
        if not admin:
            novo_admin = Usuario(email='admin@ellic.com.br', role='admin', senha_temporaria=False)
            novo_admin.set_senha('admin123')
            db.session.add(novo_admin)
            db.session.commit()

    return app

