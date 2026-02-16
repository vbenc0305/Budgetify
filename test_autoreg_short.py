import pandas as pd
from src.Generation.Case_one_has_enough_Transact_arima import fit_and_forecast_autoreg

s = pd.Series([100.0, 110.0, 120.0], index=pd.date_range("2023-01-31", periods=3, freq='ME'))
print('Series length:', len(s))
model, preds, ci = fit_and_forecast_autoreg(s, lags=5, steps=3)
print('Model:', model)
print('Preds:', preds)

