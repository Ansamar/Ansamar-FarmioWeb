from flask import Flask, render_template, request, redirect, url_for, flash
from farmiomodels import db, Farmaco, Ordine
from datetime import datetime, UTC

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///farmio.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'una-chiave-segreta-molto-complessa'

# Inizializza il database con l'app
db.init_app(app)

# Tipi di farmaco definiti globalmente
TIPI_FARMACO = ['compresse', 'capsule', 'fiale', 'sciroppo', 'crema']

@app.route('/')
def dashboard():
    farmaci = Farmaco.query.all()
    
    # Aggiorna i giorni rimanenti e ordini necessari prima di renderizzare
    for farmaco in farmaci:
        if farmaco.consumo_giornaliero > 0:
            farmaco.giorni_rimanenti = farmaco.quantita_attuale / farmaco.consumo_giornaliero
        else:
            farmaco.giorni_rimanenti = float('inf')

        # Controllo per ordini automatici
        if farmaco.giorni_rimanenti < 7 and farmaco.giorni_rimanenti != 0:
            if not Ordine.query.filter_by(farmaco_id=farmaco.id, stato='richiesta').first():
                nuovo_ordine = Ordine(
                    farmaco_id=farmaco.id, 
                    quantita_richiesta=farmaco.quantita_contenuto,
                    stato='richiesta'
                )
                db.session.add(nuovo_ordine)
    
    db.session.commit()
    
    # Ordina i farmaci in base ai giorni rimanenti
    farmaci_ordinati = sorted(farmaci, key=lambda f: f.giorni_rimanenti)
    
    ordini_in_corso = Ordine.query.filter(Ordine.stato != 'acquisita').all()
    
    return render_template('dashboard.html', farmaci=farmaci_ordinati, ordini_in_corso=ordini_in_corso)

@app.route('/farmaco/<int:farmaco_id>')
def dettaglio_farmaco(farmaco_id):
    farmaco = Farmaco.query.get_or_404(farmaco_id)
    ordini = Ordine.query.filter_by(farmaco_id=farmaco.id).order_by(Ordine.data.desc()).all()
    
    if farmaco.consumo_giornaliero > 0:
        giorni_rimanenti = farmaco.quantita_attuale / farmaco.consumo_giornaliero
    else:
        giorni_rimanenti = float('inf')
        
    return render_template('dettaglio_farmaco.html', farmaco=farmaco, ordini=ordini, giorni_rimanenti=round(giorni_rimanenti, 1))

@app.route('/nuovo_farmaco', methods=['GET', 'POST'])
def nuovo_farmaco():
    if request.method == 'POST':
        nome = request.form['nome']
        dosaggio = request.form['dosaggio']
        tipo_farmaco = request.form['tipo_farmaco']
        
        try:
            quantita_contenuto = int(request.form['quantita_contenuto'])
            consumo_giornaliero = int(request.form['consumo_giornaliero'])
            quantita_attuale = int(request.form['quantita_attuale'])
            indice_facilita = int(request.form['indice_facilita'])
        except ValueError:
            flash("Per favore, inserisci valori numerici validi per le quantità e l'indice di facilità.", 'danger')
            return redirect(url_for('nuovo_farmaco'))

        nuovo_farmaco = Farmaco(
            nome=nome,
            dosaggio=dosaggio,
            tipo_farmaco=tipo_farmaco,
            quantita_contenuto=quantita_contenuto,
            consumo_giornaliero=consumo_giornaliero,
            quantita_attuale=quantita_attuale,
            ultima_verifica=datetime.now(UTC),
            indice_facilita=indice_facilita
        )
        db.session.add(nuovo_farmaco)
        db.session.commit()
        flash(f'Farmaco {nome} aggiunto con successo!', 'success')
        return redirect(url_for('dashboard'))
    
    return render_template('nuovo_farmaco.html', tipi_farmaco=TIPI_FARMACO)

@app.route('/elimina_farmaco/<int:farmaco_id>', methods=['POST'])
def elimina_farmaco(farmaco_id):
    farmaco = Farmaco.query.get_or_404(farmaco_id)
    db.session.delete(farmaco)
    db.session.commit()
    flash('Farmaco eliminato con successo!', 'danger')
    return redirect(url_for('dashboard'))

@app.route('/nuovo_ordine/<int:farmaco_id>', methods=['POST'])
def nuovo_ordine(farmaco_id):
    quantita_richiesta = int(request.form['quantita_richiesta'])
    
    nuovo_ordine = Ordine(
        farmaco_id=farmaco_id,
        quantita_richiesta=quantita_richiesta,
        stato='richiesta'
    )
    db.session.add(nuovo_ordine)
    db.session.commit()
    
    flash('Ordine creato con successo!', 'success')
    return redirect(url_for('dettaglio_farmaco', farmaco_id=farmaco_id))

@app.route('/annulla_ordine/<int:ordine_id>', methods=['POST'])
def annulla_ordine(ordine_id):
    ordine = Ordine.query.get_or_404(ordine_id)
    
    if ordine.stato == 'acquisita':
        farmaco = Farmaco.query.get(ordine.farmaco_id)
        if farmaco:
            farmaco.quantita_attuale -= ordine.quantita_richiesta
            db.session.commit()
    
    ordine.stato = 'annullato'
    db.session.commit()
    flash('Ordine annullato con successo. La giacenza è stata aggiornata.', 'danger')
    return redirect(url_for('dettaglio_farmaco', farmaco_id=ordine.farmaco_id))


@app.route('/aggiorna_stato_ordine/<int:ordine_id>/<string:stato_id>')
def aggiorna_stato_ordine(ordine_id, stato_id):
    ordine = Ordine.query.get_or_404(ordine_id)
    
    if stato_id == 'conferma':
        ordine.stato = 'confermata'
        flash('Ordine confermato!', 'success')
    elif stato_id == 'acquisisci':
        ordine.stato = 'acquisita'
        
        # Aggiorna la quantità attuale del farmaco
        farmaco = Farmaco.query.get(ordine.farmaco_id)
        if farmaco:
            farmaco.quantita_attuale += ordine.quantita_richiesta
        
        flash('Ordine acquisito! Quantità farmaco aggiornata.', 'success')
    
    db.session.commit()
    return redirect(url_for('dettaglio_farmaco', farmaco_id=ordine.farmaco_id))

@app.route('/modifica_farmaco/<int:farmaco_id>', methods=['GET', 'POST'])
def modifica_farmaco(farmaco_id):
    farmaco = Farmaco.query.get_or_404(farmaco_id)
    tipi_farmaco = TIPI_FARMACO

    if request.method == 'POST':
        try:
            farmaco.nome = request.form['nome']
            farmaco.dosaggio = request.form['dosaggio']
            farmaco.tipo_farmaco = request.form['tipo_farmaco']
            farmaco.quantita_contenuto = int(request.form['quantita_contenuto'])
            farmaco.consumo_giornaliero = int(request.form['consumo_giornaliero'])
            farmaco.quantita_attuale = int(request.form['quantita_attuale'])
            farmaco.indice_facilita = int(request.form['indice_facilita'])
            db.session.commit()
            flash(f'Farmaco {farmaco.nome} modificato con successo!', 'success')
            return redirect(url_for('dettaglio_farmaco', farmaco_id=farmaco.id))
        except ValueError:
            flash("Per favore, inserisci valori numerici validi per le quantità e l'indice di facilità.", 'danger')
            return redirect(url_for('modifica_farmaco', farmaco_id=farmaco.id))

    return render_template('modifica_farmaco.html', farmaco=farmaco, tipi_farmaco=tipi_farmaco)

@app.route('/verifica_farmaco/<int:farmaco_id>', methods=['POST'])
def verifica_farmaco(farmaco_id):
    farmaco = Farmaco.query.get_or_404(farmaco_id)
    try:
        nuova_quantita = int(request.form['quantita_attuale'])
        farmaco.quantita_attuale = nuova_quantita
        farmaco.ultima_verifica = datetime.now(UTC)
        db.session.commit()
        flash('Quantità farmaco verificata e aggiornata!', 'success')
    except ValueError:
        flash("Per favore, inserisci un valore numerico valido per la quantità.", 'danger')
        
    return redirect(url_for('dettaglio_farmaco', farmaco_id=farmaco.id))

# ... il resto del tuo codice

if __name__ == '__main__':
    with app.app_context():
        # Questo crea il database solo la prima volta
        # Esegui questo script in locale una volta per creare il db
        db.create_all()
    # Rimuovi `debug=True` in produzione
    app.run()