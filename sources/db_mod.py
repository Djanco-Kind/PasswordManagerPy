from sqlite3 import connect, PARSE_DECLTYPES
from colorama import init, Fore
from sources.input_mod import input_helper

"""
Этот модуль содержит логику работы с базой данных.
"""

# Colorama.Initialize() для цветного форматирования в консоли
init(autoreset=True)


def to_lower_sqlite(str_input: str) -> str:
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
    with connect(path, detect_types=PARSE_DECLTYPES) as connection:
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


def search_db_entries() -> list:
    """
    Простой поиск записей в базе SQLite.
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
    user_keywords = user_keywords.lower().replace(" ", "").split(",")

    # выполняем поиск, используя ключевые слова из списка
    # результаты поиска записываем в список results
    found_results = []
    for keyword in user_keywords:
        request_str = ("SELECT * FROM data "
                       "WHERE lower(Description) LIKE '%' || ? || '%' OR URL LIKE '%' || ? || '%'")
        for item in db_worker(".//data//pswdmn.db", request_str, 2, (keyword, keyword)):
            if item not in found_results:
                found_results.append(item)
    return found_results


def print_found_in_db(found_results: list) -> bool:
    """
    Вспомогательный метод для печати результатов поиска по БД.
    Если результаты поиска пустые, то вернёт True, иначе False.
    """
    # если результаты пустые
    if len(found_results) == 0:
        print(Fore.YELLOW + "\nРезультатов не найдено, "
                            "попробуйте поиск с другими ключевыми словами.\n")
        return True
    # если результаты не пустые
    else:
        # определяем самые длинные строки
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

        # шаблон строки для печати одного из найденных результатов
        out_string = ("{:<3} - {:<" f"{longest_description + 1}" "} {:<" f"{longest_url + 1}" "} "
                      "Логин: {:<" f"{longest_nickname + 1}" "}")

        print("\nНайдены следующие сайты:\n")
        for index, result in enumerate(found_results):
            # печатаем в формате: индекс описание URL Логин: ****** Пароль: ******
            print(out_string.format(index + 1, result[1], result[2], result[4]))
            # после печати последней найденной строки добавить пустую пробельную
            if index == len(found_results) - 1:
                print()
        return False
