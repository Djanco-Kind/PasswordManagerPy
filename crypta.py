from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from os import urandom
import base64


def aes_key_derivation(salt: bytes, key: str):
    """Функция для генерации ключа RSA"""
    # инициализация Password Based Key Derivation Function
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=2500000, )
    # создание ключа на основе парольной фразы (строки key)
    return base64.urlsafe_b64encode(kdf.derive(key.encode()))


def aes_encryption(data: bytes, key: str) -> list:
    """Функция для шифрования AES-128"""
    # генерация соли
    salt = urandom(16)
    # создание ключа на основе парольной фразы
    prepared_key = aes_key_derivation(salt, key)
    fernet = Fernet(prepared_key)
    # возвращаем bytes после шифрования и соль
    results = [fernet.encrypt(data), salt]
    return results


def aes_decryption(data: bytes, key: str, salt: bytes) -> bytes:
    """Функция для расшифровки AES-128"""
    # создание ключа на основе парольной фразы
    prepared_key = aes_key_derivation(salt, key)
    fernet = Fernet(prepared_key)
    # возвращаем bytes после расшифровки
    return fernet.decrypt(data)


def hash_sha256(data: bytes) -> str:
    """Функция хеширования SHA256"""
    # устанавливаем алгоритм хеширования
    digest = hashes.Hash(hashes.SHA256())
    # указываем данные для хеширования
    digest.update(data)
    # возвращаем HEX строку с хешем
    return digest.finalize().hex()
