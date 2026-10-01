import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore

if not firebase_admin._apps:
    cred = credentials.Certificate('firebase_credentials.json')
    firebase_admin.initialize_app(cred)

db = firestore.client()
COLLECTION_NAME = 'punchlist_items'
GEWERKE_COLLECTION = 'gewerke'

def get_gewerke():
    """Holt alle Kategorien aus der Datenbank."""
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
    """Fügt eine neue Kategorie hinzu (und verhindert Duplikate)."""
    # Erst prüfen, ob es den Namen schon exakt so gibt
    docs = db.collection(GEWERKE_COLLECTION).where('name', '==', name).stream()
    vorhanden = any(True for _ in docs)
    
    if not vorhanden:
        db.collection(GEWERKE_COLLECTION).add({'name': name})

def delete_gewerk(name):
    """Löscht alle Einträge dieser Kategorie aus der Datenbank."""
    docs = db.collection(GEWERKE_COLLECTION).where('name', '==', name).stream()
    for doc in docs:
        doc.reference.delete()

def get_items():
    """Holt alle Mängel aus der Datenbank."""
    items = []
    docs = db.collection(COLLECTION_NAME).stream()
    for doc in docs:
        item = doc.to_dict()
        item['id'] = doc.id
        
        if 'status' not in item:
            item['status'] = 'Offen'
        if 'gewerk' not in item:
            item['gewerk'] = 'Nicht zugewiesen'
        if 'datum' not in item:
            item['datum'] = 'Unbekannt'
            
        items.append(item)
    return items

def add_item(titel, prioritaet, gewerk, ziel_datum):
    """Fügt einen neuen Mangel mit manuell gewähltem Zieldatum hinzu."""
    db.collection(COLLECTION_NAME).add({
        'titel': titel,
        'prioritaet': prioritaet,
        'gewerk': gewerk,
        'datum': ziel_datum,
        'status': 'Offen'
    })

def delete_item(item_id):
    db.collection(COLLECTION_NAME).document(item_id).delete()

def update_status(item_id, neuer_status):
    db.collection(COLLECTION_NAME).document(item_id).update({
        'status': neuer_status
    })