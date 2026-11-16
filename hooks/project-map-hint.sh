#!/bin/bash
# SessionStart hook: if the project has docs/PROJECT_MAP.md, tell the agent to use it
# and warn when the map is stale. Silent (no output) when there is no map.
# Part of the verdict plugin.

input=$(cat 2>/dev/null)
dir="${CLAUDE_PROJECT_DIR:-}"
if [ -z "$dir" ] && command -v jq >/dev/null 2>&1; then
  dir=$(printf '%s' "$input" | jq -r '.cwd // empty' 2>/dev/null)
fi
[ -z "$dir" ] && dir="$PWD"

root=$(git -C "$dir" rev-parse --show-toplevel 2>/dev/null || echo "$dir")
map="$root/docs/PROJECT_MAP.md"
[ -f "$map" ] || exit 0

msg="В проекте есть карта для ИИ-агентов: docs/PROJECT_MAP.md (и правила в CLAUDE.md). Перед работой с незнакомой частью кода прочитай из карты нужный раздел (Где менять X, Подводные камни, Образцы стиля, Границы), а не изучай проект с нуля."
[ -d "$root/docs/map" ] && msg="$msg Подробные разделы по областям лежат в docs/map/."

commit=$(head -n 8 "$map" | grep -oE '`[0-9a-f]{7,40}`' | head -n 1 | tr -d '`')
if [ -n "$commit" ] && git -C "$root" cat-file -e "$commit^{commit}" 2>/dev/null; then
  n=$(git -C "$root" rev-list --count "$commit..HEAD" 2>/dev/null || echo 0)
  if [ "${n:-0}" -ge 20 ]; then
    msg="$msg Карта, возможно, устарела: после её коммита $commit сделано ещё коммитов: $n. Если работа касается изменённых мест, сверяйся с кодом и предложи пользователю /verdict:audit update."
  fi
elif [ -n "$commit" ]; then
  msg="$msg Коммит карты $commit не найден в истории (rebase или shallow clone), поэтому актуальность карты не проверена."
fi

# Hand-built JSON: msg contains only fixed text, a hex hash and a number, so no escaping is needed.
printf '{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"%s"}}\n' "$msg"
