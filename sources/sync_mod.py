import os
import re
from time import sleep
from subprocess import Popen, STDOUT
from colorama import init, Fore, Style
from sources.db_mod import db_worker
from sources.input_output_mod import input_helper
from sources.config_mod import config_read_helper, config_set_helper
from sources.security_mod import check_master_pass, hash_sha256, aes_decryption, aes_encryption
from sources.localization_mod import select_language

"""
Этот модуль содержит логику для синхронизации файла паролей через Google Drive.
"""

# Colorama.Initialize() для цветного форматирования в консоли
init(autoreset=True)

_ = select_language("english-sync_mod")


def sync_db_check_changes_helper(key_field: str):
    request_str = (f"SELECT DISTINCT * FROM data, temp WHERE temp.Description = data.Description"
                   f" AND temp.{key_field} = data.{key_field} AND temp.URL = data.URL")
    db_request_data = db_worker(".//data//pswdmn.db", request_str, 1)

    for record_indx in range(len(db_request_data)):
        # проверяем даты ModificationTime, у кого дата новее, тот и содержит актуальную информацию
        if db_request_data[record_indx][8] > db_request_data[record_indx][17]:
            # если дата модификации в таблице data > чем дата в таблице temp
            request_str = f"Delete From temp Where Id = {db_request_data[0][9]}"
            db_worker(".//data//pswdmn.db", request_str, 1)
        # если дата в таблице data < чем в temp, то обновить информацию в data
        else:
            if key_field == "Email":
                request_str = ("Update data SET Login = ?, Pass = ?, Salt = ?, PasswordDate = ?,"
                               f"ModificationTime = ? Where Id = {db_request_data[record_indx][0]}")
                db_worker(".//data//pswdmn.db", request_str, 2, db_request_data[record_indx][13:])
            else:
                request_str = ("Update data SET Email = ?, Pass = ?, Salt = ?, PasswordDate = ?,"
                               f"ModificationTime = ? Where Id = {db_request_data[0][0]}")
                db_worker(".//data//pswdmn.db", request_str, 2,
                          (db_request_data[record_indx][12],) + db_request_data[record_indx][14:])
            request_str = f"Delete From temp Where Id = {db_request_data[record_indx][9]}"
            db_worker(".//data//pswdmn.db", request_str, 1)


def sync_db_main():
    selected_action = input_helper(_("\nВыберите необходимое действие: \n"
                                     "(1) - Выгрузить шифрованную копию на Google Drive \n"
                                     "(2) - Получить шифрованную копию с Google Drive \n"
                                     "Введите номер действия: "),
                                   _("Действия с таким номером не существует!"),
                                   "number",
                                   range(1, 3))

    # открываем конфиг файл и считываем путь до установленного клиента GDrive
    if os.path.isfile(os.getcwd() + "//data//config//settings.ini"):
        gdrive_path = config_read_helper("SyncViaGoogle", "executable")

        # запоминаем текущую папку и переходим в папку с клиентом GDrive
        exe_folder = os.getcwd()
        os.chdir(gdrive_path)

        if os.path.isfile("GoogleDriveFS.exe"):
            # запускаем клиента GDrive
            with open(os.devnull, "w") as f:
                Popen(["GoogleDriveFS.exe"], stdout=f, stderr=STDOUT)
            # ждём 3 секунды пока он запустится
            sleep(3)
        else:
            print(Fore.RED + _("\nКлиент Google Drive не найден, проверьте путь в файле data\\config\\settings.ini\n"))
            return

        # возвращаемся в папку с исполняемым файлом программы
        os.chdir(exe_folder)
        # получаем из конфига в какую папку на GDRive выгрузить шифрованную базу
        gdrive_path = config_read_helper("SyncViaGoogle", "syncfolder")

        # если выбрали выгрузить копию БД на GDrive для последующей синхронизации
        if selected_action == "1":
            # запрашиваем ввод мастер пароля
            master_pass = check_master_pass()
            # открываем базу данных с паролями, читаем в бинарном виде, шифруем
            with open(".//data//pswdmn.db", "rb") as db_file:
                db_binary = db_file.read()
            # считаем SHA256 хеш исходной, незашифрованной базы данных, сохраняем
            with open(gdrive_path + "\\pswdmn.db.hash", "w") as db_hash:
                db_hash.write(hash_sha256(db_binary))
            # переменная список - шифрованная база и соль
            db_binary = aes_encryption(db_binary, master_pass)
            # записываем в папку на Google Drive шифрованную базу и её соль
            with open(gdrive_path + "\\pswdmn.db.protected", "wb") as db_file_sync:
                db_file_sync.write(db_binary[0])
            with open(gdrive_path + "\\pswdmn.db.salt", "wb") as db_file_sync:
                db_file_sync.write(db_binary[1])
            print(Fore.GREEN + _("\nШифрованный файл базы данных успешно синхронизирован с Google Drive\n"))

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
                    # для запроса мастер пароля не используется security_mod.check_master_pass()
                    # т.к. этот метод проверяет пароль на основе хеша из БД, при первоначальном
                    # использовании менеджера хеша мастер пароля и самой базы может не быть.
                    master_pass = input(Fore.CYAN + "Введите мастер пароль для базы: " + Style.RESET_ALL)
                    # здесь возникнет исключение если был введён неправильный пароль
                    try:
                        db_binary = aes_decryption(db_binary, master_pass, db_salt)
                    except:
                        print(Fore.RED + _("\nВведён неправильный мастер пароль. Повторите попытку.\n"))
                    else:
                        break
                # если файл успешно расшифрован, то проверить для подстраховки его хеш с хешем оригинала
                db_hash_after_decrypt = hash_sha256(db_binary)
                if db_hash_origin != db_hash_after_decrypt:
                    print(Fore.RED + _("Копия повреждена, не совпадают хеши.\n"))
                else:
                    # записываем расшифрованную из Google Drive копию в файл
                    with open(os.getcwd() + "//data//pswdmn.db.temp", "wb") as db_file_sync:
                        db_file_sync.write(db_binary)

                    # проверяем есть ли уже в папке с программой файл паролей
                    if not os.path.isfile(".//data//pswdmn.db"):
                        # если нет, то просто переименовываем файл, полученный из Google Drive
                        # и тогда синхронизация завершена
                        os.rename(".//data//pswdmn.db.temp", ".//data//pswdmn.db")
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
                        db_worker(".//data//pswdmn.db", request_str, 1)

                        # переносим данные БД из Google Drive в temp таблицу текущей БД
                        request_str = "SELECT * from data"
                        db_request_data = db_worker(".//data//pswdmn.db.temp", request_str, 1)
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
                            db_worker(".//data//pswdmn.db", request_str, 2, item[1:])

                        # выбираем все записи из temp у которых Description, URL + Email/Login совпадают
                        # с записями из основной таблицы
                        # такие записи являются записями для одного и того же сайта
                        sync_db_check_changes_helper("Email")
                        sync_db_check_changes_helper("Login")

                        # выбираем все уникальные записи из temp и переносим в основную таблицу data
                        request_str = ("SELECT DISTINCT Description, URL, Email, Login, Pass, Salt, PasswordDate, "
                                       "ModificationTime FROM temp EXCEPT SELECT Description, URL, Email, Login, Pass, "
                                       "Salt, PasswordDate, ModificationTime FROM data")
                        db_request_data = db_worker(".//data//pswdmn.db", request_str, 1)
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
                            db_worker(".//data//pswdmn.db", request_str, 2, record)

                        request_str = "Drop Table temp"
                        db_worker(".//data//pswdmn.db", request_str, 1)
                        os.remove(".//data//pswdmn.db.temp")

                    print(Fore.GREEN + _("\nСинхронизация успешно завершена!\n"))

            else:
                print(Fore.YELLOW + _("\nНе найдены копии в папке Google Drive, синхронизация невозможна.\n"
                                      "Сначала выполните выгрузку шифрованной копии.\n"))
    else:
        print(Fore.RED + _("\nОшибка. Потерян файл конфигурации settings.ini, проверьте файл в папке data\\config\n"))


def find_gdrive_path():
    if os.name == "nt":
        path = os.path.expandvars("%systemdrive%") + r"\Program Files\Google\Drive File Stream"
        current_ver_folder = ""
        pattern = r"^\d+\.\d+\.\d+\.\d+$"
        for folder in os.listdir(path):
            if re.match(pattern, folder):
                maxnum = 0
                cur = 0
                for num in folder.split("."):
                    cur += int(num)
                if cur > maxnum:
                    maxnum = cur
                    current_ver_folder = folder
        path += "\\" + current_ver_folder
        config_set_helper("SyncViaGoogle", "executable", path)