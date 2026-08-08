## ChatList {{VERSION}}

**Дата:** {{DATE}}  
**Платформа:** Windows 10/11 (64-bit)

ChatList — приложение для отправки одного промта в несколько нейросетей через OpenRouter и сравнения ответов.

### Что нового

- {{CHANGE_1}}
- {{CHANGE_2}}
- {{CHANGE_3}}

### Скачивание

| Файл | Описание | SHA256 |
|------|----------|--------|
| `ChatViewer-Setup-{{VERSION}}.exe` | **Рекомендуется** — инсталлятор с деинсталлятором | `{{SHA256_SETUP}}` |
| `ChatViewer-{{VERSION}}.exe` | Portable-версия (без установки) | `{{SHA256_PORTABLE}}` |

### Системные требования

- Windows 10 или 11 (64-bit)
- API-ключ [OpenRouter](https://openrouter.ai/) (настраивается после установки в `.env.local`)

### Установка

1. Скачайте `ChatViewer-Setup-{{VERSION}}.exe`.
2. Запустите установщик и следуйте шагам мастера.
3. Создайте файл `.env.local` в каталоге установки:

```env
OPENROUTER_API_KEY=sk-or-v1-ваш-ключ
```

4. Запустите **ChatList** из меню «Пуск».

### Удаление

**Параметры Windows → Приложения → ChatList → Удалить**  
или **Пуск → ChatList → Удалить ChatList**.

### Полная установка с нуля

<details>
<summary>Portable-версия</summary>

1. Скачайте `ChatViewer-{{VERSION}}.exe`.
2. Поместите файл в удобный каталог.
3. Рядом создайте `.env.local` с ключом OpenRouter.
4. При первом запуске создадутся каталоги `data/` и `logs/`.

</details>

---

**Лицензия:** MIT · [Исходный код](https://github.com/DaniilSQ-tech/ChatViewer)
