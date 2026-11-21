# Визуализация зависимостей Python-пакетов. Вариант 14

Для запуска нужен Python 3.10 или новее. Визуализатор использует стандартную
библиотеку.

Из корня репозитория запустите демонстрацию в Linux или Git Bash.

```bash
./run.sh
```

Скрипт без аргументов строит пример с циклом из тестового репозитория.
При передаче параметров скрипт запускает CLI с этими параметрами.
В PowerShell тот же пример можно получить следующей командой.

```powershell
python -B src/dependency_graph_lab/dependency_graph.py -p A --test -r src/dependency_graph_lab/example_repository.json -d 4 --ascii
```

Программа читает `info.requires_dist` из PyPI JSON API по адресу
`/pypi/<пакет>/json`. Для графа имена пакетов нормализуются, а одинаковые
зависимости объединяются в одно ребро. Рекурсивный DFS учитывает оставшуюся
глубину при каждом посещении пакета. У корня глубина 0, у прямой зависимости
глубина 1. При повторном посещении с большей оставшейся глубиной обход
продолжается. В ASCII-дереве `(cycle)` отмечает возврат к узлу текущей
ветки, а `(shared)` обозначает уже раскрытый общий узел.

Тестовый репозиторий представляет собой JSON-объект. Ключи — имена пакетов
заглавными латинскими буквами, значения — массивы имён их зависимостей.
Пакет без зависимостей описывается пустым массивом. Полный тестовый граф
позволяет развернуть рёбра и найти обратные зависимости тем же DFS.

## Демонстрация этапов

Выполните команды из корня репозитория. Первый блок меняет текущую папку на каталог визуализатора.

```powershell
Push-Location -LiteralPath src/dependency_graph_lab
python -B -m dependency_graph -p A --test -r example_repository.json --show-config
python -B -m dependency_graph -p A -d -1
python -B -m dependency_graph -p requests --direct
python -B -m dependency_graph -p A --test -r example_repository.json -d 1 --graph
python -B -m dependency_graph -p A --test -r example_repository.json -d 4 --graph
python -B -m dependency_graph -p C --test -r example_repository.json -d 1 --reverse
python -B -m dependency_graph -p C --test -r example_repository.json -d 3 --reverse
```

Без флагов отображения программа выводит PlantUML. Чтобы получить изображение,
сохраните вывод от `@startuml` до `@enduml` в файл с расширением `.puml`
и откройте его в PlantUML. Следующие команды строят три примера для PyPI.

```powershell
python -B -m dependency_graph -p requests -d 1 --ascii
python -B -m dependency_graph -p click -d 1 --ascii
python -B -m dependency_graph -p jinja2 -d 1 --ascii
Pop-Location
```

При сравнении с `pip show` в Windows на локальных метаданных версий
Requests 2.32.5, Click 8.3.1 и Jinja2 3.1.6 получились такие результаты.

| Пакет | `pip show`, поле `Requires` | Дополнительно в графе |
| --- | --- | --- |
| Requests | certifi, charset_normalizer, idna, urllib3 | chardet, PySocks |
| Click | colorama | — |
| Jinja2 | MarkupSafe | Babel |

Граф сохраняет объявленные опциональные и условные зависимости. В
сравнении `pip show` учитывает установленную версию и текущее окружение.
При запросе к PyPI версии и набор объявленных зависимостей могут измениться.

## Автоматические тесты

Запустите из корня репозитория.

```powershell
python -B -m unittest discover -s tests -v
```

Тесты проверяют параметры CLI, обработку метаданных PyPI, глубину обхода,
циклы, обратные зависимости и визуализацию. Сетевые ответы подменяются
локальными данными, поэтому для запуска тестов подключение к PyPI не нужно.
