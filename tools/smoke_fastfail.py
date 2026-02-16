import os
import time

from src.Generation.data_loader import load_global_data

if __name__ == '__main__':
    email = os.getenv('SMOKE_EMAIL', 'smoketest@example.com')
    print('USE_LOCAL_FALLBACK=', os.getenv('USE_LOCAL_FALLBACK'))
    start = time.time()
    df = load_global_data(email)
    elapsed = time.time() - start
    print('rows:', len(df) if df is not None else None)
    print(f'elapsed: {elapsed:.3f}s')

