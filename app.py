import streamlit as st
from db_service import db, get_items, add_item, update_item, get_gewerke

st.set_page_config(page_title="Punchlist & Burndown Tool", layout="wide")

# --- 1. EINFACHE AUTHENTIFIZIERUNG ---
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    st.title("Login - Punchlist & Burndown Tool")
    st.info("Standard-Zugang: Benutzername: `admin` | Passwort: `admin123`")
    
    username = st.text_input("Benutzername")
    password = st.text_input("Passwort", type="password")
    
    if st.button("Einloggen"):
        if username == "admin" and password == "admin123":
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("Falscher Benutzername oder Passwort.")
    st.stop()


# --- 2. HAUPTSEITE (NACH ERFOLGREICHEM LOGIN) ---
st.title("Punchlist & Burndown Tool")
st.write("Verwaltung und Nachverfolgung von Mängeln und Projektfortschritten.")

# Sidebar zum Hinzufügen neuer Einträge
st.sidebar.header("Neuen Mangel erfassen")

with st.sidebar.form("mangel_form", clear_on_submit=True):
    titel = st.text_input("Titel / Bauteil")
    gewerk = st.selectbox("Gewerk", get_gewerke())
    beschreibung = st.text_area("Beschreibung")
    submitted = st.form_submit_button("Hinzufügen")
    
    if submitted:
        if titel:
            add_item(titel, gewerk, beschreibung)
            st.success("Mangel erfolgreich hinzugefügt!")
            st.rerun()
        else:
            st.warning("Bitte gib mindestens einen Titel ein.")
            
# Hauptbereich: Dashboard und Liste
st.header("Projekt-Dashboard")

try:
    items = get_items()
    
    if not items:
        st.info("Noch keine Einträge in der Datenbank. Nutze die Sidebar, um einen Mangel hinzuzufügen.")
    else:
        # --- DASHBOARD METRIKEN ---
        total_items = len(items)
        erledigt = sum(1 for i in items if i.get('fortschritt', 0) == 100)
        offen = total_items - erledigt
        gesamt_fortschritt = sum(i.get('fortschritt', 0) for i in items) / total_items
        
        # Kennzahlen nebeneinander anzeigen
        col1, col2, col3 = st.columns(3)
        col1.metric("Gesamtanzahl Mängel", total_items)
        col2.metric("Offen / In Arbeit", offen)
        col3.metric("Projektfortschritt", f"{gesamt_fortschritt:.1f} %")
        
        # Visueller Fortschrittsbalken für das Gesamtprojekt
        st.progress(int(gesamt_fortschritt) / 100)
        st.divider()
        
        # --- MÄNGELLISTE ---
        st.header("Aktuelle Mängelliste")
        for item in items:
            # Jeder Eintrag als aufklappbare Karte
            expander_title = f"{item.get('gewerk', 'Allgemein')} | {item.get('titel', 'Ohne Titel')} — Fortschritt: {item.get('fortschritt', 0)}%"
            
            with st.expander(expander_title):
                st.write(f"**Beschreibung:** {item.get('beschreibung', '-')}")
                
                # Eingabefelder für Fortschritt und Kommentar
                new_fortschritt = st.slider(
                    "Fortschritt (%)", 
                    0, 100, 
                    int(item.get('fortschritt', 0)), 
                    key=f"slider_{item['id']}"
                )
                new_kommentar = st.text_area(
                    "Kommentar / Status", 
                    value=item.get('kommentar', ''), 
                    key=f"kommentar_{item['id']}"
                )
                
                if st.button("Änderungen speichern", key=f"btn_{item['id']}"):
                    update_item(item['id'], new_fortschritt, new_kommentar)
                    st.success("Änderungen erfolgreich gespeichert!")
                    st.rerun()

except Exception as e:
    st.error(f"Fehler beim Laden der Einträge: {e}")
