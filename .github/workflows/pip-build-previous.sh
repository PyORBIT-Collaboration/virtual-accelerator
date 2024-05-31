python3.9 -m venv .po3_va_previous
source .po3_va_previous/bin/activate
pip install -U pip
pip install git+https://github.com/PyORBIT-Collaboration/PyORBIT3
git revert --no-commit HEAD
pip install .
virtual_accelerator --print_pvs > old_pvs.txt