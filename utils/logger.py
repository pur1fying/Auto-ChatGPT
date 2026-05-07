import sys
import logging

from datetime import datetime
from typing import Union

from rich.console import Console
from rich.markup import escape

console = Console()

class Logger:
    """
    Logger class for logging
    """

    def __init__(self, logger_signal):
        """
        :param logger_signal: Logger signal broadcasts log level and log message
        """
        # Init logger signal, logs and logger,
        # logger signal is used to output log to logger box or other output
        self.logs = ""
        self.logger_signal = logger_signal
        if not self.logger_signal:
            # if the logger signal is not configured, we use rich traceback then
            # to better display error messages in console
            from rich.traceback import install
            install(show_locals=True)
        self.logger = logging.getLogger("Auto-ChatGPT_Logger")
        formatter = logging.Formatter("%(levelname)8s |%(asctime)20s | %(message)s ")
        handler1 = logging.StreamHandler(stream=sys.stdout)
        handler1.setFormatter(formatter)
        self.logger.setLevel(logging.INFO)
        self.logger.addHandler(handler1)

    def __out__(self, message: str, level: int = 1, raw_print=False) -> None:
        """
        Output log
        :param message: log message
        :param level: log level(1: INFO, 2: WARNING, 3: ERROR, 4: CRITICAL)
        :return: None
        """
        # If raw_print is True, output log to logger box
        if level < 1 or level > 4:
            raise ValueError("Invalid log level")

        if raw_print:
            self.logs += message
            if self.logger_signal:
                self.logger_signal.emit(level, message)
            return

        while len(logging.root.handlers) > 0:
            logging.root.handlers.pop()

        levels_str = ["INFO", "WARNING", "ERROR", "CRITICAL"]
        # If logger signal is not None, output log to logger signal
        # else output log to console
        levels_color = ["#2d8cf0", "#ff9900", "#ed3f14", "#3e0480"]
        if self.logger_signal is not None:
            self.logs += f"{levels_str[level - 1]} | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | {message}"
            self.logger_signal.emit(level, message)
        else:
            console.print(f'[{levels_color[level - 1]}]'
                          f'{levels_str[level - 1]} |'
                          f' {datetime.now().strftime("%Y-%m-%d %H:%M:%S")} |'
                          f' {escape(message)}[/]', soft_wrap=True)

    def info(self, message: str) -> None:
        """
        :param message: log message

        Output info log
        """
        self.__out__(message, 1)

    def warning(self, message: str) -> None:
        """
        :param message: log message

        Output warn log
        """
        self.__out__(message, 2)

    def error(self, message: Union[str, Exception]) -> None:
        """
        :param message: log message or Exception object

        Output error log
        """
        if isinstance(message, BaseException):
            exc_message = str(message)
            formatted_message = f"{type(message).__name__}: {exc_message}" if exc_message else type(message).__name__
            self.__out__(formatted_message, 3)
            return

        self.__out__(message, 3)

    def critical(self, message: str) -> None:
        """
        :param message: log message

        Output critical log
        """
        self.__out__(message, 4)

    def line(self) -> None:
        """
        Output line
        """
        # While the line print do not need wrapping, we
        # use raw_print=True to output log to logger box
        self.__out__(
            '<div style="font-family: Consolas, monospace;color:#2d8cf0;">--------------'
            '-------------------------------------------------------------'
            '-------------------</div>', raw_print=True)


logger = Logger(None)