from src.Generation.Case_one_has_enough_Transact_arima import ForecastPipeline

p = ForecastPipeline()
print('Created pipeline instance')
res = p.run(uid=None, plot=False, verbose=True)
print('Result status:', res.get('status'))
print('Metrics:', res.get('metrics'))
print('Forecast sample:', res.get('forecast')[:3])

