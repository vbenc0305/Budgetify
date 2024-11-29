"""
Ez a main.py modul a projekt alapértelmezett belépési pontja.

### **Cél**
A fájl célja, hogy bemutassa egy Python alapú alkalmazás működésének kereteit. Ez a modul a következőket tartalmazza:
- Egy alapvető függvényt (`print_hi`), amely bemutatja a Python `f-string` formázását.
- A `__main__` blokkot, amely biztosítja, hogy a kód csak akkor fusson, ha közvetlenül futtatjuk ezt a fájlt, nem pedig modulimportként.

### **Használat**
1. Futtasd a szkriptet közvetlenül PyCharm-ból vagy bármilyen Python kompatibilis IDE-ből.
2. A program egy egyszerű üzenetet fog megjeleníteni, amely a felhasználót név szerint köszönti.
3. Ez a kód sablonként szolgálhat bármilyen Python-projekt alapjához.

### **Fontos funkciók**
- **`print_hi(name)` függvény:**
    - Argumentumok:
        - `name` (str): A felhasználó neve, amelyet az üdvözlő üzenetben használunk.
    - Visszatérési érték: Ez a függvény nem tér vissza semmilyen értékkel, csak a képernyőre nyomtat.

- **`__main__` blokk:**
    - Ez a rész biztosítja, hogy a `print_hi` függvény csak akkor hívódjon meg, ha a fájlt közvetlenül futtatjuk, nem pedig egy másik szkript által importálva.

### **Fejlesztési környezet**
- **Python verzió**: Python 3.11 vagy újabb. Az `f-string` használata csak Python 3.6+ verziókon támogatott.
- **IDE**: PyCharm, amely kiváló eszköz a Python-projektek fejlesztéséhez, a hibakereséshez és az Inspections kezeléséhez.

### **Továbbfejlesztési lehetőségek**
1. Bővítsd a modult további funkciókkal (pl. GUI, adatbázis-kezelés vagy API-integráció).
2. Használj részletesebb inputkezelést a felhasználói interakcióhoz.
3. Írj tesztelési keretrendszert (pl. unittest vagy pytest) a modul funkcióinak ellenőrzéséhez.

### **Kapcsolódó dokumentáció**
- **Python hivatalos dokumentáció**: https://docs.python.org/3/
- **PyCharm súgó**: https://www.jetbrains.com/help/pycharm/

"""


def print_hi(name):
    """
       Köszönti a megadott nevű felhasználót.

       Ez a függvény egy egyszerű üdvözlő üzenetet ír ki a konzolra, amely tartalmazza a
       megadott felhasználó nevét. A Python f-string szintaxisát használja az üzenet
       dinamikus létrehozásához, amely a megadott 'name' paramétert tartalmazza.

       Használat:
       A függvény meghívása előtt meg kell adni egy érvényes, karakterlánc típusú
       `name` paramétert, amely a felhasználó nevét tartalmazza.

       Paraméterek:
           name (str): A felhasználó neve, amelyet az üdvözlő üzenetben fogunk
                       megjeleníteni.

       Visszatérési érték:
           None: A függvény nem tér vissza értékkel, csak az üzenetet írja ki a
                 konzolra.

       Példa:
           print_hi('Alice')  # Kimenet: Hi, Alice
       """
    print(f'Hi, {name}')


if __name__ == '__main__':
    print_hi('PyCharm')
