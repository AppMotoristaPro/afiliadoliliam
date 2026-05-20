from flask import Flask, redirect, url_for, request, send_from_directory
from .extensions import db
from flask_login import LoginManager, current_user
import os
from .utils import gerar_icones_pwa

def create_app():
    app = Flask(__name__)
    
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'chave-secreta-ellic-producao')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
    }

    db.init_app(app)
    
    login_manager = LoginManager()
    login_manager.login_view = 'admin.login'
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        from .models import Usuario
        return Usuario.query.get(int(user_id))

    # TRAVA GLOBAL: Obriga a troca da senha temporária antes de liberar a plataforma
    @app.before_request
    def check_senha_temporaria():
        if current_user.is_authenticated and getattr(current_user, 'senha_temporaria', False):
            # Deixa passar apenas a tela de nova senha, o logout e o carregamento do CSS/imagens
            if request.endpoint not in ['admin.nova_senha', 'admin.logout', 'static']:
                return redirect(url_for('admin.nova_senha'))

    from .admin.routes import admin_bp
    from .parceiros.routes import parceiros_bp
    from .webhook.routes import webhook_bp

    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(parceiros_bp, url_prefix='/parceiros')
    app.register_blueprint(webhook_bp, url_prefix='/api/webhook')

    # Rota para servir o Service Worker a partir da raiz
    @app.route('/sw.js')
    def serve_sw():
        return send_from_directory(os.path.join(app.root_path, '..'), 'sw.js')

    with app.app_context():
        db.create_all()
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
            
        # Garante a geração dos ícones PWA no boot
        gerar_icones_pwa(app)

    return app

