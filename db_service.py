import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore

# --- 1. DATENBANK-VERBINDUNG MIT PUFFER ---
@st.cache_resource
def get_db_connection():
    # Prüft, ob Firebase schon gestartet wurde
    if not firebase_admin._apps:
        # Cloud-Modus (liest aus den Streamlit Secrets)
        if "firebase" in st.secrets:
            cred_dict = dict(st.secrets["firebase"])
            cred = credentials.Certificate(cred_dict)
        # Lokaler Modus (liest die Datei auf deinem Rechner)
        else:
            cred = credentials.Certificate('firebase_credentials.json')
            
        firebase_admin.initialize_app(cred)
        
    return firestore.client()

# Die zentrale Datenbank-Variable für alle Funktionen
db = get_db_connection()


# --- 2. PUNCHLIST-FUNKTIONEN ---

def get_gewerke():
    """Gibt die Liste der Gewerke für die Dropdown-Menüs zurück."""
    # Passend für Leitwarten- und Bauprojekte
    return ["Elektrotechnik", "Leittechnik", "Trockenbau", "Brandschutz", "Klima/Lüftung", "Sonstiges"]

def get_maengel():
    """Lädt alle Einträge aus der Datenbank."""
    maengel_ref = db.collection("maengel")
    docs = maengel_ref.stream()
    
    maengel_liste = []
    for doc in docs:
        mangel_daten = doc.to_dict()
        mangel_daten["id"] = doc.id
        maengel_liste.append(mangel_daten)
        
    return maengel_liste

def add_mangel(titel, gewerk, beschreibung):
    """Speichert einen neuen Eintrag in Firebase."""
    maengel_ref = db.collection("maengel")
    maengel_ref.add({
        "titel": titel,
        "gewerk": gewerk,
        "beschreibung": beschreibung,
        "fortschritt": 0,
        "kommentar": ""
    })

def update_mangel(doc_id, fortschritt, kommentar):
    """Aktualisiert den Slider-Wert und den Kommentar eines bestehenden Eintrags."""
    doc_ref = db.collection("maengel").document(doc_id)
    doc_ref.update({
        "fortschritt": fortschritt,
        "kommentar": kommentar
    })