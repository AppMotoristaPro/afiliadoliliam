from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from ..models import Usuario, ParceiroConfig, Venda
from ..extensions import db

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    # Se já estiver logado, redireciona para o painel correto
    if current_user.is_authenticated:
        if current_user.role == 'admin':
            return redirect(url_for('admin.dashboard'))
        return redirect(url_for('parceiros.dashboard'))

    if request.method == 'POST':
        email = request.form.get('email')
        senha = request.form.get('senha')
        user = Usuario.query.filter_by(email=email).first()
        
        # Verifica se o usuário existe e se a senha criptografada bate
        if user and user.check_senha(senha):
            login_user(user)
            if user.role == 'admin':
                return redirect(url_for('admin.dashboard'))
            else:
                return redirect(url_for('parceiros.dashboard'))
                
        flash('E-mail ou senha inválidos.')
        
    return render_template('admin/login.html')

@admin_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('admin.login'))

@admin_bp.route('/dashboard')
@login_required
def dashboard():
    # Proteção de rota: expulsa quem não é admin
    if current_user.role != 'admin':
        return redirect(url_for('parceiros.dashboard'))
        
    parceiros = ParceiroConfig.query.all()
    # Aqui vamos passar os dados para construir a tabela limpa no front-end
    return render_template('admin/dashboard.html', parceiros=parceiros)

