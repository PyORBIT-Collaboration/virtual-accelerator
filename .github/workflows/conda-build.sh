. /opt/conda/etc/profile.d/conda.sh
conda env create -n po3_va --file environment.yml
conda activate po3_va
pip install git+https://github.com/PyORBIT-Collaboration/PyORBIT3
pip install .