# perf-tools
Tools for the performance team that don't fit into other repositories

File issues in the [`perf-frontend-issues` repository](https://github.com/mozilla-mobile/perf-frontend-issues/issues).

## Configuration
To use this repo, you'll need to create a virtual environment and install the
dependencies:
```sh
python3 -m venv venv
source venv/bin/activate

# Ensure the previous commands executed correctly before running this one
# to avoid installing the dependencies globally.
pip install -r requirements.txt
```

If you ever open a new shell, don't forget to reactivate the virtualenv before executing these scripts!

## Development
To run the linter, make sure your virtualenv is activated and run:
```sh
pycodestyle
```

Optionally, a path can be passed in. If you want more information about an error, pass the `--show-pep8` option.
