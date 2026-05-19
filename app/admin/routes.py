from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from ..models import Usuario, ParceiroConfig, Venda, Pagamento
from ..extensions import db
from datetime import datetime
import random
import string
import re

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        if getattr(current_user, 'senha_temporaria', False):
            return redirect(url_for('admin.nova_senha'))
        return redirect(url_for('admin.dashboard') if current_user.role == 'admin' else url_for('parceiros.dashboard'))
        
    if request.method == 'POST':
        user = Usuario.query.filter_by(email=request.form.get('email')).first()
        if user and user.check_senha(request.form.get('senha')):
            login_user(user)
            if user.senha_temporaria: 
                return redirect(url_for('admin.nova_senha'))
            return redirect(url_for('admin.dashboard') if user.role == 'admin' else url_for('parceiros.dashboard'))
        flash('E-mail ou senha inválidos.')
        
    return render_template('admin/login.html')

@admin_bp.route('/nova-senha', methods=['GET', 'POST'])
@login_required
def nova_senha():
    if not getattr(current_user, 'senha_temporaria', False): 
        return redirect(url_for('admin.dashboard') if current_user.role == 'admin' else url_for('parceiros.dashboard'))
        
    config = current_user.configuracao
        
    if request.method == 'POST':
        nova_senha = request.form.get('nova_senha')
        confirmacao = request.form.get('confirmacao')
        
        if len(nova_senha) < 8 or not re.search(r'[A-Z]', nova_senha) or not re.search(r'\d', nova_senha):
            flash('A senha não atende aos requisitos de segurança.')
            return render_template('admin/nova_senha.html', config=config)
            
        if nova_senha != confirmacao:
            flash('As senhas não coincidem.')
            return render_template('admin/nova_senha.html', config=config)
            
        config.nome = request.form.get('nome')
        config.cpf = request.form.get('cpf')
        config.data_nascimento = request.form.get('data_nascimento')
        config.chave_pix = request.form.get('chave_pix')
        config.cep = request.form.get('cep')
        
        endereco_completo = f"{request.form.get('logradouro')}, {request.form.get('numero')} - {request.form.get('bairro')}, {request.form.get('cidade')}"
        config.endereco = endereco_completo
            
        current_user.set_senha(nova_senha)
        current_user.senha_temporaria = False
        db.session.commit()
        flash('Cadastro finalizado com sucesso! Bem-vinda à Ellic.')
        return redirect(url_for('parceiros.dashboard'))
        
    return render_template('admin/nova_senha.html', config=config)

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
        
    return render_template(
        'admin/dashboard.html', 
        fat_total=fat_total, com_total=com_total, 
        tot_afiliados=tot_afiliados, 
        labels_grafico=list(vendas_diarias.keys()), 
        valores_grafico=list(vendas_diarias.values()), 
        dia=dia, mes=mes
    )

@admin_bp.route('/afiliados', methods=['GET', 'POST'])
@login_required
def afiliados():
    if current_user.role != 'admin': 
        return redirect(url_for('parceiros.dashboard'))
        
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
        
        # Coleta a taxa de comissão definida no formulário (padrão 10.0 se vazio)
        taxa_definida = request.form.get('taxa_comissao')
        taxa_final = float(taxa_definida) if taxa_definida else 10.0
        
        config = ParceiroConfig(
            usuario_id=novo_user.id, 
            nome=request.form.get('nome'), 
            cpf=request.form.get('cpf'),
            codigo_utm=utm, 
            taxa_comissao=taxa_final
        )
        db.session.add(config)
        db.session.commit()
        flash(f'Acesso Liberado! E-mail: {email} | Senha provisória: {senha_temp}')
        return redirect(url_for('admin.afiliados'))
        
    lista = ParceiroConfig.query.all()
    return render_template('admin/afiliados.html', afiliados=lista)

@admin_bp.route('/afiliados/<int:id>/editar', methods=['POST'])
@login_required
def editar_afiliado(id):
    if current_user.role != 'admin':
        return redirect(url_for('parceiros.dashboard'))
        
    parceiro = ParceiroConfig.query.get_or_404(id)
    
    # Atualiza a comissão convertendo para número decimal
    taxa_input = request.form.get('taxa_comissao')
    if taxa_input:
        try:
            parceiro.taxa_comissao = float(taxa_input)
        except ValueError:
            flash('Valor de comissão inválido.')
            return redirect(url_for('admin.afiliados'))
            
    # Permite editar também o nome e CPF se o administrador desejar corrigir algo
    parceiro.nome = request.form.get('nome', parceiro.nome)
    parceiro.cpf = request.form.get('cpf', parceiro.cpf)
    parceiro.celular = request.form.get('celular', parceiro.celular)
    parceiro.chave_pix = request.form.get('chave_pix', parceiro.chave_pix)
    parceiro.endereco = request.form.get('endereco', parceiro.endereco)
    
    db.session.commit()
    flash(f'Configurações de {parceiro.nome} atualizadas com sucesso!')
    return redirect(url_for('admin.afiliados'))

@admin_bp.route('/vendas')
@login_required
def vendas():
    if current_user.role != 'admin': 
        return redirect(url_for('parceiros.dashboard'))
    todas_vendas = Venda.query.order_by(Venda.data_venda.desc()).all()
    return render_template('admin/vendas.html', vendas=todas_vendas)

@admin_bp.route('/financeiro')
@login_required
def financeiro():
    if current_user.role != 'admin': 
        return redirect(url_for('parceiros.dashboard'))
        
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
            'produtos_resumo': str(v.produtos_resumo),
            'valor_total': float(v.valor_total),
            'valor_comissao': float(v.valor_comissao)
        })
        
    historico_pagamentos = Pagamento.query.order_by(Pagamento.data_pagamento.desc()).all()
    return render_template('admin/financeiro.html', financeiro=dados.values(), historico=historico_pagamentos)

@admin_bp.route('/financeiro/<int:id>/pagar', methods=['POST'])
@login_required
def pagar_comissao(id):
    if current_user.role != 'admin': 
        return redirect(url_for('parceiros.dashboard'))
        
    vendas_pendentes = Venda.query.filter_by(parceiro_id=id, status_pagamento='pendente').all()
    if not vendas_pendentes:
        return redirect(url_for('admin.financeiro'))
        
    parceiro = ParceiroConfig.query.get_or_404(id)
    total_comissao = sum(v.valor_comissao for v in vendas_pendentes)
    
    recibo = Pagamento(parceiro_id=parceiro.id, valor_pago=total_comissao, chave_pix_utilizada=parceiro.chave_pix or 'Não Informada')
    db.session.add(recibo)
    
    for v in vendas_pendentes:
        v.status_pagamento = 'pago'
        
    db.session.commit()
    flash(f'Repasse liquidado com sucesso.')
    return redirect(url_for('admin.financeiro'))

