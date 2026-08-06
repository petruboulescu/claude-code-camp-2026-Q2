import json
import ssl
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .errors import ApiError


class Client:
    """Send a PromptBuilder payload and return the provider's raw JSON."""

    RETRYABLE_STATUS_CODES = frozenset({408, 409, 429, 500, 502, 503, 504})
    TRANSIENT_ERRORS = (
        EOFError,
        ConnectionError,
        TimeoutError,
        ssl.SSLError,
        URLError,
    )
    MAX_RETRIES = 3
    BASE_RETRY_DELAY = 0.5

    def __init__(self, builder):
        self.builder = builder

    def call(self, max_output_tokens=1024, tools=None):
        request = Request(
            self.builder.url,
            data=json.dumps(
                self.builder.to_api_payload(
                    max_output_tokens=max_output_tokens,
                    tools=tools,
                )
            ).encode("utf-8"),
            headers=self.builder.headers,
            method="POST",
        )

        attempts = 0

        while True:
            attempts += 1

            try:
                with urlopen(request) as response:
                    body = response.read()
                    status = response.status
            except HTTPError as error:
                if self._retryable_status(error.code) and attempts <= self.MAX_RETRIES:
                    error.close()
                    self._sleep(attempts)
                    continue

                body = error.read().decode("utf-8", errors="replace")
                error.close()
                raise ApiError(
                    self._http_error_message(attempts, error.code, body)
                ) from error
            except self.TRANSIENT_ERRORS as error:
                if attempts > self.MAX_RETRIES:
                    raise ApiError(
                        "API request failed after "
                        f"{attempts} attempts: {type(error).__name__}: {error}"
                    ) from error

                self._sleep(attempts)
                continue

            if not 200 <= status < 300:
                text = body.decode("utf-8", errors="replace")
                if self._retryable_status(status) and attempts <= self.MAX_RETRIES:
                    self._sleep(attempts)
                    continue

                raise ApiError(self._http_error_message(attempts, status, text))

            return json.loads(body.decode("utf-8"))

    @classmethod
    def _retryable_status(cls, status):
        return status in cls.RETRYABLE_STATUS_CODES

    @classmethod
    def _retry_delay(cls, attempt):
        return cls.BASE_RETRY_DELAY * (2 ** (attempt - 1))

    def _sleep(self, attempt):
        time.sleep(self._retry_delay(attempt))

    @staticmethod
    def _http_error_message(attempts, status, body):
        if status == 401:
            return "authentication failed (401) — check your API key"

        suffix = "" if attempts == 1 else "s"
        return (
            f"API request failed after {attempts} attempt{suffix} "
            f"({status}): {body}"
        )
