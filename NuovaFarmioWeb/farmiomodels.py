from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, UTC

db = SQLAlchemy()

class Farmaco(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    dosaggio = db.Column(db.String(50))
    tipo_farmaco = db.Column(db.String(50))
    quantita_contenuto = db.Column(db.Integer)
    consumo_giornaliero = db.Column(db.Integer)
    quantita_attuale = db.Column(db.Integer)
    ultima_verifica = db.Column(db.DateTime, default=datetime.now(UTC))
    indice_facilita = db.Column(db.Integer, default=2)

    def __repr__(self):
        return f'<Farmaco {self.nome}>'

class Ordine(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    farmaco_id = db.Column(db.Integer, db.ForeignKey('farmaco.id'), nullable=False)
    data = db.Column(db.DateTime, default=datetime.now(UTC))
    quantita_richiesta = db.Column(db.Integer, nullable=False)
    stato = db.Column(db.String(20), default='richiesta') # 'richiesta', 'confermata', 'acquisita'
    
    farmaco = db.relationship('Farmaco', backref=db.backref('ordini', lazy=True))

    def __repr__(self):
        return f'<Ordine {self.id}>'