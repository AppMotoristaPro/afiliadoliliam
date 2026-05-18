from flask import Blueprint, request, jsonify
from ..models import ParceiroConfig, Venda
from ..extensions import db
import uuid

webhook_bp = Blueprint('webhook', __name__)

@webhook_bp.route('/nuvemshop', methods=['POST'])
def nuvemshop_webhook():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Nenhum dado JSON recebido'}), 400

        utm = data.get('utm')
        # Garante que o valor total seja convertido para float sem quebrar se vier como string
        valor_total = float(data.get('valor_total', 0.0))
        pedido_id_fake = f"MOCK-{uuid.uuid4().hex[:8].upper()}" 
        
        if not utm:
            return jsonify({'message': 'Venda ignorada: Nenhuma tag UTM encontrada.'}), 200
            
        # Busca o parceiro no banco de dados pelo código UTM
        parceiro = ParceiroConfig.query.filter_by(codigo_utm=utm).first()
        
        if not parceiro:
            return jsonify({
                'error': f'Código UTM {utm} não pertence a nenhum parceiro ativo no banco de dados. Acesse o painel administrativo e verifique se o código existe.'
            }), 404
            
        # Calcula a comissão com base na taxa individual do parceiro
        valor_comissao = valor_total * (parceiro.taxa_comissao / 100)
        
        # Correção técnica: usamos parceiro.id para gravar a chave estrangeira corretamente
        nova_venda = Venda(
            parceiro_id=parceiro.id,
            pedido_id_nuvemshop=pedido_id_fake,
            valor_total=valor_total,
            valor_comissao=valor_comissao,
            status_pagamento='pago'
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

    except Exception as e:
        # Se qualquer coisa quebrar (erro de banco, conversão, etc), devolve o erro real no Postman
        db.session.rollback()
        return jsonify({
            'error': 'Erro interno ao processar webhook',
            'detalhes': str(e)
        }), 500

