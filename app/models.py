from .extensions import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

class Usuario(UserMixin, db.Model):
    __tablename__ = 'usuarios'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    senha_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False) # 'admin' ou 'parceiro'
    senha_temporaria = db.Column(db.Boolean, default=False, nullable=False) # True exige troca de senha

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
    
    usuario = db.relationship('Usuario', backref=db.backref('configuracao', uselist=False))

class Venda(db.Model):
    __tablename__ = 'vendas'
    
    id = db.Column(db.Integer, primary_key=True)
    parceiro_id = db.Column(db.Integer, db.ForeignKey('parceiros_config.id'), nullable=False)
    pedido_id_nuvemshop = db.Column(db.String(100), unique=True, nullable=False)
    valor_total = db.Column(db.Float, nullable=False)
    valor_comissao = db.Column(db.Float, nullable=False)
    data_venda = db.Column(db.DateTime, default=datetime.utcnow)
    status_pagamento = db.Column(db.String(20), default='pendente')

    parceiro = db.relationship('ParceiroConfig', backref=db.backref('vendas', lazy=True))

