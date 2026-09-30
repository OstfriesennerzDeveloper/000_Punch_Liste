import streamlit as st
import db_service

# --- KONFIGURATION & ZUGANGSDATEN (Hardcoded für Issue #2) ---
USERS = {
    "admin": {"password": "admin123", "role": "Admin"},
    "user": {"password": "user123", "role": "User"}
}

# --- SESSION STATE INITIALISIERUNG ---
# Streamlit vergisst Variablen beim Neuladen. Der session_state merkt sich den Status!
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "role" not in st.session_state:
    st.session_state.role = None
if "username" not in st.session_state:
    st.session_state.username = None

st.title("Punchlist & Burndown Tool")
st.subheader("Issue #2: Authentifizierung & Rollen")

# --- SIDEBAR: LOGIN / LOGOUT ---
with st.sidebar:
    st.header("Login-Bereich")
    
    # Wenn NICHT eingeloggt, zeige das Login-Formular
    if not st.session_state.logged_in:
        with st.form("login_form"):
            username_input = st.text_input("Benutzername")
            password_input = st.text_input("Passwort", type="password")
            login_button = st.form_submit_button("Einloggen")
            
            if login_button:
                # Prüfen, ob der Nutzer existiert und das Passwort stimmt
                if username_input in USERS and USERS[username_input]["password"] == password_input:
                    st.session_state.logged_in = True
                    st.session_state.role = USERS[username_input]["role"]
                    st.session_state.username = username_input
                    st.success("Erfolgreich eingeloggt!")
                    st.rerun() # App neu laden, um die Hauptansicht zu zeigen
                else:
                    st.error("Falscher Benutzername oder Passwort")
    
    # Wenn EINGELOGGT, zeige Nutzerinfos und Logout-Button
    else:
        st.write(f"Angemeldet als: **{st.session_state.username}**")
        st.write(f"Rolle: **{st.session_state.role}**")
        if st.button("Ausloggen"):
            st.session_state.logged_in = False
            st.session_state.role = None
            st.session_state.username = None
            st.rerun()

# --- HAUPT-APP (Nur sichtbar, wenn eingeloggt) ---
if st.session_state.logged_in:
    
    # 1. Formular zum Anlegen neuer Mängel
    with st.form("add_item_form", clear_on_submit=True):
        titel = st.text_input("Titel des Mangels")
        prioritaet = st.selectbox(
            "Priorität", 
            ["Sehr Hoch", "Hoch", "Mittel", "Niedrig", "Sehr Niedrig"]
        )
        submitted = st.form_submit_button("Mangel eintragen")
        
        if submitted and titel:
            db_service.add_item(titel, prioritaet)
            st.success("Mangel erfolgreich hinzugefügt!")
            st.rerun()

    st.divider()

    # 2. Anzeige der aktuellen Mängelliste
    st.subheader("Aktuelle Mängelliste")
    items = db_service.get_items()

    if not items:
        st.info("Es sind aktuell keine Mängel erfasst.")
    else:
        for item in items:
            col1, col2, col3 = st.columns([3, 2, 1])
            with col1:
                st.write(f"**{item.get('titel', '')}**")
            with col2:
                st.write(item.get('prioritaet', ''))
            with col3:
                # ENTSCHEIDENDE LOGIK: Löschen-Button nur für Admins!
                if st.session_state.role == "Admin":
                    if st.button("Löschen", key=item['id']):
                        db_service.delete_item(item['id'])
                        st.rerun()
                else:
                    st.write("🔒") # Platzhalter-Symbol für normale User

else:
    st.info("👈 Bitte logge dich in der Seitenleiste ein, um auf das Tool zuzugreifen.")