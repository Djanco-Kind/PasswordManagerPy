from sqlite3 import connect, PARSE_DECLTYPES
from colorama import init, Fore
from sources.input_output_mod import input_helper
from sources.localization_mod import select_language
from shutil import get_terminal_size
from textwrap import wrap

"""
Этот модуль содержит логику работы с базой данных.
"""

# Colorama.Initialize() для цветного форматирования в консоли
init(autoreset=True)

_ = select_language("english-db_mod")


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
            _("\nВведите ключевые слова, либо URL для поиска.\n"
              "Для разделения ключевых слов используйте запятые (логическое ИЛИ): "),
            _("Пустой ввод недопустим, укажите ключевые слова!"),
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


def print_db_entries(entries: list, offset=0):
    """
    Вспомогательный метод для печати результатов запроса из БД.
    """

    terminal_width = get_terminal_size()[0]
    column_max_width = int((terminal_width - 19) / 4)

    out_string = ("│ {:<3} │ {:<" f"{column_max_width}" "} │ {:<" f"{column_max_width}" "} │ " +
                  "{:<" + f"{column_max_width}" "} │ {:<" f"{column_max_width}" "} │")

    # выводим в таблице каждую колонку с данными, нарезая её под ширину терминала
    for index, result in enumerate(entries):

        out_string_len = len(out_string.format(index + 1, column_max_width, column_max_width,
                                               column_max_width, column_max_width))

        # перед печатью первой строки напечатать шапку таблицы
        if index == 0:
            print("+", "─" * (out_string_len - 4), "+")
            print(out_string.format("N", "Desc", "URL", "Login", "Email"))
            print("+", "─" * (out_string_len - 4), "+")

        # делаем wrap данных для колонок
        wrapped_data = []
        max_lines_number = 0
        for res_index in range(1, 5):
            # максимальная ширина данных в колонке column_max_width
            # нарезаем данные (делаем wrap) для каждой колонки
            wrapped_data.append(wrap(result[res_index], column_max_width))
            # находим макс число строк, которые займут данные в колонке после wrap
            if max_lines_number < len(wrapped_data[res_index - 1]):
                max_lines_number = len(wrapped_data[res_index - 1])
        # если в одних нарезанных данных число строк меньше, чем в других, то добавить пустые строки
        for wrapped_data_item in wrapped_data:
            if len(wrapped_data_item) < max_lines_number:
                for addition_line in range(0, max_lines_number - len(wrapped_data_item)):
                    wrapped_data_item.append("")

        for wrapped_res_line_indx in range(0, max_lines_number):
            # печатаем в формате: индекс описание URL Логин Email
            if offset == 0 and wrapped_res_line_indx == 0:
                print(out_string.format(index + 1, wrapped_data[0][wrapped_res_line_indx],
                                        wrapped_data[1][wrapped_res_line_indx],
                                        wrapped_data[3][wrapped_res_line_indx],
                                        wrapped_data[2][wrapped_res_line_indx]))
            elif offset > 0 and wrapped_res_line_indx == 0:
                print(out_string.format(index + 1 + offset, wrapped_data[0][wrapped_res_line_indx],
                                        wrapped_data[1][wrapped_res_line_indx],
                                        wrapped_data[3][wrapped_res_line_indx],
                                        wrapped_data[2][wrapped_res_line_indx]))
            elif wrapped_res_line_indx > 0:
                print(out_string.format("", wrapped_data[0][wrapped_res_line_indx],
                                        wrapped_data[1][wrapped_res_line_indx],
                                        wrapped_data[3][wrapped_res_line_indx],
                                        wrapped_data[2][wrapped_res_line_indx]))
        # для разделения выводимых записей вывести границу
        if index < len(entries):
            print("+", "─" * (out_string_len - 4), "+")
        # после печати последней найденной строки добавить пустую пробельную
        if index == len(entries) - 1:
            print()
