from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from ..models import Usuario, ParceiroConfig, Venda

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        if current_user.role == 'admin':
            return redirect(url_for('admin.dashboard'))
        return redirect(url_for('parceiros.dashboard'))

    if request.method == 'POST':
        email = request.form.get('email')
        senha = request.form.get('senha')
        user = Usuario.query.filter_by(email=email).first()
        
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
    if current_user.role != 'admin':
        return redirect(url_for('parceiros.dashboard'))
        
    parceiros = ParceiroConfig.query.all()
    vendas_totais = Venda.query.all()
    
    # Métricas consolidadas para o topo da visão da loja
    faturamento_total_parceiros = sum(v.valor_total for v in vendas_totais)
    comissoes_totais_geradas = sum(v.valor_comissao for v in vendas_totais)
    total_parceiros = len(parceiros)
    
    return render_template('admin/dashboard.html', 
                           parceiros=parceiros,
                           faturamento_total=faturamento_total_parceiros,
                           comissoes_totais=comissoes_totais_geradas,
                           total_parceiros=total_parceiros)

