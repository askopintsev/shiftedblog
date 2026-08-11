# Участие в разработке

Спасибо за интерес к ShiftedBlog.

English: [CONTRIBUTING.md](../../CONTRIBUTING.md)

## Локальная среда

Рекомендуемый способ — Docker:

```bash
./scripts/setup.sh
# выберите «local»
```

Подробнее: [local-deploy.md](local-deploy.md).

## Стиль кода

- Python: Ruff и Pyright (см. `pyproject.toml`)
- Бизнес-логику выносите в сервисы; views оставляйте тонкими
- Оптимизируйте queryset’ы (`select_related` / `prefetch_related`)
- Не коммитьте секреты (`.env`, `secrets.env`, ключи)

## Pull request

1. Форк и ветка под задачу
2. Изменения по возможности точечные; при смене поведения — тесты
3. Прогоните `ruff` / `pyright` и релевантные тесты
4. В описании PR кратко укажите *зачем* нужны изменения

## Безопасность

Уязвимости сообщайте приватно — см. [SECURITY.md](../../SECURITY.md).
