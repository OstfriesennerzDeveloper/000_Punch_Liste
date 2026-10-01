import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
import streamlit as st

if not firebase_admin._apps:
    if "firebase" in st.secrets:
        cred = credentials.Certificate(dict(st.secrets["firebase"]))
    else:
        cred = credentials.Certificate('firebase_credentials.json')
    firebase_admin.initialize_app(cred)

db = firestore.client()
COLLECTION_NAME = 'punchlist_items'
GEWERKE_COLLECTION = 'gewerke'

def get_gewerke():
    gewerke = []
    docs = db.collection(GEWERKE_COLLECTION).stream()
    for doc in docs:
        gewerke.append(doc.to_dict().get('name'))
    
    if not gewerke:
        standards = ["Elektro", "IT/Netzwerk", "TGA/Klima", "Trockenbau", "Projektmanagement", "Planungen", "Sonstiges"]
        for s in standards:
            add_gewerk(s)
        return sorted(standards)
    return sorted(gewerke)

def add_gewerk(name):
    docs = db.collection(GEWERKE_COLLECTION).where('name', '==', name).stream()
    if not any(True for _ in docs):
        db.collection(GEWERKE_COLLECTION).add({'name': name})

def delete_gewerk(name):
    docs = db.collection(GEWERKE_COLLECTION).where('name', '==', name).stream()
    for doc in docs:
        doc.reference.delete()

def get_items():
    items = []
    docs = db.collection(COLLECTION_NAME).stream()
    for doc in docs:
        item = doc.to_dict()
        item['id'] = doc.id
        
        # Fallbacks für ältere Einträge
        item['status'] = item.get('status', 'Offen')
        item['gewerk'] = item.get('gewerk', 'Nicht zugewiesen')
        item['datum'] = item.get('datum', 'Unbekannt')
        item['fortschritt'] = item.get('fortschritt', 0) # NEU
        item['kommentar'] = item.get('kommentar', '')    # NEU
            
        items.append(item)
    return items

def add_item(titel, prioritaet, gewerk, ziel_datum):
    db.collection(COLLECTION_NAME).add({
        'titel': titel,
        'prioritaet': prioritaet,
        'gewerk': gewerk,
        'datum': ziel_datum,
        'status': 'Offen',
        'fortschritt': 0,  # Startet bei 0%
        'kommentar': ''    # Startet leer
    })

def delete_item(item_id):
    db.collection(COLLECTION_NAME).document(item_id).delete()

def update_status(item_id, neuer_status):
    db.collection(COLLECTION_NAME).document(item_id).update({'status': neuer_status})

# NEU: Funktion zum Speichern von Fortschritt & Kommentar
def update_item_details(item_id, fortschritt, kommentar):
    neuer_status = 'Erledigt' if fortschritt == 100 else 'Offen'
    db.collection(COLLECTION_NAME).document(item_id).update({
        'fortschritt': fortschritt,
        'kommentar': kommentar,
        'status': neuer_status
    })