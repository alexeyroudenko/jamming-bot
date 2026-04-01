import json


def _safe_string(value):
    if value is None:
        return ""
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def _write_payload_to_table(table_op, payload):
    table_op.clear()
    table_op.appendRow(["key", "value"])

    if not isinstance(payload, dict):
        table_op.appendRow(["data", _safe_string(payload)])
        return

    for key, value in payload.items():
        table_op.appendRow([str(key), _safe_string(value)])


def onReceiveOSC(dat, rowIndex, message, bytes, timeStamp, address, args, peer):
    if address != "/jb/event" or not args:
        return

    raw_json = args[0]

    try:
        payload = json.loads(raw_json)
    except Exception as exc:
        debug_table = op("jb_debug")
        if debug_table:
            debug_table.clear()
            debug_table.appendRow(["status", "json_error"])
            debug_table.appendRow(["error", str(exc)])
            debug_table.appendRow(["raw", _safe_string(raw_json)])
        return

    event_name = payload.get("event", "")
    event_data = payload.get("data", {})

    debug_table = op("jb_debug")
    if debug_table:
        debug_table.clear()
        debug_table.appendRow(["field", "value"])
        debug_table.appendRow(["event", _safe_string(event_name)])
        debug_table.appendRow(["timestamp", _safe_string(payload.get("timestamp"))])
        debug_table.appendRow(["raw", _safe_string(raw_json)])

    event_table = op("jb_event")
    if event_table:
        _write_payload_to_table(event_table, payload)

    data_table = op("jb_data")
    if data_table:
        _write_payload_to_table(data_table, event_data)
