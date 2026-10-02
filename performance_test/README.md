# Performance test

A [Locust](https://locust.io/) load test to run against a deployed GPP-publicatiebank,
with readers, editors and uploaders in numbers you choose.

```bash
python3 -m venv .venv-perf
.venv-perf/bin/pip install -r requirements/perf.txt

PERF_TOKEN=<API key> .venv-perf/bin/locust -f performance_test/locustfile.py --headless \
    --host https://publicatiebank.example.nl \
    --readers 20 --editors 5 --uploaders 3 --doc-size-mb 1-50 \
    --run-time 10m --csv results/baseline --html results/baseline.html

python3 performance_test/compare.py results/baseline results/after-change
```

See [Performance testing](../docs/installation/performance_testing.rst) in the
documentation for the options, example scenarios, how to read the results and which
deployment settings to tune.

* `locustfile.py`: the users and their behaviour.
* `documents.py`: generates valid PDF/ZIP documents of an exact size.
* `compare.py`: compares the `--csv` results of two runs.
