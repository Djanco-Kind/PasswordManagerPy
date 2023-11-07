import datetime
import os
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
             "(6) - Выход\n"
             "Введите номер действия: "),
            "Действия с таким номером не существует!",
            "number",
            range(1, 7)
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
                               "PasswordDate DATE)")
                functions.db_worker(request_str, 1)

                # аналогично создать таблицу secret для хеша мастер пароля
                request_str = "CREATE TABLE IF NOT EXISTS secret (Value TEXT)"
                functions.db_worker(request_str, 1)

                # получить от пользователя описание сохраняемого сайта
                site_description = functions.input_helper(
                    "\nВведите описание сайта: ",
                    "Описание сайта не может быть пустой строкой!",
                    "string"
                )

                # получить от пользователя URL сайта в формате http(s)://бла-бла.домен
                site_url = functions.check_url_input()

                # проверять, что пользователь не пытается добавить сайт повторно
                # один сайт = один аккаунт
                request_str = f"SELECT URL FROM data WHERE URL = '{site_url}'"
                # если fetchall() в db_worker возвращает не пустой список, то это повтор
                if len(functions.db_worker(request_str, 1)) != 0:
                    print(Fore.RED + "\nНельзя повторно добавить сайт, данные которого уже есть!\n")
                    continue

                # получить от пользователя почту сайта, но это может быть и не задано
                site_email = input(Fore.CYAN+ "Введите email если используется: " + Style.RESET_ALL)
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

                # занесение информации о сайте в БД
                request_str = ("INSERT INTO data ("
                               "Description,"
                               "URL,"
                               "Email,"
                               "Login,"
                               "Pass,"
                               "Salt,"
                               "PasswordDate) VALUES(?, ?, ?, ?, ?, ?, ?)")

                functions.db_worker(request_str, 2,
                                    (site_description, site_url,
                                     site_email, site_login, crypto_result[0], crypto_result[1],
                                     datetime.date.today()))

                print(Fore.GREEN + "\nИнформация о сайте успешно добавлена!\n")

                del site_email
                del site_login
                del site_pass
                del master_pass

            # если пользователь выбрал получение сайта
            elif user_choose == "2":
                # проверяем, что база с паролями вообще есть,
                # т.е. до этого был сохранён хотя бы один сайт
                if not os.path.exists(os.getcwd() + "//pswdmn.db"):
                    print(Fore.RED + "\nНеобходимо добавить хотя бы один сайт!\n")
                    continue
                # спрашиваем у пользователя ключевые слова и ищем по ним
                found_results = functions.search_db_entries()

                # если результаты пустые search_db_helper вернёт True
                # если результаты не пустые, то он напечатает их
                if functions.search_db_helper(found_results):
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
                    print(Fore.YELLOW + f"Вы обновляли пароль для этого сайта {passMonths} месяцев назад\n"
                                        "Для безопасности рекомендуется обновить Ваш пароль.\n")

            # если пользователь выбрал редактирование сайта
            elif user_choose == "3":
                print(Fore.YELLOW + "\nБудьте внимательны при внесении изменений!")
                print("Выполните поиск сайта, который требуется отредактировать.")

                # спрашиваем у пользователя какой сайт будем редактировать
                found_results = functions.search_db_entries()

                # если результаты пустые search_db_helper вернёт True
                # если результаты не пустые, то он напечатает их
                if functions.search_db_helper(found_results):
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
                     "\n(1) - Описание\n"
                     "(2) - URL\n"
                     "(3) - Email\n"
                     "(4) - Логин\n"
                     "(5) - Пароль\n"
                     "\nВведите номер действия: "),
                    "Действия с таким номером нет!",
                    "number",
                    range(1, 6)
                ))

                # эти варианты можно просто переписать в БД никак не обрабатывая предварительно
                if edit_site_value == 1 or edit_site_value == 3 or edit_site_value == 4:
                    new_site_data = input(Fore.CYAN + "Введите новые данные: " + Style.RESET_ALL)
                    if edit_site_value == 1:
                        request_str = (f"UPDATE data SET Description = ? "
                                       f"WHERE Id = {found_results[site_id - 1][0]}")
                    if edit_site_value == 3:
                        request_str = (f"UPDATE data SET Email = ? "
                                       f"WHERE Id = {found_results[site_id - 1][0]}")
                    if edit_site_value == 4:
                        request_str = (f"UPDATE data SET Login = ? "
                                       f"WHERE Id = {found_results[site_id - 1][0]}")
                    functions.db_worker(request_str, 2, (new_site_data,))

                # URL требует проверки на соответствие формату http(s)://бла-бла.домен
                elif edit_site_value == 2:
                    site_url = functions.check_url_input()
                    request_str = ("UPDATE data SET URL = ? "
                                   "WHERE Id = {0}").format(found_results[site_id - 1][0])
                    functions.db_worker(request_str, 2, (site_url,))

                # новый пароль требуется предварительно зашифровать
                elif edit_site_value == 5:
                    site_pass = functions.input_helper(
                        "Введите пароль для сайта: ",
                        "Пароль не может быть пустой строкой!",
                        "string"
                    )

                    # проверить мастер пароль базы
                    master_pass = functions.check_master_pass()

                    # шифруем новый пароль сайта с мастер паролем AES-128
                    crypto_result = crypta.aes_encryption(site_pass.encode(), master_pass)
                    request_str = (f"UPDATE data SET Pass = ?, Salt = ?, PasswordDate = ? "
                                   f"WHERE Id = {found_results[site_id - 1][0]}")

                    functions.db_worker(request_str, 2,
                                        (crypto_result[0], crypto_result[1], datetime.date.today()))

                print(Fore.GREEN + "\nДанные сайта успешно обновлены!\n")

            # если пользователь выбрал удаление сайта
            elif user_choose == "4":
                print(Fore.YELLOW + "\nУдаление необратимая операция, будьте внимательны!")
                print("Выполните поиск сайта, который требуется удалить.")

                # спрашиваем у пользователя какой сайт будем редактировать
                found_results = functions.search_db_entries()

                # если результаты пустые search_db_helper вернёт True
                # если результаты не пустые, то он напечатает их
                if functions.search_db_helper(found_results):
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
                pass_length = functions.input_helper(
                    "Введите длину пароля: ",
                    "Недопустимая длина."
                    "\nДлина должна быть в диапазоне 8 - 128 символов",
                    "number",
                    range(8, 129)
                )
                print(f"\nСгенерированный пароль: "
                      f"{functions.pswrd_generator(int(pass_length))}\n")

            # если пользователь выбрал выход
            elif user_choose == "6":
                break
        except KeyboardInterrupt:
            # если пользователь отменяет своё действие
            # напечатать строку для удобства и пропустить итерацию
            print(Fore.YELLOW + "\nВы прервали операцию нажав Ctrl+C...\n")
            continue
