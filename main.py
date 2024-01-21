import datetime
import os
import ctypes
import functions
import crypta
from colorama import init, Fore, Style

if __name__ == "__main__":

    # Colorama.Initialize() для цветного форматирования в консоли
    init(autoreset=True)

    while True:
        # ОСНОВНОЕ МЕНЮ для работы с парольным менеджером
        user_choose = functions.input_helper(
            ("(1) - Добавить логин/пароль для сайта\n"
             "(2) - Получить логин/пароль сайта\n"
             "(3) - Отредактировать информацию о сайте\n"
             "(4) - Удалить информацию о сайте\n"
             "(5) - Сгенерировать пароль\n"
             "(6) - Очистить вывод\n"
             "(7) - Синхронизация через Google Drive\n"
             "(8) - Выход\n"
             "Введите номер действия: "),
            "Действия с таким номером не существует!",
            "number",
            range(1, 9)
        )

        try:
            # если пользователь выбрал добавление сайта
            if user_choose == "1":
                # создать таблицу data для сохранения сайтов если ещё не создана
                request_str = ("CREATE TABLE IF NOT EXISTS data ("
                               "Id INTEGER PRIMARY KEY AUTOINCREMENT,"
                               "Description TEXT,"
                               "URL TEXT,"
                               "Email TEXT,"
                               "Login TEXT,"
                               "Pass BLOB,"
                               "Salt BLOB,"
                               "PasswordDate DATE,"
                               "ModificationTime INTEGER)")
                functions.db_worker("pswdmn.db", request_str, 1)

                # аналогично создать таблицу control для хеша мастер пароля и штампа времени синхронизации
                request_str = "CREATE TABLE IF NOT EXISTS control (Value TEXT, Value2 INTEGER)"
                functions.db_worker("pswdmn.db", request_str, 1)

                # получить от пользователя описание сохраняемого сайта
                site_description = functions.input_helper(
                    "\nВведите описание сайта: ",
                    "Описание сайта не может быть пустой строкой!",
                    "string"
                )

                # получить от пользователя URL сайта
                # в формате http(s)://бла-бла.домен или http(s)://ip_address
                site_url = functions.check_url_input()

                # получить от пользователя почту для сайта, но это может быть и не задано
                site_email = input(Fore.CYAN + "Введите email если используется: " + Style.RESET_ALL)
                # если почта не используется, то сохранить это явно
                if len(site_email) == 0:
                    site_email = "На этом сайте адрес почты не используется"

                # получить от пользователя ввод логина для сайта
                site_login = functions.input_helper(
                    "Введите логин для сайта: ",
                    "Логин не может быть пустой строкой!",
                    "string"
                )

                # получить от пользователя ввод пароля сайта
                site_pass = functions.input_helper(
                    "Введите пароль для сайта: ",
                    "Пароль не может быть пустой строкой!",
                    "string"
                )

                # проверить мастер пароль, есть ли его хеш или сохранить его
                master_pass = functions.check_master_pass()

                # шифрование пользовательского пароля сайта с мастер паролем AES-128
                crypto_result = crypta.aes_encryption(site_pass.encode(), master_pass)

                # Epoch штамп времени, когда модифицировалась эта запись
                mod_epoch = int(datetime.datetime.now().timestamp())

                # занесение информации о сайте в БД
                request_str = ("INSERT INTO data ("
                               "Description,"
                               "URL,"
                               "Email,"
                               "Login,"
                               "Pass,"
                               "Salt,"
                               "PasswordDate,"
                               "ModificationTime) VALUES(?, ?, ?, ?, ?, ?, ?, ?)")

                functions.db_worker("pswdmn.db", request_str, 2,
                                    (site_description, site_url,
                                     site_email, site_login, crypto_result[0], crypto_result[1],
                                     datetime.date.today(), mod_epoch))

                print(Fore.GREEN + "\nИнформация о сайте успешно добавлена!\n")

            # если пользователь выбрал получение сайта
            elif user_choose == "2":
                # проверяем, что база с паролями вообще есть,
                # т.е. до этого был сохранён хотя бы один сайт
                if functions.db_not_exists():
                    continue

                # спрашиваем у пользователя ключевые слова и ищем по ним
                found_results = functions.search_db_entries()

                # если результаты пустые print_found_in_db вернёт True
                # если результаты не пустые, то он напечатает их
                if functions.print_found_in_db(found_results):
                    continue

                # получаем расшифровку пароля и логин для определённого результата
                user_choose = int(functions.input_helper(
                    "Введите номер для получения пароля/логина/email: ",
                    "Сайта с таким номером нет в результатах поиска!",
                    "number",
                    range(1, len(found_results) + 1)
                ))

                # запрашиваем мастер пароль у пользователя
                master_pass = functions.check_master_pass()
                # дешифруем с этим мастер паролем пароль сайта
                site_pass = crypta.aes_decryption(found_results[user_choose - 1][5],
                                                  master_pass,
                                                  found_results[user_choose - 1][6])
                site_pass = site_pass.decode()

                print(f"\nДанные сайта:\nЛогин: {found_results[user_choose - 1][4]} "
                      f"\nПароль: {site_pass} "
                      f"\nURL сайта: {found_results[user_choose - 1][2]} "
                      f"\nEmail: {found_results[user_choose - 1][3]} \n")

                # определяем как давно пользователь обновлял пароль
                passMonths = functions.timedelta_month(
                    found_results[user_choose - 1][7],
                    datetime.date.today())
                # если прошло больше 3 месяцев выводим предупреждение
                if passMonths > 3:
                    print(Fore.YELLOW + f"Вы обновляли пароль для этого сайта {passMonths} месяцев назад.\n"
                                        "Для безопасности рекомендуется обновить Ваш пароль.\n")
                    user_choose = functions.input_helper(
                        "Хотите сгенерировать новый пароль? Да - 1/Нет - 0 : ",
                        "Выберите Да = 1 или Нет = 0",
                        "number",
                        range(0, 2))
                    if user_choose == "1":
                        new_pass = functions.pswrd_generator()
                        print(f"\nСгенерированный пароль: {new_pass}\n")
                        print(Fore.YELLOW + f"После смены пароля на сайте "
                                            f"не забудьте обновить его здесь, через опцию (3).\n")
                    else:
                        print("\n")

            # если пользователь выбрал редактирование сайта
            elif user_choose == "3":
                # проверяем, что база с паролями вообще есть,
                # т.е. до этого был сохранён хотя бы один сайт
                if functions.db_not_exists():
                    continue

                print(Fore.YELLOW + "\nБудьте внимательны при внесении изменений!")
                print("Выполните поиск сайта, который требуется отредактировать.")

                # спрашиваем у пользователя какой сайт будем редактировать
                found_results = functions.search_db_entries()

                # если результаты пустые print_found_in_db вернёт True
                # если результаты не пустые, то он напечатает их
                if functions.print_found_in_db(found_results):
                    continue

                # спрашиваем какую запись будем редактировать
                site_id = int(functions.input_helper(
                    "Введите номер сайта для редактирования: ",
                    "Сайта с таким номером нет в результатах поиска!",
                    "number",
                    range(1, len(found_results) + 1)
                ))

                # спрашиваем что именно будем редактировать в записи сайта
                edit_site_value = int(functions.input_helper(
                    ("\nЧто именно требуется изменить для этого сайта?:\n"
                     "(1) - Email\n"
                     "(2) - Логин\n"
                     "(3) - Пароль\n"
                     "\nВведите номер действия: "),
                    "Действия с таким номером нет!",
                    "number",
                    range(1, 4)
                ))

                # эти варианты можно просто переписать в БД никак не обрабатывая предварительно
                request_str = ""
                if edit_site_value == 1 or edit_site_value == 2:
                    new_site_data = input(Fore.CYAN + "Введите новые данные: " + Style.RESET_ALL)
                    if edit_site_value == 1:
                        request_str = (f"UPDATE data SET Email = ? "
                                       f"WHERE Id = {found_results[site_id - 1][0]}")
                    if edit_site_value == 2:
                        request_str = (f"UPDATE data SET Login = ? "
                                       f"WHERE Id = {found_results[site_id - 1][0]}")
                    functions.db_worker("pswdmn.db", request_str, 2, (new_site_data,))

                # новый пароль требуется предварительно зашифровать
                elif edit_site_value == 3:
                    site_pass = functions.input_helper(
                        "Введите новый пароль для сайта: ",
                        "Пароль не может быть пустой строкой!",
                        "string"
                    )

                    # проверить мастер пароль базы
                    master_pass = functions.check_master_pass()

                    # шифруем новый пароль сайта с мастер паролем AES-128
                    crypto_result = crypta.aes_encryption(site_pass.encode(), master_pass)
                    request_str = (f"UPDATE data SET Pass = ?, Salt = ?, PasswordDate = ? "
                                   f"WHERE Id = {found_results[site_id - 1][0]}")

                    functions.db_worker("pswdmn.db", request_str, 2,
                                        (crypto_result[0], crypto_result[1], datetime.date.today()))
                # после внесения изменений переопределяем значение ModificationTime
                mod_epoch = int(datetime.datetime.now().timestamp())
                request_str = f"UPDATE data SET ModificationTime = ? WHERE Id = {found_results[site_id - 1][0]}"
                functions.db_worker("pswdmn.db", request_str, 2,(mod_epoch,))

                print(Fore.GREEN + "\nДанные сайта успешно обновлены!\n")

            # если пользователь выбрал удаление сайта
            elif user_choose == "4":
                # проверяем, что база с паролями вообще есть,
                # т.е. до этого был сохранён хотя бы один сайт
                if functions.db_not_exists():
                    continue

                print(Fore.YELLOW + "\nУдаление необратимая операция, будьте внимательны!")
                print("Выполните поиск сайта, который требуется удалить.")

                # спрашиваем у пользователя какой сайт будем редактировать
                found_results = functions.search_db_entries()

                # если результаты пустые search_db_helper вернёт True
                # если результаты не пустые, то он напечатает их
                if functions.print_found_in_db(found_results):
                    continue

                # спрашиваем какой сайт будем удалять
                site_id = int(functions.input_helper(
                    "Введите номер сайта для удаления: ",
                    "Сайта с таким номером нет в результатах поиска!",
                    "number",
                    range(1, len(found_results) + 1)
                ))

                request_str = f"DELETE FROM data WHERE Id = {site_id - 1}"

                print(Fore.GREEN + "Сайт успешно удалён.\n")

            # если пользователь выбрал создать пароль
            elif user_choose == "5":
                print(f"\nСгенерированный пароль: "
                      f"{functions.pswrd_generator()}\n")

            # если выбрали очистку экрана
            elif user_choose == "6":
                if os.name == "nt":
                    """
                    Команда cls выполниться не в текущем shell, а в subshell.
                    В текущем shell, где выполняется программа Python также произойдёт
                    очистка консоли, т.к.: "If command generates any output,
                    it will be sent to the interpreter standard output stream".
                    """
                    os.system("cls")
                    # Загрузка библиотеки C++, которая отправит текущему окну
                    # сочетание клавиш ALT F7 для очистки истории команд
                    mylib = ctypes.CDLL("altF7.dll")
                    # Вызов функции отправки сочетания клавиш
                    mylib.sendKeyPress()

            # если пользователь выбрал синхронизацию
            elif user_choose == "7":
                # вызываем синхронизацию
                functions.sync_db()

            # если пользователь выбрал выход
            elif user_choose == "8":
                break

        except KeyboardInterrupt:
            # если пользователь отменяет своё действие
            # напечатать строку для удобства и пропустить итерацию
            print(Fore.YELLOW + "\nВы прервали операцию нажав Ctrl+C...\n")
            continue
        except Exception as e:
            print(Fore.RED + f"\nВозникла непредвиденная ошибка: {str(e)}\n")
            continue
