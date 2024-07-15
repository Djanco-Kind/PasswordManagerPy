from datetime import datetime, date
import sources.sync_mod as sync_logic
import sources.db_mod as db_logic
import sources.input_output_mod as io_logic
import sources.security_mod as security
from colorama import init, Fore, Style
from sources.localization_mod import select_language

if __name__ == "__main__":

    # Colorama.Initialize() для цветного форматирования в консоли
    init(autoreset=True)

    while True:

        _ = select_language("english-main")

        # ОСНОВНОЕ МЕНЮ для работы с парольным менеджером
        user_choose = io_logic.input_helper(
            _("(1)  - Добавить логин/пароль для сайта\n"
              "(2)  - Получить логин/пароль сайта\n"
              "(3)  - Отредактировать информацию о сайте\n"
              "(4)  - Удалить информацию о сайте\n"
              "(5)  - Сгенерировать пароль\n"
              "(6)  - Очистить вывод\n"
              "(7)  - Синхронизация через Google Drive\n"
              "(8)  - Изменить мастер пароль\n"
              "(9)  - Посмотреть добавленные сайты\n"
              "(10) - Выход\n"
              "Введите номер действия: "),
            _("Действия с таким номером не существует!"),
            "number",
            range(1, 11)
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
                db_logic.db_worker(".//data//pswdmn.db", request_str, 1)

                # аналогично создать таблицу control для хеша мастер пароля и штампа времени синхронизации
                request_str = "CREATE TABLE IF NOT EXISTS control (Value TEXT)"
                db_logic.db_worker(".//data//pswdmn.db", request_str, 1)

                # получить от пользователя описание сохраняемого сайта
                site_description = io_logic.input_helper(
                    _("\nВведите описание сайта: "),
                    _("Описание сайта не может быть пустой строкой!"),
                    "string"
                )

                # получить от пользователя URL сайта
                # в формате http(s)://бла-бла.домен или http(s)://ip_address
                site_url = io_logic.check_url_input()

                # получить от пользователя почту для сайта, но это может быть и не задано
                site_email = input(Fore.CYAN + _("Введите email если используется: ") + Style.RESET_ALL)
                # если почта не используется, то сохранить это явно
                if len(site_email) == 0:
                    site_email = "Не указано"

                # получить от пользователя ввод логина для сайта
                site_login = io_logic.input_helper(
                    _("Введите логин для сайта: "),
                    _("Логин не может быть пустой строкой!"),
                    "string"
                )

                # получить от пользователя ввод пароля сайта
                site_pass = io_logic.input_helper(
                    _("Введите пароль для сайта: "),
                    _("Пароль не может быть пустой строкой!"),
                    "string"
                )

                # проверить мастер пароль, есть ли его хеш или сохранить его
                master_pass = security.check_master_pass()

                # шифрование пользовательского пароля сайта с мастер паролем AES-128
                crypto_result = security.aes_encryption(site_pass.encode(), master_pass)

                # Epoch штамп времени, когда модифицировалась эта запись
                mod_epoch = int(datetime.now().timestamp())

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

                db_logic.db_worker(".//data//pswdmn.db", request_str, 2,
                                   (site_description, site_url,
                                    site_email, site_login, crypto_result[0], crypto_result[1],
                                    date.today(), mod_epoch))

                print(Fore.GREEN + _("\nИнформация о сайте успешно добавлена!\n"))

            # если пользователь выбрал получение сайта
            elif user_choose == "2":
                # проверяем, что база с паролями вообще есть,
                # т.е. до этого был сохранён хотя бы один сайт
                if not security.check_db_existence():
                    continue

                # спрашиваем у пользователя ключевые слова и ищем по ним
                found_results = db_logic.search_db_entries()

                if len(found_results) == 0:
                    print(Fore.YELLOW + _("\nРезультатов не найдено, "
                                          "попробуйте поиск с другими ключевыми словами.\n"))
                    continue
                else:
                    print(_("\nНайдены следующие сайты:\n"))
                    db_logic.print_db_entries(found_results)

                # получаем расшифровку пароля и логин для определённого результата
                user_choose = int(io_logic.input_helper(
                    _("Введите номер для получения пароля/логина/email: "),
                    _("Сайта с таким номером нет в результатах поиска!"),
                    "number",
                    range(1, len(found_results) + 1)
                ))

                # запрашиваем мастер пароль у пользователя
                master_pass = security.check_master_pass()
                # дешифруем с этим мастер паролем пароль сайта
                site_pass = security.aes_decryption(found_results[user_choose - 1][5],
                                                    master_pass,
                                                    found_results[user_choose - 1][6])
                site_pass = site_pass.decode()

                print(_("\nДанные сайта:\nЛогин: "), f"{found_results[user_choose - 1][4]} ",
                      _("\nПароль: "), f"{site_pass} ",
                      _("\nURL сайта: "), f"{found_results[user_choose - 1][2]} "
                                          f"\nEmail: {found_results[user_choose - 1][3]} \n")

                # определяем как давно пользователь обновлял пароль
                passMonths = security.calc_timedelta_month(
                    found_results[user_choose - 1][7],
                    date.today())
                # если прошло больше 3 месяцев выводим предупреждение
                if passMonths > 3:
                    print(Fore.YELLOW + _("Вы обновляли пароль для этого сайта"), f"{passMonths}",
                          _("месяцев назад.\n"),
                          _("Для безопасности рекомендуется обновить Ваш пароль.\n"))
                    user_choose = io_logic.input_helper(
                        _("Хотите сгенерировать новый пароль? Да - 1/Нет - 0 : "),
                        _("Выберите Да = 1 или Нет = 0"),
                        "number",
                        range(0, 2))
                    if user_choose == "1":
                        new_pass = security.pswrd_generator()
                        print(_("\nСгенерированный пароль: "), f"{new_pass}\n")
                        print(Fore.YELLOW + _("После смены пароля на сайте "),
                              _("не забудьте обновить его здесь, через опцию (3).\n"))
                    else:
                        print("\n")

            # если пользователь выбрал редактирование сайта
            elif user_choose == "3":
                # проверяем, что база с паролями вообще есть,
                # т.е. до этого был сохранён хотя бы один сайт
                if not security.check_db_existence():
                    continue

                print(Fore.YELLOW + _("\nБудьте внимательны при внесении изменений!"))
                print(_("Выполните поиск сайта, который требуется отредактировать."))

                # спрашиваем у пользователя какой сайт будем редактировать
                found_results = db_logic.search_db_entries()

                if len(found_results) == 0:
                    print(Fore.YELLOW + _("\nРезультатов не найдено, "
                                          "попробуйте поиск с другими ключевыми словами.\n"))
                    continue
                else:
                    print(_("\nНайдены следующие сайты:\n"))
                    db_logic.print_db_entries(found_results)

                # спрашиваем какую запись будем редактировать
                site_id = int(io_logic.input_helper(
                    _("Введите номер сайта для редактирования: "),
                    _("Сайта с таким номером нет в результатах поиска!"),
                    "number",
                    range(1, len(found_results) + 1)
                ))

                # спрашиваем что именно будем редактировать в записи сайта
                edit_site_value = int(io_logic.input_helper(
                    "".join((_("\nЧто именно требуется изменить для этого сайта?:\n"),
                             "(1) - Email\n",
                             _("(2) - Логин\n"),
                             _("(3) - Пароль\n"),
                             _("\nВведите номер действия: "))),
                    _("Действия с таким номером нет!"),
                    "number",
                    range(1, 4)
                ))

                # эти варианты можно просто переписать в БД никак не обрабатывая предварительно
                request_str = ""
                if edit_site_value == 1 or edit_site_value == 2:
                    new_site_data = input(Fore.CYAN + _("Введите новые данные: ") + Style.RESET_ALL)
                    if edit_site_value == 1:
                        request_str = "UPDATE data SET Email = ? WHERE Id = ?"
                    if edit_site_value == 2:
                        request_str = "UPDATE data SET Login = ? WHERE Id = ?"
                    db_logic.db_worker(".//data//pswdmn.db", request_str, 2, (new_site_data,
                                                                              found_results[site_id - 1][0]))

                # новый пароль требуется предварительно зашифровать
                elif edit_site_value == 3:
                    site_pass = io_logic.input_helper(
                        _("Введите новый пароль для сайта: "),
                        _("Пароль не может быть пустой строкой!"),
                        "string"
                    )

                    # проверить мастер пароль базы
                    master_pass = security.check_master_pass()

                    # шифруем новый пароль сайта с мастер паролем AES-128
                    crypto_result = security.aes_encryption(site_pass.encode(), master_pass)
                    request_str = "UPDATE data SET Pass = ?, Salt = ?, PasswordDate = ? WHERE Id = ?"

                    db_logic.db_worker(".//data//pswdmn.db", request_str, 2,
                                       (crypto_result[0], crypto_result[1],
                                        date.today(), found_results[site_id - 1][0]))
                # после внесения изменений переопределяем значение ModificationTime
                mod_epoch = int(datetime.now().timestamp())
                request_str = "UPDATE data SET ModificationTime = ? WHERE Id = ?"
                db_logic.db_worker(".//data//pswdmn.db", request_str, 2, (mod_epoch, found_results[site_id - 1][0]))

                print(Fore.GREEN + _("\nДанные сайта успешно обновлены!\n"))

            # если пользователь выбрал удаление сайта
            elif user_choose == "4":
                # проверяем, что база с паролями вообще есть,
                # т.е. до этого был сохранён хотя бы один сайт
                if not security.check_db_existence():
                    continue

                print(Fore.YELLOW + _("\nУдаление необратимая операция, будьте внимательны!"))
                print(_("Выполните поиск сайта, который требуется удалить."))

                # спрашиваем у пользователя какой сайт будем редактировать
                found_results = db_logic.search_db_entries()

                if len(found_results) == 0:
                    print(Fore.YELLOW + _("\nРезультатов не найдено, "
                                          "попробуйте поиск с другими ключевыми словами.\n"))
                    continue
                else:
                    print(_("\nНайдены следующие сайты:\n"))
                    db_logic.print_db_entries(found_results)

                # спрашиваем какой сайт будем удалять
                site_id = int(io_logic.input_helper(
                    _("Введите номер сайта для удаления: "),
                    _("Сайта с таким номером нет в результатах поиска!"),
                    "number",
                    range(1, len(found_results) + 1)
                ))

                request_str = "DELETE FROM data WHERE Id = ?"

                db_logic.db_worker(".//data//pswdmn.db", request_str, 2, (found_results[site_id - 1][0],))

                print(Fore.GREEN + _("Сайт успешно удалён.\n"))

            # если пользователь выбрал создать пароль
            elif user_choose == "5":
                print(_("\nСгенерированный пароль: "),
                      f"{security.pswrd_generator()}\n")

            # если выбрали очистку экрана
            elif user_choose == "6":
                io_logic.clear_console()

            # если пользователь выбрал синхронизацию
            elif user_choose == "7":
                # пытаемся найти путь до клиента Gdrive
                sync_logic.find_gdrive_path()
                # вызываем синхронизацию
                sync_logic.sync_db_main()

            # если пользователь выбрал смену мастер пароля
            elif user_choose == "8":
                security.change_master_pass()

            # если пользователь выбрал обзор сайтов
            elif user_choose == "9":
                io_logic.clear_console()
                request_str = "SELECT COUNT(*) FROM data"
                current_offset = 0
                is_continued = True
                num_of_entries = db_logic.db_worker(".//data//pswdmn.db", request_str, 1)[0][0]
                request_str = "SELECT * FROM data LIMIT 10 OFFSET ?"
                while (True):
                    data = db_logic.db_worker(".//data//pswdmn.db", request_str, 2,
                                              (current_offset,))
                    db_logic.print_db_entries(data, current_offset)

                    if current_offset + 10 < num_of_entries and current_offset == 0:
                        print("Навигация: 'D' + enter Вперёд ->, Выход 'Q' + Enter")
                        is_continued = True
                    elif current_offset + 10 >= num_of_entries:
                        print("Навигация: <- Назад 'A' + enter, Выход 'Q' + Enter")
                        is_continued = False
                    else:
                        print("Навигация: <- Назад 'A' + enter, 'D' + enter Вперёд ->, Выход 'Q' + Enter")

                    user_nav = input()
                    if user_nav == "q" or user_nav == "Q":
                        break
                    elif (user_nav == "a" or user_nav == "A") and current_offset > 0:
                        current_offset -= 10
                    elif (user_nav == "d" or user_nav == "D") and is_continued:
                        current_offset += 10
                    io_logic.clear_console()
                io_logic.clear_console()

            # если пользователь выбрал выход
            elif user_choose == "10":
                break

        except KeyboardInterrupt:
            # если пользователь отменяет своё действие
            # напечатать строку для удобства и пропустить итерацию
            print(Fore.YELLOW + _("\nВы прервали операцию нажав Ctrl+C...\n"))
            continue
        except Exception as e:
            print(Fore.RED + _("\nВозникла непредвиденная ошибка: "), f"{str(e)}\n")
            continue
