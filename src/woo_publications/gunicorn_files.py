import json
import logging  # noqa: TID251
from datetime import datetime

from gunicorn.glogging import Logger


class AccessLogFormatter(logging.Formatter):
    def format(self, record) -> str:
        args = record.args

        if not isinstance(args, dict):
            return ""

        assert isinstance(args["t"], str)
        dt = datetime.strptime(args["t"], "[%d/%b/%Y:%H:%M:%S %z]")

        payload = {
            "source": "gunicorn",
            "event": "request",
            "level": record.levelname,
            "logger": record.name,
            "process": record.process,
            "thread": record.thread,
            "method": args["m"],
            "path": args["U"],
            "duration_in_ms": args["M"],
            "status": args["s"],
            "bytes": args["b"],
            "query": args["q"],
            "referer": args["{referer}i"],
            "host": args["{host}i"],
            "timestamp": dt.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "remote_ip": "{http_x_forwarded_for}e",
            "message": record.getMessage(),
        }

        return json.dumps(payload, default=str)


class ErrorLogFormatter(logging.Formatter):
    def format(self, record) -> str:
        payload = {
            "source": "gunicorn",
            "type": "server",
            "level": record.levelname,
            "logger": record.name,
            "process": record.process,
            "thread": record.thread,
            "timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%S%z"),
            "message": record.getMessage(),
        }

        return json.dumps(payload, default=str)


class JsonGunicornLogger(Logger):
    def setup(self, cfg):
        super().setup(cfg)

        for handler in self.access_log.handlers:
            handler.setFormatter(AccessLogFormatter())

        for handler in self.error_log.handlers:
            handler.setFormatter(ErrorLogFormatter())
