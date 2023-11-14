# virtual-accelerator

This is a virtual accelerator that creates an EPICs server and uses PyORBIT to simulate a beam.

To run the virtual accelerator:

clone the directory:
git clone https://code.ornl.gov/pyorbit3/virtual-accelerator.git

You need to be in a environment that has Python 3.9 with the PyORBIT3, numpy, and pcaspy packages installed.

Move into the EPICS folder:
cd EPICS

Then run virtual_accelerator.py:
python virtual_accelerator.py

The server will start and you should be able to change settings and read diagnostics through EPICs.