# Консольный менеджер паролей :lock_with_ink_pen:
Это реализация простого консольного менеджера паролей на языке Python3.<br>

Все пароли сайтов сохраняются в базе данных Sqlite в зашифрованном и засоленном виде.<br>
Шифрование выполняется с помощью симметричного алгоритма AES-128 c мастер паролем, т.е. для добавления или получении любого пароля сайта используется один пароль (мастер пароль).
Он задаётся при добавлении самого первого сайта, в дальнейшем для добавления новых сайтов можно использовать только его.
 
**:gear: Сейчас менеджер имеет следующий функционал :gear:**:
* Добавить информацию для нового сайта и его пароля.
* Удалить сайт и его информацию о пароле.
* Отредактировать информацию о сайте.
* Получить информацио о пароле сайта.

