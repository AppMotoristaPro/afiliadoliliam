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

        # 1. IDENTIFICAÇÃO DO ID DO PEDIDO (Nuvemshop envia como 'id' ou 'number')
        # Mantém compatibilidade com o nosso mock de testes se não achar as chaves reais
        pedido_id = str(data.get('id', data.get('number', f"MOCK-{uuid.uuid4().hex[:8].upper()}")))

        # 2. CAPTURA DO VALOR TOTAL DA VENDA
        # Nuvemshop envia como 'total' (string ou float). Se não achar, busca seu campo de teste 'valor_total'
        valor_bruto = data.get('total', data.get('valor_total'))
        if not valor_bruto:
            return jsonify({'message': 'Venda ignorada: Pedido sem valor de faturamento.'}), 200
        valor_total = float(valor_bruto)

        # 3. EXTRAÇÃO DA TAG DE RASTREIO (UTM)
        utm = None

        # Cenário A: Requisição oficial da Nuvemshop (Analisa os dados de tráfego do pedido)
        # Geralmente mapeado em 'extra' ou parâmetros de URL guardados pela plataforma
        if 'landing_page_url' in data and data['landing_page_url']:
            url_pouso = data['landing_page_url']
            if 'utm_campaign=' in url_pouso:
                # Extrai o código que vem logo após o utm_campaign=
                utm = url_pouso.split('utm_campaign=')[1].split('&')[0]
        
        # Cenário B: Fallback para o nosso teste simplificado do Postman
        if not utm:
            utm = data.get('utm')

        # Se mesmo após varrer o JSON não houver UTM, a venda foi orgânica (não veio de nenhum parceiro)
        if not utm:
            return jsonify({'message': 'Venda processada: Ignorada por não conter rastreio de parceiro (Venda Orgânica).'}), 200
            
        # 4. VALIDAÇÃO DO PARCEIRO NO BANCO NEON
        parceiro = ParceiroConfig.query.filter_by(codigo_utm=utm).first()
        
        if not parceiro:
            return jsonify({
                'message': f'Venda ignorada: O código UTM {utm} não está associado a nenhum parceiro ativo.'
            }), 200
            
        # Evita duplicidade de pedidos (Garante que o mesmo webhook não processe o mesmo ID duas vezes)
        venda_existente = Venda.query.filter_by(pedido_id_nuvemshop=pedido_id).first()
        if venda_existente:
            return jsonify({'message': 'Aviso: Esta comissão já foi processada anteriormente para este pedido.'}), 200

        # 5. CÁLCULO E GRAVAÇÃO DA COMISSÃO
        valor_comissao = valor_total * (parceiro.taxa_comissao / 100)
        
        nova_venda = Venda(
            parceiro_id=parceiro.id,
            pedido_id_nuvemshop=pedido_id,
            valor_total=valor_total,
            valor_comissao=valor_comissao,
            status_pagamento='pago'
        )
        
        db.session.add(nova_venda)
        db.session.commit()
        
        return jsonify({
            'status': 'sucesso',
            'pedido_id': pedido_id,
            'parceiro_atribuido': parceiro.nome,
            'comissao_calculada': round(valor_comissao, 2)
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'error': 'Falha interna ao processar a requisição de venda',
            'detalhes': str(e)
        }), 500

