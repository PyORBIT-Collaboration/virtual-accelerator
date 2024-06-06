# Virtual Accelerator

## Installation

### Prerequisites 
It's advised to use a virtual environment, either venv or conda. 
You also need compilers required for [PyORBIT3](https://github.com/PyORBIT-Collaboration/PyORBIT3)

### Installing with pip 
You need to have PyORBIT installed in the same virtual environment.
If you are installing on a macOS, you will need to install EPICS as well: https://epics-controls.org/resources-and-support/documents/getting-started/.
After following all the instructions, add the following line to your bash_profile:
```bash
export PYEPICS_LIBCA=${EPICS_BASE}/lib/${EPICS_HOST_ARCH}/libca.dylib
```
Using conda is advised on the latest Mac architecture. See below for installation with conda.


```bash
pip install -e .
pip list
# virtaccl should be in the list of installed packages
```
This will install VA in development mode, so you can edit the code and and immediately see the results without re-installation.

Alternatively to install in isolated mode (into your site-packages) 
```bash
pip install .
```
or even without cloning the repository

```bash
pip install git+https://URL_OF_YOUR_REPO/virtual-accelerator.git
```

### Installing with conda
This will install EPICS, PyORBIT3 and virtual accelerator, also it will define needed environament variables. You will have the standard EPICS command line tools installed as well.

```bash
conda env create -f virac.yml
conda activate virac
```


## Run

### Client environemnt setup
Your client environment, the one that connects to virtaul accelerator, should have **localhost**  included in CA search, so some setup may be needed.<br>
For example following will ensure that the client connects to virtual accelerator only while allowing large array transfers.
```bash
export EPICS_CA_ADDR_LIST=localhost
export EPICS_CA_AUTO_ADDR_LIST=NO
export EPICS_CA_MAX_ARRAY_BYTES=10000000
```

### Default SNS virtual accelerator

To see help:
```bash
virtual_accelerator -h
```

Run default MEBT -> HEBT1
```bash
virtual_accelerator
```

Run MEBT only (with printing all PVs)
```bash
   virtual_accelerator --debug --bunch MEBT_in.dat MEBT
```

### Run standard examples 
There are two client program (they connect to VA) examples:
* [Corrector.py](virtaccl/examples/Corrector.py) scans SCL_Mag:DCH00 and prints out horizontal position at SCL_Diag:BPM04 
* [Wire.py](virtaccl/examples/Wire.py) performs a scan of MEBT_Diag:WS14 (PVs are fictional) 

Both examples need VA running as a separate process (in a standalone terminla window), 
default `virtual_accelerator` command will work.
To launch an example run

```bash
python -m virtaccl.examples.Corrector 
```


### Hardcoded IDmp+ beamline of SNS accelerator

To see help:
```bash
idmp_va -h
```

Run with default bunch

```bash
idmp_va --debug
```


