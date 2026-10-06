import streamlit as st
import pandas as pd
import io
import base64
import re
from datetime import datetime, timedelta
from PIL import Image
from openpyxl.styles import Alignment
from openpyxl.utils import get_column_letter
from db_service import (
    db, get_items, add_item, update_item, get_gewerke, 
    delete_item, get_all_phases, migrate_open_items
)

st.set_page_config(page_title="Punchlist & Burndown Tool", layout="wide")

# --- HILFSFUNKTIONEN ---
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

# --- 1. AUTHENTIFIZIERUNG ---
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


# --- 2. HAUPTSEITE & PHASEN-AUSWAHL ---
st.title("Punchlist & Burndown Tool")

existing_phases = get_all_phases()

if "current_phase" not in st.session_state or st.session_state["current_phase"] not in existing_phases:
    st.session_state["current_phase"] = existing_phases[0]

phase_index = existing_phases.index(st.session_state["current_phase"])
selected_phase = st.sidebar.selectbox("Aktive Phase / Abnahme:", existing_phases, index=phase_index)
if selected_phase != st.session_state["current_phase"]:
    st.session_state["current_phase"] = selected_phase
    st.rerun()

st.sidebar.divider()

# --- 3. SIDEBAR: NEUER MANGEL ---
st.sidebar.header(f"Neuen Mangel erfassen ({st.session_state['current_phase']})")

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
            add_item(titel, gewerk, beschreibung, ziel_kw, foto_b64, phase=st.session_state["current_phase"])
            st.success("Mangel erfolgreich hinzugefügt!")
            st.rerun()
        else:
            st.warning("Bitte gib mindestens einen Titel ein.")

# --- 4. SIDEBAR: EXCEL EXPORT ---
st.sidebar.divider()
st.sidebar.header("Daten-Export")

try:
    export_items = get_items(phase=st.session_state["current_phase"])
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
                df_export.to_excel(writer, index=False, sheet_name="Maengelliste")
                worksheet = writer.sheets["Maengelliste"]
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
                file_name=f"Punchliste_{st.session_state['current_phase']}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
except Exception as e:
    st.sidebar.error(f"Export nicht möglich: {e}")

# --- 5. HAUPTBEREICH: REITER-STRUKTUR ---
try:
    items = get_items(phase=st.session_state["current_phase"])
    
    tab_liste, tab_dash, tab_chart, tab_admin = st.tabs([
        "📋 Mängelliste", 
        "📊 Dashboard", 
        "📈 Burndown-Chart", 
        "🔄 Neue Abnahme / Phase"
    ])
    
    # --- REITER 1: MÄNGELLISTE ---
    with tab_liste:
        st.subheader(f"Mängelliste für: {st.session_state['current_phase']}")
        
        if not items:
            st.info("Noch keine Mängel in dieser Phase erfasst.")
        else:
            alle_gewerke = ["Alle anzeigen"] + get_gewerke()
            selected_filter = st.selectbox("Nach Gewerk filtern:", alle_gewerke, key="filter_gewerk")
            
            if selected_filter == "Alle anzeigen":
                anzeige_items = items
            else:
                anzeige_items = [i for i in items if i.get("gewerk") == selected_filter]
                
            st.write(f"Anzahl Mängel in Ansicht: **{len(anzeige_items)}**")
            st.divider()
            
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
                    
                    if st.button("Änderungen speichern", key=f"btn_save_{item['id']}", use_container_width=True):
                        update_item(item['id'], new_fortschritt, new_kommentar, new_ziel_kw)
                        st.success("Erfolgreich gespeichert!")
                        st.rerun()
                        
                    with st.expander("⚙️ Erweitert / Mangel löschen"):
                        confirm_delete = st.checkbox("Ja, diesen Mangel unwiderruflich löschen", key=f"chk_del_{item['id']}")
                        if confirm_delete:
                            if st.button("🗑️ Endgültig löschen", key=f"btn_del_{item['id']}", type="primary"):
                                delete_item(item['id'])
                                st.rerun()

    # --- REITER 2: DASHBOARD ---
    with tab_dash:
        st.subheader(f"Projekt-Dashboard: {st.session_state['current_phase']}")
        if not items:
            st.info("Keine Daten für das Dashboard vorhanden.")
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
            
            st.markdown("### Verteilung nach Gewerken")
            df_dash = pd.DataFrame(items)
            if "gewerk" in df_dash.columns:
                gewerk_counts = df_dash["gewerk"].value_counts()
                st.bar_chart(gewerk_counts)

    # --- REITER 3: BURNDOWN-CHART ---
    with tab_chart:
        st.subheader(f"Burndown-Chart: {st.session_state['current_phase']}")
        
        if not items:
            st.info("Keine Daten für das Chart vorhanden.")
        else:
            start_key = f"start_date_{st.session_state['current_phase']}"
            
            created_dates = [pd.to_datetime(i.get("erstellt_am")).replace(tzinfo=None) for i in items if i.get("erstellt_am")]
            default_start = min(created_dates) if created_dates else datetime.now() - timedelta(days=28)
            
            if start_key not in st.session_state:
                st.session_state[start_key] = default_start.date()
            
            col_s1, col_s2 = st.columns(2)
            with col_s1:
                selected_start_date = st.date_input(
                    "Geplanter Starttermin (Diagramm-Beginn / Plandatum):",
                    value=st.session_state[start_key],
                    key=f"input_{start_key}"
                )
                if selected_start_date != st.session_state[start_key]:
                    st.session_state[start_key] = selected_start_date
                    st.rerun()

            now = datetime.now()
            start_date = datetime.combine(st.session_state[start_key], datetime.min.time())
            start_monday = start_date - timedelta(days=start_date.weekday())
            
            resolved_dates = [pd.to_datetime(i.get("erledigt_am")).replace(tzinfo=None) for i in items if i.get("erledigt_am")]
            
            target_date = start_monday + timedelta(days=28)
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
            
            chart_end_date = max(target_monday, now)
            
            timeline = []
            curr = start_monday
            while curr <= chart_end_date + timedelta(days=7):
                timeline.append(curr)
                curr += timedelta(days=7)
                
            current_monday = now - timedelta(days=now.weekday())
            
            ist_values = []
            for t_date in timeline:
                kw_end = t_date + timedelta(days=6, hours=23, minutes=59)
                if t_date > current_monday:
                    ist_values.append(None)
                else:
                    c_count = sum(1 for d in created_dates if d <= kw_end)
                    r_count = sum(1 for d in resolved_dates if d <= kw_end)
                    ist_values.append(max(0, c_count - r_count))
                    
            prognose_values = [None] * len(timeline)
            
            valid_ist_indices = [i for i, val in enumerate(ist_values) if val is not None]
            if valid_ist_indices:
                last_valid_idx = valid_ist_indices[-1]
                current_open = ist_values[last_valid_idx]
                prognose_values[last_valid_idx] = current_open
                
                weeks_passed = len(valid_ist_indices)
                total_closed = sum(1 for d in resolved_dates if d >= start_date and d <= (current_monday + timedelta(days=6)))
                velocity = total_closed / weeks_passed if weeks_passed > 0 else 0
                
                forecast_curr_idx = last_valid_idx + 1
                if current_open > 0 and velocity > 0:
                    forecast_open = current_open - velocity
                    while forecast_open > 0 and forecast_curr_idx < len(timeline):
                        prognose_values[forecast_curr_idx] = forecast_open
                        forecast_open -= velocity
                        forecast_curr_idx += 1
                    if forecast_curr_idx < len(timeline):
                        prognose_values[forecast_curr_idx] = 0
                elif current_open > 0:
                    for _ in range(4):
                        if forecast_curr_idx < len(timeline):
                            prognose_values[forecast_curr_idx] = current_open
                            forecast_curr_idx += 1
            else:
                velocity = 0
                current_open = len(items)

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

            df_chart = pd.DataFrame({
                "Datum": timeline,
                "Soll-Linie (Plan)": soll_values,
                "Ist-Linie (Realität)": ist_values,
                "Prognose (Trend)": prognose_values
            })
            
            df_chart["KW"] = df_chart["Datum"].apply(lambda x: f"KW {x.isocalendar()[1]}/{str(x.isocalendar()[0])[-2:]}")
            df_chart = df_chart.set_index("KW")
            
            try:
                st.line_chart(
                    df_chart[["Soll-Linie (Plan)", "Ist-Linie (Realität)", "Prognose (Trend)"]],
                    color=["#2ca02c", "#1f77b4", "#ff7f0e"]
                )
            except:
                st.line_chart(df_chart[["Soll-Linie (Plan)", "Ist-Linie (Realität)", "Prognose (Trend)"]])
                
            st.divider()
            if valid_ist_indices and velocity > 0 and current_open > 0:
                zero_indices = [i for i, val in enumerate(prognose_values) if val == 0]
                if zero_indices:
                    zero_date = timeline[zero_indices[0]]
                    st.info(f"💡 **Prognose:** Bei einer Velocity von **{velocity:.1f} Mängeln/Woche** wird der Bestand voraussichtlich in **KW {zero_date.isocalendar()[1]}/{zero_date.isocalendar()[0]}** abgearbeitet.")

    # --- REITER 4: NEUE ABNAHME / PHASE ---
    with tab_admin:
        st.subheader("🔄 Neue Projektphase / Abnahmetermin anlegen")
        st.write("Erstelle hier einen neuen Abnahme-Zyklus. Du kannst wählen, ob alle aktuell noch **offenen Mängel** aus der bisherigen Phase automatisch als Restmängel in die neue Phase übernommen werden sollen.")
        
        with st.form("new_phase_form"):
            new_phase_name = st.text_input("Name der neuen Phase (z.B. 'Phase 2 - Zwischenabnahme')", value="Phase 2")
            migrate_checkbox = st.checkbox("Alle offenen Mängel (< 100% Fortschritt) aus aktueller Phase mitübernehmen", value=True)
            new_phase_start = st.date_input("Geplanter Starttermin für das neue Diagramm (auch in Zukunft möglich):", value=datetime.now())
            
            create_submitted = st.form_submit_button("Neue Phase starten")
            
            if create_submitted:
                if new_phase_name and new_phase_name not in existing_phases:
                    migrated_count = 0
                    if migrate_checkbox:
                        migrated_count = migrate_open_items(
                            old_phase=st.session_state["current_phase"],
                            new_phase=new_phase_name,
                            custom_start_date=datetime.combine(new_phase_start, datetime.min.time())
                        )
                    
                    st.session_state["current_phase"] = new_phase_name
                    st.session_state[f"start_date_{new_phase_name}"] = new_phase_start
                    
                    st.success(f"Erfolgreich in '{new_phase_name}' gewechselt! {migrated_count} offene Mängel wurden übernommen.")
                    st.rerun()
                else:
                    st.warning("Bitte gib einen neuen, eindeutigen Namen für die Phase ein.")

except Exception as ec:
    st.error(f"Fehler beim Laden: {ec}")