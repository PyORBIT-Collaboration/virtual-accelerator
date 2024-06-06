. /opt/conda/etc/profile.d/conda.sh
PREVIOUS_COMMIT=$(git rev-parse HEAD^1)
echo "Previous commit SHA: $PREVIOUS_COMMIT"
git checkout $PREVIOUS_COMMIT
conda env create -f virac.yml
conda activate virac
git checkout HEAD@{1}
virtual_accelerator --print_pvs > old_pvs.txt
conda env update --f virac.yml
conda activate virac
virtual_accelerator &