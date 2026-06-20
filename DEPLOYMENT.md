# Развёртывание Домашней библиотеки

Документ описывает локальную разработку в контейнере и ручной деплой на VPS с использованием `podman-compose`. Docker-совместимость сохраняется.

## Архитектура

```
Upstream LB (TLS + routing)
        │
        ▼
   Nginx (порт 80)
        │
        ▼
Gunicorn + Django (порт 8000)
        │
   ┌────┴────┐
   ▼         ▼
SQLite    static files
volume    volume
```

- **Django** работает через **Gunicorn**.
- **Nginx** проксирует запросы к Django и раздаёт статические файлы.
- **TLS-сертификаты** обрабатываются upstream load balancer'ом, nginx получает обычный HTTP.
- **SQLite** хранится в именованном volume `library-data`.
- **Статика** собирается в именованный volume `library-static`.

## Требования

- [Podman](https://podman.io/) и [podman-compose](https://github.com/containers/podman-compose)
- Или Docker + docker-compose (файлы совместимы)
- Git
- Для macOS: запущенная `podman machine` (`podman machine init` и `podman machine start`)

## Подготовка

1. Скопируйте `.env.example` в `.env`:

   ```bash
   cp .env.example .env
   ```

2. (Опционально) Для удобной разработки измените `.env`:

   ```bash
   DEBUG=True
   SECRET_KEY=django-insecure-dev-key
   ALLOWED_HOSTS=*
   CSRF_TRUSTED_ORIGINS=http://localhost:8000
   ```

3. Запустите сервисы:

   ```bash
   podman-compose up --build -d
   ```

   Или, если образ уже собран:

   ```bash
   podman-compose up -d
   ```

4. Откройте приложение в браузере:

   ```text
   http://localhost:8000
   ```

При первом запуске `entrypoint.sh` автоматически выполнит миграции и соберёт статику.

## Ручная сборка образа

```bash
podman build -t library-app -f Containerfile .
```

## Production-деплой на VPS

1. Склонируйте репозиторий на сервер:

   ```bash
   git clone <URL_репозитория>
   cd python
   ```

2. Создайте `.env` из `.env.example` и задайте production-значения:

   ```bash
   cp .env.example .env
   # отредактируйте .env
   ```

   Минимальный набор:

   ```bash
   DEBUG=False
   SECRET_KEY=<длинный-случайный-ключ>
   ALLOWED_HOSTS=*
   CSRF_TRUSTED_ORIGINS=https://<ваш-домен>
   ```

3. Загрузите свежий образ из GitHub Container Registry:

   ```bash
   podman-compose pull
   ```

4. Запустите сервисы в фоне:

   ```bash
   podman-compose up -d
   ```

5. Настройте upstream load balancer на маршрутизацию к порту `8000` VPS. TLS-сертификаты управляются балансировщиком.

## Обновление приложения

```bash
cd python
podman-compose pull
podman-compose up -d
```

## Переменные окружения

| Переменная | Описание | Пример |
|------------|----------|--------|
| `DEBUG` | Режим отладки Django | `False` |
| `SECRET_KEY` | Секретный ключ Django | `change-me-in-production` |
| `ALLOWED_HOSTS` | Разрешённые хосты через запятую | `*` или `example.com` |
| `CSRF_TRUSTED_ORIGINS` | Доверенные origin для CSRF | `https://example.com` |

## GitHub Actions

Файл `.github/workflows/build-and-push.yml` автоматически собирает образ при пуше в ветку `main` и публикует его в GitHub Container Registry:

```text
ghcr.io/nikolyabb/library-app:latest
ghcr.io/nikolyabb/library-app:<sha>
```

После первой сборки пакет по умолчанию приватный. Для загрузки на VPS используйте `GITHUB_TOKEN` с правами `read:packages` или сделайте пакет публичным в настройках GitHub.

## Бэкап SQLite

Данные живут в именованном volume `library-data`. Пример создания резервной копии:

```bash
podman run --rm \
  -v library-data:/data:ro \
  -v $(pwd):/backup \
  docker.io/alpine \
  tar czf /backup/library-data-backup-$(date +%Y%m%d).tar.gz -C /data .
```

Восстановление:

```bash
podman run --rm \
  -v library-data:/data \
  -v $(pwd):/backup \
  docker.io/alpine \
  tar xzf /backup/library-data-backup-YYYYMMDD.tar.gz -C /data
```

## Важные замечания

- `SECRET_KEY` должен быть изменён в production.
- Файл `.env` не попадает в образ и не должен попадать в Git.
- SQLite подходит для небольшой нагрузки. Для следующего этапа планируется переход на PostgreSQL.
- Nginx не обрабатывает TLS, так как это делает upstream load balancer.
- При первом старте `nginx` может на короткое время отдавать 502, пока `web` выполняет миграции и запускается. Это нормально.
- Дизайн интерфейса — собственный CSS с шрифтом Inter и монохромной палитрой. Pico.css не используется.
- Срок возврата при выдаче книги выбирается с точностью до месяца; день устанавливается как 1-е число.
