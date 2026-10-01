import json

with open('firebase_credentials.json') as f:
    data = json.load(f)

print("\n--- KOPIERE DEN TEXT AB HIER ---")
print("[firebase]")
for k, v in data.items():
    # Zeilenumbrüche für die Cloud passend formatieren
    v = str(v).replace('\n', '\\n')
    print(f'{k} = "{v}"')
print("--- KOPIERE DEN TEXT BIS HIER ---\n")