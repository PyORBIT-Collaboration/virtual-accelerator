# Virtual Accelerator

## Installation
It's advised to use virtual environment either venv or conda.

Clone this repository and install with pip. 
You need to have PyORBIT installed in the same virtual environment.

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

## Run

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


