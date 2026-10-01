from backend.auth import hash_password, verify_password

def test_password_hashing():
    password = "strong-password"
    stored = hash_password(password)
    assert stored != password
    assert verify_password(password, stored)
    assert not verify_password("wrong-password", stored)
