#!/usr/bin/env python3
"""
Utility to encrypt API keys for .env file
Uses Fernet (AES-256) encryption

Usage:
    python utils/encrypt_keys.py
    
Then add the encrypted values to your .env file:
    INDODAX_API_KEY_ENC="gAAAAAB..."
    INDODAX_SECRET_KEY_ENC="gAAAAAB..."
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.secrets import SecretManager


def main():
    print("=" * 60)
    print("INDODAX API KEY ENCRYPTION UTILITY")
    print("=" * 60)
    print()
    
    # Create secret manager
    manager = SecretManager()
    
    # Get keys from user
    print("Masukkan API Keys Indodax:")
    api_key = input("  API Key: ").strip()
    secret_key = input("  Secret Key: ").strip()
    
    # Optional: Telegram
    print("\nMasukkan Telegram Bot Token (opsional, tekan Enter untuk skip):")
    telegram_token = input("  Bot Token: ").strip()
    
    if telegram_token:
        print("\nMasukkan Telegram Chat ID (opsional, tekan Enter untuk skip):")
        chat_id = input("  Chat ID: ").strip()
    else:
        chat_id = ""
    
    # Encrypt
    encrypted_api = manager.encrypt(api_key) if api_key else ""
    encrypted_secret = manager.encrypt(secret_key) if secret_key else ""
    encrypted_token = manager.encrypt(telegram_token) if telegram_token else ""
    
    # Print results
    print("\n" + "=" * 60)
    print("ENCRYPTED VALUES (untuk .env file):")
    print("=" * 60)
    print()
    
    if encrypted_api:
        print(f'INDODAX_API_KEY_ENC="{encrypted_api}"')
    if encrypted_secret:
        print(f'INDODAX_SECRET_KEY_ENC="{encrypted_secret}"')
    if encrypted_token:
        print(f'TELEGRAM_BOT_TOKEN_ENC="{encrypted_token}"')
    if chat_id:
        print(f'TELEGRAM_CHAT_ID="{chat_id}"')
    
    # Save encryption key
    print()
    print("=" * 60)
    print("⚠️  SECURITY: Simpan encryption key dengan aman! Jangan di-commit!")
    print("=" * 60)
    print()
    
    save_choice = input("Simpan encryption key langsung ke .env? (y/n): ").strip().lower()
    if save_choice == 'y':
        try:
            env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
            with open(env_path, "a") as f:
                f.write(f'\nENCRYPTION_KEY={manager.key.decode()}\n')
            print(f"✅ Encryption key ditambahkan ke {env_path}")
        except Exception as e:
            print(f"❌ Gagal menyimpan ke .env: {e}")
    else:
        save_key = input("Simpan ke file encryption_key.txt? (y/n): ").strip().lower()
        if save_key == 'y':
            manager.save_key("encryption_key.txt")
            print("✅ Encryption key disimpan ke encryption_key.txt")
        else:
            print()
            print("⚠️  Encryption key TIDAK disimpan. Anda harus menambahkannya secara manual ke .env:")
            print(f"ENCRYPTION_KEY={manager.key.decode()}")
            print("Perhatikan: key ini akan terlihat di terminal scrollback!")
    
    print()


if __name__ == "__main__":
    main()
