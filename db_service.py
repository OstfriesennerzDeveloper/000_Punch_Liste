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
# --- 2. PUNCHLIST-FUNKTIONEN ---

def get_gewerke():
    """Gibt die Liste der Gewerke für Dropdowns zurück."""
    return ["Elektrotechnik", "Leittechnik", "Trockenbau", "Brandschutz", "Klima/Lüftung", "Sonstiges"]

def get_items(phase="Phase 1"):
    """Lädt alle Einträge aus der Datenbank für die aktuelle Phase."""
    maengel_ref = db.collection("maengel")
    # Wir filtern nach der aktiven Projektphase
    docs = maengel_ref.where("phase", "==", phase).stream()
    
    items_liste = []
    for doc in docs:
        item_daten = doc.to_dict()
        item_daten["id"] = doc.id
        items_liste.append(item_daten)
        
    return items_liste

def get_all_phases():
    """Gibt alle existierenden Phasen zurück."""
    docs = db.collection("maengel").stream()
    phases = set()
    for doc in docs:
        p = doc.to_dict().get("phase", "Phase 1")
        phases.add(p)
    return sorted(list(phases)) if phases else ["Phase 1"]

def add_item(titel, gewerk, beschreibung, ziel_kw, foto_b64=None, phase="Phase 1"):
    """Speichert einen neuen Eintrag inkl. Phase."""
    maengel_ref = db.collection("maengel")
    maengel_ref.add({
        "titel": titel,
        "gewerk": gewerk,
        "beschreibung": beschreibung,
        "ziel_kw": ziel_kw, 
        "foto_b64": foto_b64,
        "phase": phase,
        "fortschritt": 0,
        "kommentar": "",
        "erstellt_am": datetime.now().isoformat(),
        "erledigt_am": None
    })

def update_item(doc_id, fortschritt, kommentar, ziel_kw):
    """Aktualisiert einen Eintrag."""
    doc_ref = db.collection("maengel").document(doc_id)
    
    update_data = {
        "fortschritt": fortschritt,
        "kommentar": kommentar,
        "ziel_kw": ziel_kw
    }
    
    if fortschritt == 100:
        update_data["erledigt_am"] = datetime.now().isoformat()
    else:
        update_data["erledigt_am"] = None 
        
    doc_ref.update(update_data)

def delete_item(doc_id):
    """Löscht einen Eintrag dauerhaft aus Firebase."""
    db.collection("maengel").document(doc_id).delete()

def migrate_open_items(old_phase, new_phase, custom_start_date=None):
    """Kopiert alle noch nicht erledigten Mängel (< 100%) in eine neue Phase."""
    old_items = get_items(phase=old_phase)
    creation_time = custom_start_date.isoformat() if custom_start_date else datetime.now().isoformat()
    
    count = 0
    for item in old_items:
        if item.get("fortschritt", 0) < 100:
            maengel_ref = db.collection("maengel")
            maengel_ref.add({
                "titel": item.get("titel"),
                "gewerk": item.get("gewerk"),
                "beschreibung": f"[Übernommen aus {old_phase}] {item.get('beschreibung', '')}",
                "ziel_kw": item.get("ziel_kw"),
                "foto_b64": item.get("foto_b64"),
                "phase": new_phase,
                "fortschritt": 0,
                "kommentar": f"Restmangel aus vorheriger Abnahme.",
                "erstellt_am": creation_time,
                "erledigt_am": None
            })
            count += 1
    return count