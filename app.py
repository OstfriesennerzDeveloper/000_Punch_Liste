import streamlit as st
import pandas as pd
import io
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

# --- 3. SIDEBAR: NEUER MANGEL ---
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

# --- 4. SIDEBAR: EXCEL EXPORT ---
st.sidebar.divider()
st.sidebar.header("Daten-Export")

try:
    export_items = get_items()
    if export_items:
        df_export = pd.DataFrame(export_items)
        if not df_export.empty:
            # Sicherheitshalber prüfen, ob alte Einträge alle Spalten haben
            for col in ["titel", "gewerk", "beschreibung", "fortschritt", "kommentar", "erstellt_am", "erledigt_am"]:
                if col not in df_export.columns:
                    df_export[col] = None
                    
            # Spalten auswählen und auf Deutsch umbenennen
            df_export = df_export[["titel", "gewerk", "beschreibung", "fortschritt", "kommentar", "erstellt_am", "erledigt_am"]]
            df_export.columns = ["Mangel / Bauteil", "Gewerk", "Beschreibung", "Fortschritt (%)", "Kommentar / Status", "Erstellt am", "Erledigt am"]
            
            # Excel-Datei im Hintergrund erstellen
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                df_export.to_excel(writer, index=False, sheet_name="Mängelliste")
            
            # Download-Button anzeigen
            st.sidebar.download_button(
                label="📥 Excel-Liste herunterladen",
                data=buffer.getvalue(),
                file_name="Punchliste_Export.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
except Exception as e:
    st.sidebar.error(f"Export momentan nicht möglich: {e}")

# --- 5. HAUPTBEREICH: DASHBOARD UND LISTE ---
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
        gesamt_fortschritt = sum(i.get('fortschritt', 0) for i in items) / total_items if total_items > 0 else 0
        
        # Kennzahlen nebeneinander anzeigen
        col1, col2, col3 = st.columns(3)
        col1.metric("Gesamtanzahl Mängel", total_items)
        col2.metric("Offen / In Arbeit", offen)
        col3.metric("Projektfortschritt", f"{gesamt_fortschritt:.1f} %")
        
        # Visueller Fortschrittsbalken
        st.progress(int(gesamt_fortschritt) / 100)
        st.divider()
        
        # --- BURNDOWN CHART ---
        st.subheader("Burndown-Chart (Offene Mängel über die Zeit)")
        
        burndown_data = []
        for item in items:
            if item.get("erstellt_am"):
                burndown_data.append({"Datum": item["erstellt_am"], "Änderung": 1})
            if item.get("erledigt_am"):
                burndown_data.append({"Datum": item["erledigt_am"], "Änderung": -1})
                
        if burndown_data:
            df = pd.DataFrame(burndown_data)
            df["Datum"] = pd.to_datetime(df["Datum"])
            df_grouped = df.groupby("Datum")["Änderung"].sum().reset_index()
            df_grouped = df_grouped.sort_values("Datum")
            df_grouped["Offene Mängel"] = df_grouped["Änderung"].cumsum()
            
            # Wochentage übersetzen
            wochentage = {0: "Mo", 1: "Di", 2: "Mi", 3: "Do", 4: "Fr", 5: "Sa", 6: "So"}
            df_grouped["Datum_formatiert"] = df_grouped["Datum"].apply(
                lambda x: f"{wochentage[x.weekday()]}, {x.strftime('%d.%m.')}"
            )
            df_grouped = df_grouped.set_index("Datum_formatiert")
            st.line_chart(df_grouped[["Offene Mängel"]])
        else:
            st.info("Noch nicht genug zeitliche Daten für ein Burndown-Chart vorhanden.")
            
        st.divider()
        
        # --- MÄNGELLISTE ---
        st.header("Aktuelle Mängelliste")
        for item in items:
            expander_title = f"{item.get('gewerk', 'Allgemein')} | {item.get('titel', 'Ohne Titel')} — Fortschritt: {item.get('fortschritt', 0)}%"
            
            with st.expander(expander_title):
                st.write(f"**Beschreibung:** {item.get('beschreibung', '-')}")
                
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