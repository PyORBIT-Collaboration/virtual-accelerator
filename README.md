# Virtual Accelerator

## Installation

### Prerequisites 
It's advised to use a virtual environment, either venv or conda. Using conda is advised on the latest Mac architecture. 
See below for installation with conda.

### Installing with pip

#### Installing EPICS
If you are using Linux, skip to the Installing PyORBIT step. If you are installing on a macOS, you will need to install [EPICS](https://epics-controls.org/resources-and-support/documents/getting-started/). After 
installing EPICS, add the following line to your bash_profile:

```bash
export PYEPICS_LIBCA=${EPICS_BASE}/lib/${EPICS_HOST_ARCH}/libca.dylib
```

#### Installing PyORBIT

You need to have [PyORBIT3](https://github.com/PyORBIT-Collaboration/PyORBIT3) installed in the same virtual environment.

#### Installing Virac

The following will install the virtual accelerator in development mode, so you can edit the code and and immediately see 
the results without re-installation.

```bash
pip install -e .
pip list
# virtaccl should be in the list of installed packages
```

Alternatively, to install in isolated mode (into your site-packages).
```bash
pip install .
```
or even without cloning the repository

```bash
pip install git+https://URL_OF_YOUR_REPO/virtual-accelerator.git
```

### Installing with conda
This will install EPICS, PyORBIT3, the virtual accelerator, and define the needed environment variables. You will have the standard EPICS command line tools installed as well.

```bash
conda env create -f virac.yml
conda activate virac
```


## Run

### Client environment setup
Your client environment, the one that connects to virtual accelerator, should have **localhost**  included in CA search, so some setup may be needed.<br>
For example, the following will ensure that the client connects to the virtual accelerator only while allowing large array transfers.
```bash
export EPICS_CA_ADDR_LIST=localhost
export EPICS_CA_AUTO_ADDR_LIST=NO
export EPICS_CA_MAX_ARRAY_BYTES=10000000
```

### Default SNS virtual accelerator

To see help:
```bash
sns_va -h
```

Run default MEBT -> HEBT1
```bash
sns_va
```

Run MEBT only (with printing all PVs)
```bash
sns_va --debug MEBT
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

### BTF beamline

To see help:
```bash
btf_va -h
```

Run with default bunch

```bash
btf_va --debug
```

BTF example file:

```bash
python -m virtaccl.examples.BTF_Mag_Test 
```

### Hardcoded IDmp beamline of the SNS accelerator

To see help:
```bash
idmp_va -h
```

Run with default bunch

```bash
idmp_va --debug
```


