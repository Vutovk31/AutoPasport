# AutoPassport

Канонический проект: электронный паспорт автомобиля с подтверждаемой историей обслуживания.

## Текущий канонический релиз

```text
AutoPassport_v0.24.0_Restore_Hardening.zip
SHA-256: a3ef08ff3bbd3cf5bd53d80244d3a06e798e763f8eb0dbebae86a8654f7453f3
Tests: 15 passed
```

## Состояние загрузки исходников

Полный ZIP проекта физически создан в рабочей среде ChatGPT и доступен в артефактах текущего чата. Прямая массовая загрузка всего распакованного дерева в GitHub через доступный GitHub-коннектор ограничена: коннектор поддерживает создание отдельных текстовых файлов и Git tree/blob API, но не принимает локальный ZIP/папку как единый upload-артефакт.

До ручной загрузки распакованного ZIP этот репозиторий используется как точка фиксации канонической версии, SHA-256 и дальнейшего перехода к GitHub-разработке.

## Ручная загрузка

1. Скачать `AutoPassport_v0.24.0_Restore_Hardening.zip` из текущего чата.
2. Распаковать архив локально.
3. Открыть репозиторий `Vutovk31/AutoPasport`.
4. Нажать **Add file → Upload files**.
5. Перетащить всё содержимое распакованной папки, не саму папку верхнего уровня.
6. Commit message: `chore: import AutoPassport v0.24.0 canonical source`.

## Проверка после загрузки

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
alembic upgrade head
pytest -q
uvicorn app.main:app --reload
```

Ожидаемый результат тестов:

```text
15 passed
```
