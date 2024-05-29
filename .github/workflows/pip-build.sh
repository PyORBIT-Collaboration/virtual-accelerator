python3 -m venv .po3_va
. .po3_va/bin/activate
pip install git+https://github.com/PyORBIT-Collaboration/PyORBIT3
pip install -U pip
pip install -r requirements.txt
pip install -U setuptools
pip install --no-build-isolation --editable .