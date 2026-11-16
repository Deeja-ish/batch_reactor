from src.features import build_batch_features, FEATURE_COLUMNS
import pandas as pd
from pathlib import Path 
import pytest
import numpy as np 

BASE_PATH = Path(__name__).resolve().parent
print(BASE_PATH)

data = pd.read_parquet(BASE_PATH / "data" / "raw" / "batch_readings.parquet")
remove_batch = data.drop(columns=['yield_pct'])

first_batch = remove_batch['batch_id'].iloc[0]

top_10_rows = remove_batch[remove_batch['batch_id'] == first_batch]


# create a test for the features creation function
def test_features():
    result = build_batch_features(top_10_rows)
    assert list(result.columns) == FEATURE_COLUMNS + ['batch_start']
    assert "yield_pct" not in result.columns



# create a test for few batch readings
few_batches = top_10_rows.head(5)
def test_min_batches():
    with pytest.raises(ValueError):
        result = build_batch_features(few_batches)
        return result



# check for shuffled data 
def test_shuffled_data():
    expected_result = build_batch_features(top_10_rows)
    shuffle_data = top_10_rows.sample(frac=1, random_state=42)
    shuffled_result = build_batch_features(shuffle_data)
    pd.testing.assert_frame_equal(expected_result, shuffled_result)


# test the data with broken column
def test_all_nan_sensor():
    broken_data = top_10_rows.copy()
    # turn the temp_colum to nan
    broken_data.loc[:, 'temp_c'] = np.nan
    result = build_batch_features(broken_data)
    assert len(result) == 1
    assert result['temp_c_fraction_unknow'].iloc[0] == 1
    assert pd.isna(result['temp_c_mean'].iloc[0])

