import numpy as np
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--filename", type=str, default='bunch.dat')
parser.add_argument("--n", type=int, default=1)
parser.add_argument("--offset",type=float,default=0.01)
args = parser.parse_args()

pre = args.filename.split('.')[0] 

with open(args.filename) as f:
    header = [line for line in f if (line[0]=='%')]
header = ''.join(header)
header = header[:-3]

coord = np.loadtxt(args.filename, comments="%")

for i in range(args.n):
	dxp,dyp = args.offset*np.random.randn(2)
	coord_ = coord.copy()
	coord_[:,1] += dxp
	coord_[:,3] += dyp
	
	
	outfile = pre + f"-{i}" + '.dat'
	np.savetxt(outfile,coord_,header=header,comments='')