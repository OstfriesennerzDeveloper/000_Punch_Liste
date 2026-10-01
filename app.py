import streamlit as st
import pandas as pd
import io
import db_service
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

USERS = {
    "admin": {"password": "admin123", "role": "Admin"},
    "user": {"password": "user123", "role": "User"}
}

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "role" not in st.session_state:
    st.session_state.role = None
if "username" not in st.session_state:
    st.session_state.username = None

st.title("Punchlist & Burndown Tool")
st.subheader("Issue #7: Kommentare & Fortschritt (%)")

# --- SIDEBAR: LOGIN & EINSTELLUNGEN ---
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
        if st.button("Ausloggen"):
            st.session_state.logged_in = False
            st.session_state.role = None
            st.session_state.username = None
            st.rerun()
            
        if st.session_state.role == "Admin":
            st.divider()
            with st.expander("⚙️ Gewerke verwalten"):
                gewerke_liste = db_service.get_gewerke()
                st.write("**Neues Gewerk anlegen:**")
                neues_gewerk = st.text_input("Neue Kategorie eintragen:")
                if st.button("Hinzufügen") and neues_gewerk:
                    if neues_gewerk not in gewerke_liste:
                        db_service.add_gewerk(neues_gewerk)
                        st.success(f"'{neues_gewerk}' wurde hinzugefügt!")
                        st.rerun()
                    else:
                        st.warning("Existiert bereits!")
                
                st.divider()
                st.write("**Gewerk löschen:**")
                gewerk_zum_loeschen = st.selectbox("Kategorie auswählen:", gewerke_liste)
                if st.button("🗑️ Löschen") and gewerk_zum_loeschen:
                    db_service.delete_gewerk(gewerk_zum_loeschen)
                    st.success(f"'{gewerk_zum_loeschen}' wurde gelöscht!")
                    st.rerun()

# --- HAUPT-APP ---
if st.session_state.logged_in:
    
    items = db_service.get_items()
    gewerke_liste = db_service.get_gewerke()
    
    # --- EXCEL-EXPORT ---
    with st.sidebar:
        st.divider()
        st.subheader("Projekt-Controlling")
        
        export_data = []
        for i in items:
            export_data.append({
                "Titel": i.get('titel', ''),
                "Priorität": i.get('prioritaet', ''),
                "Gewerk": i.get('gewerk', 'Nicht zugewiesen'),
                "Status (%)": f"{i.get('fortschritt', 0)}%", # NEU
                "Kommentar": i.get('kommentar', ''),         # NEU
                "Geplant bis": i.get('datum', 'Unbekannt')
            })
            
        df = pd.DataFrame(export_data)
        if df.empty:
            df = pd.DataFrame(columns=["Titel", "Priorität", "Gewerk", "Status (%)", "Kommentar", "Geplant bis"])
            
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Mängelliste')
            worksheet = writer.sheets['Mängelliste']
            header_fill = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
            header_font = Font(color="FFFFFF", bold=True, size=14)
            for col_num, value in enumerate(df.columns.values):
                cell = worksheet.cell(row=1, column=col_num + 1)
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = Alignment(horizontal="center")
            for idx, col in enumerate(worksheet.columns, 1):
                max_length = 0
                column_letter = get_column_letter(idx)
                for cell in col:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                worksheet.column_dimensions[column_letter].width = max(max_length + 2, 15)
                
        st.download_button(
            label="📥 Formatierte Matrix laden",
            data=buffer.getvalue(),
            file_name="Punchlist_Matrix.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    # --- METRIKEN ---
    total_items = len(items)
    closed_items = [i for i in items if i['status'] == 'Erledigt' or i.get('fortschritt') == 100]
    open_items = [i for i in items if i['status'] == 'Offen' and i.get('fortschritt', 0) < 100]
    
    st.markdown("### Projekt-Fortschritt")
    col1, col2, col3 = st.columns(3)
    col1.metric("Gesamt Aufgaben", total_items)
    col2.metric("Offen", len(open_items))
    col3.metric("Erledigt", len(closed_items))
    progress_percent = int((len(closed_items) / total_items * 100)) if total_items > 0 else 0
    st.progress(progress_percent / 100.0, text=f"Burndown: {progress_percent}% erledigt")
    st.divider()

    # --- FORMULAR ---
    with st.form("add_item_form", clear_on_submit=True):
        titel = st.text_input("Neue Aufgabe / Mangel erfassen")
        col_form1, col_form2, col_form3 = st.columns(3)
        with col_form1:
            prioritaet = st.selectbox("Priorität", ["Sehr Hoch", "Hoch", "Mittel", "Niedrig", "Sehr Niedrig"])
        with col_form2:
            sichere_liste = gewerke_liste if gewerke_liste else ["Bitte Gewerk anlegen"]
            gewerk = st.selectbox("Gewerk", sichere_liste)
        with col_form3:
            ziel_datum = st.date_input("Geplant bis", format="DD.MM.YYYY")
            
        submitted = st.form_submit_button("Eintragen")
        if submitted and titel:
            datum_str = ziel_datum.strftime("%d.%m.%Y")
            db_service.add_item(titel, prioritaet, gewerk, datum_str)
            st.success("Erfolgreich hinzugefügt!")
            st.rerun()

    st.divider()

    # --- MÄNGELLISTE ---
    tab1, tab2 = st.tabs(["📋 Offene Aufgaben", "✅ Erledigt"])
    
    with tab1:
        if not open_items:
            st.info("Super, keine offenen Aufgaben! 🎉")
        else:
            for item in open_items:
                # Nutze einen Expander für eine saubere Optik
                with st.expander(f"🔴 {item.get('titel', '')} | {item.get('gewerk', '')} | 🎯 {item.get('datum', '')}"):
                    col1, col2 = st.columns(2)
                    with col1:
                        # Schieberegler für Status
                        neu_fortschritt = st.select_slider(
                            "Arbeitsfortschritt (%)", 
                            options=[0, 25, 50, 75, 100], 
                            value=item.get('fortschritt', 0), 
                            key=f"prog_{item['id']}"
                        )
                        st.write(f"Priorität: **{item.get('prioritaet', '')}**")
                    with col2:
                        # Textfeld für Kommentare
                        neu_kommentar = st.text_area(
                            "Kommentar / Update", 
                            value=item.get('kommentar', ''), 
                            key=f"komm_{item['id']}"
                        )
                    
                    col_btn1, col_btn2 = st.columns([1, 5])
                    with col_btn1:
                        if st.button("💾 Speichern", key=f"save_{item['id']}"):
                            db_service.update_item_details(item['id'], neu_fortschritt, neu_kommentar)
                            st.success("Aktualisiert!")
                            st.rerun()
                    with col_btn2:
                        if st.session_state.role == "Admin":
                            if st.button("🗑️ Löschen", key=f"del_open_{item['id']}"):
                                db_service.delete_item(item['id'])
                                st.rerun()

    with tab2:
        if not closed_items:
            st.info("Noch keine Aufgaben abgearbeitet.")
        else:
            for item in closed_items:
                with st.expander(f"🟢 ~~{item.get('titel', '')}~~ | {item.get('gewerk', '')}"):
                    st.write(f"Kommentar: {item.get('kommentar', '-')}")
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("🔄 Wieder öffnen (Setzt Status auf 0%)", key=f"reopen_{item['id']}"):
                            db_service.update_item_details(item['id'], 0, item.get('kommentar', ''))
                            st.rerun()
                    with col2:
                        if st.session_state.role == "Admin":
                            if st.button("🗑️ Komplett löschen", key=f"del_closed_{item['id']}"):
                                db_service.delete_item(item['id'])
                                st.rerun()