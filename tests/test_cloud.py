"""Tests for xiao.core.cloud module — TokenExpiredError retry logic."""

from unittest.mock import MagicMock, patch

import pytest

from xiao.core.cloud import (
    TokenExpiredError,
    cloud_get_properties,
)


@pytest.fixture
def mock_cloud():
    cloud = MagicMock()
    cloud.ssecurity = "test_ssecurity"
    cloud.user_id = "123"
    cloud.service_token = "test_token"
    cloud.username = "test@test.com"
    cloud.password = "testpass"
    return cloud


class TestTokenExpiredRetry:
    def test_retry_on_token_expired(self, mock_cloud):
        """cloud_get_properties retries once on TokenExpiredError."""
        call_count = 0

        def mock_signed_request(url, params):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise TokenExpiredError("expired")
            return '{"result": [{"siid": 2, "piid": 1, "code": 0, "value": 5}]}'

        mock_cloud._signed_request = mock_signed_request

        with patch("xiao.core.cloud._refresh_cloud_session", return_value=True):
            result = cloud_get_properties(mock_cloud, "did123", [{"siid": 2, "piid": 1}], country="us")

        assert call_count == 2
        assert result[0]["value"] == 5

    def test_no_retry_when_refresh_fails(self, mock_cloud):
        """If token refresh fails, the error propagates."""
        mock_cloud._signed_request = MagicMock(side_effect=TokenExpiredError("expired"))

        with (
            patch("xiao.core.cloud._refresh_cloud_session", return_value=False),
            pytest.raises(TokenExpiredError),
        ):
            cloud_get_properties(mock_cloud, "did123", [{"siid": 2, "piid": 1}], country="us")


class TestSimpleRequest:
    def test_simple_request_method_exists(self, mock_cloud):
        """_simple_request is a method on XiaomiCloud, not on TokenExpiredError."""
        from xiao.core.cloud import XiaomiCloud

        assert hasattr(XiaomiCloud, "_simple_request")
        # Ensure it's NOT a method of TokenExpiredError
        assert not hasattr(TokenExpiredError, "_simple_request")
