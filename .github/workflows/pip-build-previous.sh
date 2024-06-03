python3.9 -m venv .po3_va_previous
source .po3_va_previous/bin/activate
pip install -U pip
pip install git+https://github.com/PyORBIT-Collaboration/PyORBIT3
PREVIOUS_COMMIT=$(git rev-parse HEAD^1)
git checkout "$PREVIOUS_COMMIT"
pip install .
virtual_accelerator --print_pvs > old_pvs.txt