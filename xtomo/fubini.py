#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Gridrec algorithm based on pseudocode using Gaussian kernel
#from numba import jit
#import matplotlib.pyplot as plt
#import h5py
#import dxchange
import tomopy
#from scipy import 
import imageio
import os
from timeit import default_timer as timer
import numpy as np
#import cupy as cp

eps=np.finfo(np.float32).eps
pi=np.pi



def gaussian_kernel(x, k_r, sigma, xp): #using sigma=2 since this is the default value for sigma
#    kernel1 = xp.exp(-1/2 * (x/sigma)**2 *16)
    #xx=xp.exp(-x)
    kernel1 = xp.exp(-1/2 * 10 * (x/sigma)**2 )
    kernel1 = kernel1* (xp.abs(x) < k_r)
    return kernel1 
    
def keiser_bessel(x, k_r, beta,xp):
    #kernel1 = xp.i0(beta*xp.sqrt(1-(2*x/(k_r))**2))/xp.abs(xp.i0(beta)) 
    #kernel1 = kernel1* (xp.abs(x) < k_r)
    #print(beta)
    beta=beta*1.85
    kernel1 =  xp.i0(beta*xp.sqrt((xp.abs(x) <= k_r)*(1-(x/(k_r))**2)))/xp.abs(xp.i0(beta))
    kernel1 = xp.reshape(kernel1, x.shape)
    kernel1 = kernel1 * (xp.abs(x) < k_r) 
    #kernel1 = (xp.abs(x) < k_r) * xp.i0(beta*xp.sqrt((xp.abs(x) <= k_r)*(1-(x/(k_r))**2)))/xp.abs(xp.i0(beta)) 
    return kernel1

# general kernel 1D
def K1(x, k_r, kernel_type, xp,  beta=1, sigma=2):
    if kernel_type == 'gaussian':
        kernel2 = gaussian_kernel(x,k_r,sigma,xp) 
        return kernel2
    elif kernel_type == 'kb':
        kernel2 = keiser_bessel(x,k_r,beta,xp) 
        return kernel2
    else:
        print("Invalid kernel type")
        
"""    
def K2(x, y, kernel_type, xp, k_r=2, beta=1, sigma=2): #k_r and beta are parameters for keiser-bessel
    if kernel_type == 'gaussian':
        kernel2 = gaussian_kernel(x,k_r,sigma,xp) * gaussian_kernel(y,k_r,sigma,xp)
        return kernel2
    elif kernel_type == 'kb':
        kernel2 = keiser_bessel(x,k_r,beta,xp) * keiser_bessel(y,k_r,beta,xp)
        return kernel2
    else:
        print("Invalid kernel type")

def deapodization_simple(num_rays,kernel_type,xp,k_r=2, beta=1, sigma=2):
    ktilde=K1(xp.array([range(-k_r, k_r+1),] ), k_r, kernel_type, xp,  beta, sigma)
    padding_array = ((0,0),(num_rays//2 - k_r , num_rays//2 - k_r-1))
    ktilde = xp.lib.pad(ktilde, padding_array, 'constant', constant_values=0)
    ktilde = xp.fft.fftshift(xp.fft.ifft(xp.fft.ifftshift(ktilde)))

    deapodization_factor = ktilde * ktilde.T 
#    print("ratio i/r=", xp.max(abs(deapodization_factor.imag))/xp.max(abs(deapodization_factor.real)))
 
    return 1./deapodization_factor.real

def deapodization(num_rays,kernel_type,xp,k_r=2, beta=1, sigma=2):
    # we upsample the kernel
    sampling=8
    step=1./sampling
    stencil=xp.array([xp.arange(-k_r, k_r+1-step*(sampling-1),step),])
   
    ktilde=K1(stencil,k_r, kernel_type, xp,  beta, sigma)
    
    padding_array = ((0,0),(num_rays*sampling//2 - k_r*sampling , num_rays*sampling//2 - k_r*sampling-1))
    ktilde1=xp.lib.pad(ktilde, padding_array, 'constant', constant_values=0)
    ktilde1 = xp.fft.fftshift(xp.fft.ifft(xp.fft.ifftshift(ktilde1)))
    #print("ratio i/r=", xp.max(abs(deapodization_factor.imag))/xp.max(abs(deapodization_factor.real)))

    ktilde2=(ktilde1[:,num_rays*(sampling)//2-num_rays//2:num_rays*(sampling)//2+num_rays//2]).real
    
    apodization_factor = ktilde2 * ktilde2.T
    
    return 1./apodization_factor
"""



def deapodization_shifted(num_rays,kernel_type,xp,k_r=2, beta=1, sigma=2):
    #stencil=xp.array([range(-k_r, k_r+1),]
    sampling=8
    step=1./sampling
    stencil=xp.array(xp.arange(-k_r, k_r+1-step*(sampling-1),step))

    #stencil=xp.array([xp.arange(-k_r, k_r+1-step*(sampling-1),step),])
   
    ktilde=K1(stencil,k_r, kernel_type, xp,  beta, sigma)
    
    #padding_array = ((0,0),(num_rays*sampling//2 - k_r*sampling , num_rays*sampling//2 - k_r*sampling-1))
    padding_array = ((num_rays*sampling//2 - k_r*sampling ),( num_rays*sampling//2 - k_r*sampling-1))
    #ktilde1=xp.pad(ktilde, padding_array, 'constant', constant_values=0)
    ktilde1=xp.pad(ktilde, padding_array, 'constant', constant_values=0)
    # skip one fftshift so that we avoid one fftshift in the iteration
    ktilde1 = xp.fft.ifftshift(xp.fft.ifft(ktilde1))
    
    ktilde1=xp.reshape(ktilde1,(1,-1))
#    print("k1 shape ",ktilde1.shape)
    # since we upsampled in Fourier space, we need to crop in real space
    ktilde2=(ktilde1[:,num_rays*(sampling)//2-num_rays//2:num_rays*(sampling)//2+num_rays//2]).real
#    print("k2 shape ",ktilde2.shape)
    
    apodization_factor = ktilde2 * ktilde2.T
#    print("shape apodization ",apodization_factor.shape)
    return 1./apodization_factor



    
def create_unique_folder(name):
   
    id_index = 0
    while True:
        id_index += 1
        folder = "Sim_" + name + "_id_" + str(id_index) + "/"
        
        if not os.path.exists(folder):
            os.makedirs(folder)
            break

    return folder


def save_cube(cube, base_fname):

    for n in range(0, cube.shape[0]):
        tname = base_fname + "_" + str(n) + '.jpeg'
        imageio.imwrite(tname, cube[n,:,:].astype(xp.float32))
        

def generate_Shepp_Logan(cube_shape):

   return tomopy.misc.phantom.shepp3d(size=cube_shape, dtype='float32')


def forward_project(cube, theta):

    #return tomopy.sim.project.project(cube, theta, pad = False, sinogram_order=False)
    return tomopy.sim.project.project(cube, theta, pad = False, sinogram_order=True)
   

def gridding_setup(num_rays, theta_array, center=None, xp=np, kernel_type = 'gaussian', k_r = 2):
    # S. Marchesini, LBL/Sigray 2019
    # setting up the sparse array
    # columns are used to pick the input data
    # rows are where the data is added on the output  image
    # values are what we multiply the input with
    
    num_angles=theta_array.shape[0]
    
    if center == None or center == num_rays//2:
        rampfactor=-1   
#        print("not centering")
    else:
#        print("centering")
        rampfactor=xp.exp(1j*2*xp.pi*center/num_rays)
    
    stencil=xp.array([range(-k_r, k_r+1),])
    stencilx=xp.reshape(stencil,[1,1,2*k_r+1,1])
    stencily=xp.reshape(stencil,[1,1,1,2*k_r+1])

    # 
    # this avoids one fftshift after fft(data)
    qray = xp.fft.fftshift(xp.array(xp.arange(num_rays) ) - num_rays/2)
    qray= xp.reshape(qray,(1,num_rays))
    
    theta_array = theta_array.astype('float64')
    theta_array+=eps*10 # gives better result if theta[0] is not exactly 0
    # coordinates of the points on the  grid, 
    px = - (xp.sin(xp.reshape(theta_array,[num_angles,1]))) * (qray)
    py =   (xp.cos(xp.reshape(theta_array,[num_angles,1]))) * (qray) 
    # we'll add the center later to avoid numerical errors
    
    # reshape coordinates and index for the stencil expansion
    px=xp.reshape(px,[num_angles,num_rays,1,1])
    py=xp.reshape(py,[num_angles,num_rays,1,1])
    
    # compute kernels
    kx=K1(stencilx - (px - xp.around(px)),k_r, kernel_type, xp); 
    ky=K1(stencily - (py - xp.around(py)),k_r, kernel_type, xp); 
    
    qray=rampfactor**qray     # this avoid the fftshift(data)
    qray.shape=(1,num_rays,1,1)
    qray[:,num_rays//2,:,:]=0 # removing highest frequency from the data

    Kval=(kx*ky)*(qray)
    
    # move the grid to the middle and add stencils
    kx=stencilx+xp.around(px)+ num_rays/2
    ky=stencily+xp.around(py)+ num_rays/2


    # this avoids fftshift2(tomo)
    Kval*=((-1)**kx)*((-1)**ky)
    # the complex conjugate
    Kval_conj=xp.conj(Kval)+0.

    # index (where the output goes on the cartesian grid)
    Krow=((kx)*(num_rays)+ky)
    
    tscale=xp.ones(num_angles)
    tscale.shape=[num_angles,1,1,1]
    # check if theta goes to 180, then assign 1/2 weight to each
    theta=theta_array
    theta_repeat=xp.abs(xp.abs(theta[0]-theta[-1])-xp.pi)<xp.abs(theta[1]-theta[0])*1e-5
    if theta_repeat:
#        print("averaging first and last angles")
        #tscale=xp.ones(num_angles)
        #tscale[([0,-1])]=4
        #tscale[([-1])]=.5
        tscale[([0,-1])]=.5
        
        #tscale=xp.fft.fftshift(tscale)
        #tscale.shape=[num_angles,1,1,1]
        #Kval*=tscale
        #print("not averaging first and last")
        #tscale[([0,-1])]=1
    
    Kval*=tscale
    #Kval_conj*=tscale
        
            
    
    # input index (where the the data on polar grid input comes from) 
    pind = xp.array(range(num_rays*num_angles))
    # we need to replicate for each point of the kernel 
    # reshape index for the stencil expansion
    pind=xp.reshape(pind,[num_angles,num_rays,1,1])
    # column index 
    Kcol=(pind+kx*0+ky*0)

    # find points out of bound
    #ii=xp.where((kx>=0) & (ky>=0) & (kx<=num_rays-1) & (ky<=num_rays-1))
    # let's remove the highest frequencies as well (kx=0,ky=0)
    ii=xp.where((kx>=1) & (ky>=1) & (kx<=num_rays-1) & (ky<=num_rays-1))
    #print("points removed",np.concatenate(ii).size)
    # remove points out of bound
    Krow=Krow[ii]
    Kcol=Kcol[ii]
    Kval=Kval[ii]
    Kval_conj=Kval_conj[ii]
    
#    print("Kval type",Kval.dtype,"Krow type",Krow.dtype)
#    Kval=xp.complex64(Kval)
#    Krow=xp.longlong(Krow)
#    Kcol=xp.longlong(Kcol)
    Krow=Krow.astype('long')
    Kcol=Kcol.astype('long')
    Kval=Kval.astype('complex64')
    Kval_conj=Kval_conj.astype('complex64')
    
    # create sparse array   
    if xp.__name__=='cupy':
        import cupyx
        #S=scipy.sparse.coo_matrix((Kval.ravel(),(Kcol.ravel(), Krow.ravel())), shape=(num_angles*num_rays, (num_rays)**2))
        #S=cupyx.scipy.sparse.coo_matrix((Kval.ravel(),(Kcol.ravel(), Krow.ravel())), shape=(num_angles*num_rays, (num_rays)**2))
        S=cupyx.scipy.sparse.coo_matrix((Kval.ravel(),(Krow.ravel(), Kcol.ravel())), shape=((num_rays)**2,num_angles*num_rays))
        S=cupyx.scipy.sparse.csr_matrix(S)
        #print("size of S in gb", (8*(S.data).size+4*(S.indptr).size+4*(S.indices).size+5*4)/((2**10)**3))
        #print("size of S",8*(S.data).size,"ind ptr",4*(S.indptr).size,'ind',4*(S.indices).size)
#       a=S
#       print("size of S",
#       (a.data).size, (a.indptr).size, (a.indices).size)
#       print("type of S",
#        (a.data).dtype, (a.indptr).dtype, (a.indices).dtype)
##        S=cupyx.scipy.sparse.csr_matrix(S)
        #S=S.tocsr()#.sort_indices()
        #S=S.sort_indices()
        #S=S.sum_duplicates()
        #print("S dtype",S.dtype)
#       ST=cupyx.scipy.sparse.coo_matrix((Kval_conj.ravel(), (Krow.ravel(), Kcol.ravel())), shape=((num_rays)**2, num_angles*num_rays))
        ST=cupyx.scipy.sparse.coo_matrix((Kval_conj.ravel(), (Kcol.ravel(), Krow.ravel())), shape=(num_angles*num_rays, (num_rays)**2))
        #.tocsr()
        ST=cupyx.scipy.sparse.csr_matrix(ST)
        #ST=cupyx.scipy.sparse.csc_matrix(ST)
        #ST=cupyx.scipy.sparse.csc_matrix(ST)
        
        #ST=(ST.sort_indices())
#        print("st dtype",ST.dtype)
#        ST.sum_duplicates()

    else:
        import scipy

        #S=scipy.sparse.csr_matrix((Kval.ravel(),      (Kcol.ravel(), Krow.ravel())), shape=(num_angles*num_rays, (num_rays)**2))
        S=scipy.sparse.csr_matrix((Kval.ravel(),      (Krow.ravel(), Kcol.ravel())), shape=((num_rays)**2,num_angles*num_rays))
        #Kval=xp.conj(Kval)
        #ST=scipy.sparse.csr_matrix((Kval_conj.ravel(), (Krow.ravel(), Kcol.ravel())), shape=((num_rays)**2, num_angles*num_rays))
        ST=scipy.sparse.csr_matrix((Kval_conj.ravel(), (Kcol.ravel(), Krow.ravel())), shape=(num_angles*num_rays, (num_rays)**2))
        
#    Kval=xp.conj(Kval)
#    # note that we swap column and rows to get the transpose
#    #ST=scipy.sparse.csr_matrix((Kval.ravel(),(Kcol.ravel(), Krow.ravel())), shape=(num_angles*num_rays, (num_rays)**2))
#    ST=scipy.sparse.csr_matrix((Kval.ravel(), (Krow.ravel(), Kcol.ravel())), shape=((num_rays)**2, num_angles*num_rays))

    
#    # create sparse array   
#    S=scipy.sparse.csr_matrix((Kval.flatten(), (Krow.flatten(), Kcol.flatten())), shape=((num_rays+2*k_r+1)**2, num_angles*num_rays))
#
#    # note that we swap column and rows to get the transpose
#    ST=scipy.sparse.csr_matrix((Kval.flatten(),(Kcol.flatten(), Krow.flatten())), shape=(num_angles*num_rays, (num_rays+2*k_r+1)**2))
    
       
    return S, ST

def masktomo(num_rays,xp,width=.95):
    xx=xp.array([range(-num_rays//2, num_rays//2)])
    msk_sino=(xp.abs(xx)<(num_rays//2*width*.98)).astype('float32')

    msk_sino.shape=(1,1,num_rays)
    
    xx=xx**2
    rr2=xx+xx.T
    msk_tomo=rr2<(num_rays//2*width)**2
    msk_tomo.shape=(1,num_rays,num_rays)
    return msk_tomo, msk_sino

import matplotlib.pyplot as plt
def radon_setup(num_rays, theta_array, xp=np, center=None, kernel_type = 'gaussian', k_r = 2, width=.5):

    #print("setting up gridding")
    #start = timer()

    S, ST = gridding_setup(num_rays, theta_array, center, xp, kernel_type , k_r)
    #end = timer()

    #print("gridding setup time=",end - start)
    if xp.__name__=='cupy':
        import fft
        #import cupy.fft as fft
    else:
        import numpy.fft as fft
        
    
    
    #deapodization_factor = deapodization(num_rays, kernel_type, xp, k_r)
    deapodization_factor = deapodization_shifted(num_rays, kernel_type, xp, k_r=k_r)
    deapodization_factor=xp.reshape(deapodization_factor,(1,num_rays,num_rays))
    
    # get the filter
    num_angles=theta_array.shape[0]
    #print("num_angles", num_angles)
    #ramlak_filter = (xp.abs(xp.array(range(num_rays)) - num_rays/2)+1./num_rays)/(num_rays**2)/num_angles/9.8
    ramlak_filter = (xp.abs(xp.array(range(num_rays)) - num_rays/2)+1./num_rays)/(num_rays**3)/num_angles
     
    # this is to avoid one fftshift
    #ramlak_filter*=(-1)**xp.arange(num_rays);
    
    
    # removing the highest frequency
    ramlak_filter[0]=0;
    
    
    # we shifted the sparse matrix output so we work directly with shifted fft
    ramlak_filter=xp.fft.fftshift(ramlak_filter)

    # reshape so that we can broadcast to the whole stack
    ramlak_filter = ramlak_filter.reshape((1, 1, ramlak_filter.size))
    none_filter=ramlak_filter*0+1./(num_rays**3)/num_angles
    

    # mask out outer tomogram
    msk_tomo,msk_sino=masktomo(num_rays,xp,width=width)
    
    
    
    deapodization_factor/=num_rays
    deapodization_factor*=msk_tomo

    deapodization_factor*=0.14652085
    deapodization_factor=(deapodization_factor).astype('complex64')
    
#    if xp.__name__=='cupy':
#        import fft
#    else:
#        from numpy import fft
        

    R  = lambda tomo:  radon(tomo, deapodization_factor , ST, k_r, num_angles,xp,fft )

    # the conjugate transpose (for least squares solvers):
    RT = lambda sino: iradon(sino, dpr, S,  k_r, none_filter,xp,fft)
    
    # inverse Radon (pseudo inverse)
    dpr= deapodization_factor*num_rays*154.10934
    IR = lambda sino: iradon(sino, dpr, S,  k_r, ramlak_filter,xp,fft)
    
    
    return R,IR,RT
    

def iradon(sinogram_stack, deapodization_factor, S, k_r , hfilter,xp,fft): 
              #iradon(sino, deapodization_factor, S,  k_r, ramlak_filter )
#    xp=np
    
    num_slices = sinogram_stack.shape[0]
    num_angles = sinogram_stack.shape[1]
    num_rays   = sinogram_stack.shape[2]
    
    
    """
    #-----------------------------------------------------------#  
    #          vectorized code                                  #  
    
    
    nslice2=xp.int(xp.ceil(num_slices/2))     
    if num_slices==1:
        qts=sinogram_stack
    elif xp.mod(num_slices,2) ==1:
        #print('odd slides other than 1 not working yet')
        qts=sinogram_stack[0::2,:,:]
        qts[0:-1]+=1j*sinogram_stack[1::2,:,:]
    else:
        qts=sinogram_stack[0::2,:,:]+1j*sinogram_stack[1::2,:,:]
        #qts=sinogram_stack

    nslice=qts.shape[0]
    qts = xp.fft.fft(qts,axis=2)
    qts *= hfilter
    qts.shape = (nslice,num_rays*num_angles)

    qxy = qts*S

    qxy.shape=(nslice,num_rays,num_rays)

    qxy=xp.fft.ifft2(qxy)
    qxy*=deapodization_factor

 
    if num_slices==1:
        return qxy
    else:
        tomo_stack = xp.empty((num_slices, num_rays , num_rays ),dtype=xp.float32)
        tomo_stack[0::2,:,:]=qxy.real
        tomo_stack[1::2,:,:]=qxy[:nslice2*2,:,:].imag
        return tomo_stack
        qxy=xp.concatenate((qxy.real,qxy.imag),axis=0)
        qxy.shape=(2,nslice2,num_rays,num_rays)
        qxy=xp.moveaxis(qxy,1,0)
        qxy=xp.reshape(qxy,(nslice2*2,num_rays,num_rays))
        return qxy[:num_slices,:,:]

    #         end vectorized code                                  #  
    #-----------------------------------------------------------#  
    """
    
    

    tomo_stack = xp.empty((num_slices, num_rays , num_rays ),dtype=xp.float32)
    
    
    
    # two slices at once    
    for i in range(0,num_slices,2):
        # merge two sinograms into one complex

        if i > num_slices-2:
            qt=sinogram_stack[i]
        else:
            qt=sinogram_stack[i]+1j*sinogram_stack[i+1]
            
        
        # radon (r-theta) to Fourier (q-theta) space        
        
        #qt = xp.fft.fft(qt)
        #qt = fft.fft(qt)
        qt = fft.fft(qt)
        
        
         ###################################
        # non uniform IFFT: Fourier polar (q,theta) to cartesian (x,y):
       
        # density compensation
        qt *= hfilter[0,0]
        
        # inverse gridding (polar (q,theta) to cartesian (qx,qy))
        #qt.shape=(-1)        
        #tomogram=qt.ravel()*S #SpMV
        tomogram=S*qt.ravel() #SpMV
        
        tomogram.shape=(num_rays,num_rays)

        # Fourier cartesian (qx,qy) to real (xy) space
        tomogram = fft.ifft2(tomogram)
#        tomogram=fft.ifft2(tomogram)*deapodization_factor[0]
        tomogram*=deapodization_factor[0]
        
        # end of non uniform FFT 
        ###################################
        # extract two slices out of complex
        if i > num_slices-2:
            tomo_stack[i]=tomogram.real
        else:
            tomo_stack[i]=tomogram.real
            tomo_stack[i+1]=tomogram.imag
    
    
    return tomo_stack
    


#def radon(tomo_stack, deapodization_factor, ST, k_r, num_angles ):
def radon(tomo_stack, deapodization_factor, ST, k_r, num_angles,xp,fft ):
    
    
    num_slices = tomo_stack.shape[0]
    num_rays   = tomo_stack.shape[2]

    sinogram_stack = xp.empty((num_slices, num_angles, num_rays),dtype=xp.float32)
    
    deapodization_factor.shape=(num_rays,num_rays)

    #go through each slice
    #for i in range(0,num_slices):
    #    tomo_slice = tomo_stack[i] 
        
    # two slices at once by merrging into a complex   
    for i in range(0,num_slices,2):
        
        # merge two slices into complex
        if i > num_slices-2:
            tomo_slice = tomo_stack[i]
            
        else:
            tomo_slice = tomo_stack[i]+1j*tomo_stack[i+1]
        
        #sinogram = radon_oneslice(tomo_slice)
        ###################################
        # non uniform FFT cartesian (x,y) to Fourier polar (q,theta):
        tomo_slice=tomo_slice*deapodization_factor
        #tomo_slice = 
        tomo_slice = fft.fft2(tomo_slice)
        
        #ts=tomo_slice*deapodization_factor
        #tomo_slice = xp.fft.fft2(ts)
        
        # gridding from cartiesian (qx,qy) to polar (q-theta)
        # tomo_slice.shape = (num_rays **2)        
        #tomo_slice.shape = (-1)        
        #sinogram=tomo_slice.ravel() * ST #SpMV
        #S=xp.conj(ST)
        #sinogram=xp.conj(ST*xp.conj(tomo_slice.ravel() ))#SpMV
        #sinogram=tomo_slice.ravel()*ST#SpMV
        sinogram=(ST)*tomo_slice.ravel() #SpMV
        sinogram.shape=(num_angles,num_rays)

        # end of non uniform FFT
        ###################################
        
        # (q-theta) to radon (r-theta) :       
        #sinogram = 
        #fft.ifft(sinogram)  
        sinogram = fft.ifft(sinogram)  
        
        # put the sinogram in the stack
        #sinogram_stack[i]=sinogram        
        # extract two slices out of complex
        if i > num_slices-2:
            #print("ratio gridrec_transpose i/r=",  xp.max(xp.abs(sinogram.imag)/xp.max(xp.abs(sinogram.real))))

            sinogram_stack[i]=sinogram.real
        else:
            sinogram_stack[i]=sinogram.real
            sinogram_stack[i+1]=sinogram.imag
        
     
    return sinogram_stack
        
        
def force_data_types(input_data):

    input_data["data"]  = input_data["data"].astype(xp.complex64)
    input_data["theta"] = input_data["theta"].astype(xp.float64)	
    #input_data["rays"]  = input_data["rays"].astype(xp.uint)

def memcopy_to_device(host_pointers):
    try:
        cp=xp
        for key, value in host_pointers.items():      
            host_pointers[key] = cp.asarray(value)
    except:
        print("Unable to import CuPy")
def memcopy_to_host(device_pointers):
    try:
        import cupy as cp
        for key, value in device_pointers.items():       
            device_pointers[key] = cp.asnumpy(value)
    except:
        print("Unable to import CuPy")
        
def tomo_reconstruct(data, theta, rays, k_r, kernel_type, algorithm, gpu_accelerated):
    input_data = {"data": data,
                  "theta": theta,
                  "rays": rays}
    mode = None    

    force_data_types(input_data)

    if gpu_accelerated == True:
        mode = "cuda"
        xp = __import__("cupy")
        memcopy_to_device(input_data)

    else:
        mode = "python"
        xp = __import__("numpy")
        
    if algorithm == "gridrec":
       output_stack = gridrec(input_data["data"], input_data["theta"], rays, k_r, kernel_type, xp, mode)    

    elif algorithm == "gridrec_transpose":
       output_stack = gridrec_transpose(input_data["data"], input_data["theta"], rays, k_r, kernel_type, xp, mode)

    output_data = {"result": output_stack}
    
    if gpu_accelerated == True:
        memcopy_to_host(output_data)

    return output_data["result"]


#    num_angles=theta_array.shape[0]
#    ooa=xp.ones((num_angles,1))
#    oor=xp.ones((1,num_rays))
#    def set0(oo):
#        oo[0]=0
#        return oo
#    
#    A = lambda oor: (((ooa*oor).ravel()*xp.abs(S)).reshape(num_rays,num_rays))[num_rays//2,:]
#    #from solvers import cgs
#    
#    #kfilter,flag, ii, nrm=cgs(A,oor, x0=oor, maxiter=1, tol=1e-4)
#    kfilter=A(oor)
#    
#    #jk.shape=(num_rays,num_rays)
#    #kfilter=1./(jk+xp.finfo(xp.float32).eps)
#    kfilter=set0(1./(kfilter+xp.finfo(xp.float32).eps))
#    #
##    kfilter=jk[num_rays//2,:]
#    
#    plt.plot(kfilter)
#    plt.show()
##    kfilter[0]=0
#
#    kfilter=xp.fft.fftshift(kfilter)
#    
#    
#    kfilter=kfilter.reshape((1, 1,num_rays))
