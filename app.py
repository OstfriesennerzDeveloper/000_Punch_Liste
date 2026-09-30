import streamlit as st
import db_service

st.title("Punchlist & Burndown Tool")
st.subheader("Issue #1: Basis-System & Firebase")

# 1. Formular zum Anlegen neuer Mängel
with st.form("add_item_form"):
	titel = st.text_input("Titel des Mangels")
	prioritaet = st.selectbox(
		"Priorität",
		["Sehr Hoch", "Hoch", "Mittel", "Niedrig", "Sehr Niedrig"],
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
			st.write(item.get("prioritaet", ""))
		with col3:
			if st.button("Löschen", key=item["id"]):
				db_service.delete_item(item["id"])
				st.rerun()
