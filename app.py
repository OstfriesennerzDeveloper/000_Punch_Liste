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

# --- 5. HAUPTBEREICH: TABS ---
try:
    items = get_items()
    
    if not items:
        st.info("Noch keine Einträge in der Datenbank. Nutze die Sidebar, um einen Mangel hinzuzufügen.")
    else:
        tab_liste, tab_chart = st.tabs(["📋 Dashboard & Mängelliste", "📈 Profi Burndown-Chart"])
        
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
                    new_ziel_kw = st.text_input("Avisierte Fertigstellung (z.B. KW 42/2026)", value=item.get('ziel_kw', ''), key=f"ziel_{item['id']}")
                    new_fortschritt = st.slider("Fortschritt (%)", 0, 100, int(item.get('fortschritt', 0)), key=f"slider_{item['id']}")
                    new_kommentar = st.text_area("Kommentar / Status", value=item.get('kommentar', ''), key=f"kommentar_{item['id']}")
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

        # --- TAB 2: PROFI BURNDOWN CHART (SOLL, IST, PROGNOSE) ---
        with tab_chart:
            st.subheader("Punchlist Burndown (Mängelabbau-Diagramm)")
            st.markdown("**🟢 Soll-Linie (Plan)** | **🔵 Ist-Linie (Realität)** | **🟠 Prognose (Velocity-Trend)**")
            
            now = datetime.now()
            
            # 1. Daten und Zeitstrahl vorbereiten
            created_dates = [pd.to_datetime(i.get("erstellt_am")).replace(tzinfo=None) for i in items if i.get("erstellt_am")]
            resolved_dates = [pd.to_datetime(i.get("erledigt_am")).replace(tzinfo=None) for i in items if i.get("erledigt_am")]
            
            start_date = min(created_dates) if created_dates else now
            start_monday = start_date - timedelta(days=start_date.weekday())
            
            # Spätestes Ziel-Datum ermitteln
            target_date = start_monday + timedelta(days=28) # Standard-Puffer
            for item in items:
                zkw = item.get("ziel_kw", "")
                if zkw:
                    m = re.search(r'(\d{1,2})(?:.*?(\d{4}))?', str(zkw))
                    if m:
                        w = int(m.group(1))
                        y = int(m.group(2)) if m.group(2) else now.year
                        if 1 <= w <= 53:
                            try:
                                dt = datetime.strptime(f"{y}-W{w:02d}-1", "%G-W%V-%u")
                                if dt > target_date:
                                    target_date = dt
                            except:
                                pass
            target_monday = target_date - timedelta(days=target_date.weekday())
            current_monday = now - timedelta(days=now.weekday())
            
            # 2. Reale Ist-Kurve aufbauen
            timeline = []
            ist_values = []
            curr = start_monday
            
            while curr <= current_monday:
                timeline.append(curr)
                kw_end = curr + timedelta(days=6, hours=23, minutes=59)
                c_count = sum(1 for d in created_dates if d <= kw_end)
                r_count = sum(1 for d in resolved_dates if d <= kw_end)
                ist_values.append(c_count - r_count)
                curr += timedelta(days=7)
                
            # 3. Prognose (Forecast) berechnen
            prognose_values = [None] * len(timeline)
            current_open = ist_values[-1] if ist_values else 0
            prognose_values[-1] = current_open # Prognose dockt nahtlos an aktueller Ist-Linie an
            
            weeks_passed = len(ist_values)
            total_closed = sum(1 for d in resolved_dates if d <= (current_monday + timedelta(days=6)))
            velocity = total_closed / weeks_passed if weeks_passed > 0 else 0 # Mängel pro Woche
            
            forecast_curr = current_monday + timedelta(days=7)
            if current_open > 0 and velocity > 0:
                forecast_open = current_open - velocity
                while forecast_open > 0 and len(timeline) < 100: # Schutz vor Endlosschleife
                    timeline.append(forecast_curr)
                    prognose_values.append(forecast_open)
                    ist_values.append(None)
                    forecast_open -= velocity
                    forecast_curr += timedelta(days=7)
                # Null-Linie berühren
                timeline.append(forecast_curr)
                prognose_values.append(0)
                ist_values.append(None)
            elif current_open > 0:
                # Keine Velocity (noch nichts geschlossen) -> Stagnierende Prognose für 4 Wochen
                for _ in range(4):
                    timeline.append(forecast_curr)
                    prognose_values.append(current_open)
                    ist_values.append(None)
                    forecast_curr += timedelta(days=7)
                    
            # 4. Soll-Kurve aufbauen (Ideallinie zum Zieldatum)
            # Timeline ggf. bis zum Ziel-Datum verlängern
            while timeline[-1] < target_monday:
                next_week = timeline[-1] + timedelta(days=7)
                timeline.append(next_week)
                ist_values.append(None)
                prognose_values.append(0 if prognose_values[-1] == 0 else None)
            
            total_items_count = len(items)
            soll_values = []
            target_idx = timeline.index(target_monday) if target_monday in timeline else len(timeline)-1
            
            for i, t in enumerate(timeline):
                if i <= target_idx:
                    if target_idx > 0:
                        val = total_items_count - (total_items_count * i / target_idx)
                        soll_values.append(max(0, val))
                    else:
                        soll_values.append(0)
                else:
                    soll_values.append(0)
                    
            # Fehlende Prognose-Werte mit 0 auffüllen, damit der Array gleich lang bleibt
            while len(prognose_values) < len(timeline):
                prognose_values.append(0 if prognose_values[-1] == 0 else None)

            # 5. Zusammenbau & Rendering
            df_chart = pd.DataFrame({
                "Datum": timeline,
                "Soll-Linie (Plan)": soll_values,
                "Ist-Linie (Realität)": ist_values,
                "Prognose (Trend)": prognose_values
            })
            
            df_chart["KW"] = df_chart["Datum"].apply(lambda x: f"KW {x.isocalendar()[1]}/{str(x.isocalendar()[0])[-2:]}")
            df_chart = df_chart.set_index("KW")
            
            try:
                # Nutzt die Streamlit-Farbpalette für klare Unterscheidung
                st.line_chart(
                    df_chart[["Soll-Linie (Plan)", "Ist-Linie (Realität)", "Prognose (Trend)"]],
                    color=["#2ca02c", "#1f77b4", "#ff7f0e"] # Grün, Blau, Orange
                )
            except:
                st.line_chart(df_chart[["Soll-Linie (Plan)", "Ist-Linie (Realität)", "Prognose (Trend)"]])
                
            # Automatische Analyse / Textausgabe
            st.divider()
            if velocity > 0 and current_open > 0:
                kw_zero = timeline[-1].isocalendar()[1]
                jahr_zero = timeline[-1].isocalendar()[0]
                st.info(f"💡 **Projektanalyse:** Bei der aktuellen Abarbeitungsgeschwindigkeit von durchschnittlich **{velocity:.1f} Mängeln pro Woche** wird der Bestand voraussichtlich in **KW {kw_zero}/{jahr_zero}** auf null sinken.")
            elif current_open > 0 and velocity == 0:
                st.warning("⚠️ **Achtung:** Es wurden bisher keine Mängel final geschlossen (Velocity = 0). Eine Prognose des Fertigstellungstermins ist aktuell nicht möglich.")

except Exception as e:
    st.error(f"Fehler beim Laden der Einträge: {e}")