# Plan: Personal Telegram Assistant MVP

## Summary

MVP: Telegram-бот на Python, который принимает естественные сообщения, через LangChain/Pydantic извлекает `event`, `reminder` или `unknown`, сохраняет события в Postgres и присылает уведомления в Telegram.

Ключевая идея: модель только парсит intent и задает уточнения. Создание записей, проверка конфликтов, списки, удаление и уведомления выполняются обычным deterministic-кодом.

Стек MVP:
- Python + `aiogram` async
- Postgres + async SQLAlchemy
- LangChain Python + Pydantic schema
- Celery worker + Celery Beat
- Redis как Celery broker
- Docker Compose для Postgres и Redis

## Key Design

- Multi-user изоляция обязательна: каждый `telegram_user_id` мапится на `users.id`; все запросы к событиям, уведомлениям и спискам всегда фильтруются по `user_id`.
- События и уведомления хранятся в Postgres. Короткий state уточняющего диалога хранится in-memory в `dict[telegram_user_id, UserDraft]`.
- Если бот перезапустился, незавершенный диалог теряется, но уже созданные события и уведомления остаются.
- Для пользователя по умолчанию использовать timezone `Europe/Kiev`; later можно добавить настройку timezone.
- Текущий TS-проект оставить как reference baseline; Python MVP строить отдельно в `app/`.

## App Structure

```text
app/
  main.py
  config.py

  bot/
    handlers.py
    callbacks.py
    keyboards.py

  agent/
    schema.py
    prompt.py
    parser.py

  db/
    models.py
    session.py
    migrations/

  services/
    drafts.py
    calendar.py
    conflicts.py
    notifications.py
```

Основные сервисы:
- `agent.parser`: переносит текущую схему `ParsedItem` и prompt logic из TS в Python.
- `services.drafts`: хранит per-user context для уточнений.
- `services.calendar`: создает, читает и удаляет события/напоминания.
- `services.conflicts`: проверяет пересечения встреч.
- `services.notifications`: создает notification rows и ставит ближайшие уведомления в Celery queue.

## Public Interfaces

Bot commands:
- `/start` - создать пользователя, показать короткое приветствие.
- `/week` - показать события и reminders на ближайшие 7 дней.
- `/month` - показать ближайший месяц.
- `/quarter` - показать ближайшие 3 месяца.
- `/cancel` - сбросить текущий in-memory draft пользователя.

Inline buttons:
- При конфликте: `Оставить оба`, `Изменить время`.
- В списках: `Удалить` для конкретного item id.

Pydantic schema mirrors current TS shape:
- `type`: `event | reminder | unknown`
- `title`, `description`
- `date`, `time`, `timezone`, `is_all_day`
- `recurrence`
- `confidence`
- `clarification_question`
- `language`: `ru | uk | en`

DB tables:
- `users`: `id`, `telegram_user_id`, `language`, `timezone`, timestamps.
- `calendar_items`: user-owned events/reminders with `start_at`, optional `end_at`, recurrence JSON, title/description.
- `notifications`: generated notification rows with `user_id`, `telegram_chat_id`, `event_id`, `send_at`, `status`, `payload`, timestamps.

## Core Flows

Create item:
1. User sends text.
2. Bot loads user draft by `telegram_user_id`.
3. LangChain parser returns `ParsedItem`.
4. If clarification is needed, bot stores draft context and asks one question.
5. If item is complete, app normalizes date/time into timezone-aware datetimes.
6. If item is an `event`, conflict service checks overlaps for the same user.
7. If conflict exists, bot shows conflict summary and inline choices.
8. If confirmed, calendar service writes item to Postgres.
9. Notification service creates notification rows.

Conflict policy:
- Events are checked as intervals.
- If duration/end time is missing, MVP assumes 1 hour.
- Conflict means intervals overlap for the same user.
- User can keep both events or change the new event time.

Notifications:
- `event`: create 2 notifications, hardcoded for MVP:
  - 30 minutes before start
  - at start time
- `reminder`: create 1 notification at the reminder time.
- New notification rows are saved in Postgres with status `pending`.
- Celery Beat runs a scheduler task every 60 seconds.
- The scheduler selects `pending` notifications where `send_at <= now() + 15 minutes`.
- Each selected notification is added to Celery as a delayed task with `eta=send_at`.
- After successful enqueue, status changes from `pending` to `queued`.
- Celery worker executes the task at `send_at`, sends `payload` to `telegram_chat_id`, then changes status to `sent`.
- Telegram send failures are retried by Celery.
- When retries are exhausted, status changes to `failed`.
- Cancelled notifications have status `cancelled` and must not be queued or sent.

Recurrence:
- MVP supports simple recurrence from current schema: daily, weekly, monthly, yearly.
- Use `python-dateutil` where useful instead of hand-rolling calendar math.
- Listing commands expand recurring items inside requested window.
- Notification generation creates upcoming notification rows for recurring items within a rolling 3-month horizon.

Delete/cancel:
- MVP deletion is not agent-based.
- `/week`, `/month`, `/quarter` show inline delete buttons.
- Delete checks ownership by `user_id` and changes related `pending` or `queued` notifications to `cancelled`.

## Test Plan

Unit tests:
- Pydantic schema accepts valid parser output and rejects invalid types.
- Draft state is isolated by `telegram_user_id`.
- Conflict detection catches overlapping intervals and ignores non-overlapping intervals.
- Default event duration is 1 hour.
- Notification service creates 2 rows for events and 1 row for reminders.
- Notification scheduler queues only `pending` rows inside the next 15 minutes.
- Celery worker changes a successfully delivered notification from `queued` to `sent`.
- Exhausted Telegram retries change notification status to `failed`.
- Delete removes only the current user's item.

Integration/manual checks:
- "Встреча с Иваном завтра в 15:00" creates an event and 2 notifications.
- Second overlapping meeting triggers conflict flow.
- "Напомни передать показания счетчиков 25 числа в 10:00" creates reminder.
- Recurring birthday/yearly reminder appears in `/quarter`.
- `/week`, `/month`, `/quarter` show only current user's data.
- User A clarification context never affects User B.

## Assumptions

- Python implementation is the next app; TS code remains learning/reference material.
- MVP favors simple explicit commands over agent-driven list/delete flows.
- Agent-based deletion and richer natural-language management are v2.
- User-specific timezone settings are postponed; default is `Europe/Kiev`.
- In-memory drafts are acceptable for MVP because losing an unfinished clarification after restart is not critical.
- `notifications.event_id` references `calendar_items.id` for both `event` and `reminder` records.
