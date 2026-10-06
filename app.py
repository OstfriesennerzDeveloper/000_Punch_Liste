import streamlit as st
import pandas as pd
import io
from openpyxl.styles import Alignment
from openpyxl.utils import get_column_letter
from db_service import db, get_items, add_item, update_item, get_gewerke, delete_item

st.set_page_config(page_title="Punchlist & Burndown Tool", layout="wide")

# --- HILFSFUNKTION FÜR DATUM + KW ---
def format_date_with_kw(date_str):
    if not date_str or pd.isna(date_str):
        return ""
    dt = pd.to_datetime(date_str)
    kw = dt.isocalendar()[1]
    return f"{dt.strftime('%d.%m.%Y')} (KW {kw})"

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
    ziel_kw = st.text_input("Avisierte Fertigstellung (z.B. KW 42/2026)")
    beschreibung = st.text_area("Beschreibung")
    submitted = st.form_submit_button("Hinzufügen")
    
    if submitted:
        if titel:
            add_item(titel, gewerk, beschreibung, ziel_kw)
            st.success("Mangel erfolgreich hinzugefügt!")
            st.rerun()
        else:
            st.warning("Bitte gib mindestens einen Titel ein.")

# --- 4. SIDEBAR: EXCEL EXPORT MIT FORMATIERUNG ---
st.sidebar.divider()
st.sidebar.header("Daten-Export")

try:
    export_items = get_items()
    if export_items:
        df_export = pd.DataFrame(export_items)
        if not df_export.empty:
            # Prüfen ob alle Spalten existieren (für alte Einträge ohne ziel_kw)
            for col in ["titel", "gewerk", "beschreibung", "ziel_kw", "fortschritt", "kommentar", "erstellt_am", "erledigt_am"]:
                if col not in df_export.columns:
                    df_export[col] = ""
                    
            df_export = df_export[["titel", "gewerk", "beschreibung", "ziel_kw", "fortschritt", "kommentar", "erstellt_am", "erledigt_am"]]
            df_export.columns = ["Mangel / Bauteil", "Gewerk", "Beschreibung", "Avisierte Fertigstellung", "Fortschritt (%)", "Kommentar / Status", "Erstellt am", "Erledigt am"]
            
            # Datum mit Kalenderwoche berechnen
            df_export["Erstellt am"] = df_export["Erstellt am"].apply(format_date_with_kw)
            df_export["Erledigt am"] = df_export["Erledigt am"].apply(format_date_with_kw)
            
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                df_export.to_excel(writer, index=False, sheet_name="Mängelliste")
                worksheet = writer.sheets["Mängelliste"]
                
                for idx, col_name in enumerate(df_export.columns):
                    col_letter = get_column_letter(idx + 1)
                    max_len = len(str(col_name))
                    for val in df_export[col_name]:
                        if val:
                            max_len = max(max_len, len(str(val)))
                    worksheet.column_dimensions[col_letter].width = min(max_len + 2, 50)
                
                for row in worksheet.iter_rows(min_row=1, max_row=worksheet.max_row, min_col=1, max_col=worksheet.max_column):
                    for cell in row:
                        cell.alignment = Alignment(wrap_text=True, vertical='top')
            
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
        total_items = len(items)
        erledigt = sum(1 for i in items if i.get('fortschritt', 0) == 100)
        offen = total_items - erledigt
        gesamt_fortschritt = sum(i.get('fortschritt', 0) for i in items) / total_items if total_items > 0 else 0
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Gesamtanzahl Mängel", total_items)
        col2.metric("Offen / In Arbeit", offen)
        col3.metric("Projektfortschritt", f"{gesamt_fortschritt:.1f} %")
        
        st.progress(int(gesamt_fortschritt) / 100)
        st.divider()
        
        # Burndown Chart
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
            
            wochentage = {0: "Mo", 1: "Di", 2: "Mi", 3: "Do", 4: "Fr", 5: "Sa", 6: "So"}
            # X-Achse mit Wochentag, Datum und KW formatieren
            df_grouped["Datum_formatiert"] = df_grouped["Datum"].apply(
                lambda x: f"{wochentage[x.weekday()]}, {x.strftime('%d.%m.')} (KW {x.isocalendar()[1]})"
            )
            df_grouped = df_grouped.set_index("Datum_formatiert")
            st.line_chart(df_grouped[["Offene Mängel"]])
        else:
            st.info("Noch nicht genug zeitliche Daten für ein Burndown-Chart vorhanden.")
            
        st.divider()
        
        # --- MÄNGELLISTE MIT FILTER ---
        st.header("Aktuelle Mängelliste")
        
        alle_gewerke = ["Alle anzeigen"] + get_gewerke()
        selected_filter = st.selectbox("Nach Gewerk filtern:", alle_gewerke)
        
        if selected_filter == "Alle anzeigen":
            anzeige_items = items
        else:
            anzeige_items = [i for i in items if i.get("gewerk") == selected_filter]
            
        if not anzeige_items:
            st.info(f"Keine Mängel für das Gewerk '{selected_filter}' gefunden.")
            
        for item in anzeige_items:
            # Zeigt die Ziel-KW direkt in der geschlossenen Karte an, wenn vorhanden
            ziel_text = f" | Ziel: {item.get('ziel_kw')}" if item.get('ziel_kw') else ""
            expander_title = f"{item.get('gewerk', 'Allgemein')} | {item.get('titel', 'Ohne Titel')}{ziel_text} — Fortschritt: {item.get('fortschritt', 0)}%"
            
            with st.expander(expander_title):
                st.write(f"**Beschreibung:** {item.get('beschreibung', '-')}")
                
                new_ziel_kw = st.text_input(
                    "Avisierte Fertigstellung (z.B. KW 42/2026)", 
                    value=item.get('ziel_kw', ''), 
                    key=f"ziel_{item['id']}"
                )
                
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
                
                col_save, col_delete = st.columns(2)
                
                with col_save:
                    if st.button("Änderungen speichern", key=f"btn_save_{item['id']}", use_container_width=True):
                        update_item(item['id'], new_fortschritt, new_kommentar, new_ziel_kw)
                        st.success("Erfolgreich gespeichert!")
                        st.rerun()
                        
                with col_delete:
                    if st.button("🗑️ Löschen", key=f"btn_del_{item['id']}", type="secondary", use_container_width=True):
                        delete_item(item['id'])
                        st.rerun()

except Exception as e:
    st.error(f"Fehler beim Laden der Einträge: {e}")