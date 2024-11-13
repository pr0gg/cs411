import pytest
import requests
from meal_max.utils.random_utils import get_random

RANDOM_DECIMAL = 0.42

@pytest.fixture
def mock_random_org(mocker):
    mock_response = mocker.Mock()
    mock_response.text = f"{RANDOM_DECIMAL}"
    mocker.patch("requests.get", return_value=mock_response)
    return mock_response


def test_get_random_success(mock_random_org):
    """Test successful retrieval of a random decimal number from random.org."""
    result = get_random()

    # Assert that the result matches the mocked random decimal
    assert result == RANDOM_DECIMAL, f"Expected random number {RANDOM_DECIMAL}, but got {result}"

    # Verify that the request URL was called correctly
    requests.get.assert_called_once_with(
        "https://www.random.org/decimal-fractions/?num=1&dec=2&col=1&format=plain&rnd=new", timeout=5
    )


def test_get_random_request_failure(mocker):
    """Test that a RuntimeError is raised when the request fails."""
    mocker.patch("requests.get", side_effect=requests.exceptions.RequestException("Connection error"))

    with pytest.raises(RuntimeError, match="Request to random.org failed: Connection error"):
        get_random()


def test_get_random_timeout(mocker):
    """Test that a RuntimeError is raised when the request times out."""
    mocker.patch("requests.get", side_effect=requests.exceptions.Timeout)

    with pytest.raises(RuntimeError, match="Request to random.org timed out."):
        get_random()


def test_get_random_invalid_response(mock_random_org):
    """Test that a ValueError is raised when the response is invalid (non-decimal)."""
    mock_random_org.text = "invalid_response"

    with pytest.raises(ValueError, match="Invalid response from random.org: invalid_response"):
        get_random()
