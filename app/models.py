from .extensions import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timezone, timedelta

def fuso_sao_paulo():
    return datetime.now(timezone(timedelta(hours=-3)))

class Usuario(UserMixin, db.Model):
    __tablename__ = 'usuarios'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    senha_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    senha_temporaria = db.Column(db.Boolean, default=False, nullable=False)

    def set_senha(self, senha):
        self.senha_hash = generate_password_hash(senha)
    def check_senha(self, senha):
        return check_password_hash(self.senha_hash, senha)

class ParceiroConfig(db.Model):
    __tablename__ = 'parceiros_config'
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False, unique=True)
    nome = db.Column(db.String(100), nullable=False)
    codigo_utm = db.Column(db.String(50), unique=True, nullable=False)
    taxa_comissao = db.Column(db.Float, default=10.0)
    chave_pix = db.Column(db.String(100), nullable=True)
    celular = db.Column(db.String(20), nullable=True)
    usuario = db.relationship('Usuario', backref=db.backref('configuracao', uselist=False))

class LinkGerado(db.Model):
    __tablename__ = 'links_gerados'
    id = db.Column(db.Integer, primary_key=True)
    parceiro_id = db.Column(db.Integer, db.ForeignKey('parceiros_config.id'), nullable=False)
    url_original = db.Column(db.String(500), nullable=False)
    url_rastreada = db.Column(db.String(500), nullable=False)
    data_criacao = db.Column(db.DateTime, default=fuso_sao_paulo)
    parceiro = db.relationship('ParceiroConfig', backref=db.backref('links', lazy=True))

class Venda(db.Model):
    __tablename__ = 'vendas'
    id = db.Column(db.Integer, primary_key=True)
    parceiro_id = db.Column(db.Integer, db.ForeignKey('parceiros_config.id'), nullable=False)
    pedido_id_nuvemshop = db.Column(db.String(100), unique=True, nullable=False)
    produtos_resumo = db.Column(db.String(500), default="Produtos Diversos")
    valor_total = db.Column(db.Float, nullable=False)
    valor_comissao = db.Column(db.Float, nullable=False)
    data_venda = db.Column(db.DateTime, default=fuso_sao_paulo)
    status_pagamento = db.Column(db.String(20), default='pendente')
    parceiro = db.relationship('ParceiroConfig', backref=db.backref('vendas', lazy=True))

class LojaConfig(db.Model):
    __tablename__ = 'loja_config'
    id = db.Column(db.Integer, primary_key=True)
    dias_carencia_comissao = db.Column(db.Integer, default=7)
    valor_minimo_saque = db.Column(db.Float, default=50.0)

