#!/usr/bin/env python3
import argparse
import json
import logging
import signal
import sys
import threading
import time
from typing import Any

import socketio
from pythonosc.udp_client import SimpleUDPClient


DEFAULT_EVENTS = [
    "step",
    "analyzed",
    "screenshot",
    "image_analyzed",
    "event",
    "sublink",
    "set_values",
    "clear",
    "my_pong",
]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Bridge Jamming Bot Socket.IO events to OSC for TouchDesigner."
    )
    parser.add_argument(
        "--server",
        default="https://jamming-bot.arthew0.online",
        help="Socket.IO server base URL",
    )
    parser.add_argument(
        "--socketio-path",
        default="/socket.io",
        help="Socket.IO path on the server",
    )
    parser.add_argument(
        "--osc-host",
        default="127.0.0.1",
        help="OSC target host",
    )
    parser.add_argument(
        "--osc-port",
        type=int,
        default=7000,
        help="OSC target port",
    )
    parser.add_argument(
        "--event",
        dest="events",
        action="append",
        default=[],
        help="Event to subscribe to; repeat flag to add more",
    )
    parser.add_argument(
        "--cookie",
        action="append",
        default=[],
        help='Cookie header entry, e.g. "session=abc123"',
    )
    parser.add_argument(
        "--transports",
        nargs="+",
        default=["polling", "websocket"],
        help="Engine.IO transports to allow",
    )
    parser.add_argument(
        "--ping-interval",
        type=float,
        default=5.0,
        help="Seconds between my_ping emits; 0 disables it",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable debug logging",
    )
    return parser


def make_payload(event_name: str, data: Any) -> dict[str, Any]:
    return {
        "event": event_name,
        "timestamp": time.time(),
        "data": data,
    }


def send_osc_bundle(client: SimpleUDPClient, event_name: str, data: Any) -> None:
    payload = make_payload(event_name, data)
    payload_json = json.dumps(payload, ensure_ascii=False, default=str)

    client.send_message("/jb/event", payload_json)
    client.send_message("/jb/event_name", event_name)

    if isinstance(data, dict):
        if "step" in data:
            client.send_message("/jb/step/number", str(data["step"]))
        if "url" in data:
            client.send_message("/jb/step/url", str(data["url"]))
        if "src_url" in data:
            client.send_message("/jb/step/src_url", str(data["src_url"]))
        if "words_count" in data:
            client.send_message("/jb/analyzed/words_count", float(data["words_count"]))
        if "url" in data and event_name == "sublink":
            client.send_message("/jb/sublink/url", str(data["url"]))

    if event_name == "clear":
        client.send_message("/jb/clear", 1)


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    events = args.events or list(DEFAULT_EVENTS)
    osc = SimpleUDPClient(args.osc_host, args.osc_port)
    sio = socketio.Client(
        logger=args.verbose,
        engineio_logger=args.verbose,
        reconnection=True,
        reconnection_attempts=0,
    )

    stop_event = threading.Event()

    @sio.event
    def connect() -> None:
        logging.info("Socket.IO connected")

    @sio.event
    def disconnect() -> None:
        logging.warning("Socket.IO disconnected")

    def register_handler(event_name: str) -> None:
        @sio.on(event_name)
        def _handler(data: Any = None) -> None:
            logging.info("event=%s", event_name)
            send_osc_bundle(osc, event_name, data)

    for event_name in events:
        register_handler(event_name)

    def ping_loop() -> None:
        while not stop_event.is_set():
            if args.ping_interval > 0 and sio.connected:
                try:
                    sio.emit("my_ping")
                except Exception:
                    logging.exception("my_ping emit failed")
            stop_event.wait(args.ping_interval if args.ping_interval > 0 else 1.0)

    ping_thread = threading.Thread(target=ping_loop, daemon=True)
    ping_thread.start()

    headers = {}
    if args.cookie:
        headers["Cookie"] = "; ".join(args.cookie)

    def _shutdown(*_args: Any) -> None:
        stop_event.set()
        try:
            sio.disconnect()
        finally:
            raise SystemExit(0)

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    logging.info(
        "Connecting to %s path=%s -> OSC %s:%s",
        args.server,
        args.socketio_path,
        args.osc_host,
        args.osc_port,
    )

    sio.connect(
        args.server,
        socketio_path=args.socketio_path.lstrip("/"),
        transports=args.transports,
        headers=headers or None,
    )
    sio.wait()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(0)
