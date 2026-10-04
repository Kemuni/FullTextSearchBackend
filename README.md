# FullTextSearchBackend
#### Тестовое задание для "Аналитические программные решения"
<p align="left">
   <img src="https://img.shields.io/badge/Python_3.12+-14354C?style=for-the-badge&logo=python&logoColor=white"/>
   <img src="https://img.shields.io/badge/Uv-DE5FE9?style=for-the-badge&logo=uv&logoColor=white"/>
   <img src="https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white"/>
   <img src="https://img.shields.io/badge/Pytest-0A9EDC?style=for-the-badge&logo=pytest&logoColor=white"/>
   <img src="https://img.shields.io/badge/Swagger-0a82E20?style=for-the-badge&logo=swagger&logoColor=white"/>
   <img src="https://img.shields.io/badge/PostgreSQL-316192?style=for-the-badge&logo=postgresql&logoColor=white"/>
   <img src="https://img.shields.io/badge/ElasticSearch-005571?style=for-the-badge&logo=elasticsearch&logoColor=white"/>
   <img src="https://img.shields.io/badge/Github_Actions-2088FF?style=for-the-badge&logo=githubactions&logoColor=white"/>
   <img src="https://img.shields.io/badge/Docker-00B2FF?style=for-the-badge&logo=docker&logoColor=white"/>

[//]: # (   <img src="https://img.shields.io/badge/Redis-a32422?style=for-the-badge&logo=redis&logoColor=white"/>)
</p>

## Цель
Реализация API для сервиса поисковика по текстам документов при помощи ElasticSearch.


## Реализовано
- [x] Используется асинхронный python веб-фреймворк FastAPI.
- [x] Инструкции в README.md для поднятия сервиса
- [x] Наличие юнит и интеграционных тестов.
- [x] Автозаполнение init-данными с постами при первом запуске (*make up-dev-env*).
- [x] Запуск сервиса с помощью Docker.
- [x] Эндпоинт поиска постов при помощи ElasticSearch.
- [x] Эндпоинты для управления данными о постах (PostgreSQL)
- [x] Настроен pre-commit хук для проверки кода.
- [x] Настроен CI с запуском линтера, проверки типов и теста.
- [x] Подружить ElasticSearch с Unicode символами (плагин `analysis-icu`) для мультиязычности постов.
- [ ] Кэширование запросов к эндпоинту поиска.
- [ ] Синхронизация данных между PostgreSQL и ElasticSearch при помощи паттерна *Outbox*.
- [ ] `docs.json` с OpenAPI документацией эндпоинтов.


# Инструкции
## Как запустить проект для разработки
1. Запускаем **Docker**.
2. Включаем VPN, поскольку для установки плагина ES (`analysis-icu`) он необходим, иначе будет **403 Forbidden**.
3. Поднимаем окружение для разработки *(Postgres, ElasticSearch, Kibana, сервис для заполнения init-данными)*:
    ```shell
    make up-dev-env
    ```
4. Синхронизируем UV и скачиваем все необходимые библиотеки:
    ```shell
    make sync-all
    ```
5. Копируем `.env.example` и настраиваем `.env`:
   ```shell
   cp .env.example .env
   ```
6. Запускаем FastAPI в режиме разработки:
   ```shell
    make fastapi-dev
    ```
7. Заходим на `http://localhost:8000/docs` и пользуемся `Swagger`.

На данном проекте настроен **pre-commit**, чтобы его зарегистрировать напишите следующую
команду для автозапуска проверки перед коммитом:
```shell
  make install-precommit
```

## Как провести тесты и проверки перед пушем коммита
Следующая команда запускает тесты и создает `html` документ с информацией о покрытии кода:
```shell
make test
```
Следующая команда запускает линтер и проверку типов (как и перед коммитом):
```shell
make precommit-check
```
