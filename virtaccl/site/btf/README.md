# BTF Virtual Accelerator
This is an offshoot of the main VIRAC project that replicates the Beam Test Facility at the SNS. It works in largely the same manner as the main project though has a few specialized elements specific to the BTF.

## Run
Run default MEBT1 -> MEBT2
```
btf_va
```

Change end point of simulation to MEBT1, or STUB
```
btf_va MEBT1
```
The BTF has two main running configurations, Bend 1 mode and Bend 2 mode. These are differentiated by whether the first dipole located halfway down the beamline is on or off. If it is on then the beam will be sent to the short STUB section and will not go through any magnets numbered 10 or higher. If it is off the beam will not go to the STUB section and will travel the full length of the beamline.

The BTF VIRAC is defaulted to Bend 2 mode. Using the qualifier STUB in start up switches it to Bend 1 mode.

## Using Test Code
In the examples folder of repository there is a test code that can be ran to ensure BTF VIRAC download success, the specific file is BTF-Mag-Test.py. To launch this code start up the BTF VIRAC in a terminal window, in a separate window run while in the repository run this command:
```
python3 virtaccl/examples/BTF_Mag_Test.py
```


## Documentation
Further documentation of specific elements of the BTF and general usage can be found here (In Development)
