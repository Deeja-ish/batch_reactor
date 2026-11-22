from .cleaning import clean_reactor, clean_operator, clean_lot_name, clean_outliers, clean_temp_pressure, clean_unit_name, fill_pressure_unit, fill_temp_unit, remove_duplicates

# create the cleaning function 
class InvalidError(ValueError):
    pass;

# write the cleaning function 
def fraction_unknow(x):
    return x.isna().mean()

def get_quantille_05(x):
    return x.quantile(0.05)

def get_quantille_90(x):
    return x.quantile(0.95)
SENSOR = ['temp_c', "pressure_bar", "agitator_rpm", "feed_rate", 'ph']
STATS = ["min", 'max', "std", "mean", fraction_unknow, get_quantille_05, get_quantille_90]
BATCH_COLUMNS = ['catalyst_lot', "reactor_id", "feed_purity", "operator_shift", "ambient_humidity", "temp_unit", "pressure_unit"]
MIN_READINGS= 160
MODEL_FEATURES = ['reactor_id',
 'operator_shift',
 'feed_purity',
 'catalyst_lot',
 'ambient_humidity',
 'temp_c_mean',
 'temp_c_std',
 'temp_c_min',
 'temp_c_max',
 'temp_c_get_quantille_05',
 'temp_c_get_quantille_90',
 'pressure_bar_mean',
 'pressure_bar_std',
 'pressure_bar_min',
 'pressure_bar_max',
 'pressure_bar_get_quantille_05',
 'pressure_bar_get_quantille_90',
 'agitator_rpm_mean',
 'agitator_rpm_std',
 'agitator_rpm_min',
 'agitator_rpm_max',
 'agitator_rpm_get_quantille_05',
 'agitator_rpm_get_quantille_90',
 'feed_rate_mean',
 'feed_rate_std',
 'feed_rate_min',
 'feed_rate_max',
 'feed_rate_get_quantille_05',
 'feed_rate_get_quantille_90',
 'ph_mean',
 'ph_std',
 'ph_min',
 'ph_max',
 'ph_get_quantille_05',
 'ph_get_quantille_90']

# create the features column
FEATURE_COLUMNS = []
for sensor in SENSOR:
    for stats in STATS:
        if callable(stats):
            stats_name = stats.__name__
        else:
            stats_name = stats

        FEATURE_COLUMNS.append(f"{sensor}_{stats_name}")

FEATURE_COLUMNS.extend(BATCH_COLUMNS)

# validate the incomming data 
def validate_readings(data):
    expected_cols = set(BATCH_COLUMNS) | set(SENSOR)
    incoming_cols = set(data.columns)

    missing_cols = expected_cols - incoming_cols
    if missing_cols:
        raise InvalidError("Incomplete column")
    if len(data) < MIN_READINGS:
        raise InvalidError("Batch has too few readings")
    if data['batch_id'].nunique() != 1:
        raise InvalidError("The Batch id must be unique")
    return data

# the master cleaning function
def clean_data(data):
    data = clean_reactor(data)
    data = clean_operator(data)
    data = clean_lot_name(data)
    data = clean_unit_name(data)
    data = remove_duplicates(data)
    data = fill_pressure_unit(data)
    data = fill_temp_unit(data)
    data = clean_temp_pressure(data)
    data = clean_outliers(data)

    return data


# create the master function 
def build_batch_features(data):
    # clean the data
    cleaned_data = clean_data(data)
    # call the validate readings

    validated_data = validate_readings(cleaned_data)
    # group the data by batch_id

    agg_result = {
        "timestamp" : "min"
    }

    for col in BATCH_COLUMNS:
        agg_result[col] = "first"
    for sensor in SENSOR:
        agg_result[sensor] = STATS
            
    grouped_data = validated_data.groupby("batch_id").agg(agg_result)

    batch_column = []
    for col in grouped_data.columns:
        if col[0] == 'timestamp' and col[1] == 'min':
            batch_column.append('batch_start')
        elif col[1] in ['first']:
            batch_column.append(col[0])
        else:
            batch_column.append(f"{col[0]}_{col[1]}")

    grouped_data.columns = batch_column

    return grouped_data[FEATURE_COLUMNS + ['batch_start']]


