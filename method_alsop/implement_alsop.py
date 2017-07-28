#!/usr/bin/python

# Available python modules
import os
import sys
import pickle
import numpy as np
import scipy.integrate as spi
import matplotlib.pyplot as plt

# modules writted by me
import maineq as meq
import orthonormality as ort

# this program will take 2 eigenfunction files (corrresponding to two different media)
# as input

effile1=sys.argv[1]
effile2=sys.argv[2]

def do_single_freq(per):

#****************************************************
# Get normalization factors
#****************************************************
	print "Computing normalization factors for period %f" %(per)

	# medium 1
	oobj1=ort.ortho(effile1,per,dcon1,True)
	dep1=oobj1.dep # depth sampling for medium 1
	mu1=oobj1.mu
	k1=oobj1.kmode
	efmat1=oobj1.egnfnmat # matrix containing eigenfunctions for medium 1
	Nmed1=oobj1.norms
	n=len(Nmed1) # no. of modes in medium 1 (at period per)
	Nmat1=np.sqrt(np.dot(Nmed1.reshape(n,1),Nmed1.reshape(1,n))) # matrix of normalizing factors for medium 1

	# medium 2
	oobj2=ort.ortho(effile2,per,dcon2,True)
	dep2=oobj2.dep # depth sampling for medium 2
	# different from dep1 in general because additional depth points will have been added by the ort module
	# around the horizontal interfaces of the two media
	efmat2=oobj2.egnfnmat # matrix containing eigenfunctions for medium 2
	Nmed2=oobj2.norms
	m=len(Nmed2) # no. of modes in medium 2
	Nmat2=np.sqrt(np.dot(Nmed2.reshape(m,1),Nmed2.reshape(1,m))) # matrix of normalizing factors for medium 2

	# matrix of mixed (medium 1 & 2) normalizing factors - required for the integrals T and P
	N12=np.sqrt(np.dot(Nmed1.reshape(n,1),Nmed2.reshape(1,m)))


#******************************************************************************************************
	# Compute required integrals - build P,S,T,V matrices
	# S and V matrices can be built by ort module as only 1 medium is involved hence the eigenfunctions have
	# same depth sampling.
	# P and T matrices must be built from scratch in this program as two different media are involved,
	# so depth sampling of eigenfunctions is different, in general, so ort cannot do the required integrations
#*******************************************************************************************************
	print "Computing required integrals"
	S=np.zeros((n,n))
	V=np.zeros((m,m))
	T=np.zeros((n,m))
	P=np.zeros((n,m))

	# S matrix
	sobj=ort.ortho(effile1,per,dcon1,False)
	S=sobj.matint/Nmat1

	# V matrix
	vobj=ort.ortho(effile2,per,dcon2,False)
	V=vobj.matint/Nmat2

	# T and P matrices
	def integrate(ef1,ef2,z1,z2,wt=None):
		checking=False	
		if wt==None:
			weight=np.ones(len(z1))
		else:
			weight=wt
		if len(np.setdiff1d(z1,z2))>0:
			#print np.setdiff1d(z1,z2)
			#print np.setdiff1d(z2,z1)
			""" Strategy will be to modify depth sampling of eigenfunction of medium 2 - remove extra points at discontinuity of medium 2 and add extra points at discontinuity of medium 1. This is because in the T and P integrals, only mu1 has a role, not mu2 """
			to_add=np.setdiff1d(z1,z2)
			to_remove=np.setdiff1d(z2,z1)
			addid=np.where(z1==to_add[0])[0][0]
			remid=np.where(z2==to_remove[0])[0][0]
			# remove appropriate points
			if checking:
				print "z2 before removal: ", z2[remid-5:remid+5]
				print "ef2 before removal: ", ef2[remid-5:remid+5]
				print "deleted samples ", z2[remid], z2[remid+2]
			z2=np.delete(z2,[remid,remid+2])
			ef2=np.delete(ef2,[remid,remid+2])
			if checking:
				print "z2 after removal ", z2[remid-5:remid+5]
				print " ef2 after removal ", ef2[remid-5:remid+5]
			# add appropriate points
			z2=np.insert(z2,[addid,addid+1],[z1[addid],z1[addid+2]]) # careful with usage
			if checking:
				print "ef2 before additon: ", ef2[addid-5:addid+5]
			ef2=np.insert(ef2,[addid,addid+1],[ef2[addid],ef2[addid]])   # of numpy insert
			if checking:
				print "added samples ", z1[addid], z1[addid+2]
				print "z2 after addition ", z2[addid-5:addid+5]
				print "ef2 after addition ", ef2[addid-5:addid+5]
			if len(z2) != len(z1) or len(ef2) != len(ef1):
				sys.exit('Problem with depth sampling of eigenfunctions from the 2 media')

		sid=np.where(z1==dcon1)[0][0]
		# integration above discontinuity
		phi_ij=ef1[:sid]*ef2[:sid]
		prod=phi_ij*weight[:sid]
		int_above=spi.simps(prod,z1[:sid])

		# integration below discontinuity
		phi_ij=ef1[sid+1:]*ef2[sid+1:]
		prod=phi_ij*weight[sid+1:]
		int_below=spi.simps(prod,z1[sid+1:])

		integral = int_above + int_below
		return integral

	for i in range(n):
		for j in range(m):
			T[i,j]=integrate(efmat1[:,i],efmat2[:,j],dep1,dep2)
			wfn=k1[i]*mu1
			P[i,j]=integrate(efmat1[:,i],efmat2[:,j],dep1,dep2,wfn)
	T=T/N12
	P=P/N12


########################################################################
# Set up and solve matrix equation
########################################################################

	rc,tc = meq.do_main(P,S,T,V)
	if len(allper)==1:
		print "Matrix of normalization factors for medium 1:\n ", Nmat1
		print "Norms for medium 1:\n ", Nmed1
		print "Matrix of normalization factors for medium 2:\n ", Nmat2
		print "Matrix of mixed normalization factors:\n ", N12
		print "P matrix:\n ", P
		print "S matrix:\n ", S
		print "T matrix:\n ", T
		print "V matrix:\n ", V
	else:
		print "Done"
	rc=np.ndarray.flatten(rc)
	tc=np.ndarray.flatten(tc)
	#energy_ref = sum(rc**2)
	#energy_trans = sum(tc**2)
	energy_ref = rc**2
	energy_trans = tc**2
	print "Reflection coefficients (Alsop normalization): ", rc
	print "Transmission coefficients (Alsop normalization): ", tc
	print "Fraction of energy transmitted: ", energy_trans
	rc_proper = rc*np.sqrt(Nmed1[0]/Nmed1)
	tc_proper = tc*np.sqrt(Nmed1[0]/Nmed2)
	# Note that because I've taken Nmed1[0], I'm assuming that incident mode
	# is the fundamental mode
	print "Transmission coefficients (surface displacement ratio): ", tc_proper
	return rc_proper,tc_proper, energy_ref, energy_trans

#************************ Main program **********************************

dcon=raw_input("Enter depths of discontinuity for the 2 media: ")
dcon1=float(dcon.split()[0])
dcon2=float(dcon.split()[1])
frange=raw_input('Enter frequency range: ')
fl=float(frange.split()[0])
fh=float(frange.split()[1])
freq=np.arange(fh,fl,-0.005)
# special additions
#freq=np.insert(freq,-1,0.007)
#freq=np.insert(freq,-3,0.012)
#freq=np.array([0.04])
allper=1/freq
# for the plotting to work properly allper must be sorted in ascending order
rcoeff=range(len(allper))
tcoeff=range(len(allper))
eng_ref=range(len(allper))
eng_trans=range(len(allper))
for p,per in enumerate(allper):
	rcper,tcper,erefper,etper=do_single_freq(per)
	if p==0:
		# find the number of modes reflected/transmitted at the shortest period
		maxmr=len(rcper)
		maxmt=len(tcper)
	else:
		if len(rcper)<maxmr:
			missing=maxmr-len(rcper)
			rcper=np.append(rcper,np.array(missing*[np.nan]))
			erefper=np.append(erefper,np.array(missing*[np.nan]))
		if len(tcper)<maxmt:
			missing=maxmt-len(tcper)
			tcper=np.append(tcper,np.array(missing*[np.nan]))
			etper=np.append(etper,np.array(missing*[np.nan]))
	rcoeff[p] = rcper
	tcoeff[p] = tcper
	eng_ref[p] = erefper
	eng_trans[p] = etper
	print p, len(rcper), len(tcper)
#print eng_ref, eng_trans
#rcm=range(maxmr); tcm=range(maxmt)
rcm=np.empty((maxmr,len(freq)))
erm=np.empty((maxmr,len(freq)))
tcm=np.empty((maxmt,len(freq)))
etm=np.empty((maxmt,len(freq)))
for i in range(maxmr):
	rcm[i,:]=[rc[i] for rc in rcoeff]
	erm[i,:]=[er[i] for er in eng_ref]
for j in range(maxmt):
	tcm[j,:]=[tc[j] for tc in tcoeff]
	etm[j,:]=[et[j] for et in eng_trans]

# plot the reflected/transmitted energy
for i in range(maxmt):
	plt.plot(freq,etm[i],'o-')
for i in range(maxmr):
	plt.plot(freq,erm[i],'o-')
plt.ylim(0,1.1)
plt.ylabel('Fraction of incident energy')

# plot the reflection/transmission surface ratios
#for i in range(maxmt):
#	plt.plot(freq,tcm[i],'o-')
#for i in range(maxmr):
#	plt.plot(freq,rcm[i],'o-')
plt.show()
usrc=raw_input("Do you want to save the result ? (y/n) : ")
if usrc=='y':
	jarname="ref.pckl"
	jar=open(jarname,'w')
	pickle.dump(freq,jar)
	pickle.dump(rcm,jar)
	jar.close()
	jarname2="trans.pckl"
	jar=open(jarname2,'w')
	pickle.dump(freq,jar)
	pickle.dump(tcm,jar)
	jar.close()
	jarname3="eref.pckl"
	jar=open(jarname3,'w')
	pickle.dump(freq,jar)
	pickle.dump(erm,jar)
	jar.close()
	jarname4="etrans.pckl"
	jar=open(jarname4,'w')
	pickle.dump(freq,jar)
	pickle.dump(etm,jar)
	jar.close()
	print "Results stored in %s, %s, %s and %s" %(jarname,jarname2,jarname3,jarname4)