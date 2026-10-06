import streamlit as st
import pandas as pd
import io
import base64
import re
from datetime import datetime, timedelta
from PIL import Image
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

# --- HILFSFUNKTION FÜR BILD-KOMPRIMIERUNG ---
def process_image(uploaded_file):
    if uploaded_file is None:
        return None
    image = Image.open(uploaded_file)
    image.thumbnail((800, 800))
    if image.mode != 'RGB':
        image = image.convert('RGB')
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=70)
    return base64.b64encode(buffer.getvalue()).decode("utf-8")

# --- 1. EINFACHE AUTHENTIFIZIERUNG ---
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    st.title("Login - Punchlist & Burndown Tool")
    
    with st.form("login_form"):
        st.info("Standard-Zugang: Benutzername: `admin` | Passwort: `admin123`")
        username = st.text_input("Benutzername")
        password = st.text_input("Passwort", type="password")
        submitted = st.form_submit_button("Einloggen")
        
        if submitted:
            if username == "admin" and password == "admin123":
                st.session_state["authenticated"] = True
                st.rerun()
            else:
                st.error("Falscher Benutzername oder Passwort.")
    st.stop()


# --- 2. HAUPTSEITE ---
st.title("Punchlist & Burndown Tool")

# --- 3. SIDEBAR: NEUER MANGEL ---
st.sidebar.header("Neuen Mangel erfassen")

with st.sidebar.form("mangel_form", clear_on_submit=True):
    titel = st.text_input("Titel / Bauteil")
    gewerk = st.selectbox("Gewerk", get_gewerke())
    ziel_kw = st.text_input("Avisierte Fertigstellung (z.B. KW 42/2026)")
    beschreibung = st.text_area("Beschreibung")
    
    foto_upload = st.file_uploader("📸 Foto hinzufügen (optional)", type=["jpg", "jpeg", "png"])
    
    submitted = st.form_submit_button("Hinzufügen")
    
    if submitted:
        if titel:
            foto_b64 = process_image(foto_upload) if foto_upload else None
            add_item(titel, gewerk, beschreibung, ziel_kw, foto_b64)
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
            for col in ["titel", "gewerk", "beschreibung", "ziel_kw", "fortschritt", "kommentar", "erstellt_am", "erledigt_am"]:
                if col not in df_export.columns:
                    df_export[col] = ""
                    
            df_export = df_export[["titel", "gewerk", "beschreibung", "ziel_kw", "fortschritt", "kommentar", "erstellt_am", "erledigt_am"]]
            df_export.columns = ["Mangel / Bauteil", "Gewerk", "Beschreibung", "Avisierte Fertigstellung", "Fortschritt (%)", "Kommentar / Status", "Erstellt am", "Erledigt am"]
            
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

# --- 5. HAUPTBEREICH: TABS FÜR MEHR ÜBERSICHT ---
try:
    items = get_items()
    
    if not items:
        st.info("Noch keine Einträge in der Datenbank. Nutze die Sidebar, um einen Mangel hinzuzufügen.")
    else:
        tab_liste, tab_chart = st.tabs(["📋 Dashboard & Mängelliste", "📈 Burndown-Chart"])
        
        # --- TAB 1: DASHBOARD UND LISTE ---
        with tab_liste:
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
            
            alle_gewerke = ["Alle anzeigen"] + get_gewerke()
            selected_filter = st.selectbox("Nach Gewerk filtern:", alle_gewerke)
            
            if selected_filter == "Alle anzeigen":
                anzeige_items = items
            else:
                anzeige_items = [i for i in items if i.get("gewerk") == selected_filter]
                
            if not anzeige_items:
                st.info(f"Keine Mängel für das Gewerk '{selected_filter}' gefunden.")
                
            for item in anzeige_items:
                ziel_text = f" | Ziel: {item.get('ziel_kw')}" if item.get('ziel_kw') else ""
                expander_title = f"{item.get('gewerk', 'Allgemein')} | {item.get('titel', 'Ohne Titel')}{ziel_text} — Fortschritt: {item.get('fortschritt', 0)}%"
                
                with st.expander(expander_title):
                    col_text, col_foto = st.columns([2, 1])
                    
                    with col_text:
                        st.write(f"**Beschreibung:** {item.get('beschreibung', '-')}")
                    
                    with col_foto:
                        if item.get("foto_b64"):
                            st.image(base64.b64decode(item["foto_b64"]), use_column_width=True)
                    
                    st.divider()
                    
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

        # --- TAB 2: SOLL/IST BURNDOWN CHART (KW-Basiert) ---
        with tab_chart:
            st.subheader("Soll- vs. Ist-Kurve (Offene Mängel nach Kalenderwochen)")
            
            # 1. Start- und Enddatum ermitteln
            erstellt_dates = [pd.to_datetime(i["erstellt_am"]).replace(tzinfo=None) for i in items if i.get("erstellt_am")]
            start_date = min(erstellt_dates) if erstellt_dates else datetime.now()
            
            end_date = datetime.now()
            for item in items:
                zkw = item.get("ziel_kw", "")
                if zkw:
                    # Versucht Formate wie "KW 42/2026" oder "42/26" intelligent zu lesen
                    m = re.search(r'(\d{1,2})(?:.*?(\d{4}))?', str(zkw))
                    if m:
                        w = int(m.group(1))
                        y = int(m.group(2)) if m.group(2) else datetime.now().year
                        if 1 <= w <= 53:
                            try:
                                dt = datetime.strptime(f"{y}-W{w:02d}-1", "%G-W%V-%u")
                                if dt > end_date:
                                    end_date = dt
                            except:
                                pass
            
            # Puffer geben, falls Start und Ende zu nah beieinander liegen
            if (end_date - start_date).days < 14:
                end_date = start_date + timedelta(days=28)
                
            # 2. Zeitstrahl in Wochen (Montage) aufbauen
            start_monday = start_date - timedelta(days=start_date.weekday())
            end_monday = end_date - timedelta(days=end_date.weekday())
            
            timeline = []
            current = start_monday
            while current <= end_monday:
                timeline.append(current)
                current += timedelta(days=7)
                
            df_chart = pd.DataFrame({"Datum": timeline})
            df_chart["KW"] = df_chart["Datum"].apply(lambda x: f"KW {x.isocalendar()[1]}/{x.isocalendar()[0]}")
            
            # 3. Soll-Kurve berechnen (Linear von Gesamtanzahl auf 0)
            total_scope = len(items)
            steps = len(df_chart)
            soll_values = []
            if steps > 1:
                for i in range(steps):
                    soll_values.append(total_scope - (total_scope * i / (steps - 1)))
            else:
                soll_values = [total_scope]
            df_chart["Soll-Kurve"] = soll_values
            
            # 4. Ist-Kurve berechnen
            now_unaware = datetime.now()
            ist_values = []
            
            for step_date in df_chart["Datum"]:
                end_of_kw = step_date + timedelta(days=6, hours=23, minutes=59)
                
                # Zukünftige Wochen bleiben leer -> Linie bricht sauber ab
                if step_date > now_unaware:
                    ist_values.append(None)
                    continue
                    
                created_count = sum(1 for d in erstellt_dates if d <= end_of_kw)
                
                erledigt_dates = [pd.to_datetime(i["erledigt_am"]).replace(tzinfo=None) for i in items if i.get("erledigt_am")]
                completed_count = sum(1 for d in erledigt_dates if d <= end_of_kw)
                
                open_issues = created_count - completed_count
                ist_values.append(open_issues)
            
            df_chart["Ist-Kurve"] = ist_values
            
            # 5. Chart zeichnen
            df_chart = df_chart.set_index("KW")
            
            try:
                # Nutzt Blau für Soll, Rot/Orange für Ist
                st.line_chart(
                    df_chart[["Soll-Kurve", "Ist-Kurve"]],
                    color=["#0000FF", "#FF0000"] 
                )
            except:
                # Fallback für ältere Streamlit-Versionen
                st.line_chart(df_chart[["Soll-Kurve", "Ist-Kurve"]])

except Exception as e:
    st.error(f"Fehler beim Laden der Einträge: {e}")