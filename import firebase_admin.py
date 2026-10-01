import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore

# Firebase initialisieren (verhindert Fehler bei App-Neustarts)
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
        item['id'] = doc.id # Wir speichern die Firebase-ID für das Löschen
        items.append(item)
    return items

def add_item(titel, prioritaet):
    """Fügt einen neuen Mangel hinzu."""
    db.collection(COLLECTION_NAME).add({
        'titel': titel,
        'prioritaet': prioritaet
    })

def delete_item(item_id):
    """Löscht einen Mangel anhand seiner ID."""
    db.collection(COLLECTION_NAME).document(item_id).delete()