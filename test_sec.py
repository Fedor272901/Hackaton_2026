from app.core.security import hash_password, verify_password

password = "123456"

# 1. Хешируем
hash1 = hash_password(password)
hash2 = hash_password(password)

print("HASH1:", hash1)
print("HASH2:", hash2)

# 2. Проверка правильного пароля
print("VERIFY CORRECT:", verify_password(password, hash1))

# 3. Проверка неправильного пароля
print("VERIFY WRONG:", verify_password("wrong_password", hash1))

# 4. Проверка соли (должны быть разные)
print("HASHES EQUAL:", hash1 == hash2)
