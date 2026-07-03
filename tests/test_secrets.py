from config.secrets import SecretManager


def test_encrypt_decrypt():
    mgr = SecretManager()
    original = "my_secret_api_key_12345"
    encrypted = mgr.encrypt(original)
    assert encrypted != original
    decrypted = mgr.decrypt(encrypted)
    assert decrypted == original


def test_different_keys_different_output():
    mgr = SecretManager()
    data = "test_data"
    e1 = mgr.encrypt(data)
    e2 = mgr.encrypt(data)
    # Same plaintext with Fernet produces different ciphertext each time
    assert e1 != e2
    assert mgr.decrypt(e1) == data
    assert mgr.decrypt(e2) == data


def test_load_key(tmp_path):
    mgr1 = SecretManager()
    key_path = str(tmp_path / "test_key.txt")
    mgr1.save_key(key_path)

    with open(key_path) as f:
        saved_key = f.read().strip()

    mgr2 = SecretManager.load_key(key_path)
    assert mgr2.key.decode() == saved_key
    data = "roundtrip"
    assert mgr2.decrypt(mgr1.encrypt(data)) == data


def test_repr_redacts_key():
    mgr = SecretManager()
    assert "***REDACTED***" in repr(mgr)
    assert mgr.key.decode() not in repr(mgr)
