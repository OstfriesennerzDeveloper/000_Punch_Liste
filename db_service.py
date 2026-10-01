import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore

# Dieser Puffer sorgt dafür, dass die Verbindung nur 1x aufgebaut wird!
@st.cache_resource
def get_db_connection():
    # Prüfen, ob die App schon initialisiert wurde
    if not firebase_admin._apps:
        # Cloud-Modus (Tresor)
        if "firebase" in st.secrets:
            cred_dict = dict(st.secrets["firebase"])
            cred = credentials.Certificate(cred_dict)
        # Lokaler Modus (JSON-Datei)
        else:
            cred = credentials.Certificate('firebase_credentials.json')
            
        firebase_admin.initialize_app(cred)
        
    return firestore.client()

# Diese zentrale Variable greift jetzt auf den Puffer zu
db = get_db_connection()