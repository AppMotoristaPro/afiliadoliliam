from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from ..models import Usuario, ParceiroConfig, Venda, Pagamento
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
    if current_user.role != 'admin': return redirect(url_for('parceiros.dashboard'))
    dia = request.args.get('dia')
    mes = request.args.get('mes')
    
    query = Venda.query
    if dia:
        dt = datetime.strptime(dia, '%Y-%m-%d')
        query = query.filter(db.func.date(Venda.data_venda) == dt.date())
    elif mes:
        ano, m = mes.split('-')
        query = query.filter(db.extract('year', Venda.data_venda) == int(ano), db.extract('month', Venda.data_venda) == int(m))
        
    vendas = query.order_by(Venda.data_venda.asc()).all()
    fat_total = sum(v.valor_total for v in vendas)
    com_total = sum(v.valor_comissao for v in vendas)
    tot_afiliados = ParceiroConfig.query.count()
    
    vendas_diarias = {}
    for v in vendas:
        d = v.data_venda.strftime('%d/%m')
        vendas_diarias[d] = vendas_diarias.get(d, 0) + v.valor_total
        
    return render_template('admin/dashboard.html', fat_total=fat_total, com_total=com_total, 
                           tot_afiliados=tot_afiliados, labels_grafico=list(vendas_diarias.keys()), 
                           valores_grafico=list(vendas_diarias.values()), dia=dia, mes=mes)

@admin_bp.route('/afiliados', methods=['GET', 'POST'])
@login_required
def afiliados():
    if current_user.role != 'admin': return redirect(url_for('parceiros.dashboard'))
    if request.method == 'POST':
        email = request.form.get('email')
        if Usuario.query.filter_by(email=email).first():
            flash('E-mail já cadastrado.')
            return redirect(url_for('admin.afiliados'))
            
        senha_temp = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
        novo_user = Usuario(email=email, role='parceiro', senha_temporaria=True)
        novo_user.set_senha(senha_temp)
        db.session.add(novo_user)
        db.session.flush()
        
        utm = f"ELLIC-{random.randint(1000, 9999)}"
        config = ParceiroConfig(usuario_id=novo_user.id, nome=request.form.get('nome'), 
                                codigo_utm=utm, taxa_comissao=float(request.form.get('taxa', 10.0)),
                                chave_pix=request.form.get('chave_pix'), celular=request.form.get('celular'))
        db.session.add(config)
        db.session.commit()
        flash(f'Afiliado criado! ID Afiliado: {utm} | Senha provisória: {senha_temp}')
        return redirect(url_for('admin.afiliados'))
        
    lista = ParceiroConfig.query.all()
    return render_template('admin/afiliados.html', afiliados=lista)

@admin_bp.route('/afiliado/<int:id>/editar', methods=['POST'])
@login_required
def editar_afiliado(id):
    if current_user.role != 'admin': return redirect(url_for('parceiros.dashboard'))
    parceiro = ParceiroConfig.query.get_or_404(id)
    novo_email = request.form.get('email')
    if novo_email != parceiro.usuario.email and not Usuario.query.filter_by(email=novo_email).first():
        parceiro.usuario.email = novo_email
        
    parceiro.celular = request.form.get('celular')
    parceiro.chave_pix = request.form.get('chave_pix')
    
    if request.form.get('resetar_senha'):
        senha_temp = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
        parceiro.usuario.set_senha(senha_temp)
        parceiro.usuario.senha_temporaria = True
        flash(f'Senha resetada para: {senha_temp}')
        
    db.session.commit()
    return redirect(url_for('admin.afiliados'))

@admin_bp.route('/financeiro')
@login_required
def financeiro():
    if current_user.role != 'admin': return redirect(url_for('parceiros.dashboard'))
    
    vendas_pendentes = Venda.query.filter_by(status_pagamento='pendente').order_by(Venda.data_venda.desc()).all()
    dados = {}
    for v in vendas_pendentes:
        if v.parceiro_id not in dados:
            dados[v.parceiro_id] = {'parceiro': v.parceiro, 'total_venda': 0.0, 'total_comissao': 0.0, 'extrato': [], 'ultima_data': v.data_venda}
        dados[v.parceiro_id]['total_venda'] += v.valor_total
        dados[v.parceiro_id]['total_comissao'] += v.valor_comissao
        dados[v.parceiro_id]['extrato'].append({
            'data_venda': v.data_venda.strftime('%Y-%m-%dT%H:%M:%S'),
            'pedido_id_nuvemshop': v.pedido_id_nuvemshop,
            'produtos_resumo': str(v.produtos_resumo) if v.produtos_resumo else "Produtos Diversos",
            'valor_total': float(v.valor_total),
            'valor_comissao': float(v.valor_comissao)
        })
        
    # Puxa o histórico consolidado de repasses realizados para a auditoria do Admin
    historico_pagamentos = Pagamento.query.order_by(Pagamento.data_pagamento.desc()).all()
    return render_template('admin/financeiro.html', financeiro=dados.values(), historico=historico_pagamentos)

@admin_bp.route('/financeiro/<int:id>/pagar', methods=['POST'])
@login_required
def pagar_comissao(id):
    if current_user.role != 'admin': return redirect(url_for('parceiros.dashboard'))
    
    vendas_pendentes = Venda.query.filter_by(parceiro_id=id, status_pagamento='pendente').all()
    if not vendas_pendentes:
        flash('Nenhum valor pendente encontrado.')
        return redirect(url_for('admin.financeiro'))
        
    parceiro = ParceiroConfig.query.get_or_404(id)
    total_comissao = sum(v.valor_comissao for v in vendas_pendentes)
    
    # 1. Registra o Log de Pagamento com a Chave PIX exata do momento
    recibo = Pagamento(
        parceiro_id=parceiro.id,
        valor_pago=total_comissao,
        chave_pix_utilizada=parceiro.chave_pix or 'Não Informada'
    )
    db.session.add(recibo)
    
    # 2. Modifica as vendas para o status de Pago, limpando o extrato corrente
    for v in vendas_pendentes:
        v.status_pagamento = 'pago'
        
    db.session.commit()
    flash(f'Sucesso! Repasse de R$ {total_comissao:.2f} arquivado no histórico de {parceiro.nome}.')
    return redirect(url_for('admin.financeiro'))

