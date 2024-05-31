python3.9 -m venv .po3_va_previous
source .po3_va_previous/bin/activate
pip install -U pip
pip install git+https://github.com/PyORBIT-Collaboration/PyORBIT3
commit_id=$(git log --format="%H" -n 1)
pip install git+https://github.com/PyORBIT-Collaboration/virtual-accelerator.git@+$commit_id
virtual_accelerator --print_pvs > old_pvs.txt