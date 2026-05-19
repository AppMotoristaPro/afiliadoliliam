from flask import Blueprint, request, jsonify
from ..models import ParceiroConfig, Venda
from ..extensions import db
import urllib.parse
import traceback

webhook_bp = Blueprint('webhook', __name__)

@webhook_bp.route('/nuvemshop', methods=['POST'])
def receive_webhook():
    try:
        # silent=True evita que o Flask crashe se o formato do JSON vier quebrado
        data = request.get_json(silent=True)
        if not data:
            return jsonify({"erro": "Nenhum dado recebido ou formato JSON invalido"}), 400

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
            return jsonify({"erro": f"Parceiro com UTM {utm_campaign} não encontrado no banco"}), 404

        pedido_id = str(data.get('id', ''))
        if not pedido_id:
            return jsonify({"erro": "ID do pedido não informado pela loja"}), 400
            
        if Venda.query.filter_by(pedido_id_nuvemshop=pedido_id).first():
            return jsonify({"status": "Venda já registrada anteriormente"}), 200

        # Tratamento seguro de conversão financeira
        try:
            valor_total = float(data.get('total', 0))
        except (ValueError, TypeError):
            valor_total = 0.0

        # Previne erro se o admin salvou o parceiro sem taxa (Nulo)
        taxa = parceiro.taxa_comissao if parceiro.taxa_comissao is not None else 10.0
        valor_comissao = valor_total * (taxa / 100.0)
        
        resumo = data.get('produtos_resumo', 'Produtos Diversos')
        foto_url = data.get('foto_produto_url', '') 

        # Registo no banco de dados
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

    except Exception as e:
        # Se algo explodir, desfaz a transação falha do banco para não corromper
        db.session.rollback()
        # Retorna o erro exato na tela do Termux para matarmos a charada na hora
        return jsonify({
            "erro_interno_critico": str(e),
            "traceback": traceback.format_exc()
        }), 500

