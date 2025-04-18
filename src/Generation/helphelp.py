import bcrypt


password = "asd123"
hashed_password = bcrypt.hashpw(password.encode(), bcrypt.gensalt())

print(hashed_password)