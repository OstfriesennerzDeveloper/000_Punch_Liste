import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
import datetime # NEU: Für den Zeitstempel

if not firebase_admin._apps:
    cred = credentials.Certificate('firebase_credentials.json')
    firebase_admin.initialize_app(cred)

db = firestore.client()
COLLECTION_NAME = 'punchlist_items'

def get_items():
    """Holt alle Mängel aus der Datenbank."""
    items = []
    docs = db.collection(COLLECTION_NAME).stream()
    for doc in docs:
        item = doc.to_dict()
        item['id'] = doc.id
        
        # Rückwärtskompatibilität für alte Einträge
        if 'status' not in item:
            item['status'] = 'Offen'
        if 'gewerk' not in item:
            item['gewerk'] = 'Nicht zugewiesen'
        if 'datum' not in item:
            item['datum'] = 'Unbekannt'
            
        items.append(item)
    return items

def add_item(titel, prioritaet, gewerk):
    """Fügt einen neuen Mangel mit Gewerk und aktuellem Datum hinzu."""
    heute = datetime.datetime.now().strftime("%d.%m.%Y")
    
    db.collection(COLLECTION_NAME).add({
        'titel': titel,
        'prioritaet': prioritaet,
        'gewerk': gewerk,
        'datum': heute,
        'status': 'Offen'
    })

def delete_item(item_id):
    db.collection(COLLECTION_NAME).document(item_id).delete()

def update_status(item_id, neuer_status):
    db.collection(COLLECTION_NAME).document(item_id).update({
        'status': neuer_status
    })