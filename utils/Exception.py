class AutoChatGPTInternalError(Exception):
    def __init__(self, message: str):
        self.message = message
        self.tag = "[AutoChatGPT]"
        super().__init__(message)

    def __str__(self):
        return f"{self.tag} {self.message}"