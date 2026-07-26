import unittest
from unittest.mock import patch
from urllib.error import HTTPError

from boukensha import ApiError, Client


class FakeBuilder:
    url = "https://example.invalid"
    headers = {}

    @staticmethod
    def to_api_payload(**kwargs):
        return {}


class ClientAuthenticationTest(unittest.TestCase):
    def test_http_401_has_specific_message_and_is_not_retried(self):
        error = HTTPError(
            FakeBuilder.url,
            401,
            "Unauthorized",
            {},
            None,
        )
        error.read = lambda: b'{"error":"bad key"}'
        error.close = lambda: None

        with patch("boukensha.client.urlopen", side_effect=error) as request:
            with self.assertRaisesRegex(
                ApiError,
                r"^authentication failed \(401\) — check your API key$",
            ):
                Client(FakeBuilder()).call()

        request.assert_called_once()

    def test_other_http_errors_keep_the_existing_message(self):
        self.assertEqual(
            Client._http_error_message(2, 400, "bad request"),
            "API request failed after 2 attempts (400): bad request",
        )


if __name__ == "__main__":
    unittest.main()
