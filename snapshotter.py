#!/usr/bin/python

import getopt, sys, datetime,math,os

if os.getuid() != 0:
	print "This script must be run as root."
	sys.exit(1)

_DefaultFormula="x**(1.2**(k-1))"
_DefaultDateFormat="%Y.%m.%d_%H.%M"

def SetDefaults():
	#formulas
	global _Formula
	_Formula=_DefaultFormula
	
	#Parameters used in formulas
	global _K
	_K=0
	
	#Label
	global _Label
	_Label=""
	
	#Create
	global _Create
	_Create=""
	
	global _CreateSnapshot,_CreateOnly,_ReadOnly
	_CreateSnapshot=False
	_CreateOnly=False
	_ReadOnly=False
	
	global _DateFormat
	_DateFormat=_DefaultDateFormat
	
	global _QuietMode
	_QuietMode=False
	
SetDefaults()


class List:
	def __init__(self):
		self.List=[]
		
	def GetNewest(self):
		topdate=Voice.min
		for v in self.List: 
			if v>topdate: topdate=v
		return topdate
	
	def CalculatePointList(self):
		datetop=self.GetNewest()
		self.List.sort()
		seclist=[]
		for v in self.List: seclist.append((datetop-v).total_seconds())
		pointlistF=[]
		pointlistB=[]
		for i in range(1,len(seclist)-1):
			sec=seclist[i]
			dt_b=sec-seclist[i+1]
			dt_f=seclist[i-1]-sec
			pointlistF.append(CalculatePoints(sec,dt_f))
			pointlistB.append(CalculatePoints(sec,dt_b))
		return pointlistF,pointlistB
			
	def RemoveMinVoice(self):
		pointlistF,pointlistB=self.CalculatePointList() #the pointlists are off one
		i_del=FindMinIndex(pointlistF,pointlistB)+1
		self.Remove(i_del)
	
	def RemoveOlder(self, max_date):
		for v in self.List: 
			if (Voice.now()-v)>max_date: 
				self.Remove(self.List.index(v))
			
	def RemoveOtherThan(self,max_amount):
		if max_amount<2: raise Exception, "max_amount must be at least 2"
		while len(self.List)>max_amount:
			self.RemoveMinVoice()
	
	def Process(self,max_amount,max_date):
		self.RemoveOlder(max_date)
		self.RemoveOtherThan(max_amount)

	def Remove(self,i):
		obj=self.List[i]
		try: obj.Path
		except AttributeError: pass
		else: obj.DeleteSnapshot()
		self.List.pop(i)

class Voice(datetime.datetime):
	def DeleteSnapshot(self):
		ret=CallBTRFS("subvolume delete '"+self.Path+"'")
		if ret==32512: print "It looks like the btrfs binary can't be found. Check that you installed it correctly."
		elif ret==12: print "Can't delete the given path"
		elif ret!=0: print "Error while deleting the snapshot"
			
def CallBTRFS(args):
	global _QuietMode
	if _QuietMode: args=args+" >/dev/null"
	ret=os.system("btrfs "+args)
	return ret

def CalculateCurvePoint(asc):
	global _Formula,_K
	x=asc
	k=_K
	d=eval(_Formula)
	return float(d)

def CalculatePoints(asc,dt):
	d=CalculateCurvePoint(asc)
	if d==0: d=0.00000001
	#print asc,dt,d
	return float(dt/d)

def FindMinIndex(listA,listB):
	min_a=min(listA)
	t=99999999999999999
	for i in range(len(listA)):
		if listA[i]==min_a and listB[i]<t:
			t=listB[i]
			min_i=i
	return min_i
	
def do_sym():
	step_seconds=3600
	max_hours=_Days*(86400/step_seconds)
	max_amount=_MaxQty
	array=List()
	tinit=1
	tadd=Voice.now()
	tstep=datetime.timedelta(seconds=step_seconds)
	for i in range(max_hours):
		tadd=tadd+tstep
		array.List.append(tadd)
		array.RemoveOtherThan(max_amount)
	for v in array.List: print v.strftime(_DateFormat)
	sys.exit(2)
	
def create_snapshot(Source,Dest,Label="",ReadOnly=False):
	dest_long=Dest+"/"+Label+datetime.datetime.now().strftime(_DateFormat)
	dest_long=os.path.normpath(dest_long)
	if os.path.isdir(dest_long):
		print "Snapshot "+dest_long+" already exists"
		sys.exit(1)
	cmd="subvolume snapshot READONLY 'SOURCE' 'DESTINATION'"
	if ReadOnly: ReadOnly_TXT="-r"
	else: ReadOnly_TXT=""
	cmd=cmd.replace('READONLY',ReadOnly_TXT)
	cmd=cmd.replace('SOURCE',Source)
	cmd=cmd.replace('DESTINATION',dest_long)
	ret=CallBTRFS(cmd)
	if ret==32512: print "It looks like the btrfs binary can't be found. Check that you installed it correctly."
	elif ret==3072: print "Error in the paths passed to btrfs"
	elif ret!=0: print "Error while creating the snapshot"

def process_directory(dir,maxnum,maxdays,Label=""):
	try: dirlist=os.listdir(dir)
	except OSError: print "Error while listing the given directory"
	time_limit=datetime.timedelta(days=maxdays)
	array=List()
	parser=Label+_DateFormat
	for name in dirlist:
		try: array.List.append(Voice.strptime(name, parser))
		except ValueError: continue
		array.List[-1].Path=dir+"/"+name
	array.RemoveOlder(time_limit)
	array.RemoveOtherThan(maxnum)
		
	
	
def usage(exit=False):
	A='\
snapshotter is a script that takes and mantains a snapshot directory where old entries get\n\
deleted more and more as time passes.\n\
You can call this script withe the -c/-C flags to create a snapshot, but you can use your own\n\
method to create snapshots as long as you follow the same naming pattern. \n\
\n\
Usage:\n\
snapshotter --days=<n> --maxqty=<n> [<options>] <dest_dir>\n\
\n\
--days and --maxqty are required options\n\
\n\
Options:\n\
    -d <n>    --days <n>     :REQUIRED. Maximum amounts of days to keep snapshots for. Any \n\
                                 snapshot older than this will be deleted regardless of score\n\
    -n <n>    --maxqty <n>   :REQUIRED. Maximum amount of snapshots to keep. This parameter \n\
                                 (along with --days and the frequency of snapshots) determines the\n\
                                 concentration of snapshots.\n\
    -c <src>                 :Creates a new snapshot using the provided subvolume as source.\n\
    -C <src>                 :Like -c, but inhibits deletion after the creation of the snapshot.\n\
    -r        --readonly     :Creates a read-only snapshot. Relevant only if used with -c or -C.\n\
    -l <str>  --label=<str>  :Defines a label to be used both for creating and filtering snapshots.\n\
    -k <float>               :Parameter used to alter the score formula. Positives values \n\
                                 concentrates on recent snapshots, negative values even\n\
                                 out the distribution. Defaults to 0.\n\
    -b <...>  --datef=<...>  :Alters the datetime format. Read the FORMAT section in the "date"\n\
                                 manpage. The default datetime format is "'+_DefaultDateFormat+'"\n\
    -f <frm>  --formula=".." :Used to enter a custom distribution formula that overwrites the\n\
                                 default "'+_DefaultFormula+'"\n\
    -s        --sym          :Sym mode. Calculates the outcome and prints the distribution after \n\
                                 <days> have passed. assumes 1 snapshot/hour.\n\
    -q        --quiet        :Quiet mode. Suppress non-error messages.\n\
'
	print A
	if exit: sys.exit(exit)

def main():
	global _Formula,_K,_Debug, _Days, _MaxQty,_CreateSnapshot,_CreateOnly,_ReadOnly,_Label,_DateFormat,_QuietMode
	_Days=False
	_MaxQty=False
	sym=False
	
	args_in=[]; 
	for ar in sys.argv[1:]: args_in.append(ar.strip()) 
	try:                                
		opts, args = getopt.gnu_getopt(args_in, "hqsd:n:f:k:l:c:C:r", ["help","sym","formula=","days=","maxqty=","label=","readonly"]) 
	except getopt.GetoptError, err:  
		print str(err)
		usage(exit=2)
	#print opts

	try:
		for opt, arg in opts:
			if opt in ("-h", "--help"): usage(exit=1)
			if opt in ("-q", "--quiet"): _QuietMode=True
			elif opt in ("-s","--sym"): sym=1
			elif opt in ("-f","--formula"): Formula=arg.strip()
			elif opt in ("-d","--days"): _Days=int(arg)
			elif opt in ("-n","--maxqty"):
				_MaxQty=int(arg)
				if _MaxQty<2: raise Exception, "MaxQty must be at least 2"
			elif opt in ("-l","--label"): _Label=arg.strip()
			elif opt in ("-c","--create"): 
				_CreateSnapshot=arg.strip()
			elif opt == "-C":
				_CreateSnapshot=arg.strip()
				_CreateOnly=True
			elif opt in ("-r","--readonly"): _ReadOnly=True
			elif opt=="-k": _K=float(arg)
			elif opt in ("-b", "--datef"): _DateFormat=arg
	except Exception, err:  
		print str(err)
		print ""
		usage(exit=2)

	#sys.exit(0)
	if _CreateSnapshot:
		if not os.path.isdir(_CreateSnapshot):
			print "Source directory "+ _CreateSnapshot+" does not exist"
			sys.exit(1)
		_CreateSnapshot=os.path.normpath(_CreateSnapshot)

	if sym: do_sym()
	else:
		if len(args)!=1: 
			print "Missing snapshot directory"
			usage(exit=2)
		destination=args[0].strip()
		if not os.path.isdir(destination):
			print "Snapshot directory "+destination+" does not exist"
			sys.exit(1)
		destination=os.path.normpath(destination)
		
		if _CreateSnapshot: create_snapshot(_CreateSnapshot, destination, Label=_Label, ReadOnly=_ReadOnly)
		if not _CreateOnly: 
        		if not _Days or not _MaxQty:
				print "You must specify the maximum age and quantity of snapshots"
				sys.exit(1)
			process_directory(destination, _MaxQty, _Days, _Label)
		
main()
