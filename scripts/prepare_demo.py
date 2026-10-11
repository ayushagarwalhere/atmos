"""Prepare explicitly synthetic models for the three UI forecast horizons."""
from backend.storage import init_db
from backend.demo import seed_demo
from backend.forecast import train

def main():
    init_db()
    seed_demo()
    for horizon in (6, 12, 24):
        report = train('demo', horizon, allow_demo=True)
        print(f"Synthetic demo +{horizon}h: {report['selected_model']}; test coverage {report['interval']['test_coverage']:.1%}", flush=True)
    print('Demo models prepared. These do not validate real pollution forecasts.', flush=True)

if __name__ == '__main__':
    main()
