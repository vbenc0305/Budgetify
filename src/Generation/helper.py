from src.DAO.DAOimpl import FirebaseDAO

firebase_dao = FirebaseDAO("user")

# **Felhasználó adatai**
user = {
    "name": "Angela Edwards",
    "email": "aliciacantu@example.com",
    "phone": "+1407592172314189",  # Fontos, hogy '+' jellel kezdődjön!
    "pwd": "F&e18KklSK",
    "role": "user",
    "birthdate": "1979-11-08",
    "last_login": "2025-01-04"
}

if firebase_dao.create(user):
    print(f"User {user['email']} successfully saved!")