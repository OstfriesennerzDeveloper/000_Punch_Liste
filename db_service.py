import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime

# --- 1. DATENBANK-VERBINDUNG MIT LOKALEM FALLBACK ---
@st.cache_resource
def get_db_connection():
    if not firebase_admin._apps:
        cred = None
        
        # Versuche, ob Streamlit-Secrets (in der Cloud) existieren
        try:
            if "firebase" in st.secrets:
                cred_dict = dict(st.secrets["firebase"])
                cred = credentials.Certificate(cred_dict)
        except Exception:
            # Lokal gibt es keinen Tresor -> Fehler abfangen und ignorieren
            pass
            
        # Wenn kein Cloud-Secret geladen wurde, nutze lokal die JSON-Datei
        if not cred:
            cred = credentials.Certificate('firebase_credentials.json')
            
        firebase_admin.initialize_app(cred)
        
    return firestore.client()

db = get_db_connection()


# --- 2. PUNCHLIST-FUNKTIONEN ---

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
    """Speichert einen neuen Eintrag mit Erstelldatum in Firebase."""
    maengel_ref = db.collection("maengel")
    maengel_ref.add({
        "titel": titel,
        "gewerk": gewerk,
        "beschreibung": beschreibung,
        "fortschritt": 0,
        "kommentar": "",
        "erstellt_am": datetime.now().isoformat(), # Neuer Zeitstempel
        "erledigt_am": None
    })

def update_item(doc_id, fortschritt, kommentar):
    """Aktualisiert einen Eintrag und setzt das Erledigt-Datum bei 100%."""
    doc_ref = db.collection("maengel").document(doc_id)
    
    update_data = {
        "fortschritt": fortschritt,
        "kommentar": kommentar
    }
    
    # Automatischen Zeitstempel setzen, wenn auf 100% geschoben wird
    if fortschritt == 100:
        update_data["erledigt_am"] = datetime.now().isoformat()
    else:
        # Falls ein Mangel wieder auf unter 100% gesetzt wird
        update_data["erledigt_am"] = None 
        
    doc_ref.update(update_data)

def delete_item(doc_id):
    """Löscht einen Eintrag dauerhaft aus Firebase."""
    db.collection("maengel").document(doc_id).delete()