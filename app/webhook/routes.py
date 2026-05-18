from flask import Blueprint, request, jsonify
from ..models import ParceiroConfig, Venda
from ..extensions import db
import uuid

webhook_bp = Blueprint('webhook', __name__)

@webhook_bp.route('/nuvemshop', methods=['POST'])
def nuvemshop_webhook():
    try:
        data = request.get_json()
        if not data: return jsonify({'error': 'Sem dados'}), 400

        pedido_id = str(data.get('id', data.get('number', f"MOCK-{uuid.uuid4().hex[:8].upper()}")))
        valor_bruto = data.get('total', data.get('valor_total'))
        if not valor_bruto: return jsonify({'message': 'Sem valor'}), 200
        valor_total = float(valor_bruto)

        # Extração de produtos para o extrato detalhado
        produtos_str = data.get('produtos_resumo', 'Produtos não especificados na simulação')
        if 'products' in data:
            nomes = [p.get('name', 'Produto') for p in data['products']]
            produtos_str = ", ".join(nomes)

        utm = data.get('utm')
        if 'landing_page_url' in data and data['landing_page_url']:
            if 'utm_campaign=' in data['landing_page_url']:
                utm = data['landing_page_url'].split('utm_campaign=')[1].split('&')[0]

        if not utm: return jsonify({'message': 'Venda Orgânica'}), 200
            
        parceiro = ParceiroConfig.query.filter_by(codigo_utm=utm).first()
        if not parceiro: return jsonify({'message': 'Sócio não encontrado'}), 200
            
        if Venda.query.filter_by(pedido_id_nuvemshop=pedido_id).first():
            return jsonify({'message': 'Comissão já processada'}), 200

        valor_comissao = valor_total * (parceiro.taxa_comissao / 100)
        
        # STATUS PENDENTE: Obriga a venda a cair na fila do admin para pagamento
        nova_venda = Venda(
            parceiro_id=parceiro.id,
            pedido_id_nuvemshop=pedido_id,
            produtos_resumo=produtos_str,
            valor_total=valor_total,
            valor_comissao=valor_comissao,
            status_pagamento='pendente' 
        )
        db.session.add(nova_venda)
        db.session.commit()
        return jsonify({'status': 'sucesso', 'comissao': valor_comissao}), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

