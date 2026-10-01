import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore

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
        
        # Rückwärtskompatibilität: Falls alte Einträge keinen Status haben
        if 'status' not in item:
            item['status'] = 'Offen'
            
        items.append(item)
    return items

def add_item(titel, prioritaet):
    """Fügt einen neuen Mangel mit Standardstatus 'Offen' hinzu."""
    db.collection(COLLECTION_NAME).add({
        'titel': titel,
        'prioritaet': prioritaet,
        'status': 'Offen' # <-- NEU: Standardstatus
    })

def delete_item(item_id):
    """Löscht einen Mangel endgültig (nur für Admins)."""
    db.collection(COLLECTION_NAME).document(item_id).delete()

def update_status(item_id, neuer_status):
    """NEU: Aktualisiert den Status eines spezifischen Mangels."""
    db.collection(COLLECTION_NAME).document(item_id).update({
        'status': neuer_status
    })