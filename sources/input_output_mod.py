from os import name, system
from ctypes import CDLL
from re import search
from colorama import init, Fore, Style
from sources.localization_mod import select_language

"""
Этот модуль содержит вспомогательные методы для обработки ввода.
"""

# Colorama.Initialize() для цветного форматирования в консоли
init(autoreset=True)

_ = select_language("english-input_output_mod")


def check_url_input() -> str:
    """
    Функция проверки вводимого URL с помощью regex.
    """
    pattern = r"^(http|https)://([a-zа-яА-Я0-9]+(\.?\-?))+(\.[a-zа-яА-Я]{2,5})$"
    pattern2 = r"^(http|https)://\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}"

    while True:
        # colorama autoreset не работает для input
        site_url = str(input(Fore.CYAN + _("Введите URL адрес сайта, "
                                           "в формате http(s)://site.domain или http(s)://IP_адрес: ")
                             + Style.RESET_ALL)).lower()
        # если возвращаемое значение поиска совпадает с паттерном, то всё ОК
        if search(pattern, site_url) or search(pattern2, site_url):
            break
        else:
            print(Fore.RED + _("Неправильный формат URL!"))
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


def clear_console():
    if name == "nt":
        """
        Команда cls выполниться не в текущем shell, а в subshell.
        В текущем shell, где выполняется программа Python также произойдёт
        очистка консоли, т.к.: "If command generates any output,
        it will be sent to the interpreter standard output stream".
        """
        system("cls")
        # Загрузка библиотеки C++, которая отправит текущему окну
        # сочетание клавиш ALT F7 для очистки истории команд
        mylib = CDLL(".//data//cpp_dll//altF7.dll")
        # Вызов функции отправки сочетания клавиш
        mylib.sendKeyPress()
    else:
        system("clear")
