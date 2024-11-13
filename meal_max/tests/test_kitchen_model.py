from contextlib import contextmanager
import re
import sqlite3

import pytest

from meal_max.models.kitchen_model import (
    Meal,
    create_meal,
    clear_meals,
    delete_meal,
    get_leaderboard,
    get_meal_by_id,
    get_meal_by_name,
    update_meal_stats
)

######################################################
#
#    Fixtures
#
######################################################

def normalize_whitespace(sql_query: str) -> str:
    return re.sub(r'\s+', ' ', sql_query).strip()

# Mocking the database connection for tests
@pytest.fixture
def mock_cursor(mocker):
    mock_conn = mocker.Mock()
    mock_cursor = mocker.Mock()

    # Mock the connection's cursor
    mock_conn.cursor.return_value = mock_cursor
    mock_cursor.fetchone.return_value = None  # Default return for queries
    mock_cursor.fetchall.return_value = []
    mock_conn.commit.return_value = None

    # Mock the get_db_connection context manager from sql_utils
    @contextmanager
    def mock_get_db_connection():
        yield mock_conn  # Yield the mocked connection object

    mocker.patch("meal_max.models.kitchen_model.get_db_connection", mock_get_db_connection)

    return mock_cursor  # Return the mock cursor so we can set expectations per test

######################################################
#
#    Add and delete
#
######################################################

def test_create_meal(mock_cursor):
    """Test creating a new meal in the catalog."""

    # Call the function to create a new song
    create_meal(meal="Test Dinner", cuisine="Imaginary", price=5.0, difficulty="LOW")

    expected_query = normalize_whitespace("""
        INSERT INTO meals (meal, cuisine, price, difficulty)
        VALUES (?, ?, ?, ?)
    """)

    actual_query = normalize_whitespace(mock_cursor.execute.call_args[0][0])

    # Assert that the SQL query was correct
    assert actual_query == expected_query, "The SQL query did not match the expected structure."

    # Extract the arguments used in the SQL call (second element of call_args)
    actual_arguments = mock_cursor.execute.call_args[0][1]

    # Assert that the SQL query was executed with the correct arguments
    expected_arguments = ("Test Dinner", "Imaginary", 5.0, "LOW")
    assert actual_arguments == expected_arguments, f"The SQL query arguments did not match. Expected {expected_arguments}, got {actual_arguments}."


def test_create_meal_duplicate(mock_cursor):
    """Test creating a meal with a duplicate meal name (should raise an error)."""

    # Simulate that the database will raise an IntegrityError due to a duplicate entry
    mock_cursor.execute.side_effect = sqlite3.IntegrityError("UNIQUE constraint failed: meals.meal")

    # Expect the function to raise a ValueError with a specific message when handling the IntegrityError
    with pytest.raises(ValueError, match="Meal with name 'Test Dinner' already exists"):
        create_meal(meal="Test Dinner", cuisine="Imaginary", price=5.0, difficulty="LOW")


def test_create_meal_invalid_price():
    """Test error when trying to create a meal with an invalid price (e.g., negative price)"""

    # Attempt to create a meal with a negative price
    with pytest.raises(ValueError, match="Invalid price: -5.0. Price must be a positive number."):
        create_meal(meal="Test Dinner", cuisine="Imaginary", price=-5.0, difficulty="LOW")

    # Attempt to create a meal with a non-float price
    with pytest.raises(ValueError, match="Invalid price: invalid. Price must be a positive number."):
        create_meal(meal="Test Dinner", cuisine="Imaginary", price="invalid", difficulty="LOW")


def test_create_meal_invalid_difficulty():
    """Test error when trying to create a meal with an invalid difficulty (e.g., integer or unexpected string)."""

    # Attempt to create a meal with a difficulty of 1
    with pytest.raises(ValueError, match="Invalid difficulty level: 1. Must be 'LOW', 'MED', or 'HIGH'."):
        create_meal(meal="Test Dinner", cuisine="Imaginary", price=5.0, difficulty=1)

    # Attempt to create a meal with a difficulty of "SUPER"
    with pytest.raises(ValueError, match="Invalid difficulty level: SUPER. Must be 'LOW', 'MED', or 'HIGH'."):
        create_meal(meal="Test Dinner", cuisine="Imaginary", price=5.0, difficulty="SUPER")


def test_delete_meal(mock_cursor):
    """Test soft deleting a meal from the list by meal ID."""

    # Simulate that the meal exists (id = 1)
    mock_cursor.fetchone.return_value = ([False])

    # Call the delete_song function
    delete_meal(1)

    # Normalize the SQL for both queries (SELECT and UPDATE)
    expected_select_sql = normalize_whitespace("SELECT deleted FROM meals WHERE id = ?")
    expected_update_sql = normalize_whitespace("UPDATE meals SET deleted = TRUE WHERE id = ?")

    # Access both calls to `execute()` using `call_args_list`
    actual_select_sql = normalize_whitespace(mock_cursor.execute.call_args_list[0][0][0])
    actual_update_sql = normalize_whitespace(mock_cursor.execute.call_args_list[1][0][0])

    # Ensure the correct SQL queries were executed
    assert actual_select_sql == expected_select_sql, "The SELECT query did not match the expected structure."
    assert actual_update_sql == expected_update_sql, "The UPDATE query did not match the expected structure."

    # Ensure the correct arguments were used in both SQL queries
    expected_select_args = (1,)
    expected_update_args = (1,)

    actual_select_args = mock_cursor.execute.call_args_list[0][0][1]
    actual_update_args = mock_cursor.execute.call_args_list[1][0][1]

    assert actual_select_args == expected_select_args, f"The SELECT query arguments did not match. Expected {expected_select_args}, got {actual_select_args}."
    assert actual_update_args == expected_update_args, f"The UPDATE query arguments did not match. Expected {expected_update_args}, got {actual_update_args}."


def test_delete_meal_bad_id(mock_cursor):
    """Test error when trying to delete a non-existent meal."""

    # Simulate that no song exists with the given ID
    mock_cursor.fetchone.return_value = None

    # Expect a ValueError when attempting to delete a non-existent song
    with pytest.raises(ValueError, match="Meal with ID 999 not found"):
        delete_meal(999)


def test_delete_meal_already_deleted(mock_cursor):
    """Test error when trying to delete a meal that's already marked as deleted."""

    # Simulate that the song exists but is already marked as deleted
    mock_cursor.fetchone.return_value = ([True])

    # Expect a ValueError when attempting to delete a song that's already been deleted
    with pytest.raises(ValueError, match="Meal with ID 999 has been deleted"):
        delete_meal(999)


def test_clear_meals(mock_cursor, mocker):
    """Test clearing the entire meals list (removes all meals)."""

    # Mock the file reading
    mocker.patch.dict('os.environ', {'SQL_CREATE_TABLE_PATH': 'sql/create_meal_table.sql'})
    mock_open = mocker.patch('builtins.open', mocker.mock_open(read_data="The body of the create statement"))

    # Call the clear_database function
    clear_meals()

    # Ensure the file was opened using the environment variable's path
    mock_open.assert_called_once_with('sql/create_meal_table.sql', 'r')

    # Verify that the correct SQL script was executed
    mock_cursor.executescript.assert_called_once()

######################################################
#
#    Get Leaderboard
#
######################################################

def test_get_leaderboard_wins(mock_cursor):
    """Test getting the leaderboard by wins."""
    # Simulate that there are multiple meals in the database
    mock_cursor.fetchall.return_value = [
        (1, "Test Dinner", "Imaginary", 5.0, "LOW", 8, 6, 0.75),
        (2, "Test Lunch", "Imaginary", 7.5, "HIGH", 2, 2, 1.0),
        (3, "Test Breakfast", "Imaginary", 3.0, "MED", 4, 1, 0.25)
    ]

    # Run the function with sort_by="wins"
    leaderboard = get_leaderboard(sort_by="wins")

    # Check the order based on 'wins'
    assert leaderboard[0]['meal'] == "Test Dinner"
    assert leaderboard[1]['meal'] == "Test Lunch"
    assert leaderboard[2]['meal'] == "Test Breakfast"


def test_get_leaderboard_wins_pct(mock_cursor):
    """Test getting the leaderboard by win percentage."""
    mock_cursor.fetchall.return_value = [
        (1, "Test Dinner", "Imaginary", 5.0, "LOW", 8, 6, 75.0),
        (2, "Test Lunch", "Imaginary", 7.5, "HIGH", 10, 5, 50.0),
        (3, "Test Breakfast", "Imaginary", 3.0, "MED", 4, 1, 25.0)
    ]

    # Run the function with sort_by="wins"
    leaderboard = get_leaderboard(sort_by="win_pct")

    # Check the order based on 'wins'
    assert leaderboard[0]['meal'] == "Test Dinner"
    assert leaderboard[1]['meal'] == "Test Lunch"
    assert leaderboard[2]['meal'] == "Test Breakfast"


def test_get_leaderboard_invalid_param():
    """Test error when trying to get leaderboard on an invalid sort (e.g., unexpected string)."""

    # Attempt to get leaderboard sorted by losses
    with pytest.raises(ValueError, match="Invalid sort_by parameter: loss"):
        get_leaderboard(sort_by="loss")

######################################################
#
#    Get Meal
#
######################################################

def test_get_meal_by_id(mock_cursor):
    # Simulate that the meal exists (id = 1)
    mock_cursor.fetchone.return_value = (1, "Test Dinner", "Imaginary", 5.0, "LOW", False)

    # Call the function and check the result
    result = get_meal_by_id(1)

    # Expected result based on the simulated fetchone return value
    expected_result = Meal(1, "Test Dinner", "Imaginary", 5.0, "LOW")

    # Ensure the result matches the expected output
    assert result == expected_result, f"Expected {expected_result}, got {result}"

    # Ensure the SQL query was executed correctly
    expected_query = normalize_whitespace("SELECT id, meal, cuisine, price, difficulty, deleted FROM meals WHERE id = ?")
    actual_query = normalize_whitespace(mock_cursor.execute.call_args[0][0])

    # Assert that the SQL query was correct
    assert actual_query == expected_query, "The SQL query did not match the expected structure."

    # Extract the arguments used in the SQL call
    actual_arguments = mock_cursor.execute.call_args[0][1]

    # Assert that the SQL query was executed with the correct arguments
    expected_arguments = (1,)
    assert actual_arguments == expected_arguments, f"The SQL query arguments did not match. Expected {expected_arguments}, got {actual_arguments}."


def test_get_meal_by_id_bad_id(mock_cursor):
    # Simulate that no meal exists for the given ID
    mock_cursor.fetchone.return_value = None

    # Expect a ValueError when the song is not found
    with pytest.raises(ValueError, match="Meal with ID 999 not found"):
        get_meal_by_id(999)


def test_get_meal_by_name(mock_cursor):
    # Simulate that the meal exists (meal = "Test Dinner")
    mock_cursor.fetchone.return_value = (1, "Test Dinner", "Imaginary", 5.0, "LOW", False)

    # Call the function and check the result
    result = get_meal_by_name("Test Dinner")

    # Expected result based on the simulated fetchone return value
    expected_result = Meal(1, "Test Dinner", "Imaginary", 5.0, "LOW")

    # Ensure the result matches the expected output
    assert result == expected_result, f"Expected {expected_result}, got {result}"

    # Ensure the SQL query was executed correctly
    expected_query = normalize_whitespace("SELECT id, meal, cuisine, price, difficulty, deleted FROM meals WHERE meal = ?")
    actual_query = normalize_whitespace(mock_cursor.execute.call_args[0][0])

    # Assert that the SQL query was correct
    assert actual_query == expected_query, "The SQL query did not match the expected structure."

    # Extract the arguments used in the SQL call
    actual_arguments = mock_cursor.execute.call_args[0][1]

    # Assert that the SQL query was executed with the correct arguments
    expected_arguments = ("Test Dinner",)
    assert actual_arguments == expected_arguments, f"The SQL query arguments did not match. Expected {expected_arguments}, got {actual_arguments}."


def test_update_meal_stats_win(mock_cursor):
    """Test updating the win count of a meal on a win."""

    # Simulate that the meal exists and is not deleted (id = 1)
    mock_cursor.fetchone.return_value = [False]

    # Call the update_meal_stats function with a sample meal ID
    meal_id = 1
    result = "win"
    update_meal_stats(meal_id, result)

    # Normalize the expected SQL query
    expected_query = normalize_whitespace("""
        UPDATE meals SET battles = battles + 1, wins = wins + 1 WHERE id = ?
    """)

    # Ensure the SQL query was executed correctly
    actual_query = normalize_whitespace(mock_cursor.execute.call_args_list[1][0][0])

    # Assert that the SQL query was correct
    assert actual_query == expected_query, "The SQL query did not match the expected structure."

    # Extract the arguments used in the SQL call
    actual_arguments = mock_cursor.execute.call_args_list[1][0][1]

    # Assert that the SQL query was executed with the correct arguments (song ID)
    expected_arguments = (meal_id,)
    assert actual_arguments == expected_arguments, f"The SQL query arguments did not match. Expected {expected_arguments}, got {actual_arguments}."


def test_update_meal_stats_loss(mock_cursor):
    """Test updating the win count of a meal on a loss."""

    # Simulate that the meal exists and is not deleted (id = 1)
    mock_cursor.fetchone.return_value = [False]

    # Call the update_meal_stats function with a sample meal ID
    meal_id = 1
    result = "loss"
    update_meal_stats(meal_id, result)

    # Normalize the expected SQL query
    expected_query = normalize_whitespace("""
        UPDATE meals SET battles = battles + 1 WHERE id = ?
    """)

    # Ensure the SQL query was executed correctly
    actual_query = normalize_whitespace(mock_cursor.execute.call_args_list[1][0][0])

    # Assert that the SQL query was correct
    assert actual_query == expected_query, "The SQL query did not match the expected structure."

    # Extract the arguments used in the SQL call
    actual_arguments = mock_cursor.execute.call_args_list[1][0][1]

    # Assert that the SQL query was executed with the correct arguments (song ID)
    expected_arguments = (meal_id,)
    assert actual_arguments == expected_arguments, f"The SQL query arguments did not match. Expected {expected_arguments}, got {actual_arguments}."


def test_update_meal_stats_invalid_result(mock_cursor):
    """Test error when trying to update win count for a meal with invalid result"""
    
    # Simulate that the meal exists and is not deleted (id = 1)
    mock_cursor.fetchone.return_value = [False]

    # Call the update_meal_stats function with a sample meal ID with invalid result
    meal_id = 1
    result = "tie"

    # Attempt to update a meal with a result of tie
    with pytest.raises(ValueError, match="Invalid result: tie. Expected 'win' or 'loss'."):
        update_meal_stats(meal_id, result)


### Test for Updating a Deleted Song:
def test_update_meal_stats_deleted_meal(mock_cursor):
    """Test error when trying to update win count for a deleted meal."""

    # Simulate that the meal exists but is marked as deleted (id = 1)
    mock_cursor.fetchone.return_value = [True]

    # Expect a ValueError when attempting to update a deleted song
    with pytest.raises(ValueError, match="Meal with ID 1 has been deleted"):
        update_meal_stats(1, "win")

    # Ensure that no SQL query for updating play count was executed
    mock_cursor.execute.assert_called_once_with("SELECT deleted FROM meals WHERE id = ?", (1,))
