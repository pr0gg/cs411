import pytest
from unittest.mock import MagicMock
from meal_max.models.battle_model import BattleModel
from meal_max.models.kitchen_model import Meal, update_meal_stats
from meal_max.utils.random_utils import get_random


@pytest.fixture
def battle_model():
    """Fixture to provide a new instance of BattleModel for each test."""
    return BattleModel()


@pytest.fixture
def sample_meal1():
    return Meal(id=1, meal="Pasta", price=10.99, cuisine="Italian", difficulty="MED")


@pytest.fixture
def sample_meal2():
    return Meal(id=2, meal="Hot pot", price=15.99, cuisine="Chinese", difficulty="HIGH")


@pytest.fixture
def mock_update_meal_stats(mocker):
    """Mock the update_meal_stats function for testing purposes."""
    return mocker.patch("meal_max.models.kitchen_model.update_meal_stats")


@pytest.fixture
def mock_get_random(mocker):
    """Mock the get_random function for testing purposes."""
    return mocker.patch("meal_max.utils.random_utils.get_random")


##################################################
# Combatant Management Test Cases
##################################################

def test_prep_combatant(battle_model, sample_meal1):
    """Test adding a single combatant to the battle model."""
    battle_model.prep_combatant(sample_meal1)
    assert len(battle_model.combatants) == 1
    assert battle_model.combatants[0].meal == "Pasta"


def test_prep_combatant_max_limit(battle_model, sample_meal1, sample_meal2):
    """Test that adding more than two combatants raises an error."""
    battle_model.prep_combatant(sample_meal1)
    battle_model.prep_combatant(sample_meal2)
    with pytest.raises(ValueError, match="Combatant list is full"):
        battle_model.prep_combatant(sample_meal1)


def test_clear_combatants(battle_model, sample_meal1):
    """Test clearing the list of combatants."""
    battle_model.prep_combatant(sample_meal1)
    battle_model.clear_combatants()
    assert len(battle_model.combatants) == 0


##################################################
# Battle Execution Test Cases
##################################################

def test_battle_winner(battle_model, sample_meal1, sample_meal2, mock_get_random, mock_update_meal_stats):
    """Test determining the winner of a battle based on scores and random delta."""
    battle_model.combatants.extend([sample_meal1, sample_meal2])
    mock_get_random.return_value = 0.1  # Set predictable random value for test

    # Conduct the battle and get winner's name
    winner_name = battle_model.battle()
    assert winner_name in ["Pasta", "Hot pot"], "Unexpected winner name"

    # Check that update_meal_stats was called for both combatants
    mock_update_meal_stats.assert_any_call(battle_model.combatants[0].id, "win")
    mock_update_meal_stats.assert_any_call(battle_model.combatants[1].id, "loss")


def test_battle_not_enough_combatants(battle_model):
    """Test that ValueError is raised if fewer than two combatants are present."""
    with pytest.raises(ValueError, match="Two combatants must be prepped"):
        battle_model.battle()


##################################################
# Battle Score Calculation Test Cases
##################################################

def test_get_battle_score(battle_model, sample_meal1):
    """Test calculating the battle score for a single combatant."""
    score = battle_model.get_battle_score(sample_meal1)
    expected_score = (sample_meal1.price * len(sample_meal1.cuisine)) - 2
    assert score == expected_score, f"Expected score: {expected_score}, got {score}"


##################################################
# Combatant Retrieval Test Cases
##################################################

def test_get_combatants(battle_model, sample_meal1, sample_meal2):
    """Test retrieving the list of combatants."""
    battle_model.combatants.extend([sample_meal1, sample_meal2])
    combatants = battle_model.get_combatants()
    assert len(combatants) == 2
    assert combatants[0].meal == "Pasta"
    assert combatants[1].meal == "Hot pot"
