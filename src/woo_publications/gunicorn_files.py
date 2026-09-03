import json
import logging
from datetime import datetime

from gunicorn.glogging import Logger

class JsonFormatter(logging.Formatter):
    def format(self, record):
        payload = {
            "source": "gunicorn",
            "type": "server",
            "level": record.levelname,
            "logger": record.name,
            "process": record.process,
            "thread": record.thread,
        }

        if record.name != "gunicorn.access":
            payload["message"] = record.getMessage()

        if isinstance(record.args, dict):
            args = record.args
            dt = datetime.strptime(
                args["t"], "[%d/%b/%Y:%H:%M:%S %z]"
            )

            payload |= {
                "event": "request",
                "status": int(args["s"]),
                "method": args["m"],
                "path": args["U"],
                "query": args["q"],
                "bytes": args["b"],
                "host": args["h"],
                "timestamp": dt.strftime("%Y-%m-%dT%H:%M:%S%z"),
                "duration_ms": args["M"],
            }

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


class JsonGunicornLogger(Logger):
    def setup(self, cfg):
        super().setup(cfg)

        json_formatter = JsonFormatter()

        for handler in self.access_log.handlers:
            handler.setFormatter(json_formatter)

        for handler in self.error_log.handlers:
            handler.setFormatter(json_formatter)
