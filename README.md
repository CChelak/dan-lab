# Summary

The following tools are used to extract, manipulate and analyze ecologocial and
geographic data.

The library to import is found in `dan-lab` directory, and scripts to run
from console can be found in the `scripts` directory.

# Setup

First, ensure you have python and pip installed on your machine. We will run the
following commands from a terminal in the project's root directory.

## Linux
Open up a bash/shell terminal of your choice and run the following commands:
```sh
python -m venv .venv --prompt dan-lab # create a local virtual environment
source .venv/bin/activate # Activates the virtual environment
pip install -r requirements.txt # installs all needed packages
pip install .
```

## Windows
Open up PowerShell and run the following:

```ps
py -m venv .venv --prompt dan-lab # create a local virtual environment
.venv\Scripts\Activate.ps1 # Activates the virtual environment
pip install -r requirements.txt # installs all needed packages
pip install .
```

