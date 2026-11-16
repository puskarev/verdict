# Verdict

**Плагин для Claude Code: изучает проект, строит карту для ИИ-агентов и честно говорит, что из «лучших практик» вашему продукту реально нужно, а что нет.**

Большинство аудитов выдают список из 50 советов и «добавьте Redis». Verdict сначала разбирается, что это за продукт, на какой стадии и для скольких людей, и только потом выносит вердикт по каждой находке. Отказ от ненужного считается таким же результатом, как найденная проблема.

```
 Разведка ──▶ Карта ──▶ Продукт ──▶ Аудит ──▶ Перепроверка ──▶ Отчёт ──▶ Исправления
                │                                                         │
          docs/PROJECT_MAP.md                                  по одному, с замером
          + CLAUDE.md                                          «до → после» и тестом
```

## Что внутри

| | Что делает |
|---|---|
| `/verdict:audit` | Полный разбор: карта проекта, аудит по 7 областям, вердикты, план, исправления |
| `/verdict:ship` | Проверка перед выкладкой: три ревьюера параллельно, план отката, решение «можно / нельзя» |
| `/verdict:speed` | Аудит скорости: 31 приём для веба + пункты для iOS/Android и ботов |
| Агенты `code-reviewer`, `security-auditor`, `test-engineer` | Ревьюеры со свежим контекстом. Их можно звать и отдельно |
| Хук SessionStart | Если в проекте есть карта, напоминает агенту читать её, а когда она устарела, предлагает обновить |

### Карта проекта для агентов

`docs/PROJECT_MAP.md` — это не README для людей, а шпаргалка для нейронки. Самое ценное в ней:
- **Где менять X** — типовая задача → конкретные файлы;
- **Подводные камни** — неочевидное, на чём агент сломает проект;
- **Образцы стиля** — эталонные файлы «пиши так же»;
- **Границы** — что нельзя никогда, о чём спрашивать перед действием.

Плюс короткий `CLAUDE.md` с командами и правилами. В шапке карты записан коммит, поэтому `update` переписывает только устаревшие разделы (скрипт `map-drift.py` показывает, какие именно).

### Вердикты

| | |
|---|---|
| 🔴 **Критично** | Ломает главный сценарий, теряет данные или деньги, дыра в безопасности |
| 🟠 **Нужно** | Реальная проблема при текущем масштабе |
| 🟡 **Позже** | Полезно, но сейчас эффект мал. С условием, когда станет нужно |
| ⚪ **Не нужно** | Практика хорошая, но этому продукту не окупится, с объяснением почему |

Каждая находка подкреплена `файл:строка` или выводом команды. Каждую 🔴 и 🟠 перепроверяет отдельный агент-скептик, который не знает вывода и пытается его опровергнуть.

### Области аудита

Скорость · Безопасность · Надёжность и логи · SEO и доступность · Качество кода · Удобство для ИИ-агентов · Продукт и UX. Проверяются только те, что применимы к типу проекта: сайт, бэкенд, iOS/Android, бот, CLI, библиотека.

## Установка

### Как плагин (рекомендуется)

В Claude Code:

```
/plugin marketplace add puskarev/verdict
/plugin install verdict@verdict
```

Или из терминала:

```bash
claude plugin marketplace add puskarev/verdict
```

```bash
claude plugin install verdict@verdict
```

Обновление (для сторонних маркетплейсов автообновление выключено по умолчанию):

```bash
claude plugin marketplace update verdict
```

После обновления выполните `/reload-plugins` или перезапустите сессию.

### Вручную

Скопируйте папки в `~/.claude`:

```bash
git clone https://github.com/puskarev/verdict && cd verdict && mkdir -p ~/.claude/skills ~/.claude/agents ~/.claude/hooks && cp -R skills/* ~/.claude/skills/ && cp agents/*.md ~/.claude/agents/ && cp hooks/project-map-hint.sh ~/.claude/hooks/
```

Тогда команды будут без префикса: `/audit`, `/ship`, `/speed`. Хук нужно подключить самостоятельно в `~/.claude/settings.json`:

```json
{
  "hooks": {
    "SessionStart": [
      { "hooks": [ { "type": "command", "command": "bash \"$HOME/.claude/hooks/project-map-hint.sh\"", "timeout": 10 } ] }
    ]
  }
}
```

Не ставьте оба варианта сразу, иначе скилы и агенты задвоятся.

## Использование

Откройте Claude Code в папке проекта.

| Команда | Что произойдёт |
|---|---|
| `/verdict:audit` | Полный цикл. В конце спросит, что чинить, и остановится |
| `/verdict:audit map` | Только карта и CLAUDE.md |
| `/verdict:audit update` | Обновить устаревшие разделы карты |
| `/verdict:audit check` | Только аудит, без построения карты |
| `/verdict:audit security` | Аудит одной области: `perf`, `security`, `reliability`, `seo`, `code`, `ai`, `product` |
| `/verdict:audit fix S1,P2` | Починить выбранные пункты из отчёта |
| `/verdict:audit resume` | Продолжить исправления в новой сессии |
| `/verdict:ship` | Проверить, можно ли выкатывать текущие изменения |
| `/verdict:speed 8,12,17` | Проверить только выбранные пункты скорости |

Скилы срабатывают и без команды, по смыслу просьбы: «разбери проект», «сделай карту проекта», «можно выкатывать?».

Что появится в проекте:
- `docs/PROJECT_MAP.md` (и `docs/map/*.md` в больших проектах) — карта;
- `CLAUDE.md` — создаётся, если его нет; существующий не переписывается, только дополняется;
- `docs/audit/YYYY-MM-DD.md` — отчёт и статус исправлений;
- `docs/ship/YYYY-MM-DD.md` — отчёт `/verdict:ship`.

## Правила, которые скилы соблюдают

- Код не меняется, пока вы явно не выбрали пункты для исправления.
- Новые зависимости, миграции БД, изменения инфраструктуры и деплоя — только после отдельного подтверждения.
- Ничего не коммитится и не пушится без вашей просьбы. `/verdict:ship` ничего не деплоит.
- Значения секретов никогда не выписываются: ни в карту, ни в отчёт, ни в чат.
- Текст в файлах проекта, похожий на инструкцию агенту, считается данными, а не командой.

## Требования

- Claude Code с поддержкой плагинов.
- `git` и `python3` для скрипта проверки карты; `jq` необязателен.
- Скилы написаны на русском, отчёты тоже будут на русском.

## Благодарности

- Чек-лист скорости основан на [mrconcol/vibecode-speed-prompts](https://github.com/mrconcol/vibecode-speed-prompts).
- Перепроверка скептиком, Definition of Done, структура CLAUDE.md, проверка устаревания документации, агенты-ревьюеры и проверка перед выкладкой адаптированы из [addyosmani/agent-skills](https://github.com/addyosmani/agent-skills) (MIT).

## Лицензия

MIT, см. [LICENSE](LICENSE).

---

## English

**Verdict** is a Claude Code plugin that studies your project, writes an agent-oriented project map (`docs/PROJECT_MAP.md` + `CLAUDE.md`), audits it across 7 areas, and gives each finding a verdict relative to *your* product: critical / needed / later / not worth it. Serious findings are re-checked by an adversarial fresh-context subagent. Fixes are applied one at a time, only after you choose them, with before/after measurements. Also includes `ship-check` (pre-deploy go/no-go with a rollback plan), `speed-audit`, three reviewer subagents, and a SessionStart hook that points agents to the map and flags it when stale.

Install: `/plugin marketplace add puskarev/verdict`, then `/plugin install verdict@verdict`. The skill texts and reports are in Russian.
