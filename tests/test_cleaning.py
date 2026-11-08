import pandas as pd 
import numpy as np 
from src.cleaning import clean_reactor, clean_operator, clean_lot_name, clean_unit_name, remove_duplicates, fill_pressure_unit, fill_temp_unit, clean_temp_pressure, clean_outliers


# test the reactor_cleaning function
def test_reactor_clean():
    reactor_data = pd.DataFrame({
        "id" : [1, 2, 3, 4, 5],
        "reactor_id" : ["Reactor 1", "r-1", "R-1", "reactor-1", "R1"]
    })
    cleaned_df = clean_reactor(reactor_data)
    assert cleaned_df['reactor_id'].to_list() == ['R1', 'R1', 'R1', 'R1', 'R1']


# test the operator shift cleaning function
def test_operator_shift():
    operator_data = pd.DataFrame({
        "id" : [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
        "operator_shift" : ['Shift A', "A", 'a', "ShiftA", "n", "N", "Night", "night", "shift_A", "shift-a"]
    })
    cleaned_df = clean_operator(operator_data)
    assert cleaned_df['operator_shift'].to_list() == ["A", "A", "A", "A", "NIGHT", "NIGHT", 'NIGHT', "NIGHT", "A", "A"]


#  create a test to standaize lot names
def test_clean_lot():
    catalyst_lot_data = pd.DataFrame({
        "catalyst_lot" : ["l123", "L456", "LOT-789"]
    })
    cleaned_df = clean_lot_name(catalyst_lot_data)
    assert cleaned_df['catalyst_lot'].to_list() == ['LOT-123', 'LOT-456', 'LOT-789']


# test the unit cleaning
def test_unit_cleaning():
    units_data = pd.DataFrame({
        "pressure_unit" : ["BAR", "kPa", "barg", "bar", "PSI", "kpa", "psi", "psig", 'PSIG'],
        "temp_unit" : ['C', 'c', '°F', 'degC', 'kelvin', '°C', 'F', 'K', 'degF']
    })

    cleaned_df = clean_unit_name(units_data)
    assert cleaned_df['pressure_unit'].to_list() == ['bar', "kpa", "barg", "bar", "psi", "kpa", "psi", "psig", "psig"]
    assert cleaned_df['temp_unit'].to_list() == ['°C', '°C', '°F', '°C', 'K', '°C', '°F', "K", '°F']


# remove duplicate
def test_remove_duplicates():
    duplicates_data = pd.DataFrame({
        "batch_id" : [1, 2, 3, 4, 1, 2],
        "name" : ["khadija", "kabir", "bashir", "musa", "khadija", "kabir"]
    })

    cleaned_df = remove_duplicates(duplicates_data)
    assert len(cleaned_df) == 4
    assert cleaned_df['name'].to_list() == ['khadija', 'kabir', 'bashir', 'musa']


# test the pressure bar refill 
def test_pressure_unit_fill():
    pressure_data = pd.DataFrame({
        "pressure_bar" : [2.4, 12.9, 406],
        "pressure_unit" : [None, None, None]

    })
    cleaned_df = fill_pressure_unit(pressure_data)
    assert cleaned_df['pressure_unit'].to_list() == ['bar', "psi", "kpa"]


# test the temperature refill 
def test_temperature_unit_fill():
    temperature_data = pd.DataFrame({
        "temp_c" : [34.90, 170.0, 256.90],
        "temp_unit" : [None, None, None]
    })
    cleaned_df = fill_temp_unit(temperature_data)
    assert cleaned_df['temp_unit'] is not None


# test the cleaning of the raw data
def test_values_and_units():
    raw_data = pd.DataFrame({
        'pressure_unit': ['psi', 'kPa', 'barg'],
        'pressure_bar': [14.50377, 100.0, 2.0],
        'temp_unit': ['°F', 'Kelvin', '°C'],
        'temp_c': [212.0, 373.15, 100.0]
    })

    cleaned_data = clean_temp_pressure(raw_data)
    assert cleaned_data['pressure_unit'].to_list() == ['bar', 'bar', 'bar']
    assert cleaned_data['temp_unit'].to_list() == ['°C', '°C', '°C']

# test clean outliers
def test_clean_outliers():
    outliers_data = pd.DataFrame({
        "temp_c" : [-345, 67, 890, 45, 209, 45, 189],
        "pressure_bar" : [-9, -87, 0, 6, 13, 34, 59],
        "agitator_rpm" : [-8, -9, 0, 98, 67, 6, 89]
    })

    cleaned_df = clean_outliers(outliers_data)

    expected_temp = pd.Series(
        [np.nan, 67, np.nan, 45, 209, 45, 189], name='temp_c'
    )
    expected_pressure = pd.Series(
        [np.nan, np.nan, 0, 6, 13, 34, np.nan], name='pressure_bar'
    )

    # check the series
    pd.testing.assert_series_equal(
        cleaned_df['temp_c'], expected_temp, check_dtype=False
    )
    pd.testing.assert_series_equal(
        cleaned_df['pressure_bar'], expected_pressure, check_dtype=False
    )

