import numpy as np
#  create the reactor cleaning function
# the reactor pattern `R1` (220k-229k), `r1` (8.1k-8.6k), `R-1` (8.1k-8.6k), `Reactor 1` (8.1k-8.6k)
def clean_reactor(data):
    replace_data = {
        "-" : "",
        "REACTOR" : "R",
        " " : ""
    }
    data['reactor_id'] = data["reactor_id"].str.upper().str.strip().replace(replace_data, regex=True)
    return data

# create a function to clean the operator shift 
#  `A`, `a`, `'A '`, `'Shift A'`, `B`, `b`, `'Shift B'`, `C`, `c`, `'Shift C '`, `Night`, `night`, `'Night '`, `N`
def clean_operator(data):
    replace_shift = {
        " " : "",
        "SHIFT" : "",
        "^N$" : "NIGHT",
        "-" : "",
        "_" : ""
    }
    data['operator_shift'] = data['operator_shift'].str.upper().str.strip().replace(replace_shift, regex=True)
    return data

# clean the lot name 
def clean_lot_name(data):
    numbers = data['catalyst_lot'].astype(str).str.strip().str.upper().str.extract(r'(\d+)')[0]
    data['catalyst_lot'] = "LOT-" + numbers
    return data

# clean the units of temperature and pressure 
# (`BAR`, `kPa`, `barg`, `bar`, `PSI`, `kpa`, `psi`, `psig`) 
#  (`C`, `c`, `°F`, `degC`, `kelvin`, `°C`, `F`, `K`, `degF`)
def clean_unit_name(data):
    replace_temp ={
        "DEGC" : "°C",
        "DEGF" : "°F",
        "KELVIN" : "K",
        "C" : "°C",
        "F" : "°F"
    }
    data['temp_unit'] = data['temp_unit'].str.strip().str.upper().replace(replace_temp)
    data['pressure_unit'] = data['pressure_unit'].str.strip().str.lower()
    return data

# create a cleaning function to remove duplicates
def remove_duplicates(data):
    data = data.drop_duplicates()
    return data

# create a function to fill the pressure units base on the pressure bar data 
# pressure_bar between 1-5 bar
# 14-70 psi since 1 bar = 14psi
# 100 - 500 is kpa since 1 bar = 100kpa
def fill_pressure_unit(data):
    missing = data['pressure_unit'].isna()

    data.loc[missing & (data['pressure_bar'] >= 0) & (data['pressure_bar'] < 10), 'pressure_unit'] = 'bar'
    data.loc[missing & (data['pressure_bar'] >= 10) & (data['pressure_bar'] < 90), "pressure_unit"] = "psi"
    data.loc[missing & (data['pressure_bar'] >= 90 ), "pressure_unit"] = 'kpa'
    return data

# a function to change the units to fill in the null units to temperature units with approprate values
def fill_temp_unit(data):
    missing_temp = data['temp_unit'].isna()
    data.loc[missing_temp & (data['temp_c'] < 140), "temp_unit"] =  '°C'
    data.loc[missing_temp & (data['temp_c'] >=140) & (data["temp_c"] < 250), "temp_unit"] = '°F'
    data.loc[missing_temp & (data['temp_c'] >= 250), "temp_unit"] =  "K"
    return data
    
# create a function to clean the pressure and temperature values and units
def clean_temp_pressure(data):
    # convert farenhite
    temp_f = data['temp_unit'] == "°F"
    data.loc[temp_f, 'temp_c'] = (data.loc[temp_f, 'temp_c'] - 32.0) * (5.0 / 9.0)
    # convert kelvin 
    temp_kelvin = data['temp_unit'] == "K"
    data.loc[temp_kelvin, 'temp_c'] = (data.loc[temp_kelvin, 'temp_c'] - 273.15)
    
    # convert pressure kpa 
    pres_kpa = data['pressure_unit'] == "kpa"
    data.loc[pres_kpa, 'pressure_bar'] = data.loc[pres_kpa, 'pressure_bar'] / 100

    # convert pressure psi and psig
    pres_psi_psig = ((data['pressure_unit'] == "psi") | (data['pressure_unit'] == "psig"))
    data.loc[pres_psi_psig, 'pressure_bar'] = data.loc[pres_psi_psig, "pressure_bar"] * 0.0689476

    # convert the other units
    data['pressure_unit'] = "bar"
    data['temp_unit'] = "°C"

    return data


# temp below -273.15 and above 300
# pressure below 0 and above 50
# agitation below 0
def clean_outliers(data):
    # remove temperature outliers
    temp_outliers = (data['temp_c'] < -273.15) | (data['temp_c'] > 300)
    data.loc[temp_outliers, "temp_c"] = np.nan

    # remove pressure outliers
    pressure_outliers = (data['pressure_bar'] < 0) | (data['pressure_bar'] > 50)
    data.loc[pressure_outliers, "pressure_bar"] = np.nan

    # remove the negetive agitation 
    agitation_outliers = (data['agitator_rpm'] < 0)
    data.loc[agitation_outliers, 'agitator_rpm'] = np.nan

    return data