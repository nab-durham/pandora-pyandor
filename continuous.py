#!/usr/bin/env python
# coding: utf-8

# In[2]:


from importlib import reload
if 'andor' in dir():
    reload(andor)
else:
    import andor
#
from andorCodes import AndorCodes
import time


# In[3]:


try:
    andor.initialize_ctypes()
except:
    raise RuntimeError("Cannot load shared libray, not installed?")
try:
    andor.initialize_sdk()
except:
    raise RuntimeError("Cannot initialise SDK, already initialised elsewhere?")
    
print("Initialised SDK")
andor.choose_camera(0) # first
print("Set current camera to be #0 (first)")
ccd_height, ccd_width=andor.detector_size()
print(f"Size of detector is {ccd_height}x{ccd_width}")


# In[8]:


## detector configuration parameters
#
hbinning,vbinning=(1,1) # horizontal then vertical
region_lrbt=100,200,100,200
region=andor.Region(hbinning,vbinning,region_lrbt[0],region_lrbt[1],region_lrbt[2],region_lrbt[3])
exposure_time=0.05 # [s]
##
andor.set_region(region)
print(f"Binning HxV is {hbinning}x{vbinning}")
print("ROI is (L,R,B,T)={0[0]}x{0[1]},{0[2]},{0[3]}".format(region_lrbt))

andor.set_exposure(exposure_time)
print(f"Asked for exposure time is {1e3*exposure_time:.1f}ms")

times=andor.get_timing()
print(f"Therefore, exposure time is {1e3*times[0]:.1f}ms and acquisition time is {1e3*times[1]:.1f}ms")


# In[9]:


print(f"Shutter {'is' if andor.get_shutter_info() else 'is not'} available")
ttl_high=True
shutter_mode='Open'
open_time,close_time=0,0
andor.set_shutter(shutter_mode,ttl_high,open_time,close_time)
print(f"Shutter set to TTL o/p {'high' if ttl_high else 'low'}")
print(f"Shutter mode is '{shutter_mode}'")
print(f"Shutter open/close time is {open_time}/{close_time}ms")

trigger_mode='Internal'
andor.set_trigger(trigger_mode)
print(f"Tigger mode is '{trigger_mode}'")

# No need to do this, the default it seems
acq_mode='Continuous'
andor.set_acquisition(acq_mode)
print(f"Acquisition mode is '{acq_mode}'")

read_mode='Image'
andor.set_read(read_mode)
print(f"Read mode is '{read_mode}'")

img_capacity=andor.get_size_of_circular_buffer()
print(f"Expect {times[1]*img_capacity:.2f}s before circular buffer is full")


# In[ ]:


andor.free_internal_memory()


# In[10]:


print(f"Number images in SDK now={andor.get_total_number_images_acquired()}")
start_time=time.time()
## start acq.
#
andor.start_acquisition()

tlen=2 # how many seconds to wait for
import ctypes
def wait_for_acquisition():
    acquiring=True
    end_of_acqs=0
    while acquiring:
        if time.time()-start_time>2:
            print(f"Acquisition ending as {tlen}s passed")
            andor.abort_acquisition()
            break
#        print("Waiting for end of acquisition")
        end_of_acqs+=1
        andor.wait_for_acquisition()
        if andor.last_ret_code==AndorCodes.DRV_NO_NEW_DATA:
            andor.abort_acquisition()
            print(f"Acquisition ended without data {AndorCodes.values[andor.last_ret_code]}")
            acquiring=False
        else:
            acc,kin=andor.get_acquisition_progress()
            if acc==0 and kin==0:
                print("Acquisition end")
            stat=andor.get_status()
            acquiring=(stat==AndorCodes.DRV_ACQUIRING)
    print(f"Acquisition completed, end of waits={end_of_acqs}")

wait_for_acquisition()
stat=andor.get_status()
print(f"Status is {AndorCodes.values[stat]}")
print(f"Number images in SDK now={andor.get_total_number_images_acquired()}")


# In[ ]:


image_indices=andor.get_number_available_images()
print("Now first/last image index={0[0]}/{0[1]}".format(image_indices))
data=andor.get_images(image_indices[0],image_indices[1])
print(f"Got the acquired data, length={data.shape}")
image_indices=andor.get_number_available_images()
print("Now first/last image index={0[0]}/{0[1]}".format(image_indices))


# In[41]:


get_ipython().run_line_magic('pylab', 'inline')
fig1=pylab.figure(figsize=(8,8))
sps1=fig1.subplots(1)
sps1.imshow(data)


# ---

# In[ ]:


status=andor.get_status()
print(f"Status is: {status}={AndorCodes.values[status]}")


# ---

# In[8]:


andor.shutdown()


# In[50]:


tmp=3.14159
temp=andor.ctypes.c_float()
temp.value=tmp
print(tmp,temp)


# In[ ]:





# In[ ]:




