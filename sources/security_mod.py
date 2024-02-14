import datetime
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from os import urandom, path
from base64 import urlsafe_b64encode
from secrets import choice
from colorama import init, Fore, Style
from datetime import date
from sources.input_mod import input_helper
from sources.db_mod import db_worker

"""
Этот модуль содержит логику работы с шифрованием и безопасностью.
"""

# Colorama.Initialize() для цветного форматирования в консоли
init(autoreset=True)


def aes_key_derivation(salt: bytes, key: str) -> bytes:
    """Функция для генерации ключа RSA"""
    # инициализация Password Based Key Derivation Function
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=2500000, )
    # создание ключа на основе парольной фразы (строки key)
    return urlsafe_b64encode(kdf.derive(key.encode()))


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


def pswrd_generator() -> str:
    """
    Метод генерирует пароль заданной длины.
    """
    pass_length = int(input_helper(
        "Введите длину пароля: ",
        "Недопустимая длина."
        "\nДлина должна быть в диапазоне 8 - 128 символов",
        "number",
        range(8, 129)
    ))
    alph = "abcdefghijklmnopqrstuvwxyz"
    special = "!@#$%?"
    numbers = "0123456789"

    result = []
    for i in range(1, pass_length + 1):
        result.append(choice(alph + alph.upper() + numbers + special))
    return "".join(result)


def check_master_pass() -> str:
    """
    Метод обработки ввода и проверки мастер пароля.
    Возвращает введённый мастер пароль.
    """
    while True:
        # colorama autoreset не работает для input
        master_pass = input(Fore.CYAN + "Введите мастер пароль для базы: " + Style.RESET_ALL)

        # запрос для получения хеша мастер пароля
        request_str = "SELECT Value FROM control"

        # если в БД нет хеша мастер пароля, то сохраняем его
        if len(db_worker(".//data//pswdmn.db", request_str, 1)) == 0:
            print(Fore.YELLOW + "\nВы задали мастер пароль в самый первый раз,"
                                "\nзапомните его, он нужен для последующего использования парольного менеджера.")
            request_str = "INSERT INTO control (Value) VALUES(?)"
            db_worker(".//data//pswdmn.db", request_str, 2, (hash_sha256(master_pass.encode()),))
            break

        # иначе сравниваем, что пытаемся шифровать/дешифровать с тем же мастер паролем
        if db_worker(".//data//pswdmn.db", request_str, 1)[0][0] != hash_sha256(master_pass.encode()):
            print(Fore.RED + "\nНеправильный мастер пароль!\n")
            continue
        else:
            break
    return master_pass


def calc_timedelta_month(then: date, now: date) -> int:
    """
    Функция определяет примерное число месяцев прошедших между двумя датами.
    """
    # если две даты в разные годы
    if now.year > then.year:
        # если прошло больше года
        month = (now.year - then.year - 1) * 12
        # количество месяцев в then до конца года
        if then.day == 1:
            month += 12 - (then.month - 1)
        else:
            month += 12 - then.month
        # количество месяцев в now с начала года
        month += now.month - 1
    # если две даты в один и тот же год
    else:
        month = now.month - then.month - 1
    return month


def check_db_existence() -> bool:
    """
    Функция проверки существования базы данных.
    Возвращает False если база не создана.
    """
    is_exist = False
    if not path.exists(".//data//pswdmn.db"):
        print(Fore.RED + "\nНеобходимо добавить хотя бы один сайт!\n")
    else:
        is_exist = True
    return is_exist


def change_master_pass():
    print("")
    old_master_password = check_master_pass()
    new_master_pass = input_helper("Введите новый мастер пароль: ",
                                   "Новый пароль не может быть пустой строкой!",
                                   "string")
    print("Выполняется процесс обновления мастер пароля, пожалуйста, подождите...")
    # получаем все пароли из БД, которые зашифрованы старым мастер паролем
    request_str = "Select Id, Pass, Salt from data"
    sites_passwords = db_worker(".//data//pswdmn.db", request_str, 1)
    # дешифруем их со старым мастер паролем, затем шифруем с новым и сохраняем в БД
    for id_password_enc in sites_passwords:
        # password это кортеж, первый элем это ид, второй это пароль, третий соль
        password = aes_decryption(id_password_enc[1], old_master_password, id_password_enc[2])
        password = aes_encryption(password, new_master_pass)
        request_str = "UPDATE data SET Pass=?, Salt=? WHERE Id=?"
        db_worker(".//data//pswdmn.db", request_str, 2,
                  (password[0], password[1], id_password_enc[0]))
        # после внесения изменений переопределяем значение ModificationTime
        mod_epoch = int(datetime.datetime.now().timestamp())
        request_str = "UPDATE data SET ModificationTime = ? WHERE Id = ?"
        db_worker(".//data//pswdmn.db", request_str, 2, (mod_epoch, id_password_enc[0]))

    request_str = "UPDATE control SET Value=?"
    db_worker(".//data//pswdmn.db", request_str, 2, (hash_sha256(new_master_pass.encode()),))
    print(Fore.GREEN + "Мастер пароль обновлён успешно!\n")
