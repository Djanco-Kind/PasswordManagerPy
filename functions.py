import datetime
import os
import secrets
import re
import time
import sqlite3
import crypta
import configparser
import subprocess
from colorama import init, Fore, Style

# Colorama.Initialize() для цветного форматирования в консоли
init(autoreset=True)


def to_lower_sqlite(str_input):
    """
    Функция перевода в нижний регистр для sqlite
    Это костыль, но он решает проблему регистрозависимости
    """
    return str_input.lower()


def db_worker(path: str, request: str, func_type: int, request_data=()) -> list:
    """
    Запросы по типу SELECT/CREATE/DELETE = 1.
    Запросы по типу INSERT/UPDATE с данными = 2.
    Возвращает список кортежей.
    """
    # PARSE_DECLTYPES нужна для автоматического определения типов
    with sqlite3.connect(path,
                         detect_types=sqlite3.PARSE_DECLTYPES) as connection:
        # подключение функции для перевода в нижний регистр
        connection.create_function("lower", 1, to_lower_sqlite)
        sql_exec = connection.cursor()
        # для SELECT/CREATE/DELETE
        if func_type == 1:
            sql_exec.execute(request)
        # для INSERT/UPDATE с данными
        elif func_type == 2:
            sql_exec.execute(request, request_data)
        result = sql_exec.fetchall()
    return result


def check_master_pass(call_from_sync=False) -> str:
    """
    Ввод и проверка мастер пароля.
    Возвращает введённый мастер пароль.
    """
    while True:
        # colorama autoreset не работает для input
        master_pass = input(Fore.CYAN + "Введите мастер пароль для базы: " + Style.RESET_ALL)
        # if not call_from_sync:
        # запрос для получения хеша мастер пароля
        request_str = "SELECT Value FROM control"
        # если в БД нет хеша мастер пароля, то сохраняем его
        if len(db_worker("pswdmn.db", request_str, 1)) == 0:
            print(Fore.YELLOW + "\nВы задали мастер пароль в самый первый раз,"
                                "\nзапомните его, он нужен для последующего использования парольного менеджера.")
            request_str = "INSERT INTO control (Value) VALUES(?)"
            db_worker("pswdmn.db", request_str, 2, (crypta.hash_sha256(master_pass.encode()),))
            break

        # иначе сравниваем, что пытаемся шифровать/дешифровать с тем же мастер паролем
        if db_worker("pswdmn.db", request_str, 1)[0][0] != crypta.hash_sha256(master_pass.encode()):
            print(Fore.RED + "\nНеправильный мастер пароль!\n")
            continue
        else:
            break
    return master_pass


def search_db_entries() -> list:
    """
    Простой поиск записей в SQLite.
    Возвращает список кортежей с найденным по ключевым словам.
    """
    while True:
        user_keywords = input_helper(
            ("\nВведите ключевые слова, либо URL для поиска.\n"
             "Для разделения ключевых слов используйте запятые (логическое ИЛИ): "),
            "Пустой ввод недопустим, укажите ключевые слова!",
            "string"
        )
        break

    # нарезаем строку в нижнем регистре, разделитель запятая
    user_keywords = user_keywords.lower().split(",")

    # выполняем поиск, используя ключевые слова из списка
    # результаты поиска записываем в список results
    found_results = []
    for keyword in user_keywords:
        request_str = ("SELECT * FROM data "
                       "WHERE lower(Description) LIKE '%{0}%' "
                       "OR URL LIKE '%{0}%'").format(keyword)
        for item in db_worker("pswdmn.db", request_str, 1):
            if item not in found_results:
                found_results.append(item)
    return found_results


def print_found_in_db(found_results: list) -> bool:
    # если результаты пустые, то пропусти эту итерацию
    if len(found_results) == 0:
        print(Fore.YELLOW + "\nРезультатов не найдено, "
                            "попробуйте поиск с другими ключевыми словами.\n")
        return True
    # иначе выведи результаты на печать
    else:
        # самые длинные строки
        longest_description = 0
        longest_url = 0
        longest_nickname = 0

        for result in found_results:
            if len(result[1]) > longest_description:
                longest_description = len(result[1])
            if len(result[2]) > longest_url:
                longest_url = len(result[2])
            if len(result[4]) > longest_nickname:
                longest_nickname = len(result[4])

        out_string = "{:<3} - {:<" f"{longest_description + 1}" "} {:<" f"{longest_url + 1}" "} Логин: {:<" f"{longest_nickname + 1}" "}"

        print("\nНайдены следующие сайты:\n")
        for index, result in enumerate(found_results):
            # в формате: индекс описание URL Логин: ****** Пароль: ******
            print(out_string.format(index + 1, result[1], result[2], result[4]))

            if index == len(found_results) - 1:
                print()
        return False


def check_url_input() -> str:
    """
    Функция проверки вводимого URL с помощью regex.
    """
    pattern = r"^(http|https)://([a-z0-9]+(\.?\-?))+(\.[a-z]{2,5})$"
    pattern2 = r"^(http|https)://\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}"

    while True:
        # colorama autoreset не работает для input
        site_url = str(input(Fore.CYAN + "Введите URL адрес сайта, "
                                         "в формате http(s)://site.ru или http(s)://IP_адрес: "
                             + Style.RESET_ALL)).lower()
        if re.search(pattern, site_url) or re.search(pattern2, site_url):
            break
        else:
            print(Fore.RED + "Неправильный формат URL!")
            continue

    return site_url


def input_helper(hint_for_user: str, hint_invalid_inp: str,
                 input_type: str, input_range=range(1)) -> str:
    """
    Вспомогательная функция для работы с пользовательским вводом.
    """
    user_input = ""
    if input_type == "string":
        while True:
            # запрашиваем пользовательский ввод
            # colorama autoreset не работает для input
            user_input = input(Fore.CYAN + hint_for_user + Style.RESET_ALL)
            # вводимая строка не должна быть пустой
            if len(user_input) == 0:
                print(Fore.RED + "\n" + hint_invalid_inp + "\n")
                continue
            else:
                break
        return user_input
    elif input_type == "number":
        while True:
            try:
                # запрашиваем пользовательский ввод
                # colorama autoreset не работает для input
                user_input = int(input(Fore.CYAN + hint_for_user + Style.RESET_ALL))
            # если возникает ошибка преобразования в целое число
            except ValueError:
                print(Fore.RED + "\n" + hint_invalid_inp + "\n")
                continue
            # вводимое число должно быть в диапазоне
            if user_input not in input_range:
                print(Fore.RED + "\n" + hint_invalid_inp + "\n")
                continue
            else:
                user_input = str(user_input)
                break
        return user_input


def pswrd_generator() -> str:
    """
    Генератор пароля заданной длины.
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
        result.append(secrets.choice(alph + alph.upper() + numbers + special))
    return "".join(result)


def timedelta_month(then: datetime.date, now: datetime.date) -> int:
    """
    Функция определяет целое число месяцев прошедших между двумя датами.
    Если даты были в разные годы, то хвостовые дни месяцев не суммируются
    и никак не округляются до месяца, т.к. в разных месяцах разное число дней.
    """
    # если две даты в разные годы
    if now.year > then.year:
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


def db_not_exists():
    # проверяем, что база с паролями вообще есть,
    # т.е. до этого был сохранён хотя бы один сайт
    if not os.path.exists(os.getcwd() + "//pswdmn.db"):
        print(Fore.RED + "\nНеобходимо добавить хотя бы один сайт!\n")
        return True


def sync_db_check_changes(key_field: str):
    request_str = (f"SELECT DISTINCT * FROM data, temp WHERE temp.Description = data.Description"
                   f" AND temp.{key_field} = data.{key_field} AND temp.URL = data.URL")
    db_request_data = db_worker("pswdmn.db", request_str, 1)

    for record_indx in range(len(db_request_data)):
        # проверяем даты ModificationTime, у кого дата новее, тот и содержит актуальную информацию
        if db_request_data[record_indx][8] > db_request_data[record_indx][17]:
            # если дата модификации в таблице data > чем дата в таблице temp
            request_str = f"Delete From temp Where Id = {db_request_data[0][9]}"
            db_worker("pswdmn.db", request_str, 1)
        # если дата в таблице data < чем в temp, то обновить информацию в data
        else:
            if key_field == "Email":
                request_str = ("Update data SET Login = ?, Pass = ?, Salt = ?, PasswordDate = ?,"
                               f"ModificationTime = ? Where Id = {db_request_data[record_indx][0]}")
                db_worker("pswdmn.db", request_str, 2, db_request_data[record_indx][13:])
            else:
                request_str = ("Update data SET Email = ?, Pass = ?, Salt = ?, PasswordDate = ?,"
                               f"ModificationTime = ? Where Id = {db_request_data[0][0]}")
                db_worker("pswdmn.db", request_str, 2,
                          (db_request_data[record_indx][12],) + db_request_data[record_indx][14:])
            request_str = f"Delete From temp Where Id = {db_request_data[record_indx][9]}"
            db_worker("pswdmn.db",request_str, 1)


def sync_db():
    selected_action = input_helper(("\nВыберете необходимое действие: \n"
                                    "(1) - Выгрузить шифрованную копию на Google Drive \n"
                                    "(2) - Получить шифрованную копию с Google Drive \n"
                                    "Введите номер действия: "),
                                   "Действия с таким номером не существует!",
                                   "number",
                                   range(1, 3))

    # открываем конфиг файл и считываем путь до установленного клиента GDrive
    if os.path.isfile(os.getcwd() + "\\sync.ini"):
        config = configparser.ConfigParser()
        config.read("sync.ini")
        gdrive_path = config.get("SyncViaGoogle", "executable")

        # запоминаем текущую папку и переходим в папку с клиентом GDrive
        exe_folder = os.getcwd()
        os.chdir(gdrive_path)

        # запускаем клиента GDrive
        with open(os.devnull, "w") as f:
            subprocess.Popen(["GoogleDriveFS.exe"], stdout=f, stderr=subprocess.STDOUT)
        # ждём 3 секунды пока он запустится
        time.sleep(3)

        # получаем из конфига в какую папку на GDRive выгрузить шифрованную базу
        gdrive_path = config.get("SyncViaGoogle", "syncfolder")
        # возвращаемся в папку с исполняемым файлом программы
        os.chdir(exe_folder)

        # если выбрали выгрузить копию БД на GDrive для последующей синхронизации
        if selected_action == "1":
            # запрашиваем ввод мастер пароля
            master_pass = check_master_pass()
            # открываем базу данных с паролями, читаем в бинарном виде, шифруем
            with open("pswdmn.db", "rb") as db_file:
                db_binary = db_file.read()
            # считаем SHA256 хеш исходной, незашифрованной базы данных, сохраняем
            with open(gdrive_path + "\\pswdmn.db.hash", "w") as db_hash:
                db_hash.write(crypta.hash_sha256(db_binary))
            # переменная список - шифрованная база и соль
            db_binary = crypta.aes_encryption(db_binary, master_pass)
            # записываем в папку на Google Drive шифрованную базу и её соль
            with open(gdrive_path + "\\pswdmn.db.protected", "wb") as db_file_sync:
                db_file_sync.write(db_binary[0])
            with open(gdrive_path + "\\pswdmn.db.salt", "wb") as db_file_sync:
                db_file_sync.write(db_binary[1])
            print(Fore.GREEN + "\nШифрованный файл базы данных успешно синхронизирован с Google Drive\n")

        # если выбрали получить файл с GDrive и выполнить синхронизацию
        else:
            # проверяем, что в GDrive вообще есть файлы для синхронизации
            if os.path.isfile(gdrive_path + "\\pswdmn.db.protected") and os.path.isfile(
                    gdrive_path + "\\pswdmn.db.salt"):
                # если они есть, то начинаем процесс синхронизации
                # считываем файлы с Google Drive папки
                with open(gdrive_path + "\\pswdmn.db.protected", "rb") as db_file_reader:
                    db_binary = db_file_reader.read()
                with open(gdrive_path + "\\pswdmn.db.salt", "rb") as db_file_reader:
                    db_salt = db_file_reader.read()
                with open(gdrive_path + "\\pswdmn.db.hash", "r") as db_hash_reader:
                    db_hash_origin = db_hash_reader.read()

                # запрашиваем ввод мастер пароля
                # затем дешифруем файл с прочитанной солью и введённым мастер паролем
                while True:
                    master_pass = input(Fore.CYAN + "Введите мастер пароль для базы: " + Style.RESET_ALL)
                    # здесь возникнет исключение если был введён неправильный пароль
                    try:
                        db_binary = crypta.aes_decryption(db_binary, master_pass, db_salt)
                    except:
                        print(Fore.RED + "\nВведён неправильный мастер пароль. Повторите попытку.\n")
                    else:
                        break
                # если файл успешно расшифрован, то проверить для подстраховки его хеш с хешем оригинала
                db_hash_after_decrypt = crypta.hash_sha256(db_binary)
                if db_hash_origin != db_hash_after_decrypt:
                    print(Fore.RED + "Копия повреждена, не совпадают хеши.\n")
                else:
                    # записываем расшифрованную из Google Drive копию в файл
                    with open(os.getcwd() + "\\pswdmn.db.temp", "wb") as db_file_sync:
                        db_file_sync.write(db_binary)

                    # проверяем есть ли уже в папке с программой файл паролей
                    if not os.path.isfile("pswdmn.db"):
                        # если нет, то просто переименовываем файл, полученный из Google Drive
                        # и тогда синхронизация завершена
                        os.rename("pswdmn.db.temp", "pswdmn.db")
                    else:
                        # если файл есть, то его нужно "склеить" с копией из GDrive
                        # создаём в нём временную таблицу temp для сохранения данных из синхронизируемой копии
                        request_str = ("CREATE TABLE IF NOT EXISTS temp ("
                                       "Id INTEGER PRIMARY KEY AUTOINCREMENT,"
                                       "Description TEXT,"
                                       "URL TEXT,"
                                       "Email TEXT,"
                                       "Login TEXT,"
                                       "Pass BLOB,"
                                       "Salt BLOB,"
                                       "PasswordDate DATE,"
                                       "ModificationTime INTEGER)")
                        db_worker("pswdmn.db", request_str, 1)

                        # переносим данные БД из Google Drive в temp таблицу текущей БД
                        request_str = "SELECT * from data"
                        db_request_data = db_worker("pswdmn.db.temp", request_str, 1)
                        request_str = ("INSERT INTO temp ("
                                       "Description,"
                                       "URL,"
                                       "Email,"
                                       "Login,"
                                       "Pass,"
                                       "Salt,"
                                       "PasswordDate,"
                                       "ModificationTime) VALUES(?, ?, ?, ?, ?, ?, ?, ?)")
                        for item in db_request_data:
                            # кортеж item содержит строку из БД Google Drive, 0 элемент это Id, он здесь не нужен
                            db_worker("pswdmn.db", request_str, 2, item[1:])

                        # выбираем все записи из temp у которых Description, URL + Email/Login совпадают
                        # с записями из основной таблицы
                        # такие записи являются записями для одного и того же сайта
                        sync_db_check_changes("Email")
                        sync_db_check_changes("Login")

                        # выбираем все уникальные записи из temp и переносим в основную таблицу data
                        request_str = ("SELECT DISTINCT Description, URL, Email, Login, Pass, Salt, PasswordDate, "
                                       "ModificationTime FROM temp EXCEPT SELECT Description, URL, Email, Login, Pass, "
                                       "Salt, PasswordDate, ModificationTime FROM data")
                        db_request_data = db_worker("pswdmn.db", request_str, 1)
                        request_str = ("INSERT INTO data ("
                                       "Description,"
                                       "URL,"
                                       "Email,"
                                       "Login,"
                                       "Pass,"
                                       "Salt,"
                                       "PasswordDate,"
                                       "ModificationTime) VALUES(?, ?, ?, ?, ?, ?, ?, ?)")
                        for record in db_request_data:
                            db_worker("pswdmn.db", request_str, 2, record)

                        request_str = "Drop Table temp"
                        db_worker("pswdmn.db", request_str, 1)
                        os.remove("pswdmn.db.temp")

                    print(Fore.GREEN + "\nСинхронизация успешно завершена!\n")

            else:
                print(Fore.YELLOW + "\nНе найдены копии в папке Google Drive, синхронизация невозможна.\n"
                                    "Сначала выполните выгрузку шифрованной копии.\n")
    else:
        print(Fore.RED + "\nОшибка. Потерян файл конфигурации sync.ini\n")
