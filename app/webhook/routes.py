from flask import Blueprint, request, jsonify
from ..models import ParceiroConfig, Venda
from ..extensions import db
import uuid

webhook_bp = Blueprint('webhook', __name__)

@webhook_bp.route('/nuvemshop', methods=['POST'])
def nuvemshop_webhook():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Nenhum dado JSON recebido'}), 400

    # Lógica de Mock: Simulando o recebimento de uma venda
    # Formato esperado no Postman: {"utm": "PRC-123", "valor_total": 150.00}
    
    utm = data.get('utm')
    valor_total = float(data.get('valor_total', 0.0))
    # Gera um ID de pedido falso apenas para permitir a gravação no banco
    pedido_id_fake = f"MOCK-{uuid.uuid4().hex[:8].upper()}" 
    
    if not utm:
        return jsonify({'message': 'Venda ignorada: Nenhuma tag UTM de parceiro foi encontrada no pedido.'}), 200
        
    # Procura no banco quem é o dono deste código UTM
    parceiro = ParceiroConfig.query.filter_by(codigo_utm=utm).first()
    
    if not parceiro:
        return jsonify({'error': f'Código UTM {utm} não pertence a nenhum parceiro ativo.'}), 404
        
    # A Mágica Matemática: Calcula a comissão com base na taxa individual do parceiro
    valor_comissao = valor_total * (parceiro.taxa_comissao / 100)
    
    # Registra a venda no banco de dados
    nova_venda = Venda(
        parceiro_id=parceiro.id,
        pedido_id_nuvemshop=pedido_id_fake,
        valor_total=valor_total,
        valor_comissao=valor_comissao,
        status_pagamento='pago' # Vamos assumir pago para o teste
    )
    
    db.session.add(nova_venda)
    db.session.commit()
    
    return jsonify({
        'status': 'sucesso',
        'mensagem': 'Comissão processada e atribuída.',
        'parceiro': parceiro.nome,
        'taxa_aplicada': f"{parceiro.taxa_comissao}%",
        'comissao_gerada': valor_comissao
    }), 201

