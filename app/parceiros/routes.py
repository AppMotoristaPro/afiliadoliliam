from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user
from ..models import ParceiroConfig, Venda

# O ERRO ESTAVA AQUI: O Flask precisa encontrar exatamente o nome 'parceiros_bp'
parceiros_bp = Blueprint('parceiros', __name__)

@parceiros_bp.route('/dashboard')
@login_required
def dashboard():
    if current_user.role != 'parceiro':
        return redirect(url_for('admin.dashboard'))
        
    config = ParceiroConfig.query.filter_by(usuario_id=current_user.id).first()
    vendas = Venda.query.filter_by(parceiro_id=config.id).order_by(Venda.data_venda.desc()).all()
    
    saldo_pago = sum(v.valor_comissao for v in vendas if v.status_pagamento == 'pago')
    saldo_pendente = sum(v.valor_comissao for v in vendas if v.status_pagamento == 'pendente')
    
    return render_template('parceiros/dashboard.html', 
                           config=config, 
                           vendas=vendas, 
                           saldo_pago=saldo_pago, 
                           saldo_pendente=saldo_pendente)

