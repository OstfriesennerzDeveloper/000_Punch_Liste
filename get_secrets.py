import json

try:
    # Lese die versteckte Passwort-Datei ein
    with open('firebase_credentials.json', 'r', encoding='utf-8') as f:
        data = json.load(f)

    print("\n--- KOPIERE DEN TEXT AB HIER ---")
    print("[firebase]")
    for k, v in data.items():
        # Zeilenumbrüche für die Streamlit Cloud passend formatieren
        v_str = str(v).replace('\n', '\\n')
        print(f'{k} = "{v_str}"')
    print("--- KOPIERE DEN TEXT BIS HIER ---\n")

except FileNotFoundError:
    print("FEHLER: Die Datei 'firebase_credentials.json' wurde im aktuellen Ordner nicht gefunden.")