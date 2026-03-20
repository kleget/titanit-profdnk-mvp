# ПрофДНК MVP (ТИТАНИТ 2026)

Рабочий MVP-проект под кейс хакатона: онлайн-конструктор диагностических методик с прохождением по уникальной ссылке, сохранением результатов и генерацией двух типов отчётов (HTML + DOCX) в реальном времени.

## Что уже реализовано (MVP)

### Роли
- `admin`: создаёт психологов, выставляет срок доступа, блокирует/разблокирует.
- `psychologist`: логинится, редактирует профиль, создаёт тесты, получает ссылки, смотрит результаты, генерирует отчёты.
- `client`: проходит тест без регистрации по уникальной ссылке.

### Сквозной сценарий
1. Психолог входит в систему.
2. Создаёт тест в конструкторе (ручной или через JSON import).
3. Копирует уникальную ссылку и отправляет клиенту.
4. Клиент заполняет обязательные поля и проходит тест с индикатором прогресса.
5. Ответы и метрики сохраняются в БД.
6. Психолог в карточке теста получает 2 вида отчётов:
   - `client` (HTML/DOCX)
   - `psychologist` (HTML/DOCX)

### Поддержка требований кейса
- Конструктор с секциями и типами вопросов:
  - `text`, `textarea`, `single_choice`, `multiple_choice`, `yes_no`, `number`, `slider`, `datetime`, `rating`
- Import/Export теста в JSON.
- Публичная визитка психолога + QR-код.
- Отчёты **не сохраняются на диск**: генерируются по запросу в памяти.
- Есть seed-данные: демо-админ, демо-психолог и заранее созданный тест.

## Технологический стек
- Backend: `Python 3.11`, `FastAPI`, `SQLAlchemy`
- DB: `PostgreSQL` (для прода и docker-compose)
- Frontend: `Jinja2 + vanilla JS` (встроенный веб-интерфейс)
- Отчёты: `python-docx`, HTML-шаблоны
- Деплой: `Docker Compose`

Примечание по фронтенду: в ТЗ рекомендованы Nuxt/Next (желательно, но не жёстко). Для ускорения MVP выбран серверный UI на FastAPI/Jinja2 с отдельным планом миграции на Next.js в фазе улучшений.

## Быстрый старт (Docker Compose)

```bash
docker compose up -d --build
```

После запуска:
- Приложение: `http://localhost:8000`
- Health: `http://localhost:8000/api/health`

## Локальный запуск (без Docker)

1. Установить зависимости:
```bash
pip install -r backend/requirements.txt
```

2. Настроить env:
- скопировать `.env.example` и выставить значения
- минимум:
  - `APP_SECRET_KEY`
  - `DATABASE_URL`
  - `BASE_URL`

3. Запуск:
```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Демо-аккаунты
- Админ: `admin@profdnk.local` / `admin123`
- Психолог: `psychologist@demo.local` / `demo12345`

## Структура проекта

```text
backend/
  app/
    routers/        # auth, admin, psychologist, public, api
    services/       # scoring, reports, tests, seed
    templates/      # HTML страницы и report templates
    static/         # css/js/uploads
    models.py       # SQLAlchemy модели
    main.py         # FastAPI приложение
docker-compose.yml
README.md
docs/
  architecture.md
  roadmap.md
```

## План доработки после MVP

См. [docs/roadmap.md](docs/roadmap.md):
- Next.js фронтенд
- drag-and-drop конструктор
- branching logic
- графики в отчётах
- клонирование тестов, тёмная/светлая тема

Рабочий трекер задач и прогресса: [docs/TODO.md](docs/TODO.md)

## Проверка, которую уже прошёл проект
- `python -m compileall backend/app`
- Автосценарий через `TestClient`:
  - логин психолога
  - прохождение теста клиентом
  - получение списка результатов
  - генерация HTML и DOCX отчётов

## Что важно показать на защите
- Полный end-to-end поток (создание теста -> прохождение -> отчёт)
- Admin flow (создание психолога, блокировки и срок доступа)
- Import/Export JSON
- Кодовая структура как основа для развития продукта
