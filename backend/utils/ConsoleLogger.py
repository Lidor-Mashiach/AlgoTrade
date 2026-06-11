from datetime import datetime


class ConsoleLogger:
    COLORS = {
        "INFO": "\033[36m",       # Cyan
        "OK": "\033[32m",         # Green
        "WARNING": "\033[33m",    # Yellow
        "ERROR": "\033[31m",      # Red
        "DEBUG": "\033[90m",      # Gray
    }

    RESET = "\033[0m"

    def __init__(self, width=70, use_colors=True, show_time=True):
        self.width = width
        self.use_colors = use_colors
        self.show_time = show_time

    def _timestamp(self):
        return datetime.now().strftime("%H:%M:%S")

    def _format_label(self, level):
        label = f"[{level}]"

        if not self.use_colors:
            return label

        color = self.COLORS.get(level, "")
        return f"{color}{label}{self.RESET}"

    def _format_timestamp(self, level):
        if not self.show_time:
            return ""

        timestamp = f"[{self._timestamp()}]"

        if not self.use_colors:
            return f"{timestamp} "

        color = self.COLORS.get(level, "")
        return f"{color}{timestamp}{self.RESET} "

    def _log(self, level, message):
        timestamp = self._format_timestamp(level)
        label = self._format_label(level)

        print(f"{timestamp}{label} {message}")

    def section(self, title):
        print()
        print(f" {title} ".center(self.width, "="))
        print()

    def subsection(self, title):
        print()
        print(f" {title} ".center(self.width, "-"))
        print()

    def info(self, message):
        self._log("INFO", message)

    def success(self, message):
        self._log("OK", message)

    def warning(self, message):
        self._log("WARNING", message)

    def error(self, message):
        self._log("ERROR", message)

    def debug(self, message):
        self._log("DEBUG", message)