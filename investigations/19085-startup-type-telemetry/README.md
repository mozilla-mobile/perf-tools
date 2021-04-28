# 19085-startup-type-telemetry
Companion repository for https://github.com/mozilla-mobile/fenix/issues/19085. See python source file comments for usage details.

### Running
Install dependencies:
```sh
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Download the raw data to `perf_startup_startup_type_normalized.csv` in this directory.

Run with:
```sh
python analyze_startup_type.py
```
