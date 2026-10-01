import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore

# --- 1. DATENBANK-VERBINDUNG MIT PUFFER ---
@st.cache_resource
def get_db_connection():
    if not firebase_admin._apps:
        if "firebase" in st.secrets:
            cred_dict = dict(st.secrets["firebase"])
            cred = credentials.Certificate(cred_dict)
        else:
            cred = credentials.Certificate('firebase_credentials.json')
            
        firebase_admin.initialize_app(cred)
        
    return firestore.client()

db = get_db_connection()


# --- 2. PUNCHLIST-FUNKTIONEN (Angepasst an app.py) ---

def get_gewerke():
    """Gibt die Liste der Gewerke für Dropdowns zurück."""
    return ["Elektrotechnik", "Leittechnik", "Trockenbau", "Brandschutz", "Klima/Lüftung", "Sonstiges"]

def get_items():
    """Lädt alle Einträge aus der Datenbank."""
    maengel_ref = db.collection("maengel")
    docs = maengel_ref.stream()
    
    items_liste = []
    for doc in docs:
        item_daten = doc.to_dict()
        item_daten["id"] = doc.id
        items_liste.append(item_daten)
        
    return items_liste

def add_item(titel, gewerk, beschreibung):
    """Speichert einen neuen Eintrag in Firebase."""
    maengel_ref = db.collection("maengel")
    maengel_ref.add({
        "titel": titel,
        "gewerk": gewerk,
        "beschreibung": beschreibung,
        "fortschritt": 0,
        "kommentar": ""
    })

def update_item(doc_id, fortschritt, kommentar):
    """Aktualisiert einen bestehenden Eintrag."""
    doc_ref = db.collection("maengel").document(doc_id)
    doc_ref.update({
        "fortschritt": fortschritt,
        "kommentar": kommentar
    })