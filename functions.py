import re
import sqlite3
import crypta


def db_worker(request: str, func_type: int, request_data=()) -> list:
    """
    Запросы по типу SELECT/CREATE/DELETE = 1.
    Запросы по типу INSERT/UPDATE с данными = 2.
    Возвращает список кортежей.
    """
    with sqlite3.connect("pswdmn.db") as connection:
        sql_exec = connection.cursor()
        # для SELECT/CREATE/DELETE
        if func_type == 1:
            sql_exec.execute(request)
        # для INSERT/UPDATE с данными
        elif func_type == 2:
            sql_exec.execute(request, request_data)
        return sql_exec.fetchall()


def check_master_pass() -> str:
    """
    Ввод и проверка мастер пароля.
    Возвращает введённый мастер пароль.
    """
    while True:
        master_pass = input("Введите пароль для базы: ")
        request_str = "SELECT Value FROM secret"
        # если в БД нет хеша мастер пароля, то сохраняем его
        if len(db_worker(request_str, 1)) == 0:
            request_str = "INSERT INTO secret (Value) VALUES(?)"
            db_worker(request_str, 2, (crypta.hash_sha256(master_pass.encode()),))
            break

        # иначе сравниваем, что пытаемся шифровать/дешифровать с тем же мастер паролем
        if db_worker(request_str, 1)[0][0] != crypta.hash_sha256(master_pass.encode()):
            print("\nНеправильный мастер пароль!\n")
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
             "Для разделения ключевых слов используйте запятые: "),
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
                       "WHERE Description LIKE '%{0}%' "
                       "OR URL LIKE '%{0}%'").format(keyword)
        for item in db_worker(request_str, 1):
            if item not in found_results:
                found_results.append(item)
    return found_results


def search_db_helper(found_results: list) -> bool:
    # если результаты пустые, то пропусти эту итерацию
    if len(found_results) == 0:
        print("\nРезультатов не найдено, попробуйте поиск с другими ключевыми словами.\n")
        return True
    # иначе выведи результаты на печать
    else:
        print("\nНайдены следующие сайты:\n")
        for index, result in enumerate(found_results):
            # в формате: индекс описание URL Логин: ****** Пароль: ******
            print(f"({index + 1}) - {result[1]} {result[2]} Логин: ****** Пароль: ******")
            if index == len(found_results) - 1:
                print()
        return False


def check_url_input() -> str:
    """
    Функция проверки вводимого URL с помощью regex.
    """
    pattern = r"^(http|https)://([a-z0-9]+(\.?\-?))+(\.[a-z]{2,5})$"

    while True:
        site_url = str(input("Введите URL адрес сайта, "
                             "в формате http(s)://site.ru : ")).lower()
        if re.search(pattern, site_url):
            break
        else:
            print("Неправильный формат URL!")
            continue

    return site_url


def input_helper(hint_for_user: str, hint_invalid_inp: str,
                 input_type: str, input_range=range(1)) -> str:
    """
    Вспомогательная функция для работы с пользовательским вводом.
    """
    if input_type == "string":
        while True:
            # запрашиваем пользовательский ввод
            user_input = input(hint_for_user)
            # вводимая строка не должна быть пустой
            if len(user_input) == 0:
                print("\n" + hint_invalid_inp + "\n")
                continue
            else:
                break
        return user_input
    elif input_type == "number":
        while True:
            try:
                # запрашиваем пользовательский ввод
                user_input = int(input(hint_for_user))
            # если возникает ошибка преобразования в целое число
            except ValueError:
                print("\n" + hint_invalid_inp + "\n")
                continue
            # вводимое число должно быть в диапазоне
            if user_input not in input_range:
                print("\n" + hint_invalid_inp + "\n")
                continue
            else:
                user_input = str(user_input)
                break
        return user_input
