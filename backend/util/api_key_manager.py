import json
from pathlib import Path
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
import base64
import os


KEYS_FILE = Path.home() / ".nokton" / "api_keys.enc"
SALT_FILE = Path.home() / ".nokton" / ".salt"


class ApiKeyManager:
    def __init__(self, storage_path: str | None = None):
        self._path = Path(storage_path) if storage_path else KEYS_FILE
        self._salt_path = SALT_FILE
        self._keys: dict[str, str] = {}
        self._load()

    def _get_machine_key(self) -> bytes:
        machine_id = os.environ.get("COMPUTERNAME", "nokton-default").encode()
        user = os.environ.get("USERNAME", "user").encode()

        if not self._salt_path.exists():
            self._salt_path.parent.mkdir(parents=True, exist_ok=True)
            salt = os.urandom(16)
            with open(self._salt_path, "wb") as f:
                f.write(salt)
        else:
            with open(self._salt_path, "rb") as f:
                salt = f.read()

        kdf = PBKDF2(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(machine_id + user))
        return key

    def _load(self):
        if not self._path.exists():
            self._keys = {}
            return
        try:
            key = self._get_machine_key()
            f = Fernet(key)
            with open(self._path, "rb") as fp:
                encrypted = fp.read()
            decrypted = f.decrypt(encrypted)
            self._keys = json.loads(decrypted.decode())
        except Exception:
            self._keys = {}

    def _save(self):
        self._path.parent.mkdir(parents=True, exist_ok=True)
        try:
            key = self._get_machine_key()
            f = Fernet(key)
            data = json.dumps(self._keys).encode()
            encrypted = f.encrypt(data)
            with open(self._path, "wb") as fp:
                fp.write(encrypted)
        except Exception:
            pass

    def set_key(self, provider: str, key: str):
        self._keys[provider] = key
        self._save()

    def get_key(self, provider: str) -> str | None:
        return self._keys.get(provider)

    def delete_key(self, provider: str):
        self._keys.pop(provider, None)
        self._save()

    def list_providers(self) -> list[str]:
        return list(self._keys.keys())

    def has_key(self, provider: str) -> bool:
        return provider in self._keys
