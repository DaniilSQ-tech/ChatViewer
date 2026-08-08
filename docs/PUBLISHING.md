# Публикация ChatList (ChatViewer)

Пошаговая инструкция: сборка релиза, GitHub Release и GitHub Pages.

**Репозиторий:** https://github.com/DaniilSQ-tech/ChatViewer  
**Сайт (Pages):** https://daniilsq-tech.github.io/ChatViewer/

---

## Что понадобится

| Инструмент | Назначение |
|------------|------------|
| Python 3.11+ и `.venv` | Сборка exe |
| [PyInstaller](https://pyinstaller.org/) | Упаковка приложения |
| [Inno Setup 6](https://jrsoftware.org/isdl.php) | Windows-инсталлятор |
| [GitHub CLI (`gh`)](https://cli.github.com/) | Создание Release из терминала (опционально) |
| Аккаунт GitHub | Release + Pages |

Установка Inno Setup (PowerShell):

```powershell
winget install --id JRSoftware.InnoSetup
```

---

## Часть 1. Подготовка версии

### Шаг 1. Обновите номер версии

Единственный источник версии — файл `version.py`:

```python
__version__ = "1.0.0"
```

Используйте [semver](https://semver.org/lang/ru/): `MAJOR.MINOR.PATCH` (например `1.0.1`, `1.1.0`).

### Шаг 2. Проверьте изменения

```powershell
git status
git diff
```

Убедитесь, что в коммит не попадут секреты (`.env`, `.env.local` уже в `.gitignore`).

### Шаг 3. Закоммитьте и отправьте в `main`

```powershell
git add .
git commit -m "Выпуск версии 1.0.0"
git push origin main
```

---

## Часть 2. Сборка артефактов

### Шаг 4. Соберите exe и инсталлятор

```powershell
.\build-installer.ps1
```

Или по шагам:

```powershell
.\build.ps1
.\build-installer.ps1 -SkipBuild
```

### Шаг 5. Проверьте результат

В каталоге `dist\` должны появиться:

| Файл | Назначение |
|------|------------|
| `ChatViewer-1.0.0.exe` | Портативная сборка (без установки) |
| `ChatViewer-Setup-1.0.0.exe` | Инсталлятор для пользователей |

Проверьте запуск на чистой машине или в VM.

### Шаг 6. Подготовьте release notes

Скопируйте шаблон и заполните плейсхолдеры:

```powershell
.\scripts\prepare-release.ps1
```

Скрипт создаст файл `dist\RELEASE_NOTES-1.0.0.md` с SHA256-хешами артефактов.

---

## Часть 3. GitHub Release

### Шаг 7. Создайте git-тег

Тег должен совпадать с версией и начинаться с `v`:

```powershell
git tag -a v1.0.0 -m "ChatList 1.0.0"
git push origin v1.0.0
```

### Шаг 8. Создайте Release

#### Вариант A — через GitHub CLI (рекомендуется)

```powershell
gh release create v1.0.0 `
  "dist\ChatViewer-Setup-1.0.0.exe" `
  "dist\ChatViewer-1.0.0.exe" `
  --title "ChatList 1.0.0" `
  --notes-file "dist\RELEASE_NOTES-1.0.0.md"
```

#### Вариант B — через веб-интерфейс

1. Откройте **Releases → Draft a new release**  
   https://github.com/DaniilSQ-tech/ChatViewer/releases/new
2. **Choose a tag:** `v1.0.0` (создайте новый тег).
3. **Release title:** `ChatList 1.0.0`
4. **Description:** вставьте текст из `dist\RELEASE_NOTES-1.0.0.md`.
5. **Attach binaries:** перетащите оба файла из `dist\`.
6. Нажмите **Publish release**.

### Шаг 9. Чеклист Release

- [ ] Тег `vX.Y.Z` совпадает с `version.py`
- [ ] Прикреплён **инсталлятор** (`ChatViewer-Setup-*.exe`) — основной файл для пользователей
- [ ] Прикреплён **portable exe** (`ChatViewer-*.exe`) — для продвинутых пользователей
- [ ] В описании указаны системные требования и SHA256
- [ ] Release помечен как **Latest** (последний релиз)
- [ ] Лендинг на Pages подтягивает ссылку на скачивание (см. часть 4)

---

## Часть 4. GitHub Pages (лендинг)

### Шаг 10. Включите GitHub Pages

1. Репозиторий → **Settings → Pages**
2. **Build and deployment → Source:** `GitHub Actions`
3. После первого push в `docs/` workflow **Deploy GitHub Pages** опубликует сайт.

### Шаг 11. Обновите лендинг при новой версии

Отредактируйте `docs/index.html`:

- блок «Текущая версия» (или он подтянется через GitHub API автоматически);
- при необходимости — список возможностей и скриншоты в `docs/assets/`.

Закоммитьте и отправьте:

```powershell
git add docs/
git commit -m "Обновление лендинга для версии 1.0.0"
git push origin main
```

Workflow `.github/workflows/pages.yml` задеплоит сайт автоматически.

### Шаг 12. Проверьте сайт

Откройте https://daniilsq-tech.github.io/ChatViewer/  
Кнопка «Скачать» должна вести на последний Release.

---

## Часть 5. Автоматизация (опционально)

### CI: сборка Release по тегу

Workflow `.github/workflows/release.yml` при push тега `v*`:

1. Собирает exe (PyInstaller)
2. Собирает инсталлятор (Inno Setup)
3. Публикует GitHub Release с артефактами

Локальная сборка остаётся основным способом; CI — запасной вариант.

Запуск вручную:

```powershell
git tag -a v1.0.0 -m "ChatList 1.0.0"
git push origin v1.0.0
```

---

## Быстрая шпаргалка (новый релиз)

```powershell
# 1. Версия
#    отредактировать version.py → "1.0.1"

# 2. Коммит
git add version.py
git commit -m "Выпуск версии 1.0.1"
git push origin main

# 3. Сборка
.\build-installer.ps1
.\scripts\prepare-release.ps1

# 4. Тег и Release
git tag -a v1.0.1 -m "ChatList 1.0.1"
git push origin v1.0.1
gh release create v1.0.1 `
  "dist\ChatViewer-Setup-1.0.1.exe" `
  "dist\ChatViewer-1.0.1.exe" `
  --title "ChatList 1.0.1" `
  --notes-file "dist\RELEASE_NOTES-1.0.1.md"

# 5. Pages обновятся при push docs/ (если меняли лендинг)
```

---

## Структура файлов публикации

```
.github/
  RELEASE_NOTES.template.md   # шаблон описания Release
  workflows/
    pages.yml                 # деплой docs/ → GitHub Pages
    release.yml               # сборка по тегу (опционально)
docs/
  index.html                  # лендинг
  PUBLISHING.md               # эта инструкция
  assets/
    logo.svg                  # логотип для сайта
scripts/
  prepare-release.ps1         # генерация release notes + checksums
```

---

## Частые проблемы

| Проблема | Решение |
|----------|---------|
| Inno Setup не найден | `winget install --id JRSoftware.InnoSetup`, перезапустите терминал |
| Pages не обновляется | Settings → Pages → Source = GitHub Actions; проверьте Actions |
| Кнопка «Скачать» ведёт в 404 | Опубликуйте Release; имя файла должно содержать `Setup` |
| SmartScreen блокирует exe | Подпишите код (codesign) или предупредите пользователей в Release notes |
