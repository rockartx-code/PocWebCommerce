class ClientError(Exception):
    """Simple stub matching boto3 ClientError signature used in tests."""

    def __init__(self, error_response=None, operation_name: str | None = None):
        super().__init__(operation_name or "ClientError")
        self.response = error_response or {}
        self.operation_name = operation_name
