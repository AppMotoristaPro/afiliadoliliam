from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from ..models import Usuario, ParceiroConfig, Venda
from ..extensions import db
import random
import string

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        if current_user.senha_temporaria:
            return redirect(url_for('admin.nova_senha'))
        return redirect(url_for('admin.dashboard') if current_user.role == 'admin' else url_for('parceiros.dashboard'))

    if request.method == 'POST':
        email = request.form.get('email')
        senha = request.form.get('senha')
        user = Usuario.query.filter_by(email=email).first()
        
        if user and user.check_senha(senha):
            login_user(user)
            if user.senha_temporaria:
                return redirect(url_for('admin.nova_senha'))
            return redirect(url_for('admin.dashboard') if user.role == 'admin' else url_for('parceiros.dashboard'))
                
        flash('E-mail ou senha inválidos.')
        
    return render_template('admin/login.html')

@admin_bp.route('/nova-senha', methods=['GET', 'POST'])
@login_required
def nova_senha():
    if not current_user.senha_temporaria:
        return redirect(url_for('admin.dashboard') if current_user.role == 'admin' else url_for('parceiros.dashboard'))
        
    if request.method == 'POST':
        nova_senha = request.form.get('nova_senha')
        confirmacao = request.form.get('confirmacao')
        
        if nova_senha != confirmacao:
            flash('As senhas não coincidem.')
            return render_template('admin/nova_senha.html')
            
        current_user.set_senha(nova_senha)
        current_user.senha_temporaria = False
        db.session.commit()
        
        flash('Senha atualizada com sucesso.')
        return redirect(url_for('admin.dashboard') if current_user.role == 'admin' else url_for('parceiros.dashboard'))
        
    return render_template('admin/nova_senha.html')

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
        
    # Sistema de Filtros Inteligentes
    busca = request.args.get('busca', '').strip()
    
    if busca:
        parceiros = ParceiroConfig.query.join(Usuario).filter(
            (ParceiroConfig.nome.ilike(f'%{busca}%')) | 
            (ParceiroConfig.codigo_utm.ilike(f'%{busca}%')) |
            (Usuario.email.ilike(f'%{busca}%'))
        ).all()
    else:
        parceiros = ParceiroConfig.query.all()
        
    vendas_totais = Venda.query.order_by(Venda.data_venda.desc()).all()
    
    faturamento_total_parceiros = sum(v.valor_total for v in vendas_totais)
    comissoes_totais_geradas = sum(v.valor_comissao for v in vendas_totais)
    total_parceiros = len(parceiros)
    
    return render_template('admin/dashboard.html', 
                           parceiros=parceiros,
                           vendas=vendas_totais,
                           faturamento_total=faturamento_total_parceiros,
                           comissoes_totais=comissoes_totais_geradas,
                           total_parceiros=total_parceiros,
                           termo_busca=busca)

@admin_bp.route('/parceiro/novo', methods=['POST'])
@login_required
def novo_parceiro():
    if current_user.role != 'admin':
        return redirect(url_for('parceiros.dashboard'))
        
    nome = request.form.get('nome')
    email = request.form.get('email')
    taxa = float(request.form.get('taxa', 10.0))
    chave_pix = request.form.get('chave_pix')
    senha_temp = request.form.get('senha_temporaria')
    
    if Usuario.query.filter_by(email=email).first():
        flash('Este e-mail já está cadastrado no sistema.')
        return redirect(url_for('admin.dashboard'))
        
    novo_usuario = Usuario(email=email, role='parceiro', senha_temporaria=True)
    novo_usuario.set_senha(senha_temp)
    db.session.add(novo_usuario)
    db.session.flush()
    
    codigo_random = f"PRC-{random.randint(1000, 9999)}"
    
    config = ParceiroConfig(
        usuario_id=novo_usuario.id,
        nome=nome,
        codigo_utm=codigo_random,
        taxa_comissao=taxa,
        chave_pix=chave_pix
    )
    
    db.session.add(config)
    db.session.commit()
    
    flash(f'Parceiro {nome} criado com sucesso! Link gerado: {codigo_random}')
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/parceiro/<int:id>/editar', methods=['POST'])
@login_required
def editar_parceiro(id):
    if current_user.role != 'admin':
        return redirect(url_for('parceiros.dashboard'))
        
    parceiro = ParceiroConfig.query.get_or_404(id)
    
    novo_email = request.form.get('email')
    
    # Verifica se o email foi alterado e se não conflita com outro usuário
    if novo_email != parceiro.usuario.email:
        if Usuario.query.filter_by(email=novo_email).first():
            flash('Erro: O novo e-mail informado já está sendo usado por outro cadastro.')
            return redirect(url_for('admin.dashboard'))
        parceiro.usuario.email = novo_email

    parceiro.nome = request.form.get('nome')
    parceiro.taxa_comissao = float(request.form.get('taxa'))
    parceiro.chave_pix = request.form.get('chave_pix')
    
    db.session.commit()
    flash(f'Dados do parceiro {parceiro.nome} atualizados com sucesso.')
    
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/parceiro/<int:id>/resetar-senha', methods=['POST'])
@login_required
def resetar_senha(id):
    if current_user.role != 'admin':
        return redirect(url_for('parceiros.dashboard'))
        
    parceiro = ParceiroConfig.query.get_or_404(id)
    
    # Gera uma senha segura de 8 caracteres
    nova_senha_temp = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
    
    parceiro.usuario.set_senha(nova_senha_temp)
    parceiro.usuario.senha_temporaria = True
    
    db.session.commit()
    
    # A mensagem flash carrega a senha na tela para a dona da loja copiar e enviar
    flash(f'Senha de {parceiro.nome} resetada! Nova senha temporária: {nova_senha_temp}')
    
    return redirect(url_for('admin.dashboard'))

