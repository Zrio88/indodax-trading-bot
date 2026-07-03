"""
Secret Manager for API Key Encryption
Uses Fernet (AES-256) for secure storage of sensitive data
"""
from cryptography.fernet import Fernet
import os


class SecretManager:
    """
    Encrypted API Key Storage using Fernet (AES-256 in CBC mode)
    
    Usage:
        manager = SecretManager()
        encrypted = manager.encrypt("my_api_key")
        decrypted = manager.decrypt(encrypted)
        
        # Save key for later use
        manager.save_key("encryption_key.txt")
        
        # Load key later
        manager = SecretManager.load_key("encryption_key.txt")
    """
    
    def __init__(self, encryption_key: str = None):
        """
        Initialize with optional encryption key.
        If no key provided, generates a new one.
        
        Args:
            encryption_key: Base64-encoded Fernet key (32 URL-safe base64-encoded bytes)
        """
        if encryption_key:
            self.key = encryption_key.encode()
        else:
            self.key = Fernet.generate_key()
        self.cipher = Fernet(self.key)
    
    def encrypt(self, data: str) -> str:
        """
        Encrypt sensitive data
        
        Args:
            data: Plain text string to encrypt
            
        Returns:
            Base64-encoded encrypted string
        """
        if not isinstance(data, str):
            data = str(data)
        return self.cipher.encrypt(data.encode()).decode()
    
    def decrypt(self, encrypted_data: str) -> str:
        """
        Decrypt sensitive data
        
        Args:
            encrypted_data: Base64-encoded encrypted string
            
        Returns:
            Decrypted plain text string
            
        Raises:
            cryptography.fernet.InvalidToken: If data is corrupted or key is wrong
        """
        return self.cipher.decrypt(encrypted_data.encode()).decode()
    
    def save_key(self, path: str = "encryption_key.txt"):
        """
        Save encryption key to file
        
        Args:
            path: File path to save the key
        """
        with open(path, "w") as f:
            f.write(self.key.decode())
        os.chmod(path, 0o600)  # Restrict permissions
    
    @classmethod
    def load_key(cls, path: str = "encryption_key.txt"):
        """
        Load encryption key from file
        
        Args:
            path: File path containing the encryption key
            
        Returns:
            SecretManager instance with loaded key
        """
        with open(path, "r") as f:
            key = f.read().strip()
        return cls(encryption_key=key)
    
    def __repr__(self):
        return f"SecretManager(key={'***REDACTED***'})"
