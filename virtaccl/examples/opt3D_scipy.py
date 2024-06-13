import os
import shutil
import time
from sns_rad.scan import ScanEngine, SetPoint
from sns_rad.scan.btf import Actuator, Magnet
from sns_rad.scan.util import main_script_name
from sns_rad.scan.scan import VALIDATION
from sns_rad.scan.scan import warning, info
from scipy.optimize import minimize
from OptimizationRoutinesScipy import Optimization
from epics import caget
import threading
import h5py



ndim = 3
verbose = False


# -- make folder
timestr = time.strftime('%Y-%m-%d')
foldername = '/Diagnostics/Data/Measurements/%s/'%timestr
os.makedirs(foldername,exist_ok=True)
filetimestamp = time.strftime('%y%m%d%H%M%S')
script_name = 'scipyse-minimize-3d'
filename = foldername + filetimestamp + '-'+script_name+'.h5'

# make file/scanengine instance
se = ScanEngine(filename, 
                suppress_naming_warning=True,enable_internal_log=True)

opt_pv = 'bs'
se.add_sync('ITSF_Diag:BS36:WF',opt_pv)


# add the variable that will be scanned and give it a name
magnet_list = ['QV10','QH11','QV12']
for mag in magnet_list:
    se.add_variable(mag, Magnet(f'BTF_MEBT_Mag:PS_{mag}',settle_time=3))
    print(f'added variable BTF_MEBT_Mag:PS_{mag}')


########################################################################
### setup optimizer
########################################################################
maxfev = 50 # max number of evaluations allowed 
bounds = [(-8,8),]*ndim # bounds on variables

opt = Optimization(verbose=verbose)

initial_step = [caget(f'BTF_MEBT_Mag:PS_{mag}:I_Set') for mag in magnet_list]
# warning: nelder mead gets confused if initial step is 0... (only valid for simulation tests)

def callback(x):
    opt.counter += 1
    info(f"Optimizer iteration {opt.counter} at {x}")
    return opt.finished # will this end optimizer early if needed?
    
minimizer_args = {'method':'Nelder-Mead','callback':callback,'bounds':bounds,
                  'options':{'maxfev':maxfev,'xatol':.01, 'fatol':0.001}}


thread = threading.Thread(target=opt.optimizer_scipy,args=(initial_step,minimize),kwargs=minimizer_args)


########################################################################
# Define generator that will go across steps
# status: seems to work for both converged + non-converged optimizations
########################################################################
def gen():
    for i in range(maxfev+1):
        
        # # break loop if optimizer finishes before maxfev
        # # (this doesn't seem to ever be catching...)
        if (opt.finished):
            info('invoked opt.finished')
            info(opt.finish_report)
            
            # yield optimum step 
            # (this should only execute once unless there are multiple optima)
            while not(opt.q_step.empty()):
                step = opt.q_step.get(); print(step)

                ####
                if verbose:
                    command = f"Generator yields optimal step {i+1}: {step}"; print(command)
                yield list(step), 3
                ####
            
            break
        
        ## MAIN LOOP
        # wait for input from optimizer function 
        # also check finished flag to not get caught in infinite loop
        while (opt.q_step.empty()) & (opt.finished == False):
            time.sleep(.1)  

        # yield next point
        while not(opt.q_step.empty()):
            step = opt.q_step.get()
            ####
            if verbose:
                command = f"Generator yields step {i}: {step}"; print(command)
            yield list(step), 3
            ####   
            
    #opt.finished = True # untested; will help cut off early?
    

    


class Validator:
    def __init__(self, required_measurements = 1, loss_pv = opt_pv, initial_wait=1, max_wait = 600):
        self.wait_time = initial_wait
        self.initial_wait = initial_wait
        self.max_wait = max_wait
        self.required_measurements = required_measurements
        self.loss_pv = loss_pv

    def validate_step(self, iteration, step, data):
        if len(data) < self.required_measurements:
            result = VALIDATION.REPEAT, self.wait_time
            warning(f'Iteration {iteration} invalid due to lack of data, will re-try in {self.wait_time} seconds.')
            self.wait_time = min(self.max_wait, self.wait_time * 2)
        else:
            # put loss in queue
            if verbose: print(data)
            loss = data[-1][1][self.loss_pv]
            
            opt.q_loss.put(loss)
            opt.q_step.task_done() # allow q_step to be joined
            
            # send ok to continue to next step
            result = VALIDATION.OK,
            self.wait_time = self.initial_wait
        return result


validator = Validator()
# launch the scan
thread.start()
se.run(gen(),validate=validator.validate_step,)
thread.join()

