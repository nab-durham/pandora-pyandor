# Simple class to help with communication with the Andor SDK using ctypes
# This file contains helper functions

import ctypes
from ctypes.util import find_library
import numpy
from andorCodes import AndorCodes
import atexit

andorsdk=None
initialized=False
last_ret_code=None
region_set=None

class Region:
    def __init__(self,horiz_binning,vert_binning,col_start,col_end,row_start,row_end):
        self.new(horiz_binning,vert_binning,col_start,col_end,row_start,row_end)
    def new(self,horiz_binning,vert_binning,col_start,col_end,row_start,row_end):
        self.binning=[horiz_binning,vert_binning]
        self.columns=[col_start,col_end]
        self.rows=[row_start,row_end]
        self.shape=(self.rows[1]-self.rows[0]+1,self.columns[1]-self.columns[0]+1)
        self._checkregion()
        self.datasize=self._datasize()
    def _datasize(self):
        return(self.shape[0]*self.shape[1]/(self.binning[0]*self.binning[1]))
    def _checkregion(self):
        self.ccdhw=detector_size()
        assert self.rows[0]>=1 and self.rows[1]<=self.ccdhw[0]
        assert self.columns[0]>=1 and self.columns[1]<=self.ccdhw[1]
        assert self.shape[0]>1 and self.shape[1]>0

def prechecklib(func):
    global andorsdk
    def wrapper(*arg):
        if andorsdk is None:
            raise RuntimeError("shared library not loaded")
        res = func(*arg)
        return res
    return wrapper
def precheckinit(func):
    global initialized
    def wrapper(*arg):
        if not initialized:
            raise RuntimeError("SDK not initialized")
        res = func(*arg)
        return res
    return wrapper
def precheck(func):
    @precheckinit    
    @prechecklib
    def wrapper(*arg):
        if andorsdk is None:
            raise RuntimeError("shared library not loaded")
        if not initialized:
            raise RuntimeError("SDK not initialized")
        res = func(*arg)
        return res
    return wrapper

def checkretcode(func):
    def wrapper(*arg):
        global last_ret_code
        last_ret_code=func(*arg)
        assert last_ret_code==AndorCodes.DRV_SUCCESS, f"Got {last_ret_code}/{AndorCodes.values[last_ret_code]}"
        return True
    return wrapper

def initialize_ctypes(lib_name="andor"):
    '''ctypes init'''
    global andorsdk
    andor_lib_name = find_library("andor")
    assert not andor_lib_name is None, "Can't find Andor library"
    andorsdk = ctypes.cdll.LoadLibrary(andor_lib_name)
    return True

@prechecklib
def initialize_sdk(dir_name="/usr/local/etc/andor"):
    '''initialise sdk'''
    global initialized
    checkretcode(andorsdk.Initialize)(bytes(dir_name,'ascii')) # obviously Oxford educated...hoho
    initialized=True
    atexit.register(shutdown,True)
    return True

@precheck
def shutdown(verbose=False):
    checkretcode(andorsdk.ShutDown)()
    if verbose: print("Andor SDK ShutDown")
    return True

@precheck
def number_cameras():
    lNumCameras=ctypes.c_long()
    checkretcode(andorsdk.GetAvailableCameras)(ctypes.byref(lNumCameras))
    return lNumCameras.value

@precheck
def choose_camera(cam_num):
    ## choose camera
    lCameraHandle=ctypes.c_long()
    checkretcode(andorsdk.GetCameraHandle)(ctypes.c_int(cam_num), ctypes.byref(lCameraHandle))
    checkretcode(andorsdk.SetCurrentCamera)(lCameraHandle)
    return True

@precheck
def free_internal_memory():
    andorsdk.FreeInternalMemory()
    return True

@precheck
def detector_size():
    ## camera detector size
    #
    ccd_width, ccd_height=ctypes.c_int(),ctypes.c_int()
    checkretcode(andorsdk.GetDetector)(ctypes.byref(ccd_width),ctypes.byref(ccd_height))
    return(ccd_height.value,ccd_width.value)

@precheck
def get_shutter_info():
    '''iXon Ultra 888 has a mechanical shutter according to,
    https://andor.oxinst.com/assets/uploads/products/andor/documents/iXon-EMCCD-Brochure.pdf
    but no idea of specs (this can be got from SDK, not implemented)'''
    shutter_avail=ctypes.c_int()
    checkretcode(andorsdk.IsInternalMechanicalShutter)(ctypes.byref(shutter_avail))
    return True if shutter_avail.value==1 else False

@precheck
def set_shutter(mode='Auto',ttl_high=True,open_time=0,close_time=0):
    '''Which shutter mode to use (Auto, Open, Closed are simple),
    whether the TTL should be high or low when the shutter is open,
    The open and close times are in ms.'''
    ttl_mode=ctypes.c_int(1 if ttl_high else 0)
    modes={'Auto':ctypes.c_int(0),'Open':ctypes.c_int(1),'Closed':ctypes.c_int(2)} # also 4 and 5
    assert mode in modes, "Expected known modes: "+", ".join(modes.keys())
    open_time,close_time=ctypes.c_int(open_time),ctypes.c_int(close_time) # [ms]
    checkretcode(andorsdk.SetShutter)(ttl_mode,modes[mode],close_time,open_time)
    return True

@precheck
def set_trigger(mode):
    '''Trigger mode (Internal, External, Software are simple)
    '''
    modes={'Internal':ctypes.c_int(0),'External':ctypes.c_int(1),'Software':ctypes.c_int(10)} # other values are 6,7,9,12
    assert mode in modes, "Expected known modes: "+", ".join(modes.keys())
    checkretcode(andorsdk.SetTriggerMode)(modes[mode])
    return True

@precheck
def set_acquisition(mode):
    '''Acquisition mode (Single, Accumulate, Kinetics, FastKinetics, Continuous are supported)
    '''
    modes={
            'Single':ctypes.c_int(1),
            'Accumulate':ctypes.c_int(2),
            'Kinetics':ctypes.c_int(3),
            'FastKinetics':ctypes.c_int(4),
            'Continuous':ctypes.c_int(5)
        } # 5 aka Run till abort
    assert mode in modes, "Expected known modes: "+", ".join(modes.keys())
    checkretcode(andorsdk.SetAcquisitionMode)(modes[mode])
    return True

@precheck
def set_read(mode):
    '''Read mode (FullVertBinning,MultiTrack,RandomTrack,SingleTrack,Image are supported)
    '''
    modes={
            'FullVertBinning':ctypes.c_int(0),
            'MultiTrack':ctypes.c_int(1),
            'RandomTrack':ctypes.c_int(2),
            'SingleTrack':ctypes.c_int(3),
            'Image':ctypes.c_int(4)
        }
    assert mode in modes, "Expected known modes: "+", ".join(modes.keys())
    checkretcode(andorsdk.SetReadMode)(modes[mode])
    return True

@precheck
def set_exposure(t):
    '''Exposure time [s]'''
    checkretcode(andorsdk.SetExposureTime)(ctypes.c_float(t))
    return True

@precheck
def set_region(region):
    '''Set binning (2x in list/tuple) and start/end of column/row (2x in list/tuple) (latter values are inclusive)
    '''
    global region_set
    binnings=[ ctypes.c_int(v) for v in region.binning ]
    columns=[ ctypes.c_int(v) for v in region.columns ]
    rows=[ ctypes.c_int(v) for v in region.rows ]
    checkretcode(andorsdk.SetImage)(binnings[0],binnings[1],columns[0],columns[1],rows[0],rows[1])
    region_set=region
    return True
#    if(error==DRV_SUCCESS) error=SetImage(int hbin,int vbin,int subImage.left, int subImage.right, int subImage.top, int subImage.bottom);

@precheck
def get_timing():
    ## Get timing information
    #
    sdk_exposure,sdk_accumulate,sdk_kinetic=ctypes.c_float(),ctypes.c_float(),ctypes.c_float()
    checkretcode(andorsdk.GetAcquisitionTimings)(
       ctypes.byref(sdk_exposure),ctypes.byref(sdk_accumulate),ctypes.byref(sdk_kinetic))
    return(sdk_exposure.value,sdk_accumulate.value,sdk_kinetic.value)

@precheck
def get_total_number_images_acquired():
    data=ctypes.c_long()
    checkretcode(andorsdk.GetTotalNumberImagesAcquired)(ctypes.byref(data))
    return(data.value)

@precheck
def start_acquisition():
    checkretcode(andorsdk.StartAcquisition)()
    return True

@precheck
def abort_acquisition():
    checkretcode(andorsdk.AbortAcquisition)()
    return True

@precheck
def wait_for_acquisition():
    checkretcode(andorsdk.WaitForAcquisition)()
    return True

@precheck
def get_acquisition_progress():
    acc,kin=ctypes.c_long(),ctypes.c_long()
    checkretcode(andorsdk.GetAcquisitionProgress)(ctypes.byref(acc), ctypes.byref(kin))
    return(acc.value,kin.value)

@precheck
def get_status():
    data=ctypes.c_int()
    andorsdk.GetStatus(ctypes.byref(data)) # do not check this returns only success!
    return(data.value)

@precheck
def get_number_available_images():
    sdk_firstimg,sdk_lastimg=ctypes.c_long(),ctypes.c_long()
    checkretcode(andorsdk.GetNumberAvailableImages)(ctypes.byref(sdk_firstimg),ctypes.byref(sdk_lastimg))
    return(sdk_firstimg.value,sdk_lastimg.value)

@precheck
def get_acquired_data(region=None,nImgs=1):
    if region is None:
        region=region_set
    datasize=ctypes.c_int(int(region.datasize)*nImgs)
    data=numpy.zeros(datasize.value,numpy.int32) # might not be continguous
    data=numpy.ascontiguousarray(data) # make continguous
    ##
    andorsdk.GetAcquiredData.argtypes = [
        numpy.ctypeslib.ndpointer(dtype=numpy.int32, ndim=1, flags='C_CONTIGUOUS'),
        ]
    #    ctypes.c_ulong ]
    checkretcode(andorsdk.GetAcquiredData)(data,datasize);
    data=data.reshape(region.shape)
    return(data)

@precheck
def get_size_of_circular_buffer():
    '''Interesting that this returns the number of images possible to be stored in the buffer,
    not the size, so using it allows you to estimate the size of the ROI'''
    data=ctypes.c_long()
    checkretcode(andorsdk.GetSizeOfCircularBuffer)(ctypes.byref(data))
    return(data.value)
# \/ improved name, as alias
get_buffer_capacity=get_size_of_circular_buffer

@precheck
def get_images(first,last,region=None):
    '''Using indices to limit which images from the buffer are obtained, starts at 1 (Fortran-like)
    '''
    if region is None:
        region=region_set
    sdk_first,sdk_last,sdk_firstvalid,sdk_lastvalid=[ ctypes.c_long() for zzz in [None]*4]
    sdk_first.value,sdk_last.value=first,last
    datasize=ctypes.c_ulong(int(region.datasize*(last-first+1)))
    data=numpy.zeros(datasize.value,numpy.int32) # might not be continguous
    data=numpy.ascontiguousarray(data) # make continguous    
    assert datasize.value>=0,f"No images requested? {first}->{last} incl"
    andorsdk.GetImages.argtypes = [
            ctypes.c_long,ctypes.c_long,
            numpy.ctypeslib.ndpointer(dtype=numpy.int32, ndim=1, flags='C_CONTIGUOUS'),
            ctypes.c_ulong,
            ctypes.c_void_p,ctypes.c_void_p
        ]
    checkretcode(andorsdk.GetImages)(sdk_first,sdk_last, data,datasize, ctypes.byref(sdk_firstvalid),ctypes.byref(sdk_lastvalid))
    return(data,sdk_firstvalid.value,sdk_lastvalid.value)
   
def _get_preamp_num_gains():
    data=ctypes.c_int()
    checkretcode(andorsdk.GetNumberPreAmpGains)(ctypes.byref(data))
    return(data.value)

@precheck
def get_preamp_gains():
    ngains=_get_preamp_num_gains()
    gains=numpy.zeros(ngains,numpy.float32)
    data=ctypes.c_float()
    for i in range(ngains):
        print(i)
        checkretcode(andorsdk.GetPreAmpGain)(ctypes.c_int(i),ctypes.byref(data))
        gains[i]=data.value
        print(gains)
    return(gains)
    
    
@precheck
def set_preamp_gain(index):
    ngains=_get_preamp_num_gains()
    assert index<ngains-1 and index>=0, "Invalid index"
    checkretcode(andorsdk.SetPreAmpGain)(ctypes.c_int(index))
    return True
    