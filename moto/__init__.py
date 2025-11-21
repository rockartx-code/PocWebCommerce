from contextlib import contextmanager


@contextmanager
def mock_dynamodb():
    yield
