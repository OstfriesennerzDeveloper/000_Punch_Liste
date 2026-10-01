import streamlit as st
import pandas as pd
import io
import db_service
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

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
st.subheader("Issue #4.1: Formatierter Excel-Export")

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
    
    # DATEN ABRUFEN
    items = db_service.get_items()
    
    # --- EXCEL-EXPORT IN DER SIDEBAR (Jetzt formatiert!) ---
    with st.sidebar:
        st.divider()
        st.subheader("Projekt-Controlling")
        
        export_data = []
        for i in items:
            export_data.append({
                "Titel": i.get('titel', ''),
                "Priorität": i.get('prioritaet', ''),
                "Status": i.get('status', 'Offen')
            })
            
        df = pd.DataFrame(export_data)
        
        if df.empty:
            df = pd.DataFrame(columns=["Titel", "Priorität", "Status"])
            
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Mängelliste')
            
            # --- EXCEL FORMATIERUNG ---
            worksheet = writer.sheets['Mängelliste']
            
            # 1. Überschriften stylen (Dunkelblau mit weißer Schrift)
            header_fill = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
            header_font = Font(color="FFFFFF", bold=True)
            
            for col_num, value in enumerate(df.columns.values):
                cell = worksheet.cell(row=1, column=col_num + 1)
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = Alignment(horizontal="center")
                
            # 2. Spaltenbreiten automatisch anpassen
            for idx, col in enumerate(worksheet.columns, 1):
                max_length = 0
                column_letter = get_column_letter(idx)
                for cell in col:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = (max_length + 2) # Ein bisschen Puffer
                # Minimale Breite erzwingen, damit es gut aussieht
                worksheet.column_dimensions[column_letter].width = max(adjusted_width, 15)
                
        st.download_button(
            label="📥 Formatierte Matrix laden",
            data=buffer.getvalue(),
            file_name="Punchlist_Matrix.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    # --- BURNDOWN METRIKEN ---
    total_items = len(items)
    closed_items = [i for i in items if i['status'] == 'Erledigt']
    open_items = [i for i in items if i['status'] == 'Offen']
    
    closed_count = len(closed_items)
    open_count = len(open_items)
    progress_percent = int((closed_count / total_items * 100)) if total_items > 0 else 0
    
    st.markdown("### Projekt-Fortschritt")
    col1, col2, col3 = st.columns(3)
    col1.metric("Gesamt Mängel", total_items)
    col2.metric("Offen", open_count)
    col3.metric("Erledigt", closed_count)
    
    st.progress(progress_percent / 100.0, text=f"Burndown: {progress_percent}% erledigt")
    st.divider()

    # --- FORMULAR ---
    with st.form("add_item_form", clear_on_submit=True):
        titel = st.text_input("Neuen Mangel erfassen")
        prioritaet = st.selectbox("Priorität", ["Sehr Hoch", "Hoch", "Mittel", "Niedrig", "Sehr Niedrig"])
        submitted = st.form_submit_button("Mangel eintragen")
        
        if submitted and titel:
            db_service.add_item(titel, prioritaet)
            st.success("Mangel erfolgreich hinzugefügt!")
            st.rerun()

    st.divider()

    # --- MÄNGELLISTE MIT TABS ---
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
                    if st.button("✔ Erledigen", key=f"done_{item['id']}"):
                        db_service.update_status(item['id'], 'Erledigt')
                        st.rerun()
                with col4:
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