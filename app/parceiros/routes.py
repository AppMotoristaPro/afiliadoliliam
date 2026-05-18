from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from ..models import ParceiroConfig, Venda, LinkGerado, Pagamento
from ..extensions import db

parceiros_bp = Blueprint('parceiros', __name__)

@parceiros_bp.route('/dashboard')
@login_required
def dashboard():
    if current_user.role != 'parceiro': return redirect(url_for('admin.dashboard'))
    config = ParceiroConfig.query.filter_by(usuario_id=current_user.id).first()
    vendas = Venda.query.filter_by(parceiro_id=config.id).all()
    
    vol_vendas = sum(v.valor_total for v in vendas)
    vol_comissoes = sum(v.valor_comissao for v in vendas)
    return render_template('parceiros/dashboard.html', config=config, vol_vendas=vol_vendas, vol_comissoes=vol_comissoes)

@parceiros_bp.route('/links', methods=['GET', 'POST'])
@login_required
def links():
    if current_user.role != 'parceiro': return redirect(url_for('admin.dashboard'))
    config = ParceiroConfig.query.filter_by(usuario_id=current_user.id).first()
    
    if request.method == 'POST':
        original = request.form.get('url_original').strip()
        if original:
            base = original.split('?')[0]
            if base.endswith('/'): base = base[:-1]
            rastreada = f"{base}/?utm_campaign={config.codigo_utm}"
            
            novo_link = LinkGerado(parceiro_id=config.id, url_original=original, url_rastreada=rastreada)
            db.session.add(novo_link)
            db.session.commit()
            flash('Link rastreável gerado com sucesso.')
            
    historico = LinkGerado.query.filter_by(parceiro_id=config.id).order_by(LinkGerado.data_criacao.desc()).all()
    return render_template('parceiros/links.html', config=config, historico=historico)

@parceiros_bp.route('/vendas')
@login_required
def vendas():
    if current_user.role != 'parceiro': return redirect(url_for('admin.dashboard'))
    config = ParceiroConfig.query.filter_by(usuario_id=current_user.id).first()
    historico_vendas = Venda.query.filter_by(parceiro_id=config.id).order_by(Venda.data_venda.desc()).all()
    return render_template('parceiros/vendas.html', vendas=historico_vendas)

@parceiros_bp.route('/recebimentos')
@login_required
def recebimentos():
    if current_user.role != 'parceiro': return redirect(url_for('admin.dashboard'))
    config = ParceiroConfig.query.filter_by(usuario_id=current_user.id).first()
    
    # Coleta a auditoria de faturamento transferido pela administração
    comprovantes = Pagamento.query.filter_by(parceiro_id=config.id).order_by(Pagamento.data_pagamento.desc()).all()
    return render_template('parceiros/recebimentos.html', pagamentos=comprovantes)

