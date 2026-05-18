from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from ..models import Usuario, ParceiroConfig, Venda, Saque
from ..extensions import db
from datetime import datetime
import random
import string

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('admin.dashboard') if current_user.role == 'admin' else url_for('parceiros.dashboard'))
    if request.method == 'POST':
        user = Usuario.query.filter_by(email=request.form.get('email')).first()
        if user and user.check_senha(request.form.get('senha')):
            login_user(user)
            return redirect(url_for('admin.dashboard') if user.role == 'admin' else url_for('parceiros.dashboard'))
        flash('Credenciais inválidas.')
    return render_template('admin/login.html')

@admin_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('admin.login'))

@admin_bp.route('/dashboard')
@login_required
def dashboard():
    if current_user.role != 'admin': return redirect(url_for('parceiros.dashboard'))
    
    data_inicio = request.args.get('data_inicio')
    data_fim = request.args.get('data_fim')
    
    query_vendas = Venda.query
    if data_inicio:
        inicio_dt = datetime.strptime(data_inicio, '%Y-%m-%d')
        query_vendas = query_vendas.filter(Venda.data_venda >= inicio_dt)
    if data_fim:
        fim_dt = datetime.strptime(data_fim + " 23:59:59", '%Y-%m-%d %H:%M:%S')
        query_vendas = query_vendas.filter(Venda.data_venda <= fim_dt)
        
    vendas = query_vendas.order_by(Venda.data_venda.asc()).all()
    
    faturamento_total = sum(v.valor_total for v in vendas)
    comissoes_totais = sum(v.valor_comissao for v in vendas)
    total_afiliados = ParceiroConfig.query.count()
    
    # Prepara dados para o gráfico (Agrupamento por dia)
    vendas_diarias = {}
    for v in vendas:
        dia = v.data_venda.strftime('%d/%m/%Y')
        vendas_diarias[dia] = vendas_diarias.get(dia, 0) + v.valor_total
        
    labels_grafico = list(vendas_diarias.keys())
    valores_grafico = list(vendas_diarias.values())

    return render_template('admin/dashboard.html', 
                           faturamento_total=faturamento_total, comissoes_totais=comissoes_totais, 
                           total_afiliados=total_afiliados, labels_grafico=labels_grafico, 
                           valores_grafico=valores_grafico, d_inicio=data_inicio, d_fim=data_fim)

@admin_bp.route('/afiliados')
@login_required
def afiliados():
    if current_user.role != 'admin': return redirect(url_for('parceiros.dashboard'))
    busca = request.args.get('busca', '')
    if busca:
        lista = ParceiroConfig.query.join(Usuario).filter(ParceiroConfig.nome.ilike(f'%{busca}%')).all()
    else:
        lista = ParceiroConfig.query.all()
    return render_template('admin/afiliados.html', afiliados=lista, busca=busca)

@admin_bp.route('/financeiro')
@login_required
def financeiro():
    if current_user.role != 'admin': return redirect(url_for('parceiros.dashboard'))
    vendas = Venda.query.order_by(Venda.data_venda.desc()).all()
    saques = Saque.query.filter_by(status='pendente').all()
    return render_template('admin/financeiro.html', vendas=vendas, saques=saques)

