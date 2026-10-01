import streamlit as st
import db_service

# --- KONFIGURATION & ZUGANGSDATEN ---
USERS = {
    "admin": {"password": "admin123", "role": "Admin"},
    "user": {"password": "user123", "role": "User"}
}

# --- SESSION STATE INITIALISIERUNG ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "role" not in st.session_state:
    st.session_state.role = None
if "username" not in st.session_state:
    st.session_state.username = None

st.title("Punchlist & Burndown Tool")
st.subheader("Issue #3: Status-Tracking & Burndown")

# --- SIDEBAR: LOGIN / LOGOUT ---
with st.sidebar:
    st.header("Login-Bereich")
    
    if not st.session_state.logged_in:
        with st.form("login_form"):
            username_input = st.text_input("Benutzername")
            password_input = st.text_input("Passwort", type="password")
            login_button = st.form_submit_button("Einloggen")
            
            if login_button:
                if username_input in USERS and USERS[username_input]["password"] == password_input:
                    st.session_state.logged_in = True
                    st.session_state.role = USERS[username_input]["role"]
                    st.session_state.username = username_input
                    st.success("Erfolgreich eingeloggt!")
                    st.rerun()
                else:
                    st.error("Falscher Benutzername oder Passwort")
    else:
        st.write(f"Angemeldet als: **{st.session_state.username}**")
        st.write(f"Rolle: **{st.session_state.role}**")
        if st.button("Ausloggen"):
            st.session_state.logged_in = False
            st.session_state.role = None
            st.session_state.username = None
            st.rerun()

# --- HAUPT-APP ---
if st.session_state.logged_in:
    
    # Daten abrufen
    items = db_service.get_items()
    
    # --- NEU: BURNDOWN METRIKEN ---
    total_items = len(items)
    closed_items = [i for i in items if i['status'] == 'Erledigt']
    open_items = [i for i in items if i['status'] == 'Offen']
    
    closed_count = len(closed_items)
    open_count = len(open_items)
    # Prozentrechnung (Verhindert Division durch Null)
    progress_percent = int((closed_count / total_items * 100)) if total_items > 0 else 0
    
    st.markdown("### Projekt-Fortschritt")
    col1, col2, col3 = st.columns(3)
    col1.metric("Gesamt Mängel", total_items)
    col2.metric("Offen", open_count)
    col3.metric("Erledigt", closed_count)
    
    # Der visuelle Fortschrittsbalken
    st.progress(progress_percent / 100.0, text=f"Burndown: {progress_percent}% erledigt")
    st.divider()

    # --- 1. Formular zum Anlegen neuer Mängel ---
    with st.form("add_item_form", clear_on_submit=True):
        titel = st.text_input("Neuen Mangel erfassen")
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

    # --- NEU: MÄNGELLISTE MIT TABS ---
    tab1, tab2 = st.tabs(["📋 Offene Mängel", "✅ Erledigte Mängel"])
    
    with tab1:
        if not open_items:
            st.info("Super, keine offenen Mängel! 🎉")
        else:
            for item in open_items:
                col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
                with col1:
                    st.write(f"**{item.get('titel', '')}**")
                with col2:
                    st.write(item.get('prioritaet', ''))
                with col3:
                    # Statuswechsel dürfen alle machen
                    if st.button("✔ Erledigen", key=f"done_{item['id']}"):
                        db_service.update_status(item['id'], 'Erledigt')
                        st.rerun()
                with col4:
                    # Harten Lösch-Button darf nur der Admin sehen
                    if st.session_state.role == "Admin":
                        if st.button("🗑️", key=f"del_open_{item['id']}"):
                            db_service.delete_item(item['id'])
                            st.rerun()
                    else:
                        st.write("🔒")

    with tab2:
        if not closed_items:
            st.info("Noch keine Mängel abgearbeitet.")
        else:
            for item in closed_items:
                col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
                with col1:
                    # Durchgestrichener Text für erledigte Mängel
                    st.write(f"~~{item.get('titel', '')}~~")
                with col2:
                    st.write(item.get('prioritaet', ''))
                with col3:
                    if st.button("🔄 Wieder öffnen", key=f"reopen_{item['id']}"):
                        db_service.update_status(item['id'], 'Offen')
                        st.rerun()
                with col4:
                    if st.session_state.role == "Admin":
                        if st.button("🗑️", key=f"del_closed_{item['id']}"):
                            db_service.delete_item(item['id'])
                            st.rerun()
                    else:
                        st.write("🔒")

else:
    st.info("👈 Bitte logge dich in der Seitenleiste ein, um auf das Tool zuzugreifen.")