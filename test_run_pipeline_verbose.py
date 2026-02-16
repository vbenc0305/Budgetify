import traceback
print('START')
try:
    from src.Generation.Case_one_has_enough_Transact_arima import ForecastPipeline
    print('Imported ForecastPipeline')
    p = ForecastPipeline()
    print('Created pipeline instance')
    res = p.run(uid=None, plot=False, verbose=True)
    print('Run completed, result status:', res.get('status'))
    print('Metrics:', res.get('metrics'))
    print('Forecast sample:', res.get('forecast')[:3])
except Exception as e:
    print('EXCEPTION during test:')
    traceback.print_exc()
print('END')

