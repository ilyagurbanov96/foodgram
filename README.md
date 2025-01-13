Foodgram

![example workflow](https://github.com/ilyagurbanov96/foodgram/actions/workflows/main.yml/badge.svg)

Ссылка на Foodgram: https://foodgram09.sytes.net/

Описание
Foodgram - социальная сеть для любителей кулинарии, которые хотят делиться рецептами своих блюд. Кроме того, можно скачать список продуктов, необходимых для приготовления блюда, просмотреть рецепты друзей и добавить любимые рецепты в список избранных. Этот проект включает в себя полностью функциональное бэкэнд-приложение на Django и фронтэнд-приложение на React.

Является альтернативным варинатом Foodgram с использованием Docker контейнеров


Возможности проекта:
Регистрация и авторизация пользователей
Добавление и изменение рецептов
Скачивание ингредиентов рецепта
Подписка на пользователей
Добавление рецепта в избранное


Технологии и инструменты
Python (Бэкенд)
React (Фронтенд)
WSGI-сервер Gunicorn
WEB-сервер Nginix
Зарегистрированное доменное имя No-ip
Шифрование через HTTPS Let's Encrypt
Мониторинг доступности и сбор ошибок UptimeRobot
Для обеспечения безопасности, секреты подгружаются из файла .env. В файле .env содержатся важные константы, которые строго исключены из хранения в коде проекта. Настройка находится в блоке "Как запустить Foodgram".
Docker
Автоматизирровано тестирование и деплой проекта Foodgram с помощью GitHub Actions

Как запустить Foodgram на сервере:

Создать директорию Foodgram на сервере
cd
mkdir foodgram
cd foodgram

Установить Docker Compose на сервер
sudo apt update
sudo apt install curl
curl -fSL https://get.docker.com -o get-docker.sh
sudo sh ./get-docker.sh
sudo apt-get install docker-compose-plugin 
Перенести docker-compose.yml на сервер
scp -i path_to_SSH/SSH_name docker-compose.yml \
    username@server_ip:/home/username/foodgram/docker-compose.yml
Перенести .env на сервер, вставив туда значения из .env.template
scp -i path_to_SSH/SSH_name .env \
    username@server_ip:/home/username/foodgram/.env
path_to_SSH — путь к файлу с SSH-ключом;
SSH_name — имя файла с SSH-ключом (без расширения);
username — ваше имя пользователя на сервере;
server_ip — IP вашего сервера.
Запустить демона
sudo docker compose -f docker-compose.yml up -d

Выполнить миграции
sudo docker compose -f docker-compose.yml exec backend python manage.py migrate
sudo docker compose -f docker-compose.yml exec backend python manage.py collectstatic
sudo docker compose -f docker-compose.yml exec backend cp -r /app/collected_static/. /backend_static/static/
sudo docker compose -f docker-compose.yml exec backend python manage.py import_tags_csv_db
sudo docker compose -f docker-compose.yml exec backend python manage.py import_csv_db

Как запустить Foodgram локально:

Клонировать репозиторий
git@github.com:ilyagurbanov96/foodgram.git
Создать .env в корневой директории, вставив туда значения из .env.template

Запустить
sudo docker compose -f docker-compose.yml up

Собрать статику
docker compose -f docker-compose.yml exec backend python manage.py migrate
docker compose -f docker-compose.yml exec backend python manage.py collectstatic
docker compose -f docker-compose.yml exec backend cp -r /app/collected_static/. /backend_static/static/
docker compose -f docker-compose.yml exec backend python manage.py import_tags_csv_db
docker compose -f docker-compose.yml exec backend python manage.py import_csv_db

Автор: Эльяр Гурбанов

