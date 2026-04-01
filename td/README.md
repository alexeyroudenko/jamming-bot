## TouchDesigner bridge

В этой папке лежит простой внешний bridge для `Jamming Bot`:

- читает `Socket.IO` события с `https://jamming-bot.arthew0.online`
- пересылает их в `TouchDesigner` по `OSC`
- не требует ставить `python-socketio` внутрь embedded Python самого TD

### Файлы

- `socketio_to_osc.py` - bridge `Socket.IO -> OSC`
- `requirements.txt` - Python-зависимости для внешнего запуска
- `td_osc_event_handler.py` - пример `Text DAT` callback для приема `/jb/event`

### Зачем так

Сайт использует не raw websocket, а `Socket.IO`, поэтому обычный `WebSocket DAT` в `TouchDesigner` обычно не подходит напрямую. Внешний Python-процесс снимает эту проблему и отдает в TD уже обычный `OSC`.

### Установка

Создай отдельное окружение Python вне TouchDesigner и установи зависимости:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r td/requirements.txt
```

На Windows:

```bat
py -m venv .venv
.venv\Scripts\activate
pip install -r td\requirements.txt
```

### Запуск

По умолчанию bridge:

- подключается к `https://jamming-bot.arthew0.online`
- использует путь `'/socket.io'`
- шлет OSC на `127.0.0.1:7000`

```bash
python td/socketio_to_osc.py
```

Если нужен другой OSC-порт:

```bash
python td/socketio_to_osc.py --osc-port 5006
```

Если нужна авторизация через cookie:

```bash
python td/socketio_to_osc.py --cookie "session=PUT_YOUR_SESSION_COOKIE_HERE"
```

Если сайт окажется за префиксом `/app`, можно явно задать путь:

```bash
python td/socketio_to_osc.py --socketio-path /app/socket.io
```

### Какие события слушаются

По умолчанию bridge подписывается на:

- `step`
- `analyzed`
- `screenshot`
- `image_analyzed`
- `event`
- `sublink`
- `set_values`
- `clear`
- `my_pong`

Можно ограничить список:

```bash
python td/socketio_to_osc.py --event step --event analyzed
```

### Что прилетает в TouchDesigner

Bridge отправляет OSC-сообщения:

- `/jb/event` - JSON целиком
- `/jb/event_name` - имя события
- `/jb/step/number` - номер шага, если есть
- `/jb/step/url` - URL шага, если есть
- `/jb/step/src_url` - source URL, если есть
- `/jb/analyzed/words_count` - `words_count`, если есть
- `/jb/sublink/url` - URL саблинка
- `/jb/clear` - `1` при событии `clear`

Самое удобное в TD:

1. Создать `OSC In DAT` или `OSC In CHOP`
2. Поставить порт `7000` или тот, который передан через `--osc-port`
3. Читать `/jb/event` как JSON и разбирать дальше уже внутри сети TD

### Пример

```bash
python td/socketio_to_osc.py --osc-host 127.0.0.1 --osc-port 7000 --event step --event analyzed
```

### Минимальная сеть в TouchDesigner

Собери такой минимальный набор операторов:

1. `OSC In DAT` на порту `7000`
2. `Table DAT` с именем `jb_debug`
3. `Table DAT` с именем `jb_event`
4. `Table DAT` с именем `jb_data`
5. `DAT Execute` или callback в `OSC In DAT`, куда вставить код из `td_osc_event_handler.py`

Логика такая:

- `OSC In DAT` принимает `/jb/event`
- callback разбирает JSON из первого аргумента
- `jb_event` получает весь envelope события
- `jb_data` получает только поле `data`
- `jb_debug` хранит последнее сырое сообщение и статус разбора

Если хочешь просто быстро проверить поток, достаточно смотреть таблицу `jb_debug`.

### Примечания

- Если поток на сайте доступен только после логина, понадобится `session` cookie.
- Если соединение не поднимается, сначала попробуй `--socketio-path /socket.io`, потом `--socketio-path /app/socket.io`.
- Для `TouchDesigner Build 2025` этот вариант обычно проще и стабильнее, чем установка `socketio` прямо во встроенный Python TD.
