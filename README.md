# ChatList (ChatViewer)

Десктопное приложение для Windows: один промт → несколько нейросетей через OpenRouter → сравнение ответов в одной таблице.

## Возможности

- Отправка промта в несколько chat-моделей OpenRouter
- AI-ассистент для улучшения промтов
- История запросов, SQLite, экспорт Markdown/JSON
- Светлая и тёмная тема, Windows-инсталлятор с деинсталлятором

## Скачать

- **Сайт:** https://daniilsq-tech.github.io/ChatViewer/
- **Releases:** https://github.com/DaniilSQ-tech/ChatViewer/releases

Рекомендуется инсталлятор `ChatViewer-Setup-*.exe`.

## Разработка

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

Сборка:

```powershell
.\build.ps1              # exe
.\build-installer.ps1    # exe + инсталлятор
```

## Публикация

Пошаговая инструкция: [docs/PUBLISHING.md](docs/PUBLISHING.md)

## Лицензия

MIT — см. [LICENSE](LICENSE)
