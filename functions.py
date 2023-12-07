import datetime
import secrets as crypto_rnd
import re
import sqlite3
import crypta
from colorama import init, Fore, Style


# Colorama.Initialize() для цветного форматирования в консоли
init(autoreset=True)

def to_lower_sqlite(str):
    """
    Функция перевода в нижний регистр для sqlite
    """
    return str.lower()

def db_worker(request: str, func_type: int, request_data=()) -> list:
    """
    Запросы по типу SELECT/CREATE/DELETE = 1.
    Запросы по типу INSERT/UPDATE с данными = 2.
    Возвращает список кортежей.
    """
    # PARSE_DECLTYPES нужна для автоматического определения типов
    with sqlite3.connect("pswdmn.db",
                         detect_types=sqlite3.PARSE_DECLTYPES) as connection:
        connection.create_function("lower", 1, to_lower_sqlite)
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
        master_pass = input(Fore.CYAN + "Введите мастер пароль для базы: " + Style.RESET_ALL)
        request_str = "SELECT Value FROM secret"
        # если в БД нет хеша мастер пароля, то сохраняем его
        if len(db_worker(request_str, 1)) == 0:
            print(Fore.YELLOW + "\nВы задали мастер пароль в самый первый раз,"
                  "\nзапомните его, он нужен для последующего использования парольного менеджера.")
            request_str = "INSERT INTO secret (Value) VALUES(?)"
            db_worker(request_str, 2, (crypta.hash_sha256(master_pass.encode()),))
            break

        # иначе сравниваем, что пытаемся шифровать/дешифровать с тем же мастер паролем
        if db_worker(request_str, 1)[0][0] != crypta.hash_sha256(master_pass.encode()):
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
                       "WHERE lower(Description) LIKE '%{0}%' "
                       "OR URL LIKE '%{0}%'").format(keyword)
        for item in db_worker(request_str, 1):
            if item not in found_results:
                found_results.append(item)
    return found_results


def search_db_helper(found_results: list) -> bool:
    # если результаты пустые, то пропусти эту итерацию
    if len(found_results) == 0:
        print(Fore.YELLOW + "\nРезультатов не найдено, "
                            "попробуйте поиск с другими ключевыми словами.\n")
        return True
    # иначе выведи результаты на печать
    else:
        print("\nНайдены следующие сайты:\n")
        for index, result in enumerate(found_results):
            # в формате: индекс описание URL Логин: ****** Пароль: ******
            print(f"({index + 1}) - {result[1]} {result[2]} Логин: {result[4]} Пароль: ******")
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
        site_url = str(input(Fore.CYAN + "Введите URL адрес сайта, "
                             "в формате http(s)://site.ru или http(s)://IP_адрес: " + Style.RESET_ALL)).lower()
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
    if input_type == "string":
        while True:
            # запрашиваем пользовательский ввод
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
        result.append(crypto_rnd.choice(alph + alph.upper() + numbers + special))
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
