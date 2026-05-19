from flask import Blueprint, request, jsonify
from ..models import ParceiroConfig, Venda
from ..extensions import db
import urllib.parse

webhook_bp = Blueprint('webhook', __name__)

@webhook_bp.route('/nuvemshop', methods=['POST'])
def receive_webhook():
    data = request.json
    if not data:
        return jsonify({"erro": "Nenhum dado recebido"}), 400

    landing_url = data.get('landing_page_url', '')
    if 'utm_campaign=' not in landing_url:
        return jsonify({"status": "Ignorado, sem UTM"}), 200
        
    parsed = urllib.parse.urlparse(landing_url)
    params = urllib.parse.parse_qs(parsed.query)
    utm_campaign = params.get('utm_campaign', [''])[0]
    
    if not utm_campaign.startswith('ELLIC-'):
        return jsonify({"status": "Ignorado, UTM não é da Ellic"}), 200

    parceiro = ParceiroConfig.query.filter_by(codigo_utm=utm_campaign).first()
    if not parceiro:
        return jsonify({"erro": "Parceiro não encontrado"}), 404

    pedido_id = str(data.get('id'))
    if Venda.query.filter_by(pedido_id_nuvemshop=pedido_id).first():
        return jsonify({"status": "Venda já registrada"}), 200

    valor_total = float(data.get('total', 0))
    # Calcula a comissão com base na taxa individual do parceiro
    valor_comissao = valor_total * (parceiro.taxa_comissao / 100.0)
    
    # Captura nome e foto
    resumo = data.get('produtos_resumo', 'Produtos Diversos')
    foto_url = data.get('foto_produto_url', '') # Enviado pelo Postman ou Nuvemshop

    nova_venda = Venda(
        parceiro_id=parceiro.id,
        pedido_id_nuvemshop=pedido_id,
        produtos_resumo=resumo,
        foto_produto_url=foto_url,
        valor_total=valor_total,
        valor_comissao=valor_comissao,
        status_pagamento='pendente'
    )
    
    db.session.add(nova_venda)
    db.session.commit()

    return jsonify({"status": "sucesso", "comissao_gerada": valor_comissao}), 201

