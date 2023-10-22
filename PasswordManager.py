import sqlite3
import time
import base64
import re
from os import urandom
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

def db_worker(request_str: str, func_type: int, request_data=()):
    """
    Запросы по типу SELECT/CREATE/DELETE = 1
    Запросы по типу INSERT/UPDATE с данными = 2
    Возвращает список кортежей
    """
    with sqlite3.connect("pswdmn.db") as connection:
        sql_exec = connection.cursor()
        #запросы по типу SELECT/CREATE/DELETE
        if func_type == 1 : sql_exec.execute(request_str)
        #запросы по типу INSERT/UPDATE с данными
        elif func_type == 2 : sql_exec.execute(request_str, request_data)
        return sql_exec.fetchall()

def crypto_worker(material1: str, func_type: int, material2="", salt=b''):
    """
    func_type = 1 шифрование
    func_type = 2 дешифрование
    func_type = 3 хеширование SHA256
    
    :material1: шифруемая/хешируемая строка
    :material2: ключ шифрования
    
    Функция для работы с криптографией
    Fernet библиотека cryptography
    Шифрование AES-128 CBC
    """
    if salt == b'' : salt = urandom(16)
    kdf = PBKDF2HMAC(
         algorithm=hashes.SHA256(),
         length=32,
         salt=salt,
         iterations=2500000,)
    key = base64.urlsafe_b64encode(kdf.derive(material2.encode()))
    fernet = Fernet(key)
    # шифрование
    if func_type == 1:
        material1 = fernet.encrypt(material1.encode())
        return (material1, salt)
    # дешифрование
    if func_type == 2:
        material1 = fernet.decrypt(material1).decode()
        return material1
    # вычисление хеша
    if func_type == 3:
        digest = hashes.Hash(hashes.SHA256())
        digest.update(material1.encode('utf-8'))
        hash_result = digest.finalize().hex()
        return hash_result
    
def check_regex(checked: str, pattern : str):
    """
    Сопоставление строки checked c шаблоном pattern
    Вернёт True если сопоставление успешно
    """
    if re.search(pattern, checked): return True
    else: return False

def check_master_pass():
    """
    Ввод и проверка мастер пароля
    Возвращает введённый мастер пароль
    """
    while True:
                db_pass = input("Введите пароль для базы: ")
                request_str = "SELECT Value FROM secret"
                # если в БД нет хеша пароля сохранить его
                if (not db_worker(request_str, 1)):
                    request_str = "INSERT INTO secret (Value) VALUES(?)"
                    db_worker(request_str, 2, (crypto_worker(db_pass, 3),))
                    break
                # иначе сравниваем, что пытаемся шифровать/дешифровать с тем же мастер паролем
                if (db_worker(request_str, 1)[0][0] != crypto_worker(db_pass, 3)):
                    print("\nПароль для БД отличается от того, что использовался ранее!\n"
                          "Попробуйте ввести пароль ещё раз.\n")
                    continue
                else: break
    return db_pass

def extract_db_entries():
    """
    Простой поиск записей в базе средствами самой SQLite
    Возвращает список кортежей с найденным
    """     
    # запрашиваем у пользователя ключевые слова для поиска в БД
    # \s возвращает пробелы
    pattern = r"\s"
    while True:
        try:
            user_keywords = (
                 str(input(("\nВведите ключевые слова, либо URL для нахождения записи.\n"
                            "Используйте запятые," 
                            "не используйте пробелы: "))).lower())
            # если строка с пробелами, то сгенерируй исключение
            if check_regex(user_keywords, pattern): 
                raise Exception("Строка содержит пробелы!")
            # если строка без пробелов, то просто заверши ввод
            print("")
            break
        except Exception as exp: 
            print("\nОшибка ввода, пожалуйста, повторите ввод!")
            print("Сообщение ошибки: " + str(exp) + "\n")
                    
    # нарезаем строку отделяя по разделителю и преобразуем это в кортеж
    user_keywords = tuple(user_keywords.split(","))
            
    # выполняем поиск по БД, беря пользовательские ключ. слова из кортежа
    # результаты поиска записываем в список results
    results = []
    for keyword in user_keywords:
        request_str = ("SELECT * FROM data "
                       "WHERE Description LIKE '%{0}%' "
                       "OR URL LIKE '%{0}%'").format(keyword)
        for res in db_worker(request_str,1): results.append(res)
                
    # выводим результаты поиска если они есть
    if (results):
        for index, result in enumerate(results):
            print("(" + str(index) + ") " + result[1] + " " + result[2] + " Логин: xxxxxx Пароль: ******")
            if index == len(results) - 1: print("")
    else:
         #если результатов нет, то пропустить итерицию и снова вывести меню на следующей
         print("Результатов не найдено!\n")
            
    return results

def check_url_input():
    """
    Функция проверки вводимого URL
    Использует check_regex()
    """
    # паттерн для проверки URL адреса
    pattern = r"^((http|https)://([a-z0-9]+(\.?\-?))+)(\.[a-z]+)$"
            
    while True:
        site_url = str(input("Введите URL адрес сайта, в формате http(s)://site.ru : ")).lower()
        if (check_regex(site_url, pattern)): break
        else: print("Неправильный формат URL!")
        
    return site_url
                
#основная точка входа в программу
if __name__ == "__main__" :
    while True:
        
        print("(1) - Добавить информацию о сайте")
        print("(2) - Получить информацию о сайте")
        print("(3) - Отредактировать информацию")
        print("(4) - Удалить информацию")
        print("(5) - Выход из программы")
        
        try: user_choose = int(input("\nВведите номер действия: "))
        except: print("Необходимо ввести число!")
        
        if user_choose == 1:
            
            # если это самый первый запуск программы, то создать таблицу БД data
            request_str = """CREATE TABLE IF NOT EXISTS data (
            Id INTEGER PRIMARY KEY AUTOINCREMENT,
            Description TEXT, 
            URL TEXT,
            Email TEXT,
            Login TEXT,
            Pass BLOB, 
            UpdateDate INTEGER,
            MagicNumber BLOB)
            """
            db_worker(request_str, 1)
            
            # если это первый запуск аналогично создать таблицу БД secret
            request_str = "CREATE TABLE IF NOT EXISTS secret (Value TEXT)"
            db_worker(request_str, 1)
            
            # получить от пользователя данные для сохранения в таблице
            site_description = str(input("\nВведите описание сайта: ")).lower()
            
            #проверять вводимый пользователем URL
            site_url = check_url_input()
            
            # проверять, что пользователь не пытается добавить повторно те же данные 
            # для одного сайта разрешён один аккаунт
            request_str = "SELECT URL FROM data WHERE URL = \"" + str(site_url) + "\""
            # если fetchall() в db_worker возвращает не пустой список, то это повтор
            if (db_worker(request_str, 1)):
                print("\nОшибка. Вы пытались добавить сайт, который уже есть в базе!\n")
                continue
            
            site_email = input("Введите email если используется: ")
            if site_email == "" : site_email = "Не задан"
            
            site_login = input("Введите логин для сайта: ")
            site_pass = input("Введите пароль для сайта: ")
            
            # проверить пароль базы, если в БД есть его хеш или сохранить хеш на будущие проверки
            db_pass = check_master_pass()
                          
            # шифрование fernet AES-128
            crypto_result = crypto_worker(site_pass,1,db_pass)
            
            # занесение информации в БД
            request_str = ("INSERT INTO data ("
            "Description," 
            "URL,"
            "Email,"
            "Login,"
            "Pass," 
            "MagicNumber) VALUES(?, ?, ?, ?, ?, ?)")
            db_worker(request_str, 2, (site_description,site_url,site_email,site_login,crypto_result[0],crypto_result[1]))
            print("\nСайт успешно добавлен в базу!\n")
            
            del site_email
            del site_login
            del site_pass
            del db_pass
            
        elif user_choose == 2:
            
            # спрашиваем у пользователя ключевые слова
            results = extract_db_entries()
            # если результаты пустые, то пропусти эту итерацию
            if not results: continue
            
            # получаем расшифровку пароля и логин для определённого результата
            choose = int(input("Введите номер для получения пароля/логина/email: "))
            db_pass = check_master_pass()
            site_pass = crypto_worker(results[choose][4], 2, db_pass, results[choose][6])
            print("\nДанные УЗ:\nЛогин: " + results[choose][3] + "\nПароль: " + site_pass + "\nURL: " 
                  + results[choose][1] + "\nEmail: " + results[choose][2] + "\n")
        
        elif user_choose == 3 or user_choose == 5:
            
            print("\nВНИМАНИЕ: внесённые изменения нельзя отменить!\nБудьте внимательны при редактировании.\n")
 
            # спрашиваем у пользователя ключевые слова
            results = extract_db_entries()
            # если результаты пустые, то пропусти эту итерацию
            if not results: continue
            
            # спрашиваем какую запись будем редактировать
            try: entry_id = int(input("Введите номер записи для редактирования/удаления: "))
            except: print("Необходимо ввести число!")
            if user_choose == 3:
                # спрашиваем что именно будем редактировать в записи
                try: sub_entry_id = int(input("\nЧто именно требуется изменить? :\n"
                                "\n(1) - Описание\n"
                                "(2) - URL\n"
                                "(3) - Email\n"
                                "(4) - Логин\n"
                                "(5) - Пароль\n"
                                "\nВведите номер действия: "))
                except: print("Необходимо ввести число!")
            
                # эти варианты можно просто переписать в БД
                # здесь можно было бы записать проще и короче через новый оператор match с версии Python 3.10
                if sub_entry_id == 1 or sub_entry_id == 3 or sub_entry_id == 4:
                    new_sub = input("Введите новые данные: ")
                    if sub_entry_id == 1:
                        request_str = "UPDATE data SET Description = ? WHERE Id = {0}".format(results[entry_id][0])
                    if sub_entry_id == 3:
                        request_str = "UPDATE data SET Email = ? WHERE Id = {0}".format(results[entry_id][0])
                    if sub_entry_id == 4:
                        request_str = "UPDATE data SET Login = ? WHERE Id = {0}".format(results[entry_id][0])
                    db_worker(request_str,2,(new_sub,))
                    
                # URL требует проверки на соответствие шаблону
                elif sub_entry_id == 2:
                    site_url = check_url_input()
                    request_str = "UPDATE data SET URL = ? WHERE Id = {0}".format(results[entry_id][0])
                    db_worker(request_str,2,(site_url,))
                # пароль требуется предварительно зашифровать
                elif sub_entry_id == 5:
                    site_pass = input("Введите новый пароль для сайта: ")
          
                    # проверить пароль базы
                    db_pass = check_master_pass()
                
                    # шифрование fernet AES-128
                    crypto_result = crypto_worker(site_pass,1,db_pass)
                    request_str = "UPDATE data SET Pass = ?, MagicNumber = ? WHERE Id = {0}".format(results[entry_id][0])
                    db_worker(request_str,2,(crypto_result[0],crypto_result[1],))
                
                print("\nДанные успешно обновлены!\n")
            else:
                request_str = "DELETE FROM data WHERE Id={0}".format(results[entry_id][0])
                db_worker(request_str,1)
            
                print("\nИнформация о сайте удалена!\n")
            
        elif user_choose == 5:
             break