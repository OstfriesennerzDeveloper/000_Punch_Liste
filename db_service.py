import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore

if not firebase_admin._apps:
    cred = credentials.Certificate('firebase_credentials.json')
    firebase_admin.initialize_app(cred)

db = firestore.client()
COLLECTION_NAME = 'punchlist_items'

def get_items():
    items = []
    docs = db.collection(COLLECTION_NAME).stream()
    for doc in docs:
        item = doc.to_dict()
        item['id'] = doc.id
        items.append(item)
    return items

def add_item(titel, prioritaet):
    db.collection(COLLECTION_NAME).add({'titel': titel, 'prioritaet': prioritaet})

def delete_item(item_id):
    db.collection(COLLECTION_NAME).document(item_id).delete()