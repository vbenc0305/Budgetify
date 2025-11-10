import pandas as pd

# --- 1. Adathalmaz Beolvasása ---
try:
    # Fontos: A szkriptet abban a mappában futtasd, ahol a 'Dataset.csv' található!
    df = pd.read_csv('../../datasets/Dataset.csv')
    print("Sikeresen beolvasva a 'Dataset.csv' fájl. Kezdődik a magyarosítás! 🚀")
except FileNotFoundError:
    print("HIBA: Nem található a 'Dataset.csv' fájl! Kérlek ellenőrizd, hogy a szkript és a fájl ugyanabban a mappában van-e. ❌")
    exit()

# --- 2. Fordítási Térképek (A te kategóriáid alapján) ---

# Fő Kategóriák Fordítása
category_map = {
    'Dining Out': 'Élelmiszer',
    'Living Expenses': 'Háztartás',
    'Transport': 'Közlekedés',
    'Discretionary': 'Egyéb / Diszkrét',
    'Charity': 'Egyéb / Diszkrét',
    'Medical': 'Egészség',
    'Salary': 'Jövedelem',
    'Passive': 'Jövedelem' # Passive Income is Jövedelem (Bevétel)
}

# Al-kategóriák Fordítása
subcategory_map = {
    # Élelmiszer (Dining Out)
    'Coffee': 'Kávé',
    'Restaurant': 'Gyorsétel / Étterem',
    # Háztartás (Living Expenses)
    'Rent': 'Lakásfenntartás',
    'Groceries': 'Konyhai alap',
    'Gas/Electrics': 'Rezsi',
    'Phone': 'Szolgáltatások / Rezsi', # A "Szolgáltatások" és "Háztartás" közötti átfedés miatt
    # Közlekedés (Transport)
    'Fueling': 'Üzemanyag',
    'Taxi': 'Taxi',
    'Cash loan': 'Egyéb Közlekedés',
    # Egyéb / Diszkrét (Discretionary & Charity)
    'Entertainment': 'Mozi / Előadás',
    'Clothes': 'Ruházat',
    'Gifts': 'Ajándékok',
    'Donation': 'Adomány',
    'Furnishings': 'Bútor / Lakásfenntartás',
    'Clubing': 'Szórakozás / Előadás',
    'Hangingout/Ticket': 'Szórakozás / Előadás',
    'Global Fashion': 'Ruházat',
    'Sport ware': 'Ruházat',
    # Egészség (Medical)
    'Doctor': 'Orvosi szolgáltatás',
    'Taken medication': 'Gyógyszertár',
    # Szolgáltatások (Különálló kategória, de az Al-kategóriákban is szerepel)
    'Online streaming': 'Előfizetés',
    # Jövedelem (Salary & Passive)
    'Data with Decision': 'Fizetés',
    'YouTube': 'Egyéb Bevétel',
    'Teachable': 'Egyéb Bevétel'
}

# Kategória Típus Fordítása
category_type_map = {
    'Income': 'Bevétel',
    'Expense': 'Kiadás'
}

# --- 3. Adatok Lecserélése (A 'map' függvény használatával) ---

# Kategóriák fordítása
df['Category'] = df['Category'].replace(category_map)
df['Sub-category'] = df['Sub-category'].replace(subcategory_map)
df['Category Type'] = df['Category Type'].replace(category_type_map)

# Oszlopok átnevezése a magyarosítás teljessége érdekében
df.rename(columns={
    'Sub-category': 'Al-kategória',
    'Category': 'Kategória',
    'Category Type': 'Kategória Típus',
    'Description': 'Leírás',
    'Debit': 'Terhelés',
    'Credit': 'Jóváírás',
    'Month Number': 'Hónap Száma',
    'Weekday': 'Hét napja',
    'Amount': 'Összeg'
}, inplace=True)


# --- 4. Eredmény Mentése ---
output_filename = 'Dataset_Magyar.csv'
df.to_csv(output_filename, index=False, encoding='utf-8')

print(f"\nSikeresen legenerálva a magyarosított adathalmaz! 🎉")
print(f"Az új fájl neve: **{output_filename}**")
print("\nA fájl első 5 sora: 👇")
print(df[['Leírás', 'Al-kategória', 'Kategória', 'Kategória Típus', 'Összeg']].head())