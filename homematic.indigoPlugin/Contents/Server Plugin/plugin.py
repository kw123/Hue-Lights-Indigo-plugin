#! /Library/Frameworks/Python.framework/Versions/Current/bin/python3
# -*- coding: utf-8 -*-
####################
# homematic Plugin
# Developed by Karl Wachs
# karlwachs@me.com

import datetime
import json

import subprocess
import os 
import sys
import pwd
import time
import platform
import codecs

import getNumber as GT
import threading
import logging
import copy
import requests
from checkIndigoPluginName import checkIndigoPluginName 

requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)


import xml.dom.minidom as xmlEtree

# left to be done:
#  
# 
#
#
#


_dataVersion = 1.0
_defaultName ="Homematic"
## Static parameters, not changed in pgm

#from params-user import *
from params import *


_defaultDateStampFormat = "%Y-%m-%d %H:%M:%S"
_defaultDateOnlyStampFormat = "%Y-%m-%d"
_defaultTimeStampFormat = "%H:%M:%S"

######### set new  pluginconfig defaults
# this needs to be updated for each new property added to pluginProps. 
# indigo ignores the defaults of new properties after first load of the plugin 
kDefaultPluginPrefs = {
	"MSG":										"please enter values",
	"portNumber":								"2121",
	"ipNumber":									"192.168.1.x",
	"ShowGeneral":								True,
	"tempUnit":									"C",
	"ignoreNewDevices":							False,
	"folderNameDevices":						_defaultName,
	"ShowDevices":								False,
	"accept_HEATING":							True,
	"accept_SYSVAR":							True,
	"accept_WatchDog":							True,
	"accept_DutyCycle":							True,
	"ShowDebug":								False,
	"writeInfoToFile":							False,
	"showLoginTest":							False,
	"debugLogic":								False,
	"debugConnect":								False,
	"debugGetData":								False,
	"debugActions":								False,
	"debugDigest":								False,
	"debugUpdateStates":						False,
	"debugTime":								False,
	"debugSpecial":								False,
	"debugAll":									False,
	"ShowExpert":								False,
	"requestTimeout":							"10",
	"delayOffForButtons":						"2",  # seconds
	"getCompleteUpdateEvery":					"120", # in secs
	"getValuesEvery":							"1000" #  = 1 second
}

_defaultAllHomematic = { "type":"", "title":"", "indigoId":0, "indigoDevType":"deviceTypeId", "lastErrorMsg":0, "lastmessageFromHomematic":0, "indigoStatus":"active", "homemtaticStatus":"active", "childInfo":{},"sValue":0}

_debugAreas = {}
for kk in kDefaultPluginPrefs:
	if kk.find("debug") == 0:
		_debugAreas[kk.split("debug")[1]] = False


################################################################################
# noinspection PyUnresolvedReferences,PySimplifyBooleanCheck,PySimplifyBooleanCheck
class Plugin(indigo.PluginBase):
	####-----------------			  ---------
	def __init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs):
		indigo.PluginBase.__init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs)

	
###############  common for all plugins ############
		self.pluginShortName 			= _defaultName
		self.quitNOW					= ""
		self.delayedAction				= {}
		self.getInstallFolderPath		= indigo.server.getInstallFolderPath()+"/"
		self.indigoPath					= indigo.server.getInstallFolderPath()+"/"
		self.indigoRootPath 			= indigo.server.getInstallFolderPath().split("Indigo")[0]
		self.pathToPlugin 				= self.completePath(os.getcwd())

		self.pluginVersion				= pluginVersion
		self.pluginId					= pluginId
		self.pluginName					= pluginId.split(".")[-1]
		self.myPID						= os.getpid()
		self.pluginState				= "init"

		self.myPID 						= os.getpid()
		self.MACuserName				= pwd.getpwuid(os.getuid())[0]

		self.MAChome					= os.path.expanduser("~")
		self.userIndigoDir				= self.MAChome + "/indigo/"
		self.indigoPreferencesPluginDir = self.getInstallFolderPath+"Preferences/Plugins/"+self.pluginId+"/"
		self.DevicesXML					= self.pathToPlugin + "Devices.xml"
		self.PluginLogDir				= indigo.server.getLogsFolderPath( pluginId=self.pluginId )
		self.PluginLogFile				= indigo.server.getLogsFolderPath( pluginId=self.pluginId ) +"/plugin.log"

		formats =	{   logging.THREADDEBUG: "%(asctime)s %(msg)s",
						logging.DEBUG:       "%(asctime)s %(msg)s",
						logging.INFO:        "%(asctime)s %(msg)s",
						logging.WARNING:     "%(asctime)s %(msg)s",
						logging.ERROR:       "%(asctime)s.%(msecs)03d\t%(levelname)-12s\t%(name)s.%(funcName)-25s %(msg)s",
						logging.CRITICAL:    "%(asctime)s.%(msecs)03d\t%(levelname)-12s\t%(name)s.%(funcName)-25s %(msg)s"}

		date_Format = { logging.THREADDEBUG: "%Y-%m-%d %H:%M:%S",		# 5
						logging.DEBUG:       "%Y-%m-%d %H:%M:%S",		# 10
						logging.INFO:        "%Y-%m-%d %H:%M:%S",		# 20
						logging.WARNING:     "%Y-%m-%d %H:%M:%S",		# 30
						logging.ERROR:       "%Y-%m-%d %H:%M:%S",		# 40
						logging.CRITICAL:    "%Y-%m-%d %H:%M:%S"}		# 50
		formatter = LevelFormatter(fmt="%(msg)s", datefmt="%Y-%m-%d %H:%M:%S", level_fmts=formats, level_date=date_Format)

		self.plugin_file_handler.setFormatter(formatter)
		self.indiLOG = logging.getLogger("Plugin")  
		self.indiLOG.setLevel(logging.THREADDEBUG)

		self.indigo_log_handler.setLevel(logging.INFO)

		logging.getLogger("requests").setLevel(logging.WARNING)
		logging.getLogger("urllib3").setLevel(logging.WARNING)


		self.indiLOG.log(20,"initializing  ...")
		self.indiLOG.log(20,"path To files:          =================")
		self.indiLOG.log(10,"indigo                  {}".format(self.indigoRootPath))
		self.indiLOG.log(10,"installFolder           {}".format(self.indigoPath))
		self.indiLOG.log(10,"plugin.py               {}".format(self.pathToPlugin))
		self.indiLOG.log(10,"indigo                  {}".format(self.indigoRootPath))
		self.indiLOG.log(20,"detailed logging in     {}".format(self.PluginLogFile))
		if self.pluginPrefs.get('showLoginTest', True):
			self.indiLOG.log(20,"testing logging levels, for info only: ")
			self.indiLOG.log( 0, "logger  enabled for     0 ==> TEST ONLY ")
			self.indiLOG.log( 5, "logger  enabled for     THREADDEBUG    ==> TEST ONLY ")
			self.indiLOG.log(10, "logger  enabled for     DEBUG          ==> TEST ONLY ")
			self.indiLOG.log(20, "logger  enabled for     INFO           ==> TEST ONLY ")
			self.indiLOG.log(30, "logger  enabled for     WARNING        ==> TEST ONLY ")
			self.indiLOG.log(40, "logger  enabled for     ERROR          ==> TEST ONLY ")
			self.indiLOG.log(50, "logger  enabled for     CRITICAL       ==> TEST ONLY ")
			self.indiLOG.log(10, "Plugin short Name       {}".format(self.pluginShortName))
		self.indiLOG.log(10, "my PID                  {}".format(self.myPID))
		self.indiLOG.log(10, "Achitecture             {}".format(platform.platform()))
		self.indiLOG.log(10, "OS                      {}".format(platform.mac_ver()[0]))
		self.indiLOG.log(10, "indigo V                {}".format(indigo.server.version))
		self.indiLOG.log(10, "python V                {}.{}.{}".format(sys.version_info[0], sys.version_info[1] , sys.version_info[2]))
		self.epoch = datetime.datetime(1970, 1, 1)



		self.restartPlugin = ""

		self.pythonPath = ""
		if os.path.isfile("/Library/Frameworks/Python.framework/Versions/Current/bin/python3"):
				self.pythonPath				= "/Library/Frameworks/Python.framework/Versions/Current/bin/python3"
		self.indiLOG.log(20,"using '{}' for utily programs".format(self.pythonPath))

		
			

###############  END common for all plugins ############
		#self.sleep(0)
		return
		
####

	####-----------------			  ---------
	def __del__(self):
		indigo.PluginBase.__del__(self)

	###########################		INIT	## START ########################

	####----------------- @ startup set global parameters, create directories etc ---------
	def startup(self):
		if not checkIndigoPluginName(self, indigo): 
			self.sleep(20000)
			exit() 

		self.checkXMLFile()
		if self.restartPlugin != "":
			self.indiLOG.log(40,self.restartPlugin)
			time.sleep(20000)
			exit()

		self.initFileDir()

		try:
			self.initSelfVariables()

			self.currentVersion	= self.readJson(self.indigoPreferencesPluginDir+"dataVersion", defReturn={}).get("currentVersion",{})

			self.setDebugFromPrefs(self.pluginPrefs)

			self.getFolderId()

			self.pluginStartTime = time.time()

		except Exception as e:
			if "{}".format(e).find("None") == -1: self.indiLOG.log(40,"", exc_info=True)
			exit()

		return

	####-----------------			  ---------
	def checkXMLFile(self):
		try:
			f = open(self.DevicesXML,"r")
			xmlfile = f.read()
			f.close()
			createnewXMLfile = False
			for devType in k_mapHomematicToIndigoDevTypeStateChannelProps:
				dev = k_mapHomematicToIndigoDevTypeStateChannelProps[devType]
				if "file_deviceXML" not in dev:
					self.indiLOG.log(20,f"checkXMLFile devtype:{devType} does not have file_deviceXML item ")
					return
				xx = dev["file_deviceXML"]

				if  "Name" not in xx:
					self.indiLOG.log(20,f"checkXMLFile Name not in dev['file_deviceXML']")
					return

				if  "Devicetype" not in xx:
					self.indiLOG.log(20,f"checkXMLFile Devicetype not in dev['file_deviceXML']")
					return

				if devType not in xmlfile:
					self.indiLOG.log(20,f"checkXMLFile Devicetype xx['Devicetype'] not in xmlfile")
					createnewXMLfile = True
					break
				if xx["Name"] not in xmlfile:
					self.indiLOG.log(20,f"checkXMLFile Name: xx['Name'] not xmlfile")
					createnewXMLfile = True
					break


			if createnewXMLfile:
				out = "<Devices>\n"
				for devType in k_mapHomematicToIndigoDevTypeStateChannelProps:
					dev = k_mapHomematicToIndigoDevTypeStateChannelProps[devType]
					if "file_deviceXML" not in dev: continue
					xx = dev["file_deviceXML"]
					out1 = '  <Device type="'+ xx["Devicetype"] +'" id="'+devType+'" allowUserCreation="false">\n'
					out1 += '    <Name>'+ xx["Name"] +'</Name>\n'
					out1 += '    <ConfigUI> </ConfigUI>\n'
					out1 += '  </Device>\n\n'
					out += out1
				out += "</Devices>\n"
				# make backupfile from existing devcies.xml file
				if os.path.isfile(self.DevicesXML):
					try: os.rename(self.DevicesXML, self.DevicesXML+"-backup")
					except: pass
				f = open(self.DevicesXML,"w")
				f.write(out)
				f.close()
				self.restartPlugin  = "\n\n created new Devices.xml file,  old is in devices.xml-backup,\n\n"
				self.restartPlugin += " ============================================\n"
				self.restartPlugin += "    ====>  Please reload plugin     <==== \n"
				self.restartPlugin += "    ====>  That will take 30 secs   <==== \n"
				self.restartPlugin += " ============================================\n"
		except Exception as e:
			if "{}".format(e).find("None") == -1: self.indiLOG.log(40,"", exc_info=True)
		return 

	###########################		util functions	## START ########################


	####----------------- @ startup set global parameters, create directories etc ---------

	def initSelfVariables(self):
		try:
			self.writeToLogAfter 								= 300 # secs 
			self.curlPath 										= "/usr/bin/curl"
			self.variablesToDevicesLast							= {}
			self.variablesToDevices 							= {}
			self.checkOnThreads 								= time.time()
			self.autosaveChangedValues							= 0
			self.dayReset 										= -1
			self.averagesCounts									= {}
			self.nextFullStateCheck 							= 0 # do a full one at start
			self.nextFullStateCheckAfter						= 251# secs
			self.oneCycleComplete								= False
			self.lastDevStates									= {} # save execution time, only check those tha have chnaged w/o reading the states
			self.resetlastDevStates								= 999999999999999
			self.hostDevId										= 0
			self.homematicIdtoTitle								= {}
			self.numberOfRooms									= -1
			self.numberOfDevices								= -1
			self.numberOfVariables								= -1
			self.listOfprograms									= ""
			self.listOfEvents 									= ""
			self.lastSucessfullHostContact						= 0
			self.devStateChangeList								= {}
			self.devNeedsUpdate									= {}
			self.pendingCommand									= {}
			self.requestSession									= ""
			self.getcompleteUpdateLast							= 0
			#self.dayReset 										= int(self.pluginPrefs.get("dayReset",	datetime.datetime.now().day)
			self.getCompleteUpdateEvery 						= float(self.pluginPrefs.get("getCompleteUpdateEvery",	kDefaultPluginPrefs["getCompleteUpdateEvery"]))
			self.getValuesEvery 								= float(self.pluginPrefs.get("getValuesEvery", 			kDefaultPluginPrefs["getValuesEvery"]))/1000.
			self.requestTimeout									= float(self.pluginPrefs.get("requestTimeout",  		kDefaultPluginPrefs["requestTimeout"]))
			self.portNumber										= 		self.pluginPrefs.get("portNumber", 				kDefaultPluginPrefs["portNumber"])
			self.ipNumber										= 		self.pluginPrefs.get("ipNumber",  				kDefaultPluginPrefs["ipNumber"])
			self.collectAllValuesFirstBeforeUsing								= {}
			self.getValuesLast									= 0
			self.restartHomematicClass							= {}
			self.folderNameDevicesID							= 0
			self.roomMembers									= {}
			self.allDataFromHomematic							= self.readJson(fName=self.indigoPreferencesPluginDir + "allData.json")
			self.getDataNow										= time.time() + 9999999999
			self.devsWithenabledChildren						= []
			self.newDevice										= False
			self.fillDevStatesErrorLog 							= 0
			self.firstReadAll 									= False
			self.forceUpdateAtStart								= True		
			self.fixAllhomematic()
			self.calculateRate_Last 							= 0
			self.calculateRate_Every							= 250.
			self.USER_AUTHORIZATION 							= {}
			self.lastInfo 										= {}
			self.relinkParentsToChildrenFlag 					= 0
#			self.indiLOG.log(20,"k_supportedDeviceTypesFromHomematicToIndigo :\n{}".format(k_supportedDeviceTypesFromHomematicToIndigo))
#			self.indiLOG.log(20,"k_indigoToHomaticeDevices :\n{}".format(k_indigoToHomaticeDevices))
			#self.indiLOG.log(20,"k_mapHomematicToIndigoDevTypeStateChannelProps :\n{}".format(json.dumps(k_mapHomematicToIndigoDevTypeStateChannelProps, sort_keys=True, indent=2)))
			#self.indiLOG.log(20,"\n\n\nafter  k_mapHomematicToIndigoDevTypeStateChannelProps :\n{}".format(json.dumps(k_mapHomematicToIndigoDevTypeStateChannelProps, sort_keys=True, indent=2)))
			#self.indiLOG.log(20,"k_createStates:\n{}".format(json.dumps(k_createStates, sort_keys=True, indent=2)))

			self.rateStore = self.readJson(fName=self.indigoPreferencesPluginDir + "rates.json", defReturn={})
			self.updateRateStore = False


			#time.sleep(1000)
		except Exception as e:
			if "{}".format(e).find("None") == -1: self.indiLOG.log(40, "", exc_info=True)
			exit(0)


		return


	####-----------------	 ---------
	def fixAllhomematic(self, address=""):
		try:
			if address == "":
				self.homematicAllDevices = self.readJson(self.indigoPreferencesPluginDir+"homematicAllDevices.json", defReturn={})
				latestV = "address-A"
				if latestV not in self.homematicAllDevices:
					self.homematicAllDevices = dict()
					self.homematicAllDevices[latestV] = copy.copy(_defaultAllHomematic)
					self.homematicAllDevices[latestV]["indigoStatus"] = "active/comDisabled/deleted"
					self.homematicAllDevices[latestV]["type"] = "here goes the type"
					self.homematicAllDevices[latestV]["title"] = "here goes the title"
					self.homematicAllDevices[latestV]["homemtaticStatus"] = "active/gone"
					self.homematicAllDevices[latestV]["childInfo"] = {"homematicStateName1":"indigoId1","homematicStateName2":"indigoId2"} 
					self.indiLOG.log(20," added default entry {} to homematicAllDevices: {}".format(latestV, self.homematicAllDevices[latestV]))
	
		
				for addr in self.homematicAllDevices:
					for dd in _defaultAllHomematic:
						if dd not in self.homematicAllDevices[addr]:
							self.homematicAllDevices[addr][dd] = copy.copy(_defaultAllHomematic[dd] )
					for nr in self.homematicAllDevices[addr]["childInfo"]:
						for state in self.homematicAllDevices[addr]["childInfo"][nr]:
							try:	devId =  self.homematicAllDevices[addr]["childInfo"][nr][state]
							except:
								#self.indiLOG.log(20,"address{}: bad child:  nr:{:2} state{:10}".format(addr, nr, state ) )
								continue
							if devId == 0: continue
							if devId not in indigo.devices:
								self.indiLOG.log(20,"address:{:15}: bad child:  nr:{:2} state:{:22}, devId:{}".format(addr, nr, state, devId)  )
								self.homematicAllDevices[addr]["childInfo"][nr][state] = 0
			else:
				if address not in self.homematicAllDevices: 
					self.homematicAllDevices[address] = {}
					for dd in _defaultAllHomematic:
						if dd not in self.homematicAllDevices[address]:
							self.homematicAllDevices[address][dd] = copy.copy(_defaultAllHomematic[dd] )
		except	Exception as e:
				if "{}".format(e).find("None") == -1: self.indiLOG.log(40,"", exc_info=True)

	
#																																				indigoStatus: active, normal state, comDisabled  igored and dev exists  --  or dev deleted, must be reenabled ]

	####-----------------	 ---------
	def initFileDir(self):

			if not os.path.exists(self.indigoPreferencesPluginDir):
				os.mkdir(self.indigoPreferencesPluginDir)
			if not os.path.exists(self.indigoPreferencesPluginDir):
				self.indiLOG.log(50,"error creating the plugin data dir did not work, can not create: {}".format(self.indigoPreferencesPluginDir)  )
				self.sleep(1000)
				exit()

	####-----------------	 ---------
	def setDebugFromPrefs(self, theDict, writeToLog=True):
		self.debugAreas = []
		try:
			for d in _debugAreas:
				if theDict.get("debug"+d, False): self.debugAreas.append(d)
			if writeToLog: self.indiLOG.log(20, "debug areas: {} ".format(self.debugAreas))
		except	Exception as e:
				if "{}".format(e).find("None") == -1: self.indiLOG.log(40,"", exc_info=True)




	####-----------------	 ---------
	def isValidIP(self, ip0):
		if ip0 == "localhost": 							return True

		ipx = ip0.split(".")
		if len(ipx) != 4:								return False

		else:
			for ip in ipx:
				try:
					if int(ip) < 0 or  int(ip) > 255: 	return False
				except:
														return False
		return True


	####-----------------	 ---------
	def isValidMAC(self, mac):
		xxx = mac.split(":")
		if len(xxx) != 6:			return False
		else:
			for xx in xxx:
				if len(xx) != 2: 	return False
				try: 	int(xx, 16)
				except: 			return False
		return True
#

	####-------------------------------------------------------------------------####
	def testPing(self, ipN):
		try:
			ret = subprocess.call("/sbin/ping  -c 1 -W 40 -o " + ipN, shell=True) # send max 2 packets, wait 40 msec   if one gets back: stop

			#indigo.server.log(  ipN+"-1  {}".format(ret) +"  {}".format(time.time() - ss)  )
			if self.decideMyLog("Connect"): self.indiLOG.log(10,"(1) /sbin/ping  -c 1 -W 40 -o {} return-code: {}".format(ipN, ret) )

			if int(ret) == 0:  return 0
			self.sleep(0.1)
			ret = subprocess.call("/sbin/ping  -c 1 -W 400 -o " + ipN, shell=True)
			if self.decideMyLog("Connect"): self.indiLOG.log(10,"(2) /sbin/ping  -c 1 -W 400 -o {} return-code: {}".format(ipN, ret) )

			#indigo.server.log(  ipN+"-2  {}".format(ret) +"  {}".format(time.time() - ss)  )

			if int(ret) == 0:  return 0
			return 1
		except	Exception as e:
			if "{}".format(e).find("None") == -1: self.indiLOG.log(40,"ping error", exc_info=True)

		#indigo.server.log(  ipN+"-3  {}".format(ret) +"  {}".format(time.time() - ss)  )
		return 1



	####-------------------------------------------------------------------------####
	def writeJson(self, data, fName="", sort = True, doFormat=True, singleLines= False ):
		try:

			if self.decideMyLog("Logic"): self.indiLOG.log(10,"writeJson: fname:{}, sort:{}, doFormat:{}, singleLines:{}, data:{} ".format(fName, sort, doFormat, singleLines, str(data)[0:100]) )
	
			out = ""
			if data == "": return ""
			if data == {} : return ""
			if data is None: return ""

			if doFormat:
				if singleLines:
					out = ""
					for xx in data:
						out += "\n{}:{}".format(xx, data[xx])
				else:
					try: out = json.dumps(data, sort_keys=sort, indent=2)
					except: pass
			else:
					try: out = json.dumps(data, sort_keys=sort)
					except: pass

			if fName !="":
				f = self.openEncoding(fName,"w")
				f.write(out)
				f.close()
			return out

		except	Exception as e:
			self.indiLOG.log(40,"", exc_info=True)
			self.indiLOG.log(20,"writeJson error for fname:{} ".format(fName))
		return ""




	####-------------------------------------------------------------------------####
	def readJson(self, fName, defReturn={}):
		try:
			if os.path.isfile(fName):
				f = self.openEncoding(fName,"r")
				data = json.loads(f.read())
				f.close()
				return data
			else:
				return defReturn

		except	Exception as e:
			if "{}".format(e).find("None") == -1: self.indiLOG.log(40,"", exc_info=True)
			self.indiLOG.log(20,"readJson error for fName:{} ".format(fName))
		return defReturn



	####-----------------	 ---------
	def getFolderId(self):
		try:
			try:
				self.folderNameDevicesID = indigo.devices.folders.getId(self.pluginPrefs.get("folderNameDevices", _defaultName))
			except:
				pass
			if self.folderNameDevicesID == 0:
				try:
					ff = indigo.devices.folder.create(self.pluginPrefs.get("folderNameDevices", _defaultName))
					self.folderNameDevicesID = ff.id
				except:
					self.folderNameDevicesID = 0
		except	Exception as e:
			if "{}".format(e).find("None") == -1: self.indiLOG.log(40,"", exc_info=True)


		return


	####-----------------	 ---------
	def completePath(self,inPath):
		if len(inPath) == 0: return ""
		if inPath == " ":	 return ""
		if inPath[-1] !="/": inPath +="/"
		return inPath


	####-----------------	 ---------
	def filterSensorONoffIcons(self, filter="", valuesDict=None, typeId=None, devId=None, action=None):
		xList = []
		for ll in k_GlobalConst_ICONLIST:
			xList.append((ll[0]+"-"+ll[1],ll[0]+", "+ll[1]))
		xList.append(("=", "     "))
		return xList


	####-----------------	 ---------
	def printConfigMenu(self,  valuesDict=None, typeId=""):
		try:
			out =  "\n"
			out += "\n "
			out += "\n{}   =============plugin config Parameters========".format(_defaultName)

			out += "\ndebugAreas".ljust(40)								+	"{}".format(self.debugAreas)
			out += "\nlogFile".ljust(40)								+	self.PluginLogFile
			out += "\nipNumber".ljust(40)								+	self.ipNumber
			out += "\nport#".ljust(40)									+	self.portNumber
			out += "\nread values every".ljust(40)						+	"{}".format(self.getValuesEvery)
			out += "\nread complete info every".ljust(40)				+	"{}".format(self.getCompleteUpdateEvery)
			out += "\nrequestTimeout".ljust(40)							+	"{}".format(self.requestTimeout)

			out += "\n{}    =============plugin config Parameters========  END\n".format(_defaultName)

			out += self.listOfprograms
			out += self.listOfEvents

			out += "\n     Homematic address -> indigo id, name  =================="
			header = "\nnn  HomematicAddr ----- indigoState HM_state Title-----------------------------------------   IndigoId devType ---------  Indigo name -----------------------------------------------------   child info --------------------------------------------"
			out += header
			sList = []
			addList =[]
			for address in self.homematicAllDevices:
				if address.find("__") >-1: continue
				if len(address) < 2: continue
				sList.append(( self.homematicAllDevices[address]["type"], self.homematicAllDevices[address]["title"], self.homematicAllDevices[address]["indigoId"], address, self.homematicAllDevices[address]["lastErrorMsg"], self.homematicAllDevices[address]["childInfo"], self.homematicAllDevices[address]["indigoStatus"], self.homematicAllDevices[address]["homemtaticStatus"]))
				addList.append(address)

			for address in self.homematicAllDevices:
				if address in addList: continue
				if len(address) < 2: continue
				devId = self.homematicAllDevices[address]["indigoId"]
				if devId not in indigo.devices: continue
				dev = indigo.devices[devId]
				dType  = dev.deviceTypeId
				aname  = dev.states["title"]
				sList.append(( dType, aname, devId, address,"","","",""))

			nn = 0
			for items in sorted(sList):
				nn +=1 
				dType 		= items[0]
				htitle 		= items[1]
				indigoId 	= items[2]
				address 	= items[3]
				status		= items[6]
				HMstatus	= items[7]
				if address.find("address") == 0: continue
				iname		= "-----"
				child 		= str(items[5])
				if len(child) < 5: 
					chOut = "no child"
				else:
					maxL = 80
					chOut = child[0:maxL]
					if len(child) > maxL:
						for i in range(maxL, len(child), maxL):
							chOut += "\n{:190}{:}".format(" ",child[i:i+maxL])
					
				if address in self.homematicAllDevices:
					indigoId = self.homematicAllDevices[address]["indigoId"]
				if indigoId in indigo.devices:
					try:	
							dev = indigo.devices[indigoId]
							iname = dev.name
							htitle = dev.states.get("title"," no title")
					except: 
							iname = "no indigo name"
							htitle = "no title"
				out += "\n{:<4}{:20}{:12}{:9}{:45}{:12} {:19}{:68}{:}".format(nn, address, status, HMstatus, htitle, indigoId, dType, iname, chOut)
 
			out += header
			out += '\n'
			out += '\n'
			out += '\n'
			out += '================================ HELP ===========================\n'
			out += 'To install correctly: \n'
			out += '1. install CCU-jack on the raspberry pi \n'
			out += '2. in config set ip # , and if wanted change folder name etc. For the rest the default should be ok\n'
			out += '~ 10 seconds after config the new devices should appear in indigo \n'
			out += 'You can configure some devices eg \n'
			out += '   if min/max average.. states should be created\n'
			out += '   if certain child devices should be created eg how many valves are used etc\n'
			out += 'In the plugin menu you can set some devices to be ignored or used again.\n'
			out += 'Radiators and thermostats are fully supported and can be set\n'
			out += '\n'
			out += 'You can switch on/off relays, set dimmers, set sound and lights, alarms and displays, set variables in menu and actions\n'
			out += '\n'
			out += 'In file params_user.py you can define a new device if not already covered in parms.py\n'
			out += '   this is only for device types that are covered current, but just show up under a differrnt name like FROLL and BROLL\n'
			out += '   then set eg \n'
			out += '    "HMIP-BROLL": "HMIP-FROLL", \n'
			out += '   that will make a BROLL device look like an FROLL device to the plugin\n'
			out += '\n'
			out += '\n'
			out += '========== For device type BUTTON/ALARM/DIGITAL-input to work you need configure: \n'
			out += '   You can use any kind of button/ALARM...  device (the type has to be registed as a button in the params.py file in the plugin directory)\n'
			out += '   BUT you need to have somthing linked to the buttons of the device on homematic. W/o any action the states will stay stale.\n'
			out += '   Set up a program that just triggers on one of the states of each button.\n'
			out += '     Programerstellung: "\n'
			out += '      Bedingung: Wenn .. "\n'
			out += '      "Geraeteauswahl" <select the button device and channel x> "bei"   "Tastendruck kurz"\n'
			out += '      "Geraeteauswahl" <select the button device and channel y> "bei"   "Tastendruck kurz"\n'
			out += '      Aktivitaet: "\n'
			out += '         No actual action has to be defined, could use kill all previous actions for this device\n'
			out += '   Then the state / channel gets updated with a new time stamp and indigo will see the change \n'
			out += '\n'
			out += '========== For device type ASIR alarm action to work you need to\n'
			out += '   (a) create a system variable on homematic eg "alarmInput" type string\n'
			out += '   (b) add a program with a "Bedingung: Wenn"  "Systemzustand"   alarmInput    "bei": blank, select "bei Aktualisierung ausloesen"  \n'
			out += '       "Aktivitaet dann" leave empty;\n'
			out += '       "Aktivitaet Sonst" "Skript"  <<then put the script here>>    /  and select "sofort"  then save and activate\n'
			out += '   (c) In indigo menu or action you can create an action that will trigger the optical or acustical output.\n'
			out += '        select the ASIR device and the variable you just created.\n'
			out += '\n'
			out += 'start of script   ! are comments --------<<<\n'
			out += '! reads variable alarmInput\n'
			out += '! must be "address/dur unit/durationvalue/acoustic alarm/optical alarm\n'
			out += '! eg 00245F29B40C63/0/10/0/4\n'
			out += '! then send commands to device ASIR to start alarm\n'
			out += '!   the lines with if (debug) {... } can be deleted \n'
			out += '\n'
			out += 'var inp = dom.GetObject("alarmInput").Variable();\n'
			out += 'var debug = false;\n'
			out += 'if (debug){WriteLine(inp)};\n'
			out += '\n'
			out += 'var address = inp.StrValueByIndex("/", 0);\n'
			out += 'var DURATION_UNIT = inp.StrValueByIndex("/", 1);\n'
			out += 'var DURATION_VALUE = inp.StrValueByIndex("/", 2);\n'
			out += 'var ACOUSTIC_ALARM_SELECTION = inp.StrValueByIndex("/", 3);\n'
			out += 'var OPTICAL_ALARM_SELECTION = inp.StrValueByIndex("/", 4);\n'
			out += '\n'
			out += 'if (debug){WriteLine("address:                    "+ address+                  " len:"+ address.Length());}\n'
			out += 'if (address.Length() < 5){quit;};\n'
			out += '\n'
			out += 'if (debug){WriteLine("DURATION_UNIT:              "+ DURATION_UNIT+             " len:"+ DURATION_UNIT.Length().ToString());}\n'
			out += 'if ((DURATION_UNIT.Length() != 1) && (DURATION_UNIT.ToInteger() > 2) ){quit;};   ! = 0,1,2\n'
			out += '\n'
			out += 'if (debug){WriteLine("DURATION_VALUE:             "+ DURATION_VALUE+            " len:"+ DURATION_VALUE.Length());}\n'
			out += 'if ((DURATION_VALUE.Length() >2) && (DURATION_VALUE.ToInteger() > 60)){quit;}; ! = 0-60\n'
			out += '\n'
			out += 'if (debug){WriteLine("ACOUSTIC_ALARM_SELECTION:   "+ ACOUSTIC_ALARM_SELECTION+  " len:"+ ACOUSTIC_ALARM_SELECTION.Length());}\n'
			out += 'if ((ACOUSTIC_ALARM_SELECTION.Length() > 1) && (ACOUSTIC_ALARM_SELECTION.ToInteger() > 7)){quit;}; ! 0,1,2,3,4,5,6,7\n'
			out += '\n'
			out += 'if (debug){WriteLine("OPTICAL_ALARM_SELECTION:    "+ OPTICAL_ALARM_SELECTION+   " len:"+ OPTICAL_ALARM_SELECTION.Length());}\n'
			out += 'if ((OPTICAL_ALARM_SELECTION.Length() > 1) && (OPTICAL_ALARM_SELECTION.ToInteger() > 7)){quit;}; ! 0,1,2,3,4,5,6,7\n'
			out += '\n'
			out += 'dom.GetObject("HmIP-RF."+address+":3.DURATION_UNIT").State(DURATION_UNIT);\n'
			out += 'dom.GetObject("HmIP-RF."+address+":3.DURATION_VALUE").State(DURATION_VALUE);\n'
			out += 'dom.GetObject("HmIP-RF."+address+":3.ACOUSTIC_ALARM_SELECTION").State(ACOUSTIC_ALARM_SELECTION);\n'
			out += 'dom.GetObject("HmIP-RF."+address+":3.OPTICAL_ALARM_SELECTION").State(OPTICAL_ALARM_SELECTION);\n'
			out += ' >>> end of script ------------- \n\n'
			out += '\n'
			out += '\n'
			out += '================================ HELP END =======================\n'

			self.indiLOG.log(20,out)
		except	Exception as e:
			if "{}".format(e).find("None") == -1: self.indiLOG.log(40,"", exc_info=True)
		return

	####-----------------	 ---------
	def printDevicePropsMenu(self,  valuesDict=None, typeId=""):

		out = " Device props file:\n"
		try: out += "{}".format(json.dumps(k_mapHomematicToIndigoDevTypeStateChannelProps, sort_keys=True, indent=2))
		except: out+= str(k_mapHomematicToIndigoDevTypeStateChannelProps)
		out += "\n"
		self.indiLOG.log(20,out)
	####-----------------	 ---------
	def printDeviceXMLMenu(self,  valuesDict=None, typeId=""):

		out = " Device XML file:\n"
		for dev in k_mapHomematicToIndigoDevTypeStateChannelProps:
				aa = k_mapHomematicToIndigoDevTypeStateChannelProps[dev].get("deviceXML", "<>")
				try:
					xx = xmlEtree.parseString(aa)
					xx = xx.toprettyxml(indent="  ")
					zz = ""
					for yy in xx.split("\n"):
						if len(yy.replace(" ","")) < 2: continue
						zz += yy +"\n"
				except	Exception as e:
					zz = "\n\n===error  "+ aa + "\n"+str(e)+"\n\n"
				out += "=====dev:{}\n{}\n".format(dev, zz)
		out += "\n"
		self.indiLOG.log(20,out)

	####-----------------	 ---------
	def printDevices(self,  valuesDict=None, typeId=""):
		try:
			header = "\n  # #Dev ------ID--- Name----------------------------------------------------------------------- device type--------- #ofstates Enabd Address------------------ "
			out =  "\n"
			out += "\n "
			out += "\n   =============Homematic plugin device list========"
			out += header
			nDev = 0
			nPhysDev = 0
			nRooms = 0
			nSysVar = 0
			nOther = 0
			nChild = 0
			devList = []
			sysVarList = []
			roomList = []
			otherList = []
			heatList = []
			
			for dev in indigo.devices.iter(self.pluginId):
				if dev.deviceTypeId.find("ROOM") >-1:
					roomList.append(dev.name)
				elif dev.deviceTypeId.find("SYSVAR") >-1:
					sysVarList.append(dev.name)
				elif dev.deviceTypeId.find("Host") >-1:
					otherList.append(dev.name)
				elif dev.states.get("address","").find("INT") >-1:
					heatList.append(dev.name)
				else:
					devList.append(dev.name)
			devList = sorted(devList)
			sysVarList = sorted(sysVarList)
			roomList = sorted(roomList)
			otherList = sorted(otherList)
	
			for devName  in devList:
				dev = indigo.devices[devName]
				nDev += 1
				nStates = len(dev.states)
				if dev.states.get("childOf","") == "":
					nPhysDev += 1
				else:
					nChild += 1

				out += "\n{:3d} {:3d}{:13d} {:75s} {:18s} {:10d}   {:2b}   {:30s}".format(nDev, nPhysDev, dev.id, dev.name, dev.deviceTypeId, nStates, dev.enabled, dev.states["address"])

			for devName  in heatList:
				dev = indigo.devices[devName]
				nDev += 1
				nStates = len(dev.states)
				out += "\n{:3d} {:3d}{:13d} {:75s} {:18s} {:10d}   {:2b}   {:30s}".format(nDev, nPhysDev, dev.id, dev.name, dev.deviceTypeId, nStates, dev.enabled, dev.states["address"])

			for devName  in sysVarList:
				dev = indigo.devices[devName]
				nSysVar  += 1
				nDev += 1 
				nStates = len(dev.states)
				out += "\n{:3d} {:3d}{:13d} {:75s} {:18s} {:10d}   {:2b}   {:30s}".format(nDev, nSysVar, dev.id, dev.name, dev.deviceTypeId, nStates, dev.enabled, dev.states["address"])

			for devName  in roomList:
				dev = indigo.devices[devName]
				nRooms += 1
				nDev += 1
				nStates = len(dev.states)
				out += "\n{:3d} {:3d}{:13d} {:75s} {:18s} {:10d}   {:2b}   {:30s}".format(nDev, nRooms, dev.id, dev.name, dev.deviceTypeId, nStates, dev.enabled, dev.states["address"])

			for devName  in otherList:
				dev = indigo.devices[devName]
				nDev += 1
				nOther += 1
				nStates = len(dev.states)
				out += "\n{:3d} {:3d}{:13d} {:75s} {:18s} {:10d}   {:2b}   {:30s}".format(nDev, nOther, dev.id, dev.name, dev.deviceTypeId, nStates, dev.enabled, dev.states["address"])

			out += header
			out += "\nNumber of physical devices: {}, # of child devices: {}".format(nPhysDev, nChild)
			out += '\n'
			out += '================================ device list END =======================\n'

			self.indiLOG.log(20,out)
		except	Exception as e:
			if "{}".format(e).find("None") == -1: self.indiLOG.log(40,"", exc_info=True)
		return

	####-----------------	 ---------
	def padDisplay(self,status):
		if	 status == "up":		 return status.ljust(11)
		elif status == "expired":	 return status.ljust(8)
		elif status == "down":		 return status.ljust(9)
		elif status == "susp":		 return status.ljust(9)
		elif status == "changed":	 return status.ljust(8)
		elif status == "double":	 return status.ljust(8)
		elif status == "ignored":	 return status.ljust(8)
		elif status == "off":		 return status.ljust(11)
		elif status == "REC":		 return status.ljust(9)
		elif status == "ON":		 return status.ljust(10)
		else:						 return status.ljust(10)

	
	####-------------------------------------------------------------------------####
	def readPopen(self, cmd):
		try:
			ret, err = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
			return ret.decode('utf-8'), err.decode('utf-8')

		except Exception as e:
			if "{}".format(e).find("None") == -1: self.indiLOG.log(40,"", exc_info=True)


	####-------------------------------------------------------------------------####
	def openEncoding(self, fName, readOrWrite):

		try:
			if readOrWrite.find("b") >-1:
				return open( fName, readOrWrite)

			if sys.version_info[0]  > 2:
				return open( fName, readOrWrite, encoding="utf-8")

			else:
				return codecs.open( fName, readOrWrite, "utf-8")

		except	Exception as e:
			self.indiLOG.log(20,"openEncoding error w r/w:{}, fname:".format(readOrWrite, fName))
			self.indiLOG.log(40,"", exc_info=True)


	####-----------------	 ---------
	def inpDummy(self, valuesDict=None, typeId="", devId=""):
		return valuesDict



	###########################		util functions	## END  ########################


	###########################		ACTIONS START  ########################
	def getAllDataCallback(self,  valuesDict={}, typeId=""):

		self.getcompleteUpdateLast = 0.
		self.resetlastDevStates = time.time() + 10

		return 
	###########################		ACTIONS START  ########################
	def setActiverelinkParentsToChildren(self, valuesDict={}, typeId=""):
		self.indiLOG.log(30,"relinkParentsToChildren, action added to the queue")
		self.relinkParentsToChildrenFlag = int(valuesDict.get("numberOfDevices",5))
		return 


	####-------------action filters  -----------
	def filterVariables(self, filter="", valuesDict="", typeId="", xxx=""):

		try:
			ret = []
			devTypes = k_actionTypes.get(filter,"variable")
			#self.indiLOG.log(20,"filterDevices: filter given.. filter:{}, devTypes:{}, valuesDict:{}".format(filter, devTypes, valuesDict))
			if devTypes == []: 
				self.indiLOG.log(20,"filterDevices: no proper filter given.. filter:{}, devType:{}".format(filter, devType))
				return ret

			boolList = []
			floatList = []
			stringList = []
	
			for dev in indigo.devices.iter(self.pluginId):
				#self.indiLOG.log(20,"filterDevices: comparing. devType:{}".format(dev.deviceTypeId))
				if dev.deviceTypeId in devTypes: 
					
					address = dev.states["address"]
					if self.homematicAllDevices[address]["sValue"] != 0: continue
					if    dev.deviceTypeId.find("FLOAT")	> -1: floatList.append( [dev.id, dev.name+"="+str(dev.states["sensorValue"])+"=NUMBER"])
					elif  dev.deviceTypeId.find("STRING")	> -1: stringList.append([dev.id, dev.name+"="+str(dev.states["value"])+"=STRING"])
					elif  dev.deviceTypeId.find("BOOL")		> -1: boolList.append(  [dev.id, dev.name+"="+str(dev.states["onOffState"])+"=BOOL"])
			ret = boolList + floatList + stringList
		except	Exception as e:
			if "{}".format(e).find("None") == -1: self.indiLOG.log(40,"", exc_info=True)

		return ret

	####-------------action filters  -----------
	def filterDevices(self, filter="", valuesDict="", typeId="", xxx=""):

		try:
			ret = []
			devTypes = k_actionTypes.get(filter,"")
			#self.indiLOG.log(20,"filterDevices: filter given.. filter:{}, devTypes:{}, valuesDict:{}".format(filter, devTypes, valuesDict))
			if devTypes == []: 
				self.indiLOG.log(20,"filterDevices: no proper filter given.. filter:{}, devType:{}".format(filter, devType))
				return ret

			for dev in indigo.devices.iter(self.pluginId):
				#self.indiLOG.log(20,"filterDevices: comparing. devType:{}".format(dev.deviceTypeId))
				if dev.deviceTypeId in devTypes: 
					ret.append([dev.id, dev.name])

		except	Exception as e:
			if "{}".format(e).find("None") == -1: self.indiLOG.log(40,"", exc_info=True)

		return ret

	####-------------button -----------
	def dynamicCallbackSetdeviceID(self, valuesDict={}, typeId=""):

		try:
			#self.indiLOG.log(20,"confirmDeviceButton: :{}".format(valuesDict))
			valuesDict["confirmedDevice"] = valuesDict.get("devId","")
			if   valuesDict.get("MSG","").find("select next device/state        3") > -1: 			valuesDict["MSG"] = valuesDict["MSG"].replace("3","2")
			elif valuesDict.get("MSG","").find("select next device/state        2") > -1:			valuesDict["MSG"] = valuesDict["MSG"].replace("2","1")
			elif valuesDict.get("MSG","").find("select next device/state        1") > -1: 			valuesDict["MSG"] = valuesDict["MSG"].replace("1","")
			elif valuesDict["confirmedDevice"]  == "": 												valuesDict["MSG"] = "select device"
			elif "stateName"    in valuesDict and valuesDict.get("stateName","")     in ["","0"]: 	valuesDict["MSG"] = "select state"
			elif "propertyName" in valuesDict and valuesDict.get("propertyName","")  in ["","0"]:	valuesDict["MSG"] = "select property"
			else:																
				devId =  valuesDict.get("confirmedDevice","")
				#   these 2 should not happen... just in case
				if devId == "": 					 return valuesDict
				if int(devId) not in indigo.devices: return valuesDict

				dev = indigo.devices[int(devId)]
				valuesDict["MSG"] = "enter new value"

				if "stateName" in valuesDict:
					oldValue = dev.states.get(valuesDict.get("stateName",""))

				elif "propertyName" in valuesDict:
					oldValue = dev.pluginProps[valuesDict.get("propertyName","")]

				valuesDict["oldValue"] = oldValue
		except	Exception as e:
			if "{}".format(e).find("None") == -1: self.indiLOG.log(40,"", exc_info=True)

		return valuesDict



	####-------------action filters  -----------
	def selectState(self, filter="", valuesDict={}, typeId="", xxx=""):

		ret = []
		try:
			devId =  valuesDict.get("confirmedDevice","")
			#self.indiLOG.log(20,"selectState: valuesDict:{}".format(valuesDict))
			if devId == "": return [["0","select device first"]]
			dev = indigo.devices[int(devId)]
			for state in dev.states:
				ret.append([state, state])
		except	Exception as e:
			if "{}".format(e).find("None") == -1: self.indiLOG.log(40,"", exc_info=True)

		return ret
	####-------------action filters  -----------
	def selectProperty(self, filter="", valuesDict={}, typeId="", xxx=""):

		ret = []
		try:
			devId =  valuesDict.get("confirmedDevice","")
			#self.indiLOG.log(20,"selectState: valuesDict:{}".format(valuesDict))
			if devId == "": return [["0","select device first"]]
			props = indigo.devices[int(devId)].pluginProps
			for prop in props:
				ret.append([str(prop), str(prop)])
		except	Exception as e:
			if "{}".format(e).find("None") == -1: self.indiLOG.log(40,"", exc_info=True)

		return ret


	####-------------action filters  -----------
	def executeOverwriteButtonState(self, valuesDict={}, typeId="", xxx=""):

		try:
			devId =  valuesDict.get("confirmedDevice","")
			if devId == "": return valuesDict
			dev = indigo.devices[int(devId)]
			newValue  = valuesDict.get("newValue","")
			newValueUi  = valuesDict.get("newValueUi","")
			stateName = valuesDict.get("stateName","")
			oldValue  = dev.states.get(stateName, "")
			if   type(oldValue) == type(1): 	newValue = int(newValue)
			elif type(oldValue) == type(1.): 	newValue = float(newValue)
			elif type(oldValue) == type(True):	newValue = newValue in ["t","true","T","True","1","on"]
			self.indiLOG.log(20,"execute Overwrite Device[State]: \"{}[{}]\", oldValue:\"{}\", newValue:\"{}\", newValueUi:\"{}\"".format(dev.name, stateName, oldValue, newValue, newValueUi))
			if newValueUi != "": 	dev.updateStateOnServer(stateName, newValue, uiValue=newValueUi )
			else:					dev.updateStateOnServer(stateName, newValue)
			valuesDict["MSG"] = "dev/state overwritten, select next device/state        3"
			valuesDict["stateName"] = ""
		except	Exception as e:
			if "{}".format(e).find("None") == -1: self.indiLOG.log(40,"", exc_info=True)

		return valuesDict
	####-------------action filters  -----------
	def executeOverwriteButtonProperty(self, valuesDict={}, typeId="", xxx=""):

		try:
			devId =  valuesDict.get("confirmedDevice","")
			if devId == "": return valuesDict
			dev = indigo.devices[int(devId)]
			props = dev.pluginProps
			newValue  = valuesDict.get("newValue","")
			propertyName = valuesDict.get("propertyName","")
			oldValue  = props.get(propertyName, "")
			if   type(oldValue) == type(1): 	newValue = int(newValue)
			elif type(oldValue) == type(1.): 	newValue = float(newValue)
			elif type(oldValue) == type(True):	newValue = newValue in ["t","true","T","True","1","on"]
			self.indiLOG.log(20,"execute Overwrite Device[Prop]: \"{}[{}]\", oldValue:\"{}\", newValue:\"{}\"".format(dev.name, propertyName, oldValue, newValue))
			props[propertyName] = newValue
			dev.replacePluginPropsOnServer(props)
			dev = indigo.devices[int(devId)]
			valuesDict["MSG"] = "dev/prop overwritten, select next device/prop        3"
			valuesDict["propertyName"] = ""
		except	Exception as e:
			if "{}".format(e).find("None") == -1: self.indiLOG.log(40,"", exc_info=True)

		return valuesDict

	####-------------ignore / unignore devices  -----------
	def filterHomematicAllDevices(self, filter="", valuesDict={}, typeId="",xxx=""):

		try:
			retUse = []
			retEna = []
			retIgn = []
			sList = []
			for address in self.homematicAllDevices:
				if address.find("address-") >-1: continue
				if self.homematicAllDevices[address]["type"] in ["RPI-RF-MOD",""," "]: continue  #["STRING","ALARM","ROOM","FLOAT","BOOL",
				sList.append(( self.homematicAllDevices[address]["type"], self.homematicAllDevices[address]["title"], address))


			for items in sorted(sList):
				enabled = False
				exists = False
				try:
					address 	= items[2]
					dType 		= self.homematicAllDevices[address]["type"]
					name 		= self.homematicAllDevices[address]["title"]
					indigoId 	= int(self.homematicAllDevices[address]["indigoId"])
					if indigoId in indigo.devices: 
						enabled = indigo.devices[indigoId].enabled
					else:
						indigoId = 0
						self.homematicAllDevices[address]["indigoId"] = 0
						if self.homematicAllDevices[address]["indigoStatus"] != "create":
							self.homematicAllDevices[address]["indigoStatus"] =  "deleted"
				except:
					self.indiLOG.log(20,"filterHomematicAllDevices: items:{}".format(items))
					continue

				
				if   indigoId > 0 and (self.homematicAllDevices[address]["indigoStatus"] == "active" and enabled):
					retUse.append((address,"{:10s}::{}::{}  ACTIVE".format(dType, name, address)))

				elif  indigoId > 0 and  self.homematicAllDevices[address]["indigoStatus"] in ["comDisabled"]:
					retIgn.append((address,"{:10s}::{}::{}  IGNORED-EXISTING".format(dType, name, address)))

				elif  indigoId == 0 and self.homematicAllDevices[address]["indigoStatus"] in ["deleted"]:
					retIgn.append((address,"{:10s}::{}::{}  IGNORED-DELETED".format(dType, name, address)))

				else:
					retEna.append((address,"{:10s}::{}::{}  ENABLED".format(dType, name, address)))

		except	Exception as e:
			if "{}".format(e).find("None") == -1: self.indiLOG.log(40,"", exc_info=True)

		if filter == "all":
			return retUse + retEna
		return retUse+retEna+retIgn

	####-------------ignore / unignore devices  -----------
	def filterHomematicAllDevicesReturnDevID(self, filter="", valuesDict={}, typeId="",xxx=""):

		try:
			retUse = []
			retDis = []
			retIgn = []
			retOther = []
			sList = []
			for address in self.homematicAllDevices:
				if address.find("address-") > -1: continue
				if self.homematicAllDevices[address]["type"] in ["RPI-RF-MOD",""," "]: continue  #["STRING","ALARM","ROOM","FLOAT","BOOL",
				indigoId 	= int(self.homematicAllDevices[address]["indigoId"])
				name = self.homematicAllDevices[address]["title"]
				theType = self.homematicAllDevices[address]["type"]
				if theType in ["ALARM", "BOOL", "STRING", "FLOAT"]: theType = "  "+theType
				elif theType in ["ROOM"]: theType = " "+theType
				enabled = False
				if indigoId in indigo.devices: 
					enabled = indigo.devices[indigoId].enabled
				else:
					indigoId = 0
					self.homematicAllDevices[address]["indigoId"] = 0
					if self.homematicAllDevices[address]["indigoStatus"] != "create":
						self.homematicAllDevices[address]["indigoStatus"] =  "deleted"
				sList.append((theType+name, name, address, enabled, indigoId))

			for items in sorted(sList):
				exists = False
				address 	= items[2]
				dType 		= self.homematicAllDevices[address]["type"]
				name 		= items[1]
				indigoId 	= items[4]
				enabled 	= items[3]

				
				if   indigoId > 0 and (self.homematicAllDevices[address]["indigoStatus"] == "active" and enabled):
					retUse.append((indigoId,"{:10s}::{}::{}  ACTIVE".format(dType, name, address)))

				elif  indigoId > 0 and  not enabled:
					retDis.append((indigoId,"{:10s}::{}::{}  DISABLED".format(dType, name, address)))

				elif  indigoId == 0 and self.homematicAllDevices[address]["indigoStatus"] in ["deleted"]:
					retIgn.append((indigoId,"{:10s}::{}::{}  IGNORED-DELETED".format(dType, name, address)))

				else:
					retOther.append((indigoId,"{:10s}::{}::{}  ??".format(dType, name, address)))

		except	Exception as e:
			if "{}".format(e).find("None") == -1: self.indiLOG.log(40,"", exc_info=True)

		return retOther+retIgn+retDis+retUse


	####-------------
	def ignoreDevicesButton(self, valuesDict, typeId=""):

		try:
			address = valuesDict["address"]
			if address not in self.homematicAllDevices: return valuesDict

			name = ""
			if address in self.homematicAllDevices and self.homematicAllDevices[address]["indigoId"] in indigo.devices:
				dev = indigo.devices[self.homematicAllDevices[address]["indigoId"]]
				name = dev.name
				indigo.device.enable(dev, value=False)

			elif address in self.homematicAllDevices :
				name = self.homematicAllDevices[address]["title"]

			self.homematicAllDevices[address]["indigoStatus"] = "comDisabled"
			if self.homematicAllDevices[address]["indigoId"] not in indigo.devices:
				self.homematicAllDevices[address]["indigoStatus"] = "deleted"
				self.homematicAllDevices[address]["indigoId"] = 0
			self.writeJson(self.homematicAllDevices, fName=self.indigoPreferencesPluginDir + "homematicAllDevices.json", doFormat=True, singleLines=False )
			self.indiLOG.log(20,"ignoreDevicesButton  set  {}::{}::{}  to IGNORE".format(address, name, self.homematicAllDevices.get(address,{})))
		except	Exception as e:
			if "{}".format(e).find("None") == -1: self.indiLOG.log(40,"", exc_info=True)

		return valuesDict


	####-------------
	def useDevicesButton(self, valuesDict, typeId=""):

		try:
			address = valuesDict["address"]
			if len(address) < 2: return valuesDict
			if address not in self.homematicAllDevices: return valuesDict

			name = ""
			indigoId = self.homematicAllDevices[address]["indigoId"]
			if indigoId in indigo.devices:
				dev= indigo.devices[indigoId]
				name = dev.name
				indigo.device.enable(dev, value=True)
				self.homematicAllDevices[address]["indigoStatus"] = "active" 

			else:
				name = self.homematicAllDevices[address]["title"]
				self.homematicAllDevices[address]["indigoId"]  = 0
				self.getcompleteUpdateLast = 1
				self.indiLOG.log(20,"useDevicesButton  set  getcompleteUpdateLast = 0")
				self.homematicAllDevices[address]["indigoStatus"] = "create" 

			self.indiLOG.log(20,"useDevicesButton  set  {}::{}::{}  to USE".format(address, name, self.homematicAllDevices.get(address,"")))
			self.writeJson(self.homematicAllDevices, fName=self.indigoPreferencesPluginDir + "homematicAllDevices.json", doFormat=True, singleLines=False )
		except	Exception as e:
			if "{}".format(e).find("None") == -1: self.indiLOG.log(40,"", exc_info=True)

		return valuesDict


	####-------------
	def removeFromListDevicesButton(self, valuesDict, typeId=""):

		try:
			address = valuesDict["address"]
			if len(address) < 2: return valuesDict
			if address not in self.homematicAllDevices: return valuesDict
			self.indiLOG.log(20,"useDevicesButton  remove   {}::{}".format(address, self.homematicAllDevices[address]))
			del  self.homematicAllDevices[address]
			self.writeJson(self.homematicAllDevices, fName=self.indigoPreferencesPluginDir + "homematicAllDevices.json", doFormat=True, singleLines=False )
		except	Exception as e:
			if "{}".format(e).find("None") == -1: self.indiLOG.log(40,"", exc_info=True)

		return valuesDict


	####-------------ignore / unignore devices  ----------- END


	#  ---------- variable action
	def setVariableAction(self, action, typeId):
		return self.setVariable(action.props, typeId)

	def setVariable(self, action, typeId=""):

		try:
			
			if self.decideMyLog("Actions"): self.indiLOG.log(20,"setVariable action:{}".format(str(action).replace("\n",", ")))

			dev = indigo.devices[int(action["deviceId"])]
			if dev.deviceTypeId not in k_mapHomematicToIndigoDevTypeStateChannelProps: return 
			out = action["text"]
			if dev.deviceTypeId.find("FLOAT") >-1:	
				if action["text"].find(".") >-1:		out = float(action["text"])
				else:									out = int(action["text"])
			elif dev.deviceTypeId.find("BOOL")	>-1:	out = self.isBool2(action["text"],False,False)
			elif dev.deviceTypeId.find("ALARM")	>-1:	out = self.isBool2(action["text"],False,False)
			else:										out = action["text"]

			self.doSendActionVariable( dev.states["address"], json.dumps({"v": out}) )

		except Exception as e:
			if "{}".format(e).find("None") == -1: self.indiLOG.log(40,"", exc_info=True)





	#  ---------- thermostat action  boost
	def boostThermostatAction(self, action, typeId):
		return self.boostThermostat(action.props, typeId)

	def boostThermostat(self, action, typeId=""):

		try:
			
			if self.decideMyLog("Actions"): self.indiLOG.log(20,"boostThermostat action:{}".format(str(action).replace("\n",", ")))

			dev = indigo.devices[int(action["deviceId"])]

			address = dev.states["address"]

			if dev.deviceTypeId not in k_mapHomematicToIndigoDevTypeStateChannelProps: return 
			acp = k_mapHomematicToIndigoDevTypeStateChannelProps[dev.deviceTypeId].get("actionParams",{})

			props = dev.pluginProps
			dj = json.dumps({"v": action.get("OnOff","on") == "on" })

			if "states" not in acp: return
			state = acp["states"].get("BOOST_MODE","BOOST_MODE")
			channels = acp["channels"].get("BOOST_MODE","1")
			self.doSendAction( channels, address, state, dj )

		except Exception as e:
			if "{}".format(e).find("None") == -1: self.indiLOG.log(40,"", exc_info=True)




	# Main thermostat action set target temp called by Indigo Server.
	####-------------
	def actionControlThermostat(self, action, typeId=""):

		try:
			dev = indigo.devices[action.deviceId]
			if self.decideMyLog("Actions"): self.indiLOG.log(20,"actionControlThermostat  action:{}".format( str(action).replace("\n",", ")))
			if action.thermostatAction == indigo.kThermostatAction.SetHeatSetpoint: 
				value = action.actionValue
			elif action.thermostatAction == indigo.kThermostatAction.DecreaseHeatSetpoint: 
				value = dev.states["setpointHeat"] - action.actionValue
			elif action.thermostatAction == indigo.kThermostatAction.IncreaseHeatSetpoint: 
				value = dev.states["setpointHeat"] + action.actionValue
			else:
				value = 18

			address = dev.states["address"]

			props = dev.pluginProps
			dj = json.dumps({"v": value })

			if dev.deviceTypeId not in k_mapHomematicToIndigoDevTypeStateChannelProps: return
			acp = k_mapHomematicToIndigoDevTypeStateChannelProps[dev.deviceTypeId].get("actionParams",{})

			if "states" not in acp: return
			state =	acp["states"].get("SET_POINT_TEMPERATURE","SET_POINT_TEMPERATURE")
			channels = acp["channels"].get("SET_POINT_TEMPERATURE",["1"])

			self.doSendAction( channels, address, state, dj )

		except Exception as e:
			if "{}".format(e).find("None") == -1: self.indiLOG.log(40,"", exc_info=True)




	####-------------
	def sendTSringToDisplayAction(self, action, typeId):
		return self.sendTSringToDisplay(action.props, typeId)

	####-------------
	def sendTSringToDisplay(self, valuesDict, typeId):
		try:
#
#  send something like this 
# curl  -X PUT -d '{"v":"{DDBC=WHITE,DDTC=BLACK,DDA=CENTER,DDS=abc,DDI=2,DDID=1},{DDBC=WHITE,DDTC=BLACK,DDI=1,DDA=CENTER,DDS=def,DDID=2},{DDBC=WHITE,DDTC=BLACK,DDI=3,DDA=CENTER,DDS=Zeile3,DDID=3},{DDBC=WHITE,DDTC=BLACK,DDI=5,DDA=CENTER,DDS=Zeile4,DDID=4},{DDBC=WHITE,DDTC=BLACK,DDI=3,DDA=CENTER,DDS=Zeile5,DDID=5,DDC=true},{R=1,IN=5,ANS=4}"}'  http://192.168.1.49:2121/device/002A60C9950CB5/3/COMBINED_PARAMETER/~pv
#
#
			address = indigo.devices[int(valuesDict["devId"])].states["address"]

			lines = ["","","","",""]
			for ii in range(5):
				jj = str(ii+1)
				for item in ["DDBC","DDTC","DDA","DDS","DDI"]:
					xx =  item+"-"+jj 
					if xx not in valuesDict: # all items must be present 
						lines[ii] = ""
						break
					if item != "DDS" and valuesDict[xx] == "":  # reject lines w empty props, but  accept empty text line = 1 space 
						lines[ii] = ""
						break
					if item == "DDI" and valuesDict[xx] == "0": continue # no icon
						
					lines[ii] +=  item +"="+valuesDict[xx]+","

				if lines[ii] != "": lines[ii] += "DDID="+jj

			#if self.decideMyLog("Actions"): self.indiLOG.log(20,"sendTSringToDisplay lines:{}".format(lines))
			outLines = ""
			for nn in range(len(lines)):
				if lines[nn] == "": continue
				outLines += "{"+lines[nn]+"}"+","

			sound = ""
			if "ANS" in valuesDict and valuesDict["ANS"] not in ["","-1"]:
				R = valuesDict.get("ANS","1")
				IN = valuesDict.get("IN","1")
				sound = ",{R="+R+",IN="+IN+",ANS="+valuesDict["ANS"]+"}"

			outLines = outLines.strip(",").strip("}") + ',DDC=true}' +sound
			#if self.decideMyLog("Actions"): self.indiLOG.log(20,"sendTSringToDisplay outLines:{}".format(outLines))

			dj = json.dumps({"v":outLines })
			self.doSendAction( ["3"], address, "COMBINED_PARAMETER", dj )

		except Exception as e:
			if "{}".format(e).find("None") == -1: self.indiLOG.log(40,"", exc_info=True)




	####- set alarm on ASIR
	def alarmSIRENaction(self, action, typeId):
		return self.alarmSIREN(action.props, typeId)

	def alarmSIREN(self, action, typeId):
		try:
			if self.decideMyLog("Actions"): self.indiLOG.log(20,"alarmASIR action:{}".format(action))

			addressDev = indigo.devices[int(action["alarmDevId"])].states["address"]
			addressVar = indigo.devices[int(action["alarmVarId"])].states["address"]

			DURATION = int(action["DURATION"])
			unit = 0
			if DURATION >= 60:
				DURATION //= 60
				unit = 1
						#address/unit/length/acoust/optical
			dj = { "v":"{}/{}/{}/{}/{}".format(addressDev, unit, DURATION, action["ACOUSTIC_ALARM_SELECTION"], action["OPTICAL_ALARM_SELECTION"]) }
	
			self.doSendActionVariable( addressVar, json.dumps(dj) )

		except Exception as e:
			if "{}".format(e).find("None") == -1: self.indiLOG.log(40,"", exc_info=True)





	####-  lock/unlock 
	####-------------
	def LockUnLockAction(self, action, typeId):
		return self.LockUnLock(action.props, typeId)

	####-------------
	def LockUnLock(self, action, typeId):
		try:


			if self.decideMyLog("Actions"): self.indiLOG.log(20,"LockUnLock  action:{}".format( str(action).replace("\n",", ")))


			address = dev.states["address"].split("-")[0]
			channels = []

			if dev.deviceTypeId not in k_mapHomematicToIndigoDevTypeStateChannelProps: 
				self.indiLOG.log(30,"LockUnLock {}  device:{}, bad deviceTypeId:{} ".format(dev.name, action, dev.deviceTypeId) )
				return

			acp =  k_mapHomematicToIndigoDevTypeStateChannelProps[dev.deviceTypeId].get("actionParams",{})


			if self.decideMyLog("Actions"): self.indiLOG.log(20,"LockUnLock acp:{}".format(acp))

			if "states" not in acp: 
				self.indiLOG.log(30,"LockUnLock {}  device:{}, states not in acp:{} ".format(dev.name, action, acp) )
				return

			dj = "{}"
			for ch in acp["channels"]:
				channels.append(ch) # turn off all channels
			if action["value"] == "lock":
				dj =json.dumps({"v":acp["OnOffValues"]["On"]})
			else:
				dj =json.dumps({"v":acp["OnOffValues"]["Off"]})
			state =	acp["states"].get("OnOff","LOCK_TARGET_LEVEL")

			self.doSendAction( channels, address, state, dj )
								

		except Exception as e:
			if "{}".format(e).find("None") == -1: self.indiLOG.log(40,"", exc_info=True)


		

	####- dimmer relay actions
	####-------------
	def actionControlDimmerRelay(self, action, dev):
		try:


			if self.decideMyLog("Actions"): self.indiLOG.log(20,"actionControlDimmerRelay dev:{}, action:{}".format(dev.name, str(action).replace("\n",", ")))


			address = dev.states["address"].split("-")[0]
			channels = []

			if dev.deviceTypeId not in k_mapHomematicToIndigoDevTypeStateChannelProps: 
				self.indiLOG.log(30,"actionControlDimmerRelay {}  device:{}, bad deviceTypeId:{} ".format(dev.name, action, dev.deviceTypeId) )
				return

			acp = k_mapHomematicToIndigoDevTypeStateChannelProps[dev.deviceTypeId].get("actionParams",{})

			if self.decideMyLog("Actions"): self.indiLOG.log(20,"actionControlDimmerRelay acp:\n{}".format(acp))

			if "states" not in acp: 
				self.indiLOG.log(30,"actionControlDimmerRelay {}  device:{}, states not in acp:{} ".format(dev.name, action, acp) )
				return

			dj = "{}"

			if action.deviceAction == indigo.kDeviceAction.TurnOn:
				if "mult" in acp:
					dj = json.dumps({"v": round(100* acp["mult"]["Dimm"],2)})
					for ch in acp["channels"].get("Dimm",["1"]):
						channels.append(ch)	
						break	
				else:
					dj = json.dumps({"v":True })
					state =		acp["states"].get("OnOff","")
					for ch in acp["channels"].get("OnOff",["1"]):
						channels.append(ch)	# turn on only one channel
						break	

			elif action.deviceAction == indigo.kDeviceAction.TurnOff:
				if "mult" in acp:
					dj = json.dumps({"v":0.})
					state =		acp["states"].get("Dimm","")
					for ch in acp["channels"].get("Dimm",["1"]):
						channels.append(ch)	
				else:
					dj = json.dumps({"v":False })
					state =		acp["states"].get("OnOff","")
					for ch in acp["channels"].get("OnOff",["1"]):
						channels.append(ch) # turn off all channels

			elif action.deviceAction == indigo.kDeviceAction.Toggle:
				if "onOffState" in dev.states:
					state =		acp["states"].get("OnOff","")
					if dev.states["onOffState"]:
						dj = json.dumps({"v":False})
						for ch in acp["channels"].get("OnOff",["1"]):
							channels.append(ch) # turn off all channels
					else:
						dj = json.dumps({"v":True})
						for ch in acp["channels"].get("OnOff",["1"]):
							channels.append(ch) # turn only ch 1
							break


			elif action.deviceAction == indigo.kDeviceAction.SetBrightness:
				if action.actionValue == 0:	
					dj = json.dumps({"v":0 })
					state =		acp["states"].get("Dimm","")
					for ch in acp["channels"].get("Dimm",["1"]):
						channels.append(ch) # turn off all channels
				else:
					state =		acp["states"].get("Dimm","")
					if "mult" in acp:
						dj = json.dumps({"v": round(action.actionValue*acp["mult"]["Dimm"] ,2)})
					else:
						dj = json.dumps({"v":action.actionValue})
					for ch in acp["channels"].get("Dimm",["1"]):
						channels.append(ch)	# dimm only one channel
						break
			elif action.deviceAction == indigo.kDeviceAction.SetColorLevels:
				colorCode = 0
				if "whiteLevel"  in action.actionValue:	
					dj = json.dumps({"v":7})
					state = "COLOR"
					evalChannels = [str(eval(acp["channels"].get("Dimm",["1"])[0]))]
					self.doSendAction( evalChannels, address, state, dj )

					state = "LEVEL"
					dj = json.dumps({"v":action.actionValue["whiteLevel"]*acp["mult"].get("Dimm",1)})
					channels = [acp["channels"].get("Dimm",["1"])[0]]

				else:
					minLevel =  (action.actionValue["blueLevel"]  + action.actionValue["greenLevel"]  + action.actionValue["redLevel"])*0.2
					if action.actionValue["blueLevel"]  > minLevel: colorCode +=1
					if action.actionValue["greenLevel"] > minLevel: colorCode +=2
					if action.actionValue["redLevel"]   > minLevel: colorCode +=4
					dj = json.dumps({"v":colorCode})
					channels = [acp["channels"].get("Dimm",["1"])[0]]
					state = "COLOR"

			else:
				self.indiLOG.log(30,"actionControlDimmerRelay  {}  action not suppported  {}".format(dev.name, action))
				state =	acp["states"].get("Dimm","")


			if self.decideMyLog("Actions"): self.indiLOG.log(20,"actionControlDimmerRelay channels:{}".format(channels))
			evalChannels = []
			for xx in channels:
				evalChannels.append(str(eval(xx)))
			self.doSendAction( evalChannels, address, state, dj )

		except Exception as e:
			if "{}".format(e).find("None") == -1: self.indiLOG.log(40,f"{dev.name:}, States\n{dev.states:}\n actionV:{action:}", exc_info=True)

		return 


	####- exec send 
	####-------------
	def doSendAction(self, channels, address, state, dj ):
		try:
			if not self.isValidIP(self.ipNumber): 
				self.indiLOG.log(30,"doSendAction  bad IP number:{} ".format(self.ipNumber) )
				return 
			thisRequestSession = requests.Session()
			for ch in channels:	
				html = "http://{}:{}/device/{}/{}/{}/~pv".format(self.ipNumber ,self.portNumber, address, ch, state )
				r = "error"
				if self.decideMyLog("Actions"): self.indiLOG.log(20,"doSendAction html: {}, dj:{}<<".format(html, dj))

				try:
					r = thisRequestSession.put(html, data=dj, timeout=self.requestTimeout, headers={'Connection':'close',"Content-Type": "application/json"})
				except Exception as e:
					self.indiLOG.log(30,"doSendAction  bad return for html: {}, dj: {} ==> {}, err: {}".format(html, dj, r, e))

				if type(r) != type("") and  r.status_code != 200:
					self.indiLOG.log(30,"doSendAction return error:{}!=200, hmtl: {},  dj: {}".format(r.status_code, html, dj))
				elif type(r) == type(""):
					self.indiLOG.log(30,"doSendAction return error:{}!=200, hmtl: {},  dj: {}".format(r, html, dj))

				if self.decideMyLog("Actions"): self.indiLOG.log(20,"doSendAction ret:{}".format(r))
		except Exception as e:
			if "{}".format(e).find("None") == -1: self.indiLOG.log(40,"", exc_info=True)

		# force refresh of data from homematic
		self.getDataNow = time.time() + min(3.5,self.getValuesEvery)  # it takes ~ 3.5 secs after set to get new value back from homematic
		#if self.decideMyLog("Special"): self.indiLOG.log(20,"setting getDataNow")

		return 

		## exec update variale
	####-------------
	def doSendActionVariable(self, address, dj ):
		try:
			if not self.isValidIP(self.ipNumber): 
				self.indiLOG.log(30,"doSendActionVariable  bad IP number:{} ".format(self.ipNumber) )
				return 
			thisRequestSession = requests.Session()
			html = "http://{}:{}/sysvar/{}/~pv".format(self.ipNumber ,self.portNumber, address)
			r = "error"

			if self.decideMyLog("Actions"): self.indiLOG.log(20,"doSendActionVariable html: {}, dj: {}<<".format(html, dj))
			try:
				r = thisRequestSession.put(html, data=dj, timeout=self.requestTimeout, headers={'Connection':'close',"Content-Type": "application/json"})
			except Exception as e:
				self.indiLOG.log(30,"doSendActionVariable  bad return for html:{}, dj:{} ==> {}, err:{}".format(html, dj, r, e))
			if type(r) != type("") and  r.status_code != 200:
				self.indiLOG.log(30,"doSendActionVariable return error:{}!=200, hmtl: {},  dj: {}".format(r.status_code, html, dj))
			elif type(r) == type(""):
				self.indiLOG.log(30,"doSendActionVariable return error:{}!=200, hmtl: {},  dj: {}".format(r, html, dj))

			if self.decideMyLog("Actions"): self.indiLOG.log(20,"doSendActionVariable ret:{}".format(str(r)))
		except Exception as e:
			if "{}".format(e).find("None") == -1: self.indiLOG.log(40,"", exc_info=True)

		# force refresh of data from homematic
		self.getDataNow = time.time() + min(3.5,self.getValuesEvery)  # it takes ~ 3.5 secs after set to get new value back from homematic
		#if self.decideMyLog("Special"): self.indiLOG.log(20,"setting getDataNow")

		return 


	###########################		ACTIONS END  ########################





	###########################		DEVICE	#################################
	####-------------
	def deviceStartComm(self, dev):
		try:
			if self.decideMyLog("Logic"): self.indiLOG.log(10,"starting device:  {}  {} ".format(dev.name, dev.id))
	
			if	self.pluginState == "init":
				dev.stateListOrDisplayStateIdChanged()
				props = dev.pluginProps
				updateProp = False
				if dev.deviceTypeId in k_mapHomematicToIndigoDevTypeStateChannelProps:
					for prop in k_mapHomematicToIndigoDevTypeStateChannelProps[dev.deviceTypeId]["props"]:
						if prop != "" and  props.get(prop,"") == "":
							props[prop] = k_mapHomematicToIndigoDevTypeStateChannelProps[dev.deviceTypeId]["props"][prop]
							updateProp = True
							if self.decideMyLog("Logic"): self.indiLOG.log(10,"starting device:{}  uodating prop from  {}  to {} ".format(dev.name, props[prop], defaultProps[devTdev.deviceTypeIdypeId][prop]))

				if dev.deviceTypeId == "HMIP-BUTTON":
					if props.get("displayS","") != "":
						del props["displayS"]
						updateProp = True
						if self.decideMyLog("Logic"): self.indiLOG.log(20,"======= starting device:{}  removing from prop displayS".format(dev.name))
					if dev.states.get("onOffState",False):
						self.addToStatesUpdateDict(dev, "onOffState", False)
						if self.decideMyLog("Logic"): self.indiLOG.log(20,"======= starting device:{}  setting button to False at start".format(dev.name))


				if dev.deviceTypeId in k_deviceIsRateDevice:
					if props.get("isDeviceWithRate","") == "":
						props["isDeviceWithRate"] = True
						updateProp = True

				if updateProp:
					dev.replacePluginPropsOnServer(props)

				if dev.deviceTypeId in k_mapHomematicToIndigoDevTypeStateChannelProps:
					childInfo = k_mapHomematicToIndigoDevTypeStateChannelProps[dev.deviceTypeId ]["states"].get("childInfo",{})
					if childInfo !={} and dev.states["childInfo"] == "": 
							self.indiLOG.log(20,"======= starting device:{}  adding back child info:{}".format(dev.name, childInfo))
							self.addToStatesUpdateDict(dev, "childInfo", childInfo["init"])
							
	
				if "created" in dev.states and len(dev.states["created"]) < 5:
					self.addToStatesUpdateDict(dev, "created", datetime.datetime.now().strftime(_defaultDateStampFormat))
	
			if "address" in dev.states:
				address = dev.states["address"]
				if len(address) < 2:
					#self.indiLOG.log(20,"starting device:  {}  {}  address empty, states:{}".format(dev.name, dev.id, dev.states))
					if len(dev.address) > 1: 
						address = dev.address
						self.addToStatesUpdateDict(dev, "address", address)
	
				if not  dev.pluginProps.get("isChild", False):
					if address not in self.homematicAllDevices:
						self.fixAllhomematic(address=address)
						self.homematicAllDevices[address]["type"]				= dev.states.get("homematicType","")
						self.homematicAllDevices[address]["title"]				= dev.states.get("title","")
						self.homematicAllDevices[address]["indigoId"]			= dev.id
						self.homematicAllDevices[address]["indigoDevType"]		= dev.deviceTypeId
	
						if dev.states.get("childInfo","") != "":
							try:	
								chId , chn, childDevType  =  json.loads(childInfo)
								if childDevType  in k_mapHomematicToIndigoDevTypeStateChannelProps: 
									if "states"  in k_mapHomematicToIndigoDevTypeStateChannelProps[childDevType]: 
										homematicStateNames = k_mapHomematicToIndigoDevTypeStateChannelProps[childDevType]["states"]
		
										if chn not in  self.homematicAllDevices[address]["childInfo"]:
											self.homematicAllDevices[address]["childInfo"][chn] = {}
										for homematicStateName in homematicStateNames:
											if homematicStateName not in k_dontUseStatesForOverAllList:
												self.homematicAllDevices[address]["childInfo"][chn][homematicStateName] = chId
										self.homematicAllDevices[address]["childInfo"] = json.loads(dev.states["childInfo"])
							except: pass
	
					try:
						if dev.enabled:
							self.homematicAllDevices[address]["indigoStatus"] = "active"
						else:
							self.homematicAllDevices[address]["indigoStatus"] = "comDisabled"
					except Exception as e:
						if "{}".format(e).find("None") == -1: self.indiLOG.log(40,"deviceStartComm: homematicAllDevices= {}".format(self.homematicAllDevices[address]), exc_info=True)
	
			if self.pluginState == "run":
				self.devNeedsUpdate[dev.id] = True
		except Exception as e:
			if "{}".format(e).find("None") == -1: self.indiLOG.log(40,f"{dev.name:}, States\n{dev.states:}", exc_info=True)

		return

	####-----------------	 ---------
	def deviceStopComm(self, dev):
		if	self.pluginState != "stop":
			self.devNeedsUpdate[dev.id] = True
			if not dev.enabled and dev.pluginProps.get("isChild",False):
				self.homematicAllDevices[address]["indigoStatus"]	= "comDisabled"
				
			if self.decideMyLog("Logic"): self.indiLOG.log(10,"stopping device:  {}  {}".format(dev.name, dev.id) )

	####-----------------	 ---------
	def deviceDeleted(self, dev):  ### indigo calls this
		if dev.deviceTypeId == "Homematic-Host":
			self.hostDevId = 0
		elif "address" in dev.states:
			address = dev.states["address"]
			if address in self.homematicAllDevices and dev.states.get("childOf","") == "":
				self.homematicAllDevices[address]["indigoId"] = 0
				self.homematicAllDevices[address]["indigoStatus"] = "deleted"
				self.indiLOG.log(30,"removing dev w address:{}, and indigo id:{}, from internal list, indigo device was deleted, setting to ignored. If you want to enable again:  use in menu (un)Ignore.. ".format(address, self.homematicAllDevices[address]["indigoId"] ))
		return 


	####-----------------	 ---------
	def xxxdidDeviceCommPropertyChange(self, origDev, newDev):
		#if origDev.pluginProps['xxx'] != newDev.pluginProps['address']:
		#	 return True
		return False


	####-------------------------------------------------------------------------####
	def getDeviceConfigUiValues(self, pluginProps, typeId, devId):
		try:
			theDictList =  super(Plugin, self).getDeviceConfigUiValues(pluginProps, typeId, devId)

			if typeId == "Homematic-Host":
				theDictList[0]["ipNumber"] = self.pluginPrefs.get("ipNumber","192.168.1.99")
				theDictList[0]["portNumber"] = self.pluginPrefs.get("portNumber","2121")

			return theDictList
		except Exception as e:
			if "{}".format(e).find("None") == -1: self.indiLOG.log(40,"", exc_info=True)

		return super(Plugin, self).getDeviceConfigUiValues(pluginProps, typeId, devId)


	####-----------------	 ---------
	def validateDeviceConfigUi(self, valuesDict=None, typeId="", devId=0):
		try:
			if self.decideMyLog("Logic"): self.indiLOG.log(10,"Validate Device dict:, devId:{}  vdict:{}".format(devId,valuesDict) )
			self.devNeedsUpdate[int(devId)] = True
			errorDict = indigo.Dict()

			if devId != 0:
				dev = indigo.devices[devId]
	
				props = dev.pluginProps	
				if typeId == "Homematic-Host":
					if not self.isValidIP(valuesDict["ipNumber"]):
						errorDict["ipNumber"] = "bad ip number"
						return False, valuesDict, errorDict
	
					if devId != 0:
						self.hostDevId = devId
						dev = indigo.devices[devId]
						if 	props.get("ipNumber","") != valuesDict["ipNumber"]:
							self.pluginPrefs["ipNumber"] = valuesDict["ipNumber"]
							self.ipNumber = valuesDict["ipNumber"]
							self.pendingCommand["restartHomematicClass"] = True
	
						if 	props.get("portNumber","") != valuesDict["portNumber"]:
							self.pluginPrefs["portNumber"] = valuesDict["portNumber"]
							self.portNumber = valuesDict["portNumber"]
							self.pendingCommand["restartHomematicClass"] = True
		
						if len(dev.states["created"]) < 10:
							self.addToStatesUpdateDict(dev, "created", datetime.datetime.now().strftime(_defaultDateStampFormat))
	
						valuesDict["address"] = valuesDict["ipNumber"]+":"+valuesDict["portNumber"]





			return True, valuesDict
		except	Exception as e:
			if "{}".format(e).find("None") == -1: self.indiLOG.log(40,"", exc_info=True)
		errorDict = valuesDict
		return False, valuesDict, errorDict

	###########################		update States start  ########################

	###########################		changed Values Start  ########################
	####-------------------------------------------------------------------------####
	def readChangedValues(self):
		try:
			self.changedValues = {}
			version = "-2"
			## cleanup from older version
			if  os.path.isfile(self.indigoPreferencesPluginDir+"changedValues.json"):
				f = open(self.indigoPreferencesPluginDir + "changedValues.json", "r")
				self.changedValues = json.loads(f.read())
				f.close()
				# check for -Version#, if not correct:  rest storage 
				if version  not in self.changedValues: 
					self.changedValues = {version:"version .. format is: indigoId:{stateList:[[timestamp:value],[timestamp:value],...]}"}

				for devId in copy.copy(self.changedValues):
					if devId.find("-") > -1: continue
					if  int(devId) not in indigo.devices:
						del self.changedValues[devId]
		except	Exception as e:
			if "{}".format(e).find("None") == -1: self.indiLOG.log(40,"", exc_info=True)
		self.saveChangedValues()

	####-------------------------------------------------------------------------####
	def saveChangedValues(self):
		try:
			self.writeJson(self.changedValues, fName=self.indigoPreferencesPluginDir + "changedValues")
		except Exception as e:
			self.exceptionHandler(40, e)




	####-------------------------------------------------------------------------####
	## this will update the states xxxChangeXXMinutes / Hours eg TemperatureChange10Minutes TemperatureChange1Hour TemperatureChange6Hour
	## has problems when there are no updates, values can be  stale over days
	def updateChangedValuesInLastXXMinutes(self,dev, value, stateToUpdate, localCopy,  decimalPlaces=1):
		try:
			if stateToUpdate not in dev.states:
				self.indiLOG.log(10,"updateChangedValuesInLastXXMinutes: {}, state {}   not defined".format(dev.name, stateToUpdate))
				return localCopy

			#self.indiLOG.log(20,"updateChangedValuesInLastXXMinutes: {}, state {}, updateListStates:{}".format(dev.name, stateToUpdate, dev.pluginProps.get("isMememberOfChangedValues","")))
			if stateToUpdate +"_"+ k_testIfmemberOfStateMeasures not in dev.states:
				return localCopy

			doPrint = False #dev.id == 1199916063 and stateToUpdate == "Temperature"

			updateList = []

			devIdS = str(dev.id)
			props = dev.pluginProps
			trendTimeDeltaMin = int(props.get("trendTimeDeltaMin_"+stateToUpdate,"600"))
			trendDelta = float(props.get("trendDelta_"+stateToUpdate,100.)) / 100.

			# create the measurement time stamps in minutes
			for state in dev.states:
				## state  eg =  "temperatureChange1Hour"
				if state.find(stateToUpdate+"_Change") == 0:
					if state.find(".ui") > 8: continue
					if state.find("_ui") > 8: continue
					upU = state.split("Change")[1]
					if len(upU) < 2: continue
					if upU.find("Hours") > -1:     updateN = "Hours";   updateMinutes = 3600
					elif upU.find("Minutes") > -1: updateN = "Minutes"; updateMinutes = 60
					else: continue
					amount = int(upU.split(updateN)[1])
					updateList.append( {"state":state, "unit":updateN, "deltaSecs":updateMinutes * amount, "pointer":0, "changed":0} )

			if len(updateList) < 1: 
				#self.indiLOG.log(10,"updateChangedValuesInLastXXMinutes:{},  state:{}Changexx value:{} \nnot in states: {}".format(dev.name, stateToUpdate, value, dev.states))
				return localCopy

			## get last list
			if devIdS not in self.changedValues:
				self.changedValues[devIdS] = {}

			updateList = sorted(updateList, key = lambda x: x["deltaSecs"])
			if doPrint: self.indiLOG.log(20,"{}: {}, = {}  updateList:{},  ".format(dev.name, stateToUpdate, value, updateList))
			#if doPrint: self.indiLOG.log(20,"{}: start changedValues:{},  ".format(dev.name, self.changedValues[devIdS][stateToUpdate+"list"]))


			if stateToUpdate+"list" in self.changedValues[devIdS]:
				valueList = self.changedValues[devIdS][stateToUpdate+"list"]
			else:
				valueList = [(0,0),(0,0)]


			try: decimalPlaces = int(decimalPlaces)
			except: 
				self.indiLOG.log(20,"updateChangedValuesInLastXXMinutes dev{}: bad decimalPlaces {}: type:{}  must be >=0 and integer ".format(dev.name, decimalPlaces, type(decimalPlaces)))
				return localCopy

			if decimalPlaces == 0: 
				valueList.append([int(time.time()),int(value)])
			elif decimalPlaces > 0: 
				valueList.append([int(time.time()), round(value,decimalPlaces)])
			else:  
				self.indiLOG.log(20,"updateChangedValuesInLastXXMinutes dev{}: bad decimalPlaces {}: type:{}  must be >=0 and integer ".format(dev.name, decimalPlaces, type(decimalPlaces)))
				return localCopy

			jj 		= len(updateList)
			cutMax	= updateList[-1]["deltaSecs"] # this is for 172800 secs = 48 hours
			ll		= len(valueList)
			for ii in range(ll):
				if len(valueList) <= 2: break
				if (valueList[-1][0] - valueList[0][0]) > cutMax: valueList.pop(0)
				else: 				    break


			changedPerc = 0
			ll = len(valueList)
			if ll > 1:
				for kk in range(jj):
					cut = updateList[kk]["deltaSecs"] # = 5 min = 300, 10 min = 600, 20 min=1200, 1 hour = 3600 ... 48hours = 172800 secs
					updateList[kk]["pointer"] = 0
					if cut != cutMax: # we can skip the largest, must be first and last entry
						for ii in range(ll-1,-1,-1):
							if (valueList[-1][0] - valueList[ii][0]) <= cut:
								updateList[kk]["pointer"] = ii
							else:
								break

					if decimalPlaces == "":
						changed			 = round(( valueList[-1][1] - valueList[updateList[kk]["pointer"]][1] ))
					elif decimalPlaces == 0:
						changed			 = int(valueList[-1][1] - valueList[updateList[kk]["pointer"]][1] )
					else:
						changed			 = round(( valueList[-1][1] - valueList[updateList[kk]["pointer"]][1] ), decimalPlaces)

					if changed != dev.states[updateList[kk]["state"]]:
						localCopy[ updateList[kk]["state"] ] = [changed,""]

					if stateToUpdate+"_Trend" in dev.states:
						if cut == trendTimeDeltaMin:
							changedPerc	 =      200 * ( valueList[-1][1] - valueList[updateList[kk]["pointer"]][1] ) / max (0.01,valueList[-1][1] + valueList[updateList[kk]["pointer"]][1] ) 
							if   changedPerc > trendDelta*8:	Trend = "^^^^"
							elif changedPerc > trendDelta*4:	Trend = "^^^"
							elif changedPerc > trendDelta*2:	Trend = "^^"
							elif changedPerc > trendDelta: 		Trend = "^"
							elif changedPerc < -trendDelta*8:	Trend = "vvvv"
							elif changedPerc < -trendDelta*4:	Trend = "vvv"
							elif changedPerc < -trendDelta*2:	Trend = "vv"
							elif changedPerc < -trendDelta:		Trend = "v"
							else:								Trend = "=="
							if doPrint: self.indiLOG.log(20,"{}: stateToUpdate:{:15}, Trend:>{:2}< changedPerc:{:6.3f}, cut:{:5}, trendTimeDeltaMin:{:5}, trendDelta:{:.2f}, tnow:{:8.2f}, tPast:{:8.2f}, update?:{}, st exists?:{}".format(dev.name, stateToUpdate, Trend, changedPerc, cut, trendTimeDeltaMin, trendDelta, float(valueList[-1][1]), float(valueList[updateList[kk]["pointer"]][1]), Trend != dev.states[stateToUpdate+"_Trend"], stateToUpdate+"_Trend" in dev.states ))
							if Trend != dev.states[stateToUpdate+"_Trend"]:
								localCopy[stateToUpdate+"_Trend"] = [Trend,""]

			self.changedValues[devIdS][stateToUpdate+"list"] = valueList

			return localCopy

		except	Exception as e:
			if "{}".format(e).find("None") == -1: self.indiLOG.log(40,"", exc_info=True)
		return localCopy


	###########################		changed Values END  ########################


	###########################		averages  Start  ########################
	####----------------------reset sensor min max at midnight -----------------------------------####
	def moveAveragesToLastDay(self):
		try:
			dNow = datetime.datetime.now()
			if dNow.hour != 0 or self.pluginPrefs.get("dayReset", -1)  == dNow.day: return 
			self.pluginPrefs["dayReset"] = dNow.day
			self.indiLOG.log(20,"moveAveragesToLastDay: resetting averages and moving values_today --> values_yesterday etc" )
			self.averagesCounts = {}
			for dev in indigo.devices.iter(self.pluginId):
					self.averagesCounts[dev.id] = {}
					if not dev.enabled: continue
					props = dev.pluginProps
					try:
						doPrint =  dev.states["address"] == "xx0052E3C0003026" 
						if props.get("hasMinMaxOption", False):
							for ttx in k_statesWithfillMinMax:
								if ttx in dev.states and ttx+"_MaxToday" in dev.states:
									val = dev.states[ttx]

									for xx in ["_Max", "_Min", "_Ave", "_Measurements"]:
										self.addToStatesUpdateDict(dev,ttx+xx+"Yesterday",dev.states[ttx+xx+"Today"])
										if xx != "_Measurements": self.addToStatesUpdateDict(dev,ttx+xx+"Today", dev.states[ttx])
									self.addToStatesUpdateDict(dev,ttx+"_MeasurementsToday", 1)

									self.addToStatesUpdateDict(dev,ttx+"_MaxTodayAt",		datetime.datetime.now().strftime(_defaultTimeStampFormat))
									self.addToStatesUpdateDict(dev,ttx+"_MinTodayAt",		datetime.datetime.now().strftime(_defaultTimeStampFormat))
									self.addToStatesUpdateDict(dev,ttx+"_MaxYesterdayAt",	dev.states[ttx+"_MaxTodayAt"])
									self.addToStatesUpdateDict(dev,ttx+"_MinYesterdayAt",	dev.states[ttx+"_MinTodayAt"])


						if dev.deviceTypeId in k_deviceWithDayWeekMonth:
							statesDWMY = k_deviceWithDayWeekMonth[dev.deviceTypeId]
							indigoState = statesDWMY["indigoState"]
							if indigoState in dev.states and indigoState+"_At0" in dev.states:

								try:	at0 = json.loads(dev.states[indigoState+"_At0"])
								except:
									at0 = self.resetTotalAt0()
									self.addToStatesUpdateDict(dev,indigoState+"_At0", at0)
									self.indiLOG.log(20,"moveAveragesToLastDay fixing total at 0 for  :{}  indigoState:{:}   bad value:>{}<".format(dev.name, indigoState, dev.states[indigoState+"_At0"]) )
								if doPrint: self.indiLOG.log(20,"moveAveragesToLastDay testing :{}  indigoState:{:}, at0:{}".format(dev.name, indigoState, at0) )

								for xx in [7,6,5,4,3]:
									self.addToStatesUpdateDict(dev,indigoState+"_Day-"+str(xx), dev.states[indigoState+"_Day-"+str(xx-1)])
								self.addToStatesUpdateDict(dev,indigoState+"_Day-2", 			dev.states[indigoState+"_Yesterday"])

								todayS = indigoState+"_Today"
								todayV = dev.states[todayS]
								self.addToStatesUpdateDict(dev,indigoState+"_Yesterday", todayV	)
								if props.get("displayS","") == todayS and props.get("SupportsSensorValue",False):
									theformat   =  statesDWMY.get("format","") # {.0f[Min]}
									if theformat != "":	uiV = theformat.format(0)
									else:				uiV = 0
									self.addToStatesUpdateDict(dev, "sensorValue", 0,  uiValue=uiV)
								self.addToStatesUpdateDict(dev,todayS, 0)
								self.addToStatesUpdateDict(dev,todayS, 0)

								at0["day"] = dev.states[indigoState]

								# if monday move this week to lastweek etc 
								if   f"{dNow:%A}" == "Monday":
									if doPrint: self.indiLOG.log(20,"moveAveragesToLastDay  is Monday" )
									for xx in [4,3,2]:
										self.addToStatesUpdateDict(dev,indigoState+"_Week-"+str(xx), dev.states[indigoState+"_Week-"+str(xx-1)])
									self.addToStatesUpdateDict(dev,indigoState+"_Week-1",			 dev.states[indigoState+"_ThisWeek"])
									self.addToStatesUpdateDict(dev,indigoState+"_ThisWeek", 0)
									at0["week"] = dev.states[indigoState]

								# if first day of month  move this momths to September etc 
								if dNow.day == 1:
									thisMonth = dNow.month
									lastMonth = str(thisMonth - 1)
									if lastMonth  == "0": lastMonth = "12"
									replaceMonth = k_mapMonthNumberToMonthName[lastMonth]
									self.addToStatesUpdateDict(dev,indigoState+"_"+replaceMonth, dev.states[indigoState+"_ThisMonth"])
									self.addToStatesUpdateDict(dev,indigoState+"_ThisMonth", 0)
									at0["month"] = dev.states[indigoState]

									# if january move this year to last 
									if dNow.month == 1:
										self.addToStatesUpdateDict(dev,indigoState+"LastYear", dev.states[indigoState+"_ThisYear"])
										self.addToStatesUpdateDict(dev,indigoState+"_ThisYear", 0)
										at0["year"] = dev.states[indigoState]


								self.addToStatesUpdateDict(dev,indigoState+"_At0",json.dumps(at0))
								if doPrint:self.indiLOG.log(20,"moveAveragesToLastDay finished:{}  indigoState:{:},  at0:{}".format(dev.name, indigoState, at0) )
					except	Exception as e:
						if len("{}".format(e))	> 5 :
							if "{}".format(e).find("None") == -1: self.indiLOG.log(40,"", exc_info=True)

			self.executeUpdateStatesList()					
		except	Exception as e:
			if len("{}".format(e))	> 5 :
				if "{}".format(e).find("None") == -1: self.indiLOG.log(40,"", exc_info=True)


	####----------------------fill min max, ave-----------------------------------####
	def fillMinMaxSensors(self, dev, stateName, value, decimalPlaces, localCopy):
		try:
			if stateName not in dev.states: 													return localCopy 
			if stateName+"_MaxToday" not in dev.states: 										return localCopy
			if value == "": 																	return localCopy
			if dev.pluginProps.get("ignoreZerominMaxEnable_"+stateName, False) and value == 0:	return localCopy

			if value > float(dev.states[stateName+"_MaxToday"]) or len(str(dev.states[stateName+"_MaxTodayAt"])) == 0:
				localCopy[stateName+"_MaxToday"]   = [value,""]
				localCopy[stateName+"_MaxTodayAt"] = [datetime.datetime.now().strftime(_defaultTimeStampFormat),""]

			if (
					( value < float(dev.states[stateName+"_MinToday"]) or len(str(dev.states[stateName+"_MinTodayAt"])) == 0 ) or 
					( value > 0 and dev.pluginProps.get("ignoreZerominMaxEnable_"+stateName, False) and float(dev.states[stateName+"_MinToday"]) == 0 )
				):
				localCopy[stateName+"_MinToday"] = [value,""]
				localCopy[stateName+"_MinTodayAt"] = [datetime.datetime.now().strftime(_defaultTimeStampFormat),""]

			if stateName+"_AveToday" in dev.states and stateName+"_MeasurementsToday" in dev.states:
					if dev.id not in self.averagesCounts: self.averagesCounts[dev.id] = {}
					if stateName+"_MeasurementsToday"  not in self.averagesCounts[dev.id]: 
						self.averagesCounts[dev.id][stateName+"_MeasurementsToday"] = [dev.states[stateName+"_MeasurementsToday"], 0]

					currentAve = dev.states[stateName+"_AveToday"]
					nMeas = max(0,self.averagesCounts[dev.id][stateName+"_MeasurementsToday"][0])
					newAve = ( currentAve*nMeas + value ) / (nMeas+1)
					if decimalPlaces == 0: newAve = int(newAve)
					else: newAve = round(newAve, decimalPlaces)

					localCopy[stateName+"_AveToday"] = [newAve,""]
					self.averagesCounts[dev.id][stateName+"_MeasurementsToday"][0] += 1
					if time.time() - self.averagesCounts[dev.id][stateName+"_MeasurementsToday"][1] > 63.1:
						self.averagesCounts[dev.id][stateName+"_MeasurementsToday"][1] = time.time()
						localCopy[stateName+"_MeasurementsToday"] = [nMeas+1,""]
			return localCopy				

		except	Exception as e:
			if len("{}".format(e))	> 5 :
				if "{}".format(e).find("None") == -1: self.indiLOG.log(40,"", exc_info=True)

		return localCopy				

	###########################		averages  END  ########################

	####-----------------	 ---------
	def addToStatesUpdateDict(self, dev, key, value, uiValue="", image="", force = False):
		try:

			doPrint = False # key == "onOffState" and value is None  #dev.id == 1199916063 and key == "Temperature_Trend"
			keyLocal = copy.copy(key)
			if doPrint:
				self.indiLOG.log(20,"addToStatesUpdateDict (1) dev:{:35s}, key:{}; value:>{}<, uiValue:>{}<".format(dev.name, keyLocal, value, uiValue) )

			localCopy = copy.deepcopy(self.devStateChangeList)
			if dev.id not in localCopy:
				localCopy[dev.id] = {}

			localCopy[dev.id][keyLocal] = [value, uiValue, force, image]

			if keyLocal in k_doubleState:
				keyLocal = k_doubleState[keyLocal]
				localCopy[dev.id][keyLocal] = [value, uiValue, force, image]

			if keyLocal in k_statesThatHaveMinMaxReal:
				localCopy[dev.id] = self.fillMinMaxSensors( dev, keyLocal, float(value), 1, localCopy[dev.id])
				localCopy[dev.id] = self.updateChangedValuesInLastXXMinutes(dev, value, keyLocal, localCopy[dev.id],  decimalPlaces=1)
			if keyLocal in k_statesThatHaveMinMaxInteger:
				localCopy[dev.id] = self.fillMinMaxSensors( dev, keyLocal, int(value), 0, localCopy[dev.id])
				localCopy[dev.id] = self.updateChangedValuesInLastXXMinutes(dev, value, keyLocal, localCopy[dev.id], decimalPlaces=0)

			self.devStateChangeList = copy.deepcopy(localCopy)
			if	doPrint: self.indiLOG.log(20,"addToStatesUpdateDict (2) dev:{:35s}, key:{}; devStateChangeList:{}".format(dev.name, key, self.devStateChangeList[dev.id]) )


		except	Exception as e:
			if len("{}".format(e))	> 5 :
				if "{}".format(e).find("None") == -1: self.indiLOG.log(40,"", exc_info=True)
		return


	####-----------------	 ---------
	def executeUpdateStatesList(self, onlyDevId=0):
		devId = ""
		key = ""
		local = ""
		image = ""
		dt = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
		try:
			if len(self.devStateChangeList) == 0: return
			local = copy.deepcopy(self.devStateChangeList)
			if onlyDevId == 0:
				self.devStateChangeList = {}
			if onlyDevId in self.devStateChangeList:
				del self.devStateChangeList[onlyDevId]
			trigList = []
			for devId in  local:
				if onlyDevId != 0 and devId != onlyDevId: continue
				lastSensorChangeFound = False
				onlyIfChanged = []
				try: int(devId)
				except: continue
				if len( local[devId]) > 0:
					try: 	dev = indigo.devices[int(devId)]
					except: continue
					props = dev.pluginProps

					keyAlreadyInList = []
					for key in local[devId]:
						#if  dev.deviceTypeId == "HMIP-ROOM": self.indiLOG.log(10,"executeUpdateStatesList :{}, key:{}".format(dev.name,key))
						doPrint = False # devId == 1199916063 and key == "Temperature_Trend"
						if doPrint:  self.indiLOG.log(20,"executeUpdateStatesList (1) :{}, key:{}, value:>{}< ".format(dev.name, key, local[devId][key][0]))
						if key not in dev.states: 
							self.indiLOG.log(20,"executeUpdateStatesList :{}, key:{} not in states".format(dev.name,key))
							continue
						if key in keyAlreadyInList: continue
						value = local[devId][key][0]
						uiValue = local[devId][key][1]
						force = False
						image = ""
						if len(local[devId][key]) == 3: force = local[devId][key][2]
						if len(local[devId][key]) == 4: image = local[devId][key][3]
						# excude from update old=new or if  new =="" and old =0.
						nv = "{}".format(value).strip()
						ov = "{}".format(dev.states[key]).strip()
						ov0 = ov.replace(".0","") 
						ouiv = dev.states.get(state+".ui", uiValue)
						if doPrint: self.indiLOG.log(20,"executeUpdateStatesList (2) test :{},key:{}, nv:{}, ov:{}, ov0:{}".format(dev.name, key, value, nv, ov, ov0))

						if not force:
							if   key.find("RSSI") == 0 			and abs(dev.states[key] - value) < 1:   continue
							elif key == "humidityInput1"		and abs(dev.states[key] - value) < 1:   continue
							elif key == "HUMIDITY" 				and abs(dev.states[key] - value) < 2:   continue
							elif key == "humidityInput1" 		and abs(dev.states[key] - value) < 2:   continue
							elif key == "ILLUMINATION" 			and abs(dev.states[key] - value) < 3:   continue
							elif key == "Temperature" 			and abs(dev.states[key] - value) < 0.1: continue
							elif key == "temperatureInput1" 	and abs(dev.states[key] - value) < 0.1: continue
							elif key == "brightnessLevel" 		and abs(dev.states[key] - value) < 1:   continue
							elif dev.states[key] == value:											    continue
							if doPrint: self.indiLOG.log(20,"executeUpdateStatesList (3)")
	
							if (
								( nv == ov) or (nv == "" and ov0 == "0") or (nv == "0" and ov0 == "0")  or ( uiValue != "" and uiValue !=  ouiv)
								): continue
	
						keyAlreadyInList.append(key)
						if uiValue != "":
							onlyIfChanged.append({"key":key,"value":value,"uiValue":uiValue})
						else:
							onlyIfChanged.append({"key":key,"value":value})

						if key in k_statesWithPreviousValue and key+"_PreviousValue" in dev.states:
							onlyIfChanged.append({"key":key+"_PreviousValue","value":dev.states[key]})

						if 	(
								("lastSensorChange" in dev.states) and 
								(not lastSensorChangeFound) and 
								(key == "sensorValue" or key == "onOffState" or (dev.deviceTypeId in k_mapHomematicToIndigoDevTypeStateChannelProps and  "triggerLastSensorChange" in k_mapHomematicToIndigoDevTypeStateChannelProps[dev.deviceTypeId] and  key in k_mapHomematicToIndigoDevTypeStateChannelProps[dev.deviceTypeId]["triggerLastSensorChange"]) 	)
							):
							if doPrint: self.indiLOG.log(20,"executeUpdateStatesList (4) key:{}".format(key))
							onlyIfChanged.append({"key":"lastSensorChange","value":dt})
							lastSensorChangeFound = True # only add lastSensorChange once per dev.

						# show in status field if .. 
						if props.get("displayStateId","xxx") == "displayStatus" and key == props.get("displayS",""):
							if not lastSensorChangeFound:
								onlyIfChanged.append({"key":"lastSensorChange","value":dt})
								lastSensorChangeFound = True # only add lastSensorChange once per dev.
							onlyIfChanged.append({"key":"displayStatus","value":value,"uiValue":uiValue})


				if onlyIfChanged != []:
					if doPrint:
						self.indiLOG.log(20,f"executeUpdateStatesList (5) update device:{dev.name:30}, keys/values:{onlyIfChanged:} ")
					try:
						#if True or dev.id == 1518189768: self.indiLOG.log(20,f"update device:{dev.name:30}, keys/values:{onlyIfChanged:} ")
						dev.updateStatesOnServer(onlyIfChanged)
					except	Exception as e:
						if "{}".format(e).find("None") == -1: self.indiLOG.log(40,"", exc_info=True)

					if image != "":
						try:
							dev.updateStateImageOnServer(getattr(indigo.kStateImageSel, image, "NoImage"))
						except Exception as e:
							pass



		except	Exception as e:
			if len("{}".format(e))	> 5 :
				if "{}".format(e).find("None") == -1: self.indiLOG.log(40,"", exc_info=True)
				try:
					self.indiLOG.log(40,"{}     {}  {};  devStateChangeList:\n{}".format(dev.name, devId , key, local) )
				except:pass

		return
	###########################		update States END   ########################



	###########################		DEVICE	## END ############################

	"""
	###########################		Prefs	## Start ############################
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine returns the XML for the PluginConfig.xml by default; you probably don't
	# want to use this unless you have a need to customize the XML (again, uncommon)
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def xxgetPrefsConfigUiXml(self):
		return super(Plugin, self).getPrefsConfigUiXml()



	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine returns the UI values for the configuration dialog; the default is to
	# simply return the self.pluginPrefs dictionary. It can be used to dynamically set
	# defaults at run time
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def getPrefsConfigUiValues(self):
		try:
			(valuesDict, errorsDict) = super(Plugin, self).getPrefsConfigUiValues()

		except	Exception as e:
			if "{}".format(e).find("None") == -1: self.indiLOG.log(40,"", exc_info=True)
		return (valuesDict, errorsDict)

	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine is called once the user has exited the preferences dialog
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def closedPrefsConfigUi(self, valuesDict , userCancelled):
		# if the user saved his/her preferences, update our member variables now
		if userCancelled == False:
			pass
		return
	"""

	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine is called once the user has exited the preferences dialog
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	####-----------------  set the geneeral config parameters---------
	def validatePrefsConfigUi(self, valuesDict):

		errorDict = indigo.Dict()
		try:
			valuesDict["MSG"]								= "ok"
			self.getCompleteUpdateEvery =					float(valuesDict.get("getCompleteUpdateEvery", "180"))
			self.getValuesEvery =							float(valuesDict.get("getValuesEvery", "3000"))/1000.
			self.requestTimeout =							float(valuesDict.get("requestTimeout", "10"))
			if ( 
				valuesDict["ipNumber"] != self.pluginPrefs.get("ipNumber","") or
				valuesDict["portNumber"] != self.pluginPrefs.get("portNumber","") or
				 "{}".format(self.requestTimeout) != "{}".format(self.pluginPrefs.get("requestTimeout",0))
				):
				self.ipNumber = valuesDict["ipNumber"]
				self.portNumber = valuesDict["portNumber"]
				self.pendingCommand["restartHomematicClass"] = True

			if not self.isValidIP(valuesDict["ipNumber"]):
				valuesDict["MSG"] = "bad IP number"
				return False, errorDict, valuesDict

			self.ipNumber =									valuesDict["ipNumber"]

			self.pendingCommand["getFolderId"] = True
			self.pendingCommand["setDebugFromPrefs"] = True

			found = False
			for dev in indigo.devices.iter(self.pluginId):
				if dev.deviceTypeId == "Homematic-Host":
					found = True
					if dev.deviceTypeId == "Homematic-Host":
						found = True
						props = dev.pluginProps
						upd = False
						if props.get("ipNumber") != valuesDict["ipNumber"]:
							props["ipNumber"] = valuesDict["ipNumber"]
							upd = True
						if props.get("portNumber") != valuesDict["portNumber"]:
							props["portNumber"] = valuesDict["portNumber"]
							upd = True
						if upd:
							props["address"] = valuesDict["ipNumber"] + ":" + valuesDict["portNumber"]
							dev.replacePluginPropsOnServer(props)
						break

			if not found:
				self.pendingCommand["createHometicHostDev"] = True

			return True, valuesDict

		except	Exception as e:
			if "{}".format(e).find("None") == -1: self.indiLOG.log(40,"", exc_info=True)
		errorDict["MSG"]  = "error please check indigo eventlog"
		valuesDict["MSG"] =	"error please check indigo eventlog"
		return False, errorDict, valuesDict

	###########################		Prefs	## END ############################


	####-------------action  -----------
	def filterThermostat(self):
		try:
			ret = []
			for dev in indigo.devices.iter(self.pluginId):
				if dev.deviceTypeId not in ["HMIP-ETRV"]: continue
				ret.append([dev.id,dev.name])

		except	Exception as e:
			if "{}".format(e).find("None") == -1: self.indiLOG.log(40,"", exc_info=True)
		return ret

	####-----------------	 ---------
	def doGetDevStateType(self, newStateList, deviceTypeId, statesToCreate, dev = "", isChild= False):
		try:
			checkStates = []
			nch = 99
			for state in statesToCreate:
				stateType = statesToCreate[state]
	
				if isChild and state in k_doNotCreateStateForChildDevices: continue
	
				if state != "" and state not in k_alreadyDefinedStatesInIndigo:
					ignore = False
					if dev != "":
						for chkState in  k_checkIfPresentInValues:
							#if dev.id == 1228156796: self.indiLOG.log(20,"doGetDevStateType testing:{:35}, isChild:{}, state::22{},  chkState:{:15},  stTest:{:2} T?; prop:{:} T?, value:{}".format(dev.name, isChild, state,  chkState, state.upper().find(chkState) , chkState+"_Ignore" in dev.pluginProps ,dev.pluginProps.get(chkState +"_Ignore","not present")  ))
							if state.upper().find(chkState) == 0 and chkState+"_Ignore" in dev.pluginProps:
								if dev.pluginProps.get(chkState +"_Ignore",True): 
									ignore = True
									break
					if ignore: continue
					if   stateType == "real":			newStateList.append(self.getDeviceStateDictForRealType(state, state, state))
					elif stateType == "integer":		newStateList.append(self.getDeviceStateDictForIntegerType(state, state, state))
					elif stateType == "number":			newStateList.append(self.getDeviceStateDictForNumberType(state, state, state))
					elif stateType == "string":			newStateList.append(self.getDeviceStateDictForStringType(state, state, state))
					elif stateType == "booltruefalse":	newStateList.append(self.getDeviceStateDictForBoolTrueFalseType(state, state, state))
					elif stateType == "boolonezero":	newStateList.append(self.getDeviceStateDictForBoolOneZeroType(state, state, state))
					elif stateType == "boolonoff":		newStateList.append(self.getDeviceStateDictForBoolOnOffType(state, state, state))
					elif stateType == "boolyesno":		newStateList.append(self.getDeviceStateDictForBoolYesNoType(state, state, state))
					elif stateType == "enum":			newStateList.append(self.getDeviceStateDictForEnumType(state, state, state))
					elif stateType == "separator":		newStateList.append(self.getDeviceStateDictForSeparatorType(state, state, state))
	
				if state in k_statesWithfillMinMax and dev !="" and dev.pluginProps.get("minMaxEnable_"+state,True):
					
						if state in k_statesThatHaveMinMaxReal:
	
							for yy in k_stateMeasures:
								if yy.find("At") > 6:
									newStateList.append(self.getDeviceStateDictForStringType(state+"_"+yy, state+"_"+yy, state+"_"+yy))
									#self.indiLOG.log(20,"typeId:{}, state:{}, state:{}, yy:{}, newStateList:{}".format(dev.name, state, state, yy, newStateList ))
								else:
									newStateList.append(self.getDeviceStateDictForRealType(state+"_"+yy, state+"_"+yy, state+"_"+yy))
	
							for yy in k_stateMeasuresCount:
								newStateList.append(self.getDeviceStateDictForIntegerType(state+"_"+yy, state+"_"+yy, state+"_"+yy))
	
						if state in k_statesThatHaveMinMaxInteger: 
	
							for yy in k_stateMeasures:
								if yy.find("At") > 6:
									newStateList.append(self.getDeviceStateDictForStringType(state+"_"+yy, state+"_"+yy, state+"_"+yy))
								else:
									newStateList.append(self.getDeviceStateDictForIntegerType(state+"_"+yy, state+"_"+yy, state+"_"+yy))
	
						for yy in k_stateMeasuresCount:
								newStateList.append(self.getDeviceStateDictForIntegerType(state+"_"+yy, state+"_"+yy, state+"_"+yy))
	
				if state in k_statesWithPreviousValue and dev !="" and dev.pluginProps.get("previousValue_"+state,True):
						newStateList.append(self.getDeviceStateDictForRealType(state+"_PreviousValue", state+"_PreviousValue",state+"_PreviousValue"))
	
				if state in k_statesWithTrend and dev !="" and dev.pluginProps.get("enableTrend_"+state ,True):
						newStateList.append(self.getDeviceStateDictForStringType(state+"_Trend", state+"_Trend",state+"_Trend"))
	

		except	Exception as e:
			if "{}".format(e).find("None") == -1: self.indiLOG.log(40,"", exc_info=True)

		return newStateList

	####-----------------	 ---------
	def getDeviceStateList(self, dev):
		# called if dev is saved, or at startup

		try:
			# this dict is filled, then returned to indigo
			newStateList  = super(Plugin, self).getDeviceStateList(dev)

			newStateList = self.doGetDevStateType(newStateList, dev.deviceTypeId, k_allDevicesHaveTheseStates, dev=dev)

			newStateList = self.doGetDevStateType(newStateList, dev.deviceTypeId, k_createStates[dev.deviceTypeId], dev=dev, isChild=dev.pluginProps.get("isChild",False))

			if dev.deviceTypeId.find("Homematic") == -1 and dev.deviceTypeId.find("HMIP-SYSVAR-") == -1:
				if  dev.deviceTypeId not in k_isNotRealDevice and  dev.deviceTypeId not in k_devsThatAreChildDevices and dev.deviceTypeId.find("child") == -1 and not dev.pluginProps.get("isChild",False):
						newStateList = self.doGetDevStateType(newStateList, dev.deviceTypeId, k_statesToCreateisRealDevice, dev=dev)

				if  dev.pluginProps.get("isChild",False):
						newStateList = self.doGetDevStateType(newStateList, dev.deviceTypeId, k_ChildrenHaveTheseStates, dev=dev)

			# reset last values dict to force update
			if dev.id in self.lastDevStates: del self.lastDevStates[dev.id]

		except	Exception as e:
			self.indiLOG.log(20,"deviceTypeId:{}, {}".format(dev.deviceTypeId, dev.name))
			if "{}".format(e).find("None") == -1: self.indiLOG.log(40,"", exc_info=True)

		return newStateList 

	####-----------------	 ---------
	def getDeviceDisplayStateId(self, dev):
			displayStateId  = super(Plugin, self).getDeviceDisplayStateId(dev)
			newd = ""
			deviceTypeId = dev.deviceTypeId

			if deviceTypeId in k_mapHomematicToIndigoDevTypeStateChannelProps:
				newd =  k_mapHomematicToIndigoDevTypeStateChannelProps[deviceTypeId]["props"].get("displayStateId","")
				if newd != "": return newd

			return displayStateId



	####-------------
	def getDeviceConfigUiXml(self, typeId, devId):
		dev = indigo.devices[devId]
		#self.indiLOG.log(20,"getDeviceConfigUiXml typeId:{}, devId:{}  0 ".format(typeId, devId))
		if typeId not in k_mapHomematicToIndigoDevTypeStateChannelProps: 
			#self.indiLOG.log(20,"typeId:{}, not pass 1 ".format(typeId, devId))
			return super(Plugin, self).getDeviceConfigUiXml(typeId, devId)

		if "deviceXML" not in k_mapHomematicToIndigoDevTypeStateChannelProps[typeId]: 
			#self.indiLOG.log(20,"typeId:{}, not pass 2 ".format(typeId, devId))
			return super(Plugin, self).getDeviceConfigUiXml(typeId, devId)

		if k_mapHomematicToIndigoDevTypeStateChannelProps[typeId]["deviceXML"] == "":
			#self.indiLOG.log(20,"typeId:{}, not pass 3 ".format(typeId, devId))
			return super(Plugin, self).getDeviceConfigUiXml(typeId, devId)

		#self.indiLOG.log(20,"typeId:{}, :{} new:{} ".format(typeId, dev.name, k_mapHomematicToIndigoDevTypeStateChannelProps[typeId]["deviceXML"]))
		return k_mapHomematicToIndigoDevTypeStateChannelProps[typeId]["deviceXML"] 



######## set defaults for action and menu screens
	#/////////////////////////////////////////////////////////////////////////////////////
	# Actions Configuration
	#/////////////////////////////////////////////////////////////////////////////////////
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine returns the actions for the plugin; you normally don't need to
	# override this as the base class returns the actions from the Actions.xml file
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def xxgetActionsDict(self):
		return super(Plugin, self).getActionsDict()

	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine obtains the callback method to execute when the action executes; it
	# normally just returns the action callback specified in the Actions.xml file
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def xxgetActionCallbackMethod(self, typeId):
		return super(Plugin, self).getActionCallbackMethod(typeId)

	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine returns the configuration XML for the given action; normally this is
	# pulled from the Actions.xml file definition and you need not override it
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def xxgetActionConfigUiXml(self, typeId, devId):
		return super(Plugin, self).getActionConfigUiXml(typeId, devId)

	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine returns the UI values for the action configuration screen prior to it
	# being shown to the user
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	####-----------------	 ---------
	def xxgetActionConfigUiValues(self, pluginProps, typeId, devId):
		return super(Plugin, self).getActionConfigUiValues(pluginProps, typeId, devId)


	#/////////////////////////////////////////////////////////////////////////////////////
	# Menu Item Configuration
	#/////////////////////////////////////////////////////////////////////////////////////
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine returns the menu items for the plugin; you normally don't need to
	# override this as the base class returns the menu items from the MenuItems.xml file
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def xxgetMenuItemsList(self):
		return super(Plugin, self).getMenuItemsList()

	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine returns the configuration XML for the given menu item; normally this is
	# pulled from the MenuItems.xml file definition and you need not override it
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	def xxgetMenuActionConfigUiXml(self, menuId):
		return super(Plugin, self).getMenuActionConfigUiXml(menuId)

	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	# This routine returns the initial values for the menu action config dialog, if you
	# need to set them prior to the GUI showing
	#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
	####-----------------	 ---------
	def xxgetMenuActionConfigUiValues(self, menuId):
		valuesDict = indigo.Dict()
		self.menuXML = dict()
		self.menuXML["MSG"] = ""
		

		for item in self.menuXML:
			valuesDict[item] = self.menuXML[item]
		errorsDict = indigo.Dict()
		#self.indiLOG.log(20,"getMenuActionConfigUiValues - menuId:{}".format(menuId))
		return valuesDict, errorsDict



######################################################################################
	# Indigo Trigger Start/Stop
######################################################################################

	####-----------------	 ---------
	def triggerStartProcessing(self, trigger):
		self.triggerList.append(trigger.id)

	####-----------------	 ---------
	def triggerStopProcessing(self, trigger):
		if trigger.id in self.triggerList:
			self.triggerList.remove(trigger.id)

	#def triggerUpdated(self, origDev, newDev):
	#	self.triggerStopProcessing(origDev)
	#	self.triggerStartProcessing(newDev)


######################################################################################
	# Indigo Trigger Firing
######################################################################################

	####-----------------	 ---------
	def triggerEvent(self, eventId):
		for trigId in self.triggerList:
			trigger = indigo.triggers[trigId]
			if trigger.pluginTypeId == eventId:
				indigo.trigger.execute(trigger)
		return




	###########################	   MAIN LOOP  ############################
	###########################	   MAIN LOOP  ############################
	###########################	   MAIN LOOP  ############################
	###########################	   MAIN LOOP  ############################
	####-----------------init  main loop ---------
	def fixBeforeRunConcurrentThread(self):

		nowDT = datetime.datetime.now()
		self.lastMinute		= nowDT.minute
		self.lastHour		= nowDT.hour
		self.writeJson({"version":_dataVersion}, fName=self.indigoPreferencesPluginDir + "dataVersion")

		self.threads = dict()
		self.threads["getDeviceData"] = dict()
		self.threads["getDeviceData"]["thread"]  = threading.Thread(name='getDeviceData', target=self.getDeviceData)
		self.threads["getDeviceData"]["thread"].start()

		self.threads["getCompleteupdate"] = dict()
		self.threads["getCompleteupdate"]["thread"]  = threading.Thread(name='getCompleteupdate', target=self.getCompleteupdate)
		self.threads["getCompleteupdate"]["thread"].start()


		self.pluginStartTime = time.time()

		for dev in indigo.devices.iter(self.pluginId):
			if dev.deviceTypeId == "Homematic-Host":
				self.hostDevId = dev.id
				break

		try:
			# ceck if we have some old devices with the same address in our environment
			devList = []
			ratesAddrsFound = {}
			for dev in indigo.devices.iter(self.pluginId):
				if "address" in dev.states:
					devList.append((dev.id, dev.name, dev.states["address"], dev.states.get("childOf",-1), dev.states["homematicType"], dev.states["created"] ))
					for addr2 in self.rateStore:
						if addr2 == dev.states["address"]: 
							ratesAddrsFound[addr2] = copy.copy(self.rateStore[addr2])
							break
			self.rateStore = copy.copy(ratesAddrsFound)


			## relink children to parents
			for nn in range(len(devList)):
				for kk in range(nn, len(devList)):
					if kk == nn: continue
					dev1addr = devList[nn][2]
					dev2addr = devList[kk][2]
					if dev1addr == dev2addr:
						dev1id = int(devList[nn][0])
						dev2id = int(devList[kk][0])
						dev1name = devList[nn][1]
						dev2name = devList[kk][1]
						dev1ParentID = int(devList[nn][3])
						dev2ParnetID = int(devList[kk][3])
						dev1homType = devList[nn][4]
						dev2homType = devList[kk][4]
						dev1created = devList[nn][5]
						dev2created = devList[kk][5]
						if dev1ParentID != -1  and dev2id == dev1ParentID:
							xx = "fixme"
							try:	xx = dev1name.split(" ")[0].split("-child-")[-1]
							except	Exception as e:
								self.indiLOG.log(40,"", exc_info=True)
								continue
							yy = xx.split("-")[0]
							self.indiLOG.log(30,"doing  fix #1 adding: {} to address  {}".format(xx, dev2addr))
							dev1 = indigo.devices[dev1id]
							#dev1.updateStateOnServer("address", dev1addr+"-child-"+xx)
							continue
						elif dev2ParnetID != -1 and dev1id == dev2ParnetID:
							xx = "fixme"
							try: 	xx =dev2name.split(" ")[0].split("-child-")[-1]
							except	Exception as e:
								self.indiLOG.log(40,"", exc_info=True)
							self.indiLOG.log(30,"doing  fix #2  adding: {} to address  {}".format( xx, dev1addr)) 
							dev2 = indigo.devices[dev2id]
							dev2.updateStateOnServer("address", dev2.states["address"]+"-child-"+xx)
							continue

						self.indiLOG.log(30,"device with same address:{}, delete one and restart plugin:\ndev1 == {:35} {:12} {:12} {:55s}- type:{:12}, created:{}\ndev2 == {:35} {:12} {:12} {:55s}- type:{:12}, created:{}\n".format( dev1name, 
																										dev1addr, dev1id, dev1ChildID, dev1name, dev1homType, dev1created,    
																										dev2addr, dev2id, dev2ChildID, dev2name, dev2homType, dev2created))


		except	Exception as e:
			if "{}".format(e).find("None") == -1: self.indiLOG.log(40,"", exc_info=True)

		self.pluginState   = "run"
		self.readChangedValues()
		return True

	####-----------------            ---------
	def relinkParentsToChildren(self):
		try:
			if self.relinkParentsToChildrenFlag == 0: return 
			counter = self.relinkParentsToChildrenFlag
			self.relinkParentsToChildrenFlag  = 0
			self.indiLOG.log(30,"relinkParentsToChildren, max {}# of devices to be handled.. starting".format(counter))

			devList = []
			for dev in indigo.devices.iter(self.pluginId):
				if "address" in dev.states:
					devList.append((dev.id, dev.name, dev.states.get("address", ""), dev.states.get("childOf",-1), dev.states["homematicType"], dev.states["created"], dev.states.get("childInfo",""), dev.deviceTypeId , dev.states.get("channelNumber","") ))

			devsFixed = {} # just to count

			# loop through parents
			# thenloop through children
			for nn in range(len(devList)):
				dev1addr = devList[nn][2]
				dev1id = int(devList[nn][0])
				dev1name = devList[nn][1]
				dev1ParentID = int(devList[nn][3])
				dev1homType = devList[nn][4]
				dev1created = devList[nn][5]
				dev1childinfo = devList[nn][6]
				dev1deviceTypeId = devList[nn][7]
				dev1channelNumber = devList[nn][8]
				noChanges = ""
				changes = ""
				if counter == 0: break
				if dev1addr == "": continue
				anyFix = 0
				anythingWrong = 0
				if dev1childinfo == "": continue
				try: dev1childinfo = json.loads(dev1childinfo)
				except:
					self.indiLOG.log(30,"device:{} skipping fixing child info, bad childInfo state {}".format(dev1name, dev1childinfo))
					continue
				copyChinfo = copy.copy(dev1childinfo)
				commonAddress = dev1addr
				out = f"fixing dev parent \"{dev.name}\" commonAddress:{commonAddress} childInfo:{dev1childinfo}\n      "

				#	     devchName     devchId   devchCH  devchType
				# eg: {"Temperature": [1199916063, "1", "HMIP-Temperature"], "Humidity": [1180765844, "1", "HMIP-Humidity"], "Illumination": [415486247, "1", "HMIP-Illumination"], "Rain": [609515741, "1", "HMIP-Rain"], "Sunshine": [1989700163, "1", "HMIP-Sunshine"], "Wind": [913070011, "1", "HMIP-Wind"]}
				for devchName in copyChinfo:
					devchildInfo = copyChinfo[devchName]
					devchId = devchildInfo[0] 
					devchChan = devchildInfo[1] 
					devchType = devchildInfo[2] 
					fixed = False
					if devchId == 0: # only do anything if child devid ==0
						anythingWrong = 1
						# search for child in indigo devices
						#self.indiLOG.log(20,f"     -- looking for  devchName:{devchName},   devChannel:{devchChan}, devType:{devchType}")
						for kk in range(len(devList)):
							dev2addr = devList[kk][2]
							dev2id = int(devList[kk][0])
							dev2name = devList[kk][1]
							dev2ParnetID = int(devList[kk][3])
							dev2homType = devList[kk][4]
							dev2created = devList[kk][5]
							dev2childinfo = devList[kk][6]
							dev2deviceTypeId = devList[kk][7]
							dev2channelNumber = devList[kk][8]
							if dev2addr == "": continue
							# test if this is the right one: 1. hometic address must be same, 2. dev types must be correct, 3. channel # must be the same, then use child id and put into parent childInfo json dev state and save
							if commonAddress in dev2addr and devchType == dev2deviceTypeId and devchChan == dev2channelNumber :
								chAddress = dev2addrsplit("-child-")
								#self.indiLOG.log(20,f"     ------  found: {chAddress} == {dev2name}")
								if len(chAddress) != 2: continue
								childInfo[devchName][0] = dev2id
								anyFix +=1
								devsFixed[dev1name] = True
								fixed = True
								changes += str(childInfo[devchName])+"; "
								break
						if not fixed: noChanges += str(devchildInfo) +"; "
				if anythingWrong > 0:
					if anyFix == 0: 
						self.indiLOG.log(20,f" {dev1name:40s}  no changes for children: {noChanges} ")
					else:
						dev = indigo.states[dev1id]
						dev.updateStateOnServer("childInfo", json.dumps(childInfo))
						self.indiLOG.log(30,f" {out}    ===== #of fixes:{anyFix},  fixes for children: {changes} ")
						counter -= 1
				else:
					self.indiLOG.log(20,f" {dev1name:40s}  no fixes all children linked")

		except	Exception as e:
			if "{}".format(e).find("None") == -1: self.indiLOG.log(40,"", exc_info=True)
		self.indiLOG.log(30,f"relinkParentsToChildren, finished #of devs fixed: {len(devsFixed)}")

		return 

	####-----------------   main loop          ---------
	def runConcurrentThread(self):

		if not self.fixBeforeRunConcurrentThread():
			self.indiLOG.log(40,"..error in startup")
			self.sleep(10)
			return

		self.indiLOG.log(10,"runConcurrentThread.....")

		self.dorunConcurrentThread()

		self.sleep(1)
		if self.quitNOW !="":
			self.indiLOG.log(20, "runConcurrentThread stopping plugin due to:  ::::: {} :::::".format(self.quitNOW))
			serverPlugin = indigo.server.getPlugin(self.pluginId)
			serverPlugin.restart(waitUntilDone=False)
		return

	####-----------------   main loop            ---------
	def dorunConcurrentThread(self):

		self.indiLOG.log(10," start   runConcurrentThread, initializing loop settings and threads ..")


		indigo.server.savePluginPrefs()
		self.lastDayCheck				= -1
		self.lastHourCheck				= datetime.datetime.now().hour
		self.lastMinuteCheck			= datetime.datetime.now().minute
		self.pluginStartTime 			= time.time()
		self.countLoop					= 0
		self.indiLOG.log(20,"initialized ... looping")
		indigo.server.savePluginPrefs()	
		self.lastSecCheck = time.time()

		self.sleep(1)
		try:
			while True:
				self.countLoop += 1
				ret = self.doTheLoop()

				if ret != "ok":
					self.indiLOG.log(20,"LOOP   return break: >>{}<<".format(ret) )
				for ii in range(2):
					if self.quitNOW != "": 
						break
					self.sleep(1)

				if self.quitNOW != "": 
					break
	 
		except	Exception as e:
			if "{}".format(e).find("None") == -1: self.indiLOG.log(40,"", exc_info=True)

		self.indiLOG.log(20,"after loop , quitNow= >>{}<<".format(self.quitNOW ) )

		self.postLoop()

		return


	###########################	   exec the loop  ############################
	####-----------------	 ---------
	def doTheLoop(self):


		if self.quitNOW != "": return "break"

		try:

			self.periodCheck()
			self.executeUpdateStatesList()

			if self.quitNOW != "": return "break"

		except	Exception as e:
			if "{}".format(e).find("None") == -1: self.indiLOG.log(40,"", exc_info=True)

		return "ok"


	###########################	   after the loop  ############################
	####-----------------	 ---------
	def postLoop(self):

		self.pluginState   = "stop"
		self.threads["getDeviceData"]["status"] = "stop" 
		self.threads["getCompleteupdate"]["status"] = "stop" 

		self.saveChangedValues()
		self.writeJson(self.homematicAllDevices, fName=self.indigoPreferencesPluginDir + "homematicAllDevices.json", doFormat=True, singleLines=False )
		self.writeJson(self.rateStore, fName=self.indigoPreferencesPluginDir + "rates.json")

		indigo.server.savePluginPrefs()	

		if self.quitNOW == "config changed":
			pass
		if self.quitNOW == "": self.quitNOW = " restart / stop requested "
		self.sleep(1)

		return 


	####-----------------	 ---------
	def periodCheck(self):
		try:
			changed = False
			if	self.countLoop < 2:						return changed
			if time.time() - self.pluginStartTime < 5: return changed
			self.processPendingCommands()
			self.checkOnDelayedActions()

			if time.time() - self.lastSecCheck  > 27:
				if self.hostDevId > 0:
					if  self.numberOfVariables >= 0:
						dev = indigo.devices[self.hostDevId]
						self.addToStatesUpdateDict(dev, "numberOfVariables", self.numberOfVariables)
						self.addToStatesUpdateDict(dev, "numberOfDevices", self.numberOfDevices)
						self.addToStatesUpdateDict(dev, "numberOfRooms", self.numberOfRooms)

						if time.time() - self.lastSucessfullHostContact  > 100:
							if self.hostDevId != 0 and  dev.states["onOffState"]:
								self.addToStatesUpdateDict(indigo.devices[self.hostDevId], "onOffState", False, uiValue="offline")

				self.moveAveragesToLastDay()
				if time.time() - self.autosaveChangedValues > 20: 
					self.saveChangedValues()
					self.autosaveChangedValues = time.time()

				if time.time() - self.checkOnThreads > 20: 
					for xx in self.threads:
						if self.threads[xx]["status"] != "running":
							if xx == "getDeviceData":
								self.threads[xx]["thread"]  = threading.Thread(name=xx, target=self.getDeviceData)
								self.threads[xx]["thread"].start()
							elif xx == "getCompleteupdate":
								self.threads[xx]["thread"]  = threading.Thread(name=xx, target=self.getCompleteupdate)
								self.threads[xx]["thread"].start()
					self.checkOnThreads = time.time()

				if self.devsWithenabledChildren == []:
					for dev in indigo.devices.iter(self.pluginId):
						if "enabledChildren" in dev.states: 
							self.devsWithenabledChildren.append(dev.id)

				newL = []
				for devId in self.devsWithenabledChildren:
					if devId not in indigo.devices:
						continue
					dev = indigo.devices[devId]
					if not dev.enabled: continue
					if  "enabledChildren" not in dev.states:
						continue
					props = dev.pluginProps
					enabledChildren = ""
					for ii in range(100):
						if props.get("enable-"+str(ii), False ):
							enabledChildren += str(ii)+","

					for pr in props:
						if pr.find("enable-") == 0:
							etype = pr.split("-")[1]
							try: 
								int(etype)
								continue
							except: pass
							enabledChildren += etype+","
					enabledChildren = enabledChildren.strip(",")	
					self.addToStatesUpdateDict(dev, "enabledChildren", enabledChildren)
					if props.get("displayS","") == "enabledChildren" and "sensorValue" in dev.states:
						self.addToStatesUpdateDict(dev, "sensorValue", 1, uiValue="channels:"+enabledChildren.strip(","))
					newL.append(devId)
				self.devsWithenabledChildren = newL
				self.writeJson(self.homematicAllDevices, fName=self.indigoPreferencesPluginDir + "homematicAllDevices.json", doFormat=True, singleLines=False )
				if self.updateRateStore:
					self.updateRateStore = False
					self.writeJson(self.rateStore, fName=self.indigoPreferencesPluginDir + "rates.json")

				self.relinkParentsToChildren()
				self.lastSecCheck = time.time()

		except	Exception as e:
			if "{}".format(e).find("None") == -1: self.indiLOG.log(40,"", exc_info=True)
		return	changed


	####-----------------	 ---------
	def fillDevStatesPlain(self, dev, props, address, homematicStateName, indigoState, indigoInfo, channelNumber, iChannelNumber, v, s, doInverse, vInverse, dt, ts, checkCH=True, doPrint=False, force = False):
		try:
			devTypeId = dev.deviceTypeId
			#doPrint = address == "00189F29B032F2" and channelNumber == "1" and indigoState == "ALARMSTATE"
			if doPrint: self.indiLOG.log(20,"fillDevStatesPlain: ---0-- {}: devTypeId:{}, channelNumber:{}, homematicStateName:{:30}, indigoState:{:25}, test1:{}, test2:{} checkCH:{}".format(dev.name, devTypeId, channelNumber,  homematicStateName, indigoState,  devTypeId in k_mapHomematicToIndigoDevTypeStateChannelProps, homematicStateName in  k_mapHomematicToIndigoDevTypeStateChannelProps[devTypeId]["states"],checkCH))
			if False and doPrint: self.indiLOG.log(20,"fillDevStatesPlain: ---0-1  homematicStateName:{} , states:{}".format( homematicStateName , k_mapHomematicToIndigoDevTypeStateChannelProps[devTypeId]["states"]))
			if s !=0:
				#self.writeErrorToLog(address, "fillDevStatesPlain: {} st:{} ch#:{} has error, v={}, not  valid:{}!=0".format(dev.name, homematicStateName, channelNumber, v, s))
				self.addToStatesUpdateDict(dev, "lastBadValue", "{} >{}<".format(dt, v) )
				return 0

			if devTypeId in k_mapHomematicToIndigoDevTypeStateChannelProps and homematicStateName in  k_mapHomematicToIndigoDevTypeStateChannelProps[devTypeId]["states"]:

					if checkCH:
						ich = int( indigoInfo.get("channelNumber","-1"))
						if  	ich < 0: chn = "-1" 
						elif 	ich == iChannelNumber: 	chn = channelNumber
						else: 
							if doPrint: self.indiLOG.log(20,"fillDevStatesPlain: ---1-1               test3 false:ich:{}, ch#:{}, test:{} ".format(ich, channelNumber, ich == iChannelNumber))
							return -1 # return state name ok but false channel number
					else:
						chn = channelNumber; ich = iChannelNumber

					if devTypeId in k_mapHomematicToIndigoDevTypeStateChannelProps and indigoInfo.get("inverse",False):
							doInverse = True
							try: 	
								if type(v) == type(1):
									vInverse = - v + 1
								elif type(v) == type(True):
									if v: vInverse = False
									else: vInverse = True
							except:	pass

					mult		= indigoInfo.get("mult",1)
					dType		= indigoInfo.get("dType","integer")
					uiForm		= indigoInfo.get("format","{}")

					try: 	offset 	= float(props.get("offset-"+indigoState,0))
					except: offset	= 0.
					if doPrint: self.indiLOG.log(20,"fillDevStatesPlain: ---2 ====>      OK      state:{}, mult:{}, offset:{},  dType:{}, v:{},  devTypeId:{}, ich:{}, replaceNumberByString:{}".format( indigoState,  mult, offset, dType, v,  devTypeId, ich, indigoInfo.get("replaceNumberByString",False)))

					if offset !=0:	v += offset
					if mult   != 1:	v *= mult

					if dType == "integer": 
						try:
							v = int(v)
						except:
							#self.writeErrorToLog(address, "fillDevStatesPlain: {} st:{} ch#:{} has error, not an integer>{}<, valid:{}==0?".format(dev.name, homematicStateName, channelNumber, v, s))
							self.addToStatesUpdateDict(dev, "lastBadValue", "{} >{}<".format(dt, v)  )
							return 0

						try:
							self.addToStatesUpdateDict(dev, indigoState, v, uiValue = uiForm.format(v))
						except	Exception as e:
							self.indiLOG.log(20,"{},1- state:{}, v:{},  uiForm:{}".format(dev.name, indigoState, v, uiForm))

						if props.get("displayS","--") == indigoState and "sensorValue" in dev.states and props.get("SupportsSensorValue",False):
							if doPrint: self.indiLOG.log(20,"fillDevStatesPlain {}:  add sensorvalue".format(dev.name))
							self.addToStatesUpdateDict(dev, "sensorValue", v, uiValue= uiForm.format(v))

						if indigoState in dev.states:
							try:
								self.addToStatesUpdateDict(dev, indigoState, v, uiValue= uiForm.format(v))
							except	Exception as e:
								self.indiLOG.log(20,"{},2- state:{}, v:{},  uiForm:{}".format(dev.name, indigoState, v, uiForm))
							resetState = indigoState.split("Total")[0]+"_reset"
							if (resetState in dev.states) and ( v < 1 and ( dt[0:-5] > dev.states[resetState][0:-5]  or len(dev.states[resetState]) < 5) ) :
								self.addToStatesUpdateDict(dev, resetState, dt)

							self.updateDayWeekMonthRate(address, dev, props,indigoState, v, ts, dt, force=force)

					elif dType == "real":
						try:
							v = float(v)
						except:
							self.writeErrorToLog(address, "fillDevStatesPlain: {} adr:{} st:{} has error not a float>{}<, valid:{}==0?".format(dev.name, homematicStateName, channelNumber, v, s))
							self.addToStatesUpdateDict(dev, "lastBadValue",  "{} >{}<".format(dt, v) )
							return 0

						if props.get("displayS","--") == indigoState and "sensorValue" in dev.states and props.get("SupportsSensorValue",False):
								self.addToStatesUpdateDict(dev, "sensorValue", v, uiValue=uiForm.format(v))

						if indigoState in dev.states:
							self.addToStatesUpdateDict(dev, indigoState, v, uiValue= uiForm.format(v))
							resetState = indigoState.split("Total")[0]+"_reset"
							if (resetState in dev.states) and ( v < 1 and ( dt[0:-5] > dev.states[resetState][0:-5]  or len(dev.states[resetState]) < 5) ) :
								self.addToStatesUpdateDict(dev, resetState, dt)

							self.updateDayWeekMonthRate(address, dev, props, indigoState, v, ts, dt, force=force)

							if indigoState == "OperatingVoltage" and props.get("operatingVoltage100","") != "" and "batteryLevel" in dev.states and s == 0:
								operatingVoltage100 = float(props.get("operatingVoltage100","0"))
								operatingVoltage0 = float(props.get("operatingVoltage0","0"))
								batteryLevel = min(100, int((v-operatingVoltage0)/max(0.01,operatingVoltage100 - operatingVoltage0) *100))
								oldbatteryLevel = dev.states.get("batteryLevel",0)
								if "lastBatteryReplaced" in dev.states:
									if (oldbatteryLevel < 90 and batteryLevel == 100 )or len(dev.states.get("lastBatteryReplaced","")) < 5:
										self.addToStatesUpdateDict(dev, "lastBatteryReplaced", dt)
								if batteryLevel != oldbatteryLevel: self.addToStatesUpdateDict(dev, "batteryLevel", batteryLevel)


					elif dType == "booltruefalse":
							if False and  v is None: 
								self.indiLOG.log(20,"fillDevStatesPlain: ---9-- {}: devTypeId:{}, channelNumber:{}, homematicStateName:{:30}, indigoState:{:30}, displayS:{}, dt:{} v:{}".format(dev.name, devTypeId, channelNumber,  homematicStateName,  indigoState, props.get("displayS","--"), dt, v) )
							TF = self.isBool2(v, doInverse, vInverse)
							UIF = props.get("useForOn","on") if TF else props.get("useForOff","off")

							if doPrint: self.indiLOG.log(20,"fillDevStatesPlain: ---9-- {}: devTypeId:{}, channelNumber:{}, homematicStateName:{:30}, indigoState:{:30}, displayS:{}, dt:{}, doInverse:{}, v:{}, vInverse:{}".format(dev.name, devTypeId, channelNumber,  homematicStateName,  indigoState, props.get("displayS","--"), dt, doInverse,v, vInverse) )
							if props.get("displayS","--") == indigoState and "onOffState" in dev.states and props.get("SupportsOnState",False):
								if dev.states["onOffState"] != TF:
									self.addToStatesUpdateDict(dev, "onOffState", TF, uiValue=UIF)

									if "lastEventOn" in dev.states:
										if TF:
											self.addToStatesUpdateDict(dev, "lastEventOn", dt)
										else:
											self.addToStatesUpdateDict(dev, "lastEventOff", dt)

							if doPrint: self.indiLOG.log(20,"fillDevStatesPlain: ---9-1 {}: devTypeId:{}, channelNumber:{}, indigoState:{:30}, TF:{}, UIF:{}".format(dev.name, devTypeId, channelNumber,  indigoState, TF, UIF))
							if indigoState in dev.states:
								if doPrint: self.indiLOG.log(20,"fillDevStatesPlain: ---9-1 {}: devTypeId:{}, channelNumber:{}, indigoState:{:30}, updating".format(dev.name, devTypeId, channelNumber,  indigoState, TF, UIF))
								self.addToStatesUpdateDict(dev, indigoState, TF, uiValue=UIF)

							if indigoState == "LOW_BAT" and "batteryLevel" in dev.states and props.get("operatingVoltage100","") == "":
								if v: 	batteryLevel = 10
								else:	batteryLevel = 100
								if "lastBatteryReplaced" in dev.states:
									if (batteryLevel == 100 and dev.states.get("batteryLevel",0) == 0) or len(dev.states.get("lastBatteryReplaced","")) < 5:
										self.addToStatesUpdateDict(dev, "lastBatteryReplaced", dt)
								if batteryLevel != dev.states.get("batteryLevel",0): self.addToStatesUpdateDict(dev, "batteryLevel", batteryLevel)


					elif dType == "string":
						replaceNumberByString =  indigoInfo.get("replaceNumberByString","")
						if replaceNumberByString != "":
							useStateName = ""
							if indigoState in dev.states: 			useStateName = indigoState
							elif homematicStateName in dev.states: 	useStateName = homematicStateName
							if doPrint: self.indiLOG.log(20,"fillDevStatesPlain: ---14-1 {}:  useStateName:{}, replaceNumberByString:{}, t1:{}, t2:{}".format(dev.name, useStateName, replaceNumberByString, useStateName in dev.states, replaceNumberByString in k_stateValueNumbersToTextInIndigo))
							if useStateName in dev.states and replaceNumberByString in k_stateValueNumbersToTextInIndigo:
								if type(v) == type(" "):
									#self.writeErrorToLog(address, "fillDevStatesKeypad: {} st:{} ch:{} has error v:>{}<, valid:{}==0?".format(dev.name, homematicStateName, channelNumber, v, s))
									vui =  v
								else:
									replacementList = k_stateValueNumbersToTextInIndigo[replaceNumberByString]
									vui = "{}".format( replacementList[ max(0, min(len(replacementList)-1, v)) ] )  

								self.addToStatesUpdateDict(dev, useStateName, vui)

								if homematicStateName == "COLOR" and devTypeId in k_mapHomematicToIndigoDevTypeStateChannelProps and k_mapHomematicToIndigoDevTypeStateChannelProps[devTypeId]["props"].get("isSimpleColorDevice",False): 
									self.setRGB07(dev, v)

						else:
							if indigoState in dev.states: 			self.addToStatesUpdateDict(dev, indigoState, v )
							elif homematicStateName in dev.states: 	self.addToStatesUpdateDict(dev, homematicStateName, v )

					elif dType == "datetime":
							self.addToStatesUpdateDict(dev, indigoState, dt)

					else:
							self.addToStatesUpdateDict(dev, indigoState, v )

					return 0 # this is done, no more processing
			return 1 # this is not done

		except	Exception as e:
			self.indiLOG.log(20,"{}, state:{}, value:{}".format(dev.name, homematicStateName, v))
			if "{}".format(e).find("None") == -1: self.indiLOG.log(30,"", exc_info=True)
			time.sleep(2)

		return -99 # error 


	####-----------------	 ---------

	def dofillDevStatesPlainChild(self,  dev, address, chId, homematicStateName, channelNumber, iChannelNumber, v, s, doInverse, vInverse, dt, ts, checkCH=False, doPrint=False, force=False ):
		try:
			processed = 9
			if channelNumber in self.homematicAllDevices[address]["childInfo"]:
				if homematicStateName in self.homematicAllDevices[address]["childInfo"][channelNumber] and self.homematicAllDevices[address]["childInfo"][channelNumber][homematicStateName] > 0:
					chIdNew = self.homematicAllDevices[address]["childInfo"][channelNumber][homematicStateName]
					if doPrint: self.indiLOG.log(20,"upDateDeviceValues  7 ... childInfo:{}".format(  self.homematicAllDevices[address]["childInfo"]))
					if chIdNew != chId:
						try:
							devChild = indigo.devices[chIdNew]
							devTypeChild = devChild.deviceTypeId
							chId = chIdNew
						except:
							self.writeErrorToLog(address, "upDateDeviceValues 5.1: {}-{}-{} , parent:{}, id:{}  does not exist;   please disable child device in parent device edit".format(address, homematicStateName, channelNumber, dev.name, chIdNew ), logLevel = 30)
							return processed
					if 	devTypeChild  in k_mapHomematicToIndigoDevTypeStateChannelProps and homematicStateName in k_mapHomematicToIndigoDevTypeStateChannelProps[devTypeChild]["states"]: 
						indigoInfo = k_mapHomematicToIndigoDevTypeStateChannelProps[devTypeChild]["states"][homematicStateName]
						processed = self.fillDevStatesPlain( devChild, devChild.pluginProps, address, homematicStateName, indigoInfo.get("indigoState",homematicStateName), indigoInfo, channelNumber, iChannelNumber, v, s, doInverse, vInverse, dt, ts, checkCH=False, doPrint=doPrint, force=force)
			return processed
		except	Exception as e:
			self.indiLOG.log(20,"{}, :{}".format(dev.name, homematicStateName))
			if "{}".format(e).find("None") == -1: self.indiLOG.log(30,"", exc_info=True)
			time.sleep(2)

		return -99 # error 



	####-----------------	 ---------
	def updateDayWeekMonthRate(self, address, dev, props, indigoState0, v, ts, dt, force=False):
		try:
				doPrint =  address == "xx0052E3C0003026"
				states = k_deviceWithDayWeekMonth.get(dev.deviceTypeId,{})
				if states == {}: return 
				indigoState = states["indigoState"] # RainTotal
				resultState = states.get("rateState","") # RainRate_mm_pH
				onOffState  = states.get("onOffState","") # Raining
				totalReset  = states["reset"] # Rain_reset
				divideBy    = states["devideby"] # Rain
				roundBy     = states["roundBy"] # Rain
				roundByRate = states.get("roundByRate",0) # Rain
				theformat   = states.get("format","") # {.0f[Min]}
				if indigoState != indigoState0: return 
				upDate = False

				if indigoState+"_At0" not in dev.states: return 
				if doPrint: self.indiLOG.log(20,"updateDayWeekMonthRate: --1 {}: indigoState:{}, v:{}, ts:{}, dt:{}".format(dev.name, indigoState0, v, ts, dt))
				minV = 0.

				# check if reset or new:
				if len(dev.states.get(totalReset,"")) < 5:
					totalat0 = self.resetTotalAt0(minV)
				else:
					totalat0 = dev.states.get(indigoState+"_At0","")
					if len(totalat0) < 10: 
						totalat0 = self.resetTotalAt0(minV)
						upDate = True

					else:
						try:
							totalat0 = json.loads(totalat0)
							if "day"  not in totalat0:
								totalat0 = self.resetTotalAt0(minV)
								upDate = True
							if "year" not in totalat0:
								totalat0["year"] = minV
								upDate = True

						except	Exception as e:
							if "{}".format(e).find("None") == -1: self.indiLOG.log(30,"updateDayWeekMonthRate -1.1 name:{}, indigoState:{}, resetting totalat0:{}".format(dev.name, indigoState, totalat0))
							totalat0 = self.resetTotalAt0(minV)
							upDate = True

				for yy in k_at0ToThis:
					if doPrint: self.indiLOG.log(20,"updateDayWeekMonthRate: --1.05 testing {}: indigoState:{}, yy:{}, tot:{}, v:{}".format(dev.name, indigoState, yy, totalat0[yy] , v))
				 	# {day":"_Today", "week": "_ThisWeek", "month": "_ThisMonth", "yeear": "_ThisYear"}
					if  totalat0[yy] - v  > 0.1:
						old = dev.states.get(indigoState+k_at0ToThis[yy],0)
						olduse = - round(float(old)* divideBy, roundBy)
						if doPrint: self.indiLOG.log(20,"updateDayWeekMonthRate: --1.2 reset {}: indigoState:{}, yy:{}, tot:{}, v:{}, old:{}, olduse:{}, devideBy:{}, roundBy:{}".format(dev.name, indigoState, yy, totalat0[yy], v, old, olduse, divideBy, roundBy))
						totalat0[yy] = - round(float(dev.states.get(indigoState+k_at0ToThis[yy],0))* divideBy, roundBy)
						upDate = True
					if upDate: self.indiLOG.log(30,"updateDayWeekMonthRate -1.3 {}, indigoState:s{}, updating totalat0[{}]:{}".format(dev.name, indigoState, yy, totalat0[yy]))

				vUpdate = {}
				uiVD = {}
				for yy in k_at0ToThis:
					vUpdate[yy]  = round((v-totalat0[yy])  /divideBy, roundBy)
					if theformat != "":
						uiVD[yy] = theformat.format(vUpdate[yy])
					else:
						uiVD[yy] = str(vUpdate[yy])

				if dev.states.get(totalReset,"") == "" or upDate:
					self.addToStatesUpdateDict(dev, totalReset, dt)

				if upDate: 
					self.addToStatesUpdateDict(dev, indigoState+"_At0", json.dumps(totalat0))
					self.indiLOG.log(30,"updateDayWeekMonthRate -1.4 {}, indigoState:{}, v:{}, updating total at0:{}".format(dev.name, indigoState, v, totalat0))


				curStateV 	= dev.states.get(indigoState,0)
				if v != curStateV or force:
					for yy in k_at0ToThis:
						self.addToStatesUpdateDict(dev, indigoState+k_at0ToThis[yy],	vUpdate[yy], 	uiValue=uiVD[yy])
					if doPrint: self.indiLOG.log(20,"updateDayWeekMonthRate: --11 displayS:{},  indigostate:{} , T2:{}? format:{}, uiv:{}".format(props.get("displayS","") , indigoState , props.get("SupportsSensorValue",False), theformat, uiVD))
					if props.get("displayS","") == indigoState+"_Today" and props.get("SupportsSensorValue",False):
						self.addToStatesUpdateDict(dev, "sensorValue", 	vUpdateDay,  uiValue=uiVD)



				if dev.deviceTypeId in k_deviceIsRateDevice:
					if dev.states["address"] not in self.rateStore: self.rateStore[dev.states["address"]] = []
					self.rateStore[dev.states["address"]].append([ts,v])
					if doPrint: self.indiLOG.log(20,"updateDayWeekMonthRate: --12 address:{},  v:{} , ts:{}".format(dev.states["address"] , v, ts))
					self.updateRateStore = True
					self.calculateRate_Last = time.time() - self.calculateRate_Every + 0.5

		except	Exception as e:
			if "{}".format(e).find("None") == -1: self.indiLOG.log(30,"", exc_info=True)

	####-----------------	 ---------
	def resetTotalAt0(self, minV=0):
		return {"day":minV, "month":minV, "week":minV, "year":minV}

	####-----------------	 ---------
	def calculateRate(self):
		try:
			dtTest =  time.time() - self.calculateRate_Last
			if dtTest < self.calculateRate_Every:
				return 
			self.calculateRate_Last = time.time()

			updateRateStoretemp = False
			for dev in indigo.devices.iter("props.isDeviceWithRate"):
				states = k_deviceWithDayWeekMonth.get(dev.deviceTypeId,{})
				if states == {}: continue
				resultState = states.get("rateState","") # RainRate_mm_pH
				if resultState == "": continue
				indigoState = states["indigoState"] # RainTotal
				onOffState  = states.get("onOffState","") # Raining 
				totalReset  = states["reset"] # Rain_reset
				divideBy    = states["devideby"] # Rain
				roundBy     = states["roundBy"] # Rain
				roundByRate = states.get("roundByRate",0) # Rain
				doPrint 	= indigoState == "xxRainTotal"

				if  onOffState not in dev.states or  resultState not in dev.states: continue 

				address = dev.states["address"]
				onOff = dev.states[onOffState]
				minmeas = 4
				maxmeas = 8
				convTohours = 3600.
				timespan = 900

				if address not in self.rateStore: continue
				#if doPrint: self.indiLOG.log(20,"calculateRate: --1{}  address:{},  onOff:{}, rateStore:{}".format(dev.name, address, onOff, self.rateStore[address] ))
				if len(self.rateStore[address]) < minmeas: continue

				# make weighted average, reduce weight of long time ago values 
				newrates = []
				rate = 0
				tLast = 0
				vLast = 0
				nowTS = time.time()
	
				for ts, v in self.rateStore[address]:
					#if doPrint: self.indiLOG.log(20,"calculateRate: --4 :       ts:{}, tLast:{}, v:{}, vLast:{},".format( ts, tLast, v, vLast))
					if nowTS-ts > timespan: # 15 minutes
						#if doPrint: self.indiLOG.log(20,"calculateRate: --4.1 :    dropping >{}   ts:{}, nowTS:{}, v:{}, vLast:{},".format(timespan, ts, nowTS, v, vLast))
						updateRateStoretemp = True
						continue # drop values from 10 minutes ago.
					if tLast >= ts: # wrong sequence
						#if doPrint: self.indiLOG.log(20,"calculateRate: --4.2 :    dropping >=   ts:{}, tLast:{}, v:{}, vLast:{},".format( ts, tLast, v, vLast))
						updateRateStoretemp = True
						continue
					tLast = ts
					vLast = v
					newrates.append([ts,v])

				nMeas = len(newrates)
				if nMeas == 0: 
					self.rateStore[address] = []
					continue
				if nMeas > maxmeas:
					#if doPrint: self.indiLOG.log(20,"calculateRate: --4.3 :    nRate > {}   dropping:{},".format( maxmeas, newrates[:ll-10]))
					newrates = newrates[nMeas-maxmeas:]

				self.rateStore[address] = newrates

				if len(newrates) == 0: continue
				endTS, endV  = newrates[-1]
				firstTS, firstV  = newrates[0]
				dv = endV  - firstV
				dt = endTS - firstTS
				ratePs =  dv / max(dt, 1.)
				ratepH = round(ratePs * convTohours, roundByRate) 
				dtNow = datetime.datetime.now().strftime(_defaultTimeStampFormat)
				if doPrint: self.indiLOG.log(20,"calculateRate: --4.4 @:{}  dtTest:{:.1f}; calculateRate_Every:{:.1f},  nMeas:{},  onOff:{}, firstTS:{:.1f}, endTS:{:.1f}, dt:{:5.1f},  firstV:{}, endV:{},  dv:{:.3f},  rate:{:.4f} ->{:.2f}/h".format(dtNow, dtTest,self.calculateRate_Every,  nMeas, onOff, firstTS, endTS, dt, firstV, endV, dv,ratePs, ratepH))


				if not onOff: 
					ratepH = 0
				if dev.states[resultState] != ratepH:
					self.addToStatesUpdateDict(dev, resultState, ratepH )

			if updateRateStoretemp: 
				self.updateRateStore = True

		except	Exception as e:
			if "{}".format(e).find("None") == -1: self.indiLOG.log(30,"", exc_info=True)


	####-----------------	 ---------
	def setRGB07(self, dev, v):
		if   v == 0: r=0  ;g=0  ;b=0
		elif v == 7: r=33 ;g=33 ;b=33
		elif v == 6: r=50 ;g=50 ;b=0
		elif v == 5: r=50 ;g=0  ;b=50
		elif v == 4: r=100;g=0  ;b=0
		elif v == 3: r=0  ;g=50 ;b=50
		elif v == 2: r=0  ;g=100;b=0
		elif v == 1: r=0  ;g=0  ;b=100
		self.addToStatesUpdateDict(dev, 'redLevel',   r )
		self.addToStatesUpdateDict(dev, 'greenLevel', g )
		self.addToStatesUpdateDict(dev, 'blueLevel',  b )

	####-----------------	 ---------
	def fillDevStatesKeypad(self, dev, address, homematicStateName, channelNumber, chState, v, s, tso, vHomatic, dt):
		try:
				if s > 0: 
					#self.addToStatesUpdateDict(dev, "lastBadValue", "{} >{}<".format(dt, v) )
					self.writeErrorToLog(address, "fillDevStatesKeypad: {} adr:{} st:{} has error s !=0 v:>{}<, valid:{}==0?".format(dev.name, homematicStateName, channelNumber, v, s))
					return 
				#v = ts # button press always has true after first press, never goes to false, the info is the time stamp
				# anything valid here?
				# get last values:
				NumberOfUsersMax = int(dev.pluginProps.get("NumberOfUsersMax",8))
				if dev.id not in self.lastInfo: 
					lastValuesText = dev.states.get("lastValuesText","")
					try: 	self.lastInfo[dev.id] = json.loads(lastValuesText)
					except: self.lastInfo[dev.id] = {}

				if dev.id not in self.USER_AUTHORIZATION or len(self.USER_AUTHORIZATION[dev.id]) != NumberOfUsersMax: 
					self.USER_AUTHORIZATION[dev.id] = dev.states["USER_AUTHORIZATION"].split(",")
					if  len(self.USER_AUTHORIZATION[dev.id]) != NumberOfUsersMax:
						self.USER_AUTHORIZATION[dev.id] = ["0" for i in range(NumberOfUsersMax)]
						self.addToStatesUpdateDict(dev, "USER_AUTHORIZATION", ",".join(self.USER_AUTHORIZATION[dev.id] ))

				if dev.id not in self.delayedAction: self.delayedAction[dev.id] = []
				#self.indiLOG.log(20,"fillDevStatesKeypad dev:{},  chState:{}, v:{}, t:{}, s:{}, lastInfo:{}".format(dev.name,  chState, v, tso, s, self.lastInfo[dev.id]  ))


				if channelNumber == "0": 
					if homematicStateName == "CODE_ID"  and int(v) > NumberOfUsersMax: return 

					if homematicStateName.find("USER_AUTHORIZATION_") == 0:
						nn = min(NumberOfUsersMax,max(1,int(homematicStateName.rsplit("_",1)[1]))) - 1  # looks like: /USER_AUTHORIZATION_08  -> 08 --> int 8 --> 7

						if vHomatic != (self.USER_AUTHORIZATION[dev.id][nn] == "1"):
							#self.USER_AUTHORIZATION[dev.id][nn] = "1" if vHomatic else self.USER_AUTHORIZATION[dev.id][nn] = "0"       ## does not work ???  why
							if vHomatic: self.USER_AUTHORIZATION[dev.id][nn] = "1"
							else:		 self.USER_AUTHORIZATION[dev.id][nn] = "0"
							self.addToStatesUpdateDict(dev, "USER_AUTHORIZATION", ",".join(self.USER_AUTHORIZATION[dev.id] ))

					if homematicStateName == "CODE_ID" and tso != 0 and vHomatic and s == 0: 
						self.indiLOG.log(20,"fillDevStatesKeypad   lastTSO:{} ...  !=tso?:{}".format(self.lastInfo[dev.id].get(chState, -1), self.lastInfo[dev.id].get(chState+"-"+str(v), -1) != tso))
						if self.lastInfo[dev.id].get(chState+"-"+str(v), -1) != tso:
							self.addToStatesUpdateDict(dev, "user", dev.states.get("user"))
							self.addToStatesUpdateDict(dev, "userPrevious_at", dev.states.get("user_at"))
							if int(v) == 0: 
								stValue = "bad usercode"
							else:
								stValue = str(v)
								self.addToStatesUpdateDict(dev, "onOffState", True)
								if dev.id not in self.delayedAction:
									self.delayedAction[dev.id] = []
								self.delayedAction[dev.id].append(["updateState", time.time() + float(self.pluginPrefs.get("delayOffForButtons",5)), "onOffState",False] )
							self.addToStatesUpdateDict(dev, "user", stValue)
							self.addToStatesUpdateDict(dev, "user_at", dt)
							self.lastInfo[dev.id][chState+"-"+str(v)] = tso
							#self.indiLOG.log(20,"fillDevStatesKeypad   new,  lastInfo:{} dt:{}".format(self.lastInfo[dev.id], dt))
							self.addToStatesUpdateDict(dev, "lastValuesText", json.dumps(self.lastInfo[dev.id]))

		except	Exception as e:
			self.indiLOG.log(20,"{}, :{}".format(dev.name, homematicStateName))
			if "{}".format(e).find("None") == -1: self.indiLOG.log(30,"", exc_info=True)
			time.sleep(2)
		return 
		
	####-----------------	 ---------
	def fillWaterValveDevs(self, dev, props, address, homematicStateName, channelNumber, chState, v, s, tso, vHomatic, dt, indigoInfo, indigoState):
		try:
			if homematicStateName not in ["WATER_FLOW","WATER_VOLUME","WATER_VOLUME_SINCE_OPEN"] or channelNumber != "2": return 1
			doPrint =  address == "xx0052E3C0003026" 
			if s > 0: 
				#self.addToStatesUpdateDict(dev, "lastBadValue", "{} >{}<".format(dt, v) )
				self.writeErrorToLog(address, "fillDevStatesKeypad: {} adr:{} st:{} has error s !=0 v:>{}<, valid:{}==0?".format(dev.name, homematicStateName, channelNumber, v, s))
				return 0

			# first collect all 3 components
			if address not in self.collectAllValuesFirstBeforeUsing: self.collectAllValuesFirstBeforeUsing[address] = {"ts":time.time()}

			# if new data: reset dict
			if time.time() - self.collectAllValuesFirstBeforeUsing[address]["ts"]  > 0.5:
				self.collectAllValuesFirstBeforeUsing[address] = {"ts":time.time()}
			self.collectAllValuesFirstBeforeUsing[address][homematicStateName] = [indigoState, v, dt, tso]

			# complete?
			for dd in ["WATER_FLOW","WATER_VOLUME","WATER_VOLUME_SINCE_OPEN"]:
				if dd not in self.collectAllValuesFirstBeforeUsing[address]: return 0
				

	
			# all data present now go through all and fill dev states			
			if   self.collectAllValuesFirstBeforeUsing[address]["WATER_FLOW"][1] != 0 and  dev.states.get("Flow") == 0: valveState = "newOpen"
			elif self.collectAllValuesFirstBeforeUsing[address]["WATER_FLOW"][1] == 0 and  dev.states.get("Flow") != 0: valveState = "newClose"
			else: valveState = "steady"
			
			if doPrint: self.indiLOG.log(20,"fillWaterValveDevs   address:{},  valveState:{}, dict:{}".format(address, valveState, self.collectAllValuesFirstBeforeUsing[address]))

			for dd in ["WATER_FLOW","WATER_VOLUME","WATER_VOLUME_SINCE_OPEN"]:
				indigoStateI = self.collectAllValuesFirstBeforeUsing[address][dd][0]
				vI= self.collectAllValuesFirstBeforeUsing[address][dd][1]
				dtI = self.collectAllValuesFirstBeforeUsing[address][dd][2]
				tsoI = self.collectAllValuesFirstBeforeUsing[address][dd][3]
				if dd == "WATER_VOLUME_SINCE_OPEN":
					#self.indiLOG.log(20,"fillWaterValveDevs     ".format())
					if valveState == "newOpen": # this is new start of watering
						#self.indiLOG.log(20,"fillWaterValveDevs      pass A" .format())
						lastOpen = dev.states.get("Last_open")
						if len(lastOpen) < 10: lastOpen = dtI
	
						Last_close = dev.states.get("Last_close")
						if len(Last_close) < 10: Last_close = dtI
	
						try: 	Last_Minutes = int(dev.states.get("Last_Minutes"))
						except: Last_Minutes = 0
						
						self.addToStatesUpdateDict(dev, "Previous_Minutes", Last_Minutes)
						self.addToStatesUpdateDict(dev, "Previous_open", lastOpen)
						self.addToStatesUpdateDict(dev, "Previous_close", Last_close)
						self.addToStatesUpdateDict(dev, "Volume_previous_open", dev.states.get("Volume_last_open"))
	
						self.addToStatesUpdateDict(dev, "Last_open", dtI)
						self.addToStatesUpdateDict(dev, "Last_close", "")
						self.addToStatesUpdateDict(dev, "Volume_last_open", 0)
						self.addToStatesUpdateDict(dev, "Last_Minutes", 0)
						
						
					elif valveState == "newClose": # this is end of watering
						#self.indiLOG.log(20,"fillWaterValveDevs      pass B" .format())
						lastOpen = dev.states.get("Last_open")
						if len(lastOpen) < 10: lastOpen = dtI
						DeltaHMS = int( 0.5 + (datetime.datetime.now() -  datetime.datetime.strptime(lastOpen, _defaultDateStampFormat)).total_seconds()/60.  ) 
	
						self.addToStatesUpdateDict(dev, "Last_close", dt)
						self.addToStatesUpdateDict(dev, "Volume_last_open", round(vI, 1))
						self.addToStatesUpdateDict(dev, "Last_Minutes", DeltaHMS)
						
					else: # steady
						#self.indiLOG.log(20,"fillWaterValveDevs      pass C" .format())
						self.addToStatesUpdateDict(dev, "Volume_last_open", round(vI, 1))
															
	
				elif  dd == "WATER_VOLUME":
					#self.indiLOG.log(20,"fillWaterValveDevs      into WATER_VOLUME".format())
					self.addToStatesUpdateDict(dev, indigoStateI, round(vI, 1))
					self.updateDayWeekMonthRate(address, dev, props,indigoStateI, vI, tsoI, dtI)
				
				elif  dd == "WATER_FLOW":
					#self.indiLOG.log(20,"fillWaterValveDevs      into WATER_FLOW".format())
					self.addToStatesUpdateDict(dev, indigoStateI, round(vI, 1))
			return 0
					
	
	
		except	Exception as e:
			self.indiLOG.log(20,"{}, :{}".format(dev.name, homematicStateName))
			if "{}".format(e).find("None") == -1: self.indiLOG.log(30,"", exc_info=True)
			time.sleep(2)
		return 1

	####-----------------	 ---------
	def fillDevStatesButton(self, dev, lastDevStatesTemp, address, chState, homematicStateName, channelNumber, vHomatic, tso, dt, doPrint=False):
		try:
			state = "buttonAction"

			yPrint = doPrint #or (address == "001F20C98F2D3D" )
			xPrint = yPrint #doPrint or (address == "001F20C98F2D3D" and channelNumber =="2" and homematicStateName == "STATE")

			if yPrint: self.indiLOG.log(20,"fillDevStatesButton pass 0  {}:  address:{}, channelNumber:{}, chState:{:25s},  tso:{}, homematicStateName:{}, vHomatic:{}<".format( dev.name, address, channelNumber, chState, tso, homematicStateName, vHomatic))

			if channelNumber == "0" or tso == 0: return lastDevStatesTemp  

			if True:
					state = "buttonAction"
					lastValuesText = {}
					if dev.id not in lastDevStatesTemp :
						lastDevStatesTemp[dev.id] = {}

					if "lastValuesText" in lastDevStatesTemp[dev.id]:
						try: 	lastValuesText = json.loads(lastDevStatesTemp[dev.id]["lastValuesText"])
						except: lastValuesText = {}

					if lastValuesText == {}:
						lastValuesText = dev.states.get("lastValuesText","")
						try: 	
							lastValuesText = json.loads(lastValuesText)
							lastDevStatesTemp[dev.id]["lastValuesText"] = json.dumps(lastValuesText)
						except: 
							lastValuesText = {}
							lastDevStatesTemp[dev.id]["lastValuesText"] = json.dumps(lastValuesText)
					if xPrint: self.indiLOG.log(20,"fillDevStatesButton pass 1   address:{}, chState:{:25s},  tso:{}, lastValuesText.chState:{}, TF:{}<".format( address, chState, tso, lastValuesText.get(chState, -1) , lastValuesText.get(chState, -1) != tso))

					if lastValuesText.get(chState, -1) != tso:
							if yPrint: self.indiLOG.log(20,"fillDevStatesButton pass 2   updating states for chn:{},".format( channelNumber))
							self.addToStatesUpdateDict(dev, "buttonPressedPrevious", dev.states.get("buttonPressed"))
							self.addToStatesUpdateDict(dev, "buttonPressedTimePrevious", dev.states.get("buttonPressedTime"))
							self.addToStatesUpdateDict(dev, "buttonPressedTypePrevious", dev.states.get("buttonPressedType"))
							self.addToStatesUpdateDict(dev, "buttonPressed", channelNumber)
							self.addToStatesUpdateDict(dev, "buttonPressedTime", dt)
							self.addToStatesUpdateDict(dev, "buttonPressedType", homematicStateName)
							self.addToStatesUpdateDict(dev, "onOffState", True)
							if dev.id not in self.delayedAction:
								self.delayedAction[dev.id] = []
							if xPrint: self.indiLOG.log(20,"fillDevStatesButton pass 3   adding delay action  after {} secs".format( float(self.pluginPrefs.get("delayOffForButtons",5))))
							self.delayedAction[dev.id].append(["updateState", time.time() + float(self.pluginPrefs.get("delayOffForButtons",5)), "onOffState",False] )
							lastValuesText[chState] = tso
							self.addToStatesUpdateDict(dev, "lastValuesText", json.dumps(lastValuesText))
							if xPrint: self.indiLOG.log(20,"fillDevStatesButton pass 3-json    lastValuesText:{}".format( lastValuesText))
							self.executeUpdateStatesList(onlyDevId=dev.id)
							lastDevStatesTemp[dev.id]["lastValuesText"] = json.dumps(lastValuesText)

						
		except	Exception as e:
			self.indiLOG.log(20,"{}, :{}".format(dev.name, homematicStateName))
			if "{}".format(e).find("None") == -1: self.indiLOG.log(30,"", exc_info=True)
			time.sleep(2)
		return lastDevStatesTemp



	####-----------------	 ---------
	def dofillDevStatesButtonChild(self, dev, chId, lastDevStatesTemp, address, chState, homematicStateName, channelNumber, vHomatic, tso, dt, doPrint=False):
		processed = 9
		try:
			xx = dev.states.get("childInfo","{}")
			childInfo = json.loads(xx)
		except:
			childInfo = {}
		try:
			for mtype in k_deviceTypesWithButtonPress:
				for chIndex in childInfo:
					chIdnew, chn, childDevType = childInfo[chIndex]
					if mtype  == childDevType and chIdnew > 0:
						if chId != chIdnew:
							try:
								devChild = indigo.devices[chIdnew]
								chId = chIdnew
								if chIdnew > 0: 
									lastDevStatesTemp = self.fillDevStatesButton(devChild,  lastDevStatesTemp, address, chState, homematicStateName, channelNumber, vHomatic, tso, dt, doPrint= address=="xx0002DF29B41271" and channelNumber =="2") # = address == "xx00251D89BBD7FC")
									processed = 0
							except: 
								self.indiLOG.log(30,"upDateDeviceValues 5 address:{},  devtype:{}  removing child device from listing, does not exist?!".format(address,  childDevType ))
								chIdnew = 0
								childInfo[chI] = [chIdnew, chn, childDevType ]
								self.addToStatesUpdateDict(dev, "childInfo", json.dumps(childInfo))
		except	Exception as e:
			self.indiLOG.log(20,"{}, :{}".format(dev.name, homematicStateName))
			if "{}".format(e).find("None") == -1: self.indiLOG.log(30,"", exc_info=True)
			time.sleep(2)
		return lastDevStates, processed


	####-----------------	 ---------
	def fillDevStatesOnOff(self, dev, props, lastDevStatesTemp, address, chState, homematicStateName, channelNumber, vHomatic, tso, dt,doPrint=False):
		try:
			if doPrint: self.indiLOG.log(20,"fillDevStatesOnOff pass 0  {}:  address:{}, channelNumber:{}, chState:{:25s},  tso:{}, homematicStateName:{}, vHomatic:{}<".format( dev.name, address, channelNumber, chState, tso, homematicStateName, vHomatic))

			if dev.id not in lastDevStatesTemp:
				lastDevStatesTemp[dev.id] = {}

			if homematicStateName == "STATE":
				if (channelNumber in dev.states and channelNumber == dev.states.get("channelNumber","-1"))  or channelNumber == "1":
					lastDevStatesTemp[dev.id]["STATE"] = [vHomatic, tso]
					if props.get("inverse",False):	val = not vHomatic
					else:							val = vHomatic
					if val: 						valUi = props.get("useForOn","on")
					else: 							valUi = props.get("useForOff","off")
					if doPrint: self.indiLOG.log(20,"fillDevStatesOnOff pass 12   updating states for chn:{}, vHomatic:{}, val:{}, valUi:{}".format( channelNumber, vHomatic, val, valUi))
					if str(val) != str(dev.states.get("onOffState","--")):
						image = props.get("image","")
						if doPrint: self.indiLOG.log(20,"fillDevStatesOnOff pass 13   image:{}".format(image))
						if image.find("-") > 0:
							image = image.split("-")
							if val: 	image = image[0]
							else:		image = image[1]
						if doPrint: self.indiLOG.log(20,"fillDevStatesOnOff pass 13   .... updating ")
						self.addToStatesUpdateDict(dev, "onOffState", val, uiValue=valUi, image=image, force=False)
						if "STATE" in dev.states:
							self.addToStatesUpdateDict(dev, "STATE", val, uiValue=valUi, image=image, force=False)
	
												
		except	Exception as e:
			self.indiLOG.log(20,"{}, :{}".format(dev.name, homematicStateName))
			if "{}".format(e).find("None") == -1: self.indiLOG.log(30,"", exc_info=True)
			time.sleep(2)
		return lastDevStatesTemp

	####-----------------	 ---------
	def dofillDevStatesOnOffChild(self, dev, lastDevStatesTemp, chId, address, chState, homematicStateName, channelNumber, vHomatic, tso, dt, doPrint= False):
		try:
			if doPrint: self.indiLOG.log(30,"upDateDeviceValues 6 {}< ".format(address))
			try:
				xx = dev.states.get("childInfo","{}")
				childInfo = json.loads(xx)
			except:
				childInfo = {}
			for mtype in k_deviceTypesWithOnOff:
				if doPrint: self.indiLOG.log(30,"upDateDeviceValues 7 {}, mtype:{}< ".format(address, mtype))
				for chIndex in childInfo:
					chIdnew, chn, childDevType = childInfo[chIndex]
					#if doPrint: self.indiLOG.log(30,"upDateDeviceValues 8 {}, chIdnew:{}, chn:{}, childDevType:{}< ".format(address, chIdnew, chn, childDevType))
					if mtype  == childDevType and chIdnew > 0:
						if doPrint: self.indiLOG.log(30,"upDateDeviceValues 9 {}, chId:{}< ".format(address, chId))
						if True or chId != chIdnew:
							if doPrint: self.indiLOG.log(30,"upDateDeviceValues 10 {},  ".format(address, chIdnew, chn, childDevType))
							try:
								devChild = indigo.devices[chIdnew]
								chId = chIdnew
								if chIdnew > 0: lastDevStatesTemp = self.fillDevStatesOnOff(devChild, devChild.pluginProps, lastDevStatesTemp, address, chState, homematicStateName, channelNumber, vHomatic, tso, dt, doPrint= doPrint) # = address == "xx00251D89BBD7FC")
							except: 
								self.indiLOG.log(30,"upDateDeviceValues 5 address:{},  devtype:{}  removing child device from listing, does not exist?!".format(address,  childDevType ))
								chIdnew = 0
								childInfo[chI] = [chIdnew, chn, childDevType ]
								self.addToStatesUpdateDict(dev, "childInfo", json.dumps(childInfo))
		except	Exception as e:
			self.indiLOG.log(20,"{}, :{}".format(dev.name, homematicStateName))
			if "{}".format(e).find("None") == -1: self.indiLOG.log(30,"", exc_info=True)
			time.sleep(2)
		return lastDevStatesTemp



	####-----------------	 ---------
	def fillDevStatesLeftRight(self, dev, props, homematicStateName, v, s, channelNumber, dt):
		try:
			if   channelNumber == "2": indigoState = homematicStateName+"-left"
			elif channelNumber == "3": indigoState = homematicStateName+"-right"
			else: return 1

			if v != dev.states[indigoState]:		
				self.addToStatesUpdateDict(dev, indigoState, v) 
				self.addToStatesUpdateDict(dev, "onOffState", True)
				if dev.id not in self.delayedAction:
					self.delayedAction[dev.id] = []
				self.delayedAction[dev.id].append(["updateState", time.time() + float(self.pluginPrefs.get("delayOffForButtons",5)), "onOffState", False] )

				usWhatforDirection = props.get("useWhatForDirection","left-right").split("-")
				if channelNumber == "2":
					self.addToStatesUpdateDict(dev, "direction", usWhatforDirection[0])
					self.addToStatesUpdateDict(dev, "PREVIOUS_PASSAGE-left", dev.states["LAST_PASSAGE-left"])
					self.addToStatesUpdateDict(dev, "LAST_PASSAGE-left", dt)
				elif channelNumber == "3":
					self.addToStatesUpdateDict(dev, "direction", usWhatforDirection[1])
					self.addToStatesUpdateDict(dev, "PREVIOUS_PASSAGE-right", dev.states["LAST_PASSAGE-right"])
					self.addToStatesUpdateDict(dev, "LAST_PASSAGE-right", dt)

		except	Exception as e:
			self.indiLOG.log(20,"{}, :{}".format(dev.name, homematicStateName))
			if "{}".format(e).find("None") == -1: self.indiLOG.log(30,"", exc_info=True)
			time.sleep(2)
		return  0

	####-----------------	 ---------
	def upDateDeviceValues(self, allValues, NumberOfhttpcalls, repeatLevel):

			#self.indiLOG.log(10,"all Values:{}".format(json.dumps(allValues, sort_keys=True, indent=2)))
		## this for saving execution time. there are several states for each device, we don't need to reload the device multile times
		devChild = ""
		devTypeChild = ""
		devCurrent = ""
		devIdCurrent = -1
		devButtonCurrent = ""
		devButtonIdCurrent = -1
		indigoIdforChild = -1
		tStart = time.time()
		dtimes = []
		self.devCounter +=1
		lastAddress = 0
		chId = -1
		dtNow = datetime.datetime.now().strftime(_defaultDateStampFormat)
		if allValues == {} or allValues == "": return 
		if allValues is None: return 
		doPrint = False

		forceAtStart  = self.forceUpdateAtStart
		self.forceUpdateAtStart = False
		lastDevStatesTemp = copy.copy(self.lastDevStates)
		#self.indiLOG.log(20,"upDateDeviceValues lastDevStatesTemp:{}".format(str(lastDevStatesTemp)[0:100]))
		updsystodev = False
		#self.indiLOG.log(20,"upDateDeviceValues: #links:{}".format(len(allValues)) )
		nVars = 0
		nDevs = 0
		for link in allValues:
			if self.pluginState == "stop": return 
			if link == "": continue

			while True:
				try:
					lStart = time.time()
					
					address, channelNumber, homematicStateName, homematicType = "",-1,"value", ""
	
	
					if time.time() - self.lastSucessfullHostContact  > 10:
						if self.hostDevId != 0:
							devHost = indigo.devices[self.hostDevId]
							if not devHost.states.get("onOffState",False):
								self.addToStatesUpdateDict( devHost, "onOffState", True, uiValue="online")
							self.lastSucessfullHostContact = time.time()
	
	
					if link.find("/sysvar/") > -1: 
						nVars +=1
						updsystodev = updsystodev or self.upDateSysvar( link, allValues, dtNow)
	
	
					### devices ----------------------------------
					elif link.find("/device/") > -1: 
						nDevs +=1
						try:	
							dummy, dd, address, channelNumber, homematicStateName  = link.split("/") 
							homematicType =  "device"
						except: break
	
					if address not in self.homematicAllDevices: break
					if self.homematicAllDevices[address].get("indigoId",-1) > 0:
						if self.homematicAllDevices[address]["indigoStatus"] != "active": break
						# get data:
						lastAddress = address

						try: iChannelNumber = int(channelNumber)
						except: iChannelNumber  = -1
						chState = channelNumber+"-"+homematicStateName
						stateCh = homematicStateName+"-"+channelNumber
						indigoState = homematicStateName
	
						vHomatic = allValues[link].get("v","")
						v = vHomatic
						vui = ""
						tso = allValues[link].get("ts",0)
						ts = tso/1000.
						s = allValues[link].get("s",100)
	
						processed = 99
						doPrint =  False # address == "00349F29B562E3" and channelNumber == "1"  and homematicStateName == "STATE"
						# now check how to use this 
	
						newdevTypeId = self.homematicAllDevices[address]["indigoDevType"] 
						
						devIdNew = self.homematicAllDevices[address]["indigoId"] 
						if devIdNew < 1: break
	
						if devIdNew not in lastDevStatesTemp:
							lastDevStatesTemp[devIdNew] = {}
						#self.indiLOG.log(20,"upDateDeviceValues 2 address:{}, chState:{}".format(address, chState))
	
						#if doPrint: self.indiLOG.log(20,"upDateDeviceValues 1 address:{},  devIdNew:{}, chState: {}, v:{}, tso:{}".format(address,  devIdNew, chState ,  v, tso))
						# test if same value as last time, if yes skip, but do a fulll one every 100 secs anyway
						if repeatLevel == "3" and time.time() > self.nextFullStateCheck: # don't do this check if last full is xx secs ago
							lastDevStatesTemp[devIdNew][chState] = [v, tso] 
	
						else:
							if chState not in lastDevStatesTemp[devIdNew]:
								lastDevStatesTemp[devIdNew][chState] = [v, tso]
							else:
								if lastDevStatesTemp[devIdNew][chState][0] == v and lastDevStatesTemp[devIdNew][chState][1] == tso: 
									break
								else:
									#self.indiLOG.log(20,"upDateDeviceValues address:{},  devId:{}, chState: {}, old:{}, v:{}, tso:{}".format(address,  devIdNew, chState , lastDevStatesTemp[devIdNew][chState] , v, tso))
									lastDevStatesTemp[devIdNew][chState] = [v, tso] 
	
						if doPrint: self.indiLOG.log(20,"upDateDeviceValues address:{}, chState:{:30}, v:{:5}, tso:{}".format(address,  chState , v, tso))
	
						try:	dt = datetime.datetime.fromtimestamp(ts).strftime(_defaultDateStampFormat)
						except: dt = ""
	
						# data accepted, now load it into indigo states
						if devIdCurrent == devIdNew:
							dev = devCurrent
							devTypeId = dev.deviceTypeId
						else:
							try:
								dev = indigo.devices[self.homematicAllDevices[address]["indigoId"] ]
								devCurrent = dev
								devIdCurrent = dev.id
								devTypeId = dev.deviceTypeId
							except	Exception as e:
								self.indiLOG.log(30,"removing dev w address:{}, and indigo id:{}, from internal list, indigo device was deleted, setting to ignored, re-allow in menu (un)Ignore.. ".format(address, self.homematicAllDevices[address]["indigoId"] ))
								self.homematicAllDevices[address]["indigoId"] = 0
								self.homematicAllDevices[address]["indigoStatus"] = "deleted"
								processed = -1
								break
	
						#if doPrint: self.indiLOG.log(20,"upDateDeviceValues address:{}, enabled:{} 3".format(address,  dev.enabled , v))
						#if doPrint: self.indiLOG.log(20,"upDateDeviceValues 3 address:{}, ".format(address))
	
						if not dev.enabled: break
						props = dev.pluginProps
						#if address == "002E1F2991EB72": self.indiLOG.log(20,"upDateDeviceValues address:{},4".format(address,  chState , v))
	
						indigoInfo = {}
						#if doPrint: self.indiLOG.log(20,"upDateDeviceValues 3 address:{}, chState:{}, newdevTypeId:{},  t1:{},".format(address, chState, newdevTypeId, newdevTypeId in k_mapHomematicToIndigoDevTypeStateChannelProps))
						if newdevTypeId in k_mapHomematicToIndigoDevTypeStateChannelProps:
							#if doPrint: self.indiLOG.log(20,"upDateDeviceValues 3.1 address:{}, chState:{}, t2:{},".format(address,  chState, "states" in k_mapHomematicToIndigoDevTypeStateChannelProps[newdevTypeId]))
							if "states" in k_mapHomematicToIndigoDevTypeStateChannelProps[newdevTypeId] :
								#if doPrint: self.indiLOG.log(20,"upDateDeviceValues 3.2 address:{}, chState:{}, t3:{},  states in..:{}".format(address, chState,  homematicStateName in k_mapHomematicToIndigoDevTypeStateChannelProps[newdevTypeId]["states"], k_mapHomematicToIndigoDevTypeStateChannelProps[newdevTypeId]["states"]))
								if homematicStateName in k_mapHomematicToIndigoDevTypeStateChannelProps[newdevTypeId]["states"]:
									indigoInfo 	= k_mapHomematicToIndigoDevTypeStateChannelProps[newdevTypeId]["states"][homematicStateName]
									indigoState  = indigoInfo.get("indigoState", homematicStateName)
								elif "noIndigoState" in  k_mapHomematicToIndigoDevTypeStateChannelProps[newdevTypeId] and homematicStateName in k_mapHomematicToIndigoDevTypeStateChannelProps[newdevTypeId]["noIndigoState"]:
									indigoInfo 	= k_mapHomematicToIndigoDevTypeStateChannelProps[newdevTypeId]["noIndigoState"][homematicStateName]
									indigoState  = indigoInfo.get("indigoState", homematicStateName)
	
						if homematicStateName.lower().find("temperature"):
							if "Temperature" in dev.states and not "temperatureStatesEnabled" in props:
								props["temperatureStatesEnabled"] = True 
								dev.replacePluginPropsOnServer(props)
	
	
	
						doInverse = False
						vInverse = v
						if newdevTypeId in k_mapHomematicToIndigoDevTypeStateChannelProps and indigoInfo.get("inverse",False):
								doInverse = True
								try: 	
									if type(v) == type(1):
										vInverse = - v + 1
									elif type(v) == type(True):
										if v: vInverse = False
										else: vInverse = True
								except:	pass
	
						if doPrint: self.indiLOG.log(20,"upDateDeviceValues 4 address:{},  newdevTypeId:{}, chState:{},    v:{}, vInverse:{}, doInverse:{}".format(address,  newdevTypeId, chState,  v, vInverse, doInverse))

						## prep work done, now fill dev states ################


						if  newdevTypeId in ["ELV-SH-WSM"]: # 
							if self.fillWaterValveDevs( dev, props, address, homematicStateName, channelNumber, chState, v, s, tso, vHomatic, dt, indigoInfo, indigoState) == 0:
								processed = 0
								break


						if newdevTypeId in k_deviceTypesWithKeyPad and homematicStateName in k_keyPressStates: 
							self.fillDevStatesKeypad( dev, address, homematicStateName, channelNumber, chState, v, s, tso, vHomatic, dt)
							processed = 0
							break
	
						if newdevTypeId == "HMIP-SPDR" and homematicStateName == "PASSAGE_COUNTER_VALUE":
							processed = self.fillDevStatesLeftRight( dev, props, homematicStateName, v, s, channelNumber, dt)
							if processed == 0:
								break
	
						if newdevTypeId in ["HMIP-DLD"] and indigoState == "LOCK_STATE":
							self.addToStatesUpdateDict(dev, "onOffState", v > 1, uiValue=2 )
							processed = 0
							break
	
	
						if newdevTypeId in k_deviceTypesWithOnOff and (homematicStateName in k_OnOffStates ) and vHomatic != "" and s == 0:
							lastDevStatesTemp = self.fillDevStatesOnOff(dev, props, lastDevStatesTemp, address, chState, homematicStateName, channelNumber, vHomatic, tso, dt, doPrint=doPrint)
							processed = 0
							break
	
						if  newdevTypeId in k_deviceTypesParentWithOnOffChild and  (homematicStateName in k_OnOffStates ) and s == 0:
							lastDevStatesTemp = self.dofillDevStatesOnOffChild(dev, lastDevStatesTemp, chId, address, chState, homematicStateName, channelNumber, vHomatic, tso, dt, doPrint=doPrint) # = address == "xx00251D89BBD7FC")
							processed = 0
							break
	
						if newdevTypeId in k_deviceTypesWithButtonPress and (homematicStateName in k_buttonPressStates ) and vHomatic !="" and s == 0:
							lastDevStatesTemp = self.fillDevStatesButton(dev,  lastDevStatesTemp, address, chState, homematicStateName, channelNumber, vHomatic, tso, dt, doPrint=doPrint)
							processed = 0
							break
	
						if  newdevTypeId in k_deviceTypesParentWithButtonPressChild and  (homematicStateName in k_buttonPressStates ) and vHomatic and s == 0:
							lastDevStatesTemp, processed = self.dofillDevStatesButtonChild(dev, chId,  lastDevStatesTemp, address, chState, homematicStateName, channelNumber, vHomatic, tso, dt, doPrint=doPrint)
							processed = 0
							break
	
						if newdevTypeId in ["HMIP-DLD"] and indigoState == "LOCK_STATE":
							self.addToStatesUpdateDict(dev, "onOffState", v > 1, uiValue=2 )
							processed = 0
							break
	
						# normal types of  children
						if devTypeId in k_devTypeHasChildren:
							processed = self.dofillDevStatesPlainChild( dev, address, chId, homematicStateName, channelNumber, iChannelNumber, v, s, doInverse, vInverse, dt, ts, checkCH=False, doPrint=doPrint, force=forceAtStart)
							if processed == 0: break
	
						if processed > 0:
							processed = self.fillDevStatesPlain(dev, props, address, homematicStateName, indigoState, indigoInfo, channelNumber, iChannelNumber, v, s, doInverse, vInverse, dt, ts, doPrint=doPrint, force=forceAtStart)
	
						# and here the rest:..   UNREACH, CONFIG_PENDING, RSSI_DEVICE, LOW_BAT, RSSI_PEER, ... 
						if indigoState in dev.states and processed  > 0:
							self.addToStatesUpdateDict(dev, indigoState, v, uiValue=vui)
							
					if self.decideMyLog("Time"): dtimes.append(time.time() - lStart)

				
				except	Exception as e:
					if "{}".format(e).find("None") == -1: self.indiLOG.log(40,"", exc_info=True)

				break # end of while true

			continue # end of for link in allValues


		if  time.time() - self.resetlastDevStates > 0:
			lastDevStatesTemp = {}
			self.resetlastDevStates = 999999999999999
		self.lastDevStates = copy.copy(lastDevStatesTemp)

		if self.decideMyLog("Time"):  tMain = time.time() - tStart

		if repeatLevel == "3" and time.time() > self.nextFullStateCheck:  
			self.nextFullStateCheck  = time.time() + self.nextFullStateCheckAfter

		self.calculateRate()


		self.doallVarToDev(updsystodev)
		self.executeUpdateStatesList()
		if self.decideMyLog("Time"):  
			tAve = 0
			for x in dtimes:
				tAve += x
			tAve = tAve / max(1,len(dtimes))
			self.indiLOG.log(20,"upDateDeviceValues, counter:{} elapsed times - tot:{:.3f}, tMain:{:.3f}   per state ave:{:.5f},  N-States:{:}  NumberOfhttpcalls:{}".format(self.devCounter, time.time() - tStart, tMain, tAve, len(dtimes), NumberOfhttpcalls ) )

		#self.indiLOG.log(20,"upDateDeviceValues, nDevs:{}, nVars:{}".format(nDevs, nVars ) )

		return 





	####-----------------	 ---------
	def makeListOfallPrograms(self, doit):
		try:
			if doit and "address" in self.allDataFromHomematic["allProgram"]: 
				self.listOfprograms = "\nPrograms on host ====================\n"
				self.listOfprograms += "Address Title                                    TS                    s Value\n"
				for address in self.allDataFromHomematic["allProgram"]["address"]:
					xx = self.allDataFromHomematic["allProgram"]["address"][address]
					val = xx.get("value",{})
					self.listOfprograms += "{:6}  {:40} {:19} {:3} {:}\n".format(
						address,  
						xx.get("title",""), 
						datetime.datetime.fromtimestamp(val.get("ts",0.)/1000. ).strftime(_defaultDateStampFormat), 
						val.get("s",0.), val.get("v","")
						)
		except	Exception as e:
			if "{}".format(e).find("None") == -1: self.indiLOG.log(40,"", exc_info=True)
		return

	####-----------------	 ---------
	def makeListOfallVendors(self, doit):
		try:
			if doit and "address" in self.allDataFromHomematic["allVendor"]: 
				self.listOfEvents = "\nEvents on host ========================\n"
				self.listOfEvents += "TS                   Type     Event ---------\n"
				xx = self.allDataFromHomematic["allVendor"]["address"]
				if "diagnostics" in xx:
					yy = xx["diagnostics"]
					if "value" in yy and "v" in yy["value"]:
						zz = yy["value"]["v"]
						if "Log" in zz:
							for event in zz["Log"]:
									self.listOfEvents += "{:19}  {:8} {:}\n".format(event[0], event[1], event[3][0:150])
				#self.indiLOG.log(20,self.listOfEvents)
		except	Exception as e:
			if "{}".format(e).find("None") == -1: self.indiLOG.log(40,"", exc_info=True)
		return



	####-----------------	 ---------
	def doallRooms(self, doit):
		try:
			if doit and "address" in self.allDataFromHomematic["allRoom"]: 
				#self.indiLOG.log(20,"doallRooms, rooms :{}; :{} .. all:{}".format( doRooms, "address" in self.allDataFromHomematic["allRoom"], str(self.allDataFromHomematic["allRoom"]["address"])[0:100]) )
 
				self.numberOfRooms = 0
				homematicType = "ROOM"
				self.roomMembers = {}
				for address in self.allDataFromHomematic["allRoom"]["address"]:
					if self.pluginState == "stop": return 
					try:
						self.lastSucessfullHostContact = time.time()
						if self.hostDevId  > 0 and time.time() - self.lastSucessfullHostContact  > 20:
							devHost = indigo.devices[self.hostDevId]
							if not devHost.states.get("onOffState",False):
								self.addToStatesUpdateDict(devHost, "onOffState", True, uiValue="online")


						thisDev = self.allDataFromHomematic["allRoom"]["address"][address]
						self.numberOfRooms += 1

						indigoType = "HMIP-ROOM" 
						devFound = False
						for dev in indigo.devices.iter(self.pluginId):
							if dev.deviceTypeId != indigoType: continue
							if dev.states["address"] == address: 
								devFound = True
								break
						#self.indiLOG.log(20,"doallRooms, theType:{}, devFound:{};  address:{}".format(theType, devFound, address) )

						title = thisDev.get("title","")
						name = "room-"+title +"-"+	address		
	
						if not devFound:
							try: 
								dev = indigo.devices[name]
								devFound = True
							except: pass

						newprops = {}
						if indigoType in k_mapHomematicToIndigoDevTypeStateChannelProps:
							newprops = k_mapHomematicToIndigoDevTypeStateChannelProps[indigoType]["props"]
						nDevices = 0
						roomListIDs = ""
						roomListNames = ""
						for devD in thisDev["devices"]:
							link = devD.get("link", "").split("/")
							if len(link) != 4: continue
							homematicAddress = link[2]
							if homematicAddress in roomListIDs: continue
							roomListIDs += homematicAddress+";"
								
							nDevices += 1
							tt = devD.get("title", "")
							if tt.rfind(":") == len(tt) -2:
								tt = tt[:-2]
							roomListNames += tt+";"
							try:
								if homematicAddress not in self.roomMembers:
									self.roomMembers[homematicAddress] = []
								if address not in self.roomMembers[homematicAddress]: 
									self.roomMembers[homematicAddress].append(address)
							except: pass

						if self.decideMyLog("Digest"): self.indiLOG.log(10,"doallRooms,  devFound:{};  address:{}, ndevs:{}, room list:{} == {}".format( devFound, address, nDevices, roomListNames, roomListIDs) )
						roomListNames = roomListNames.strip(";")
						roomListIDs = roomListIDs.strip(";")
						newprops["roomListIDs"] = roomListIDs
						newprops["roomListNames"] = roomListNames
						if not devFound:
							if self.pluginPrefs.get("ignoreNewDevices", False): continue
							self.newDevice	= True							
							dev = indigo.device.create(
								protocol		= indigo.kProtocol.Plugin,
								address			= address,
								name			= name,
								description		= "",
								pluginId		= self.pluginId,
								deviceTypeId	= indigoType,
								folder			= self.folderNameDevicesID,
								props			= newprops
								)
							self.newDevice	= False							
							self.lastDevStates[dev.id] = {}
							self.addToStatesUpdateDict(dev, "created", datetime.datetime.now().strftime(_defaultDateStampFormat))
							self.addToStatesUpdateDict(dev, "address", address)

						if address not in self.homematicAllDevices:
							self.homematicAllDevices[address] = copy.copy(_defaultAllHomematic)
							
						if not dev.enabled: continue
						self.homematicAllDevices[address]["indigoId"] 	= dev.id
						self.homematicAllDevices[address]["indigoDevType"] 	= dev.deviceTypeId

						props = dev.pluginProps
						uiValue = uiValue="{} devices".format(nDevices)
						self.addToStatesUpdateDict(dev, "title", title)
						self.addToStatesUpdateDict(dev, "roomListIDs", roomListIDs)
						self.addToStatesUpdateDict(dev, "homematicType", homematicType)
						self.addToStatesUpdateDict(dev, "roomListNames", roomListNames)
						if nDevices != dev.states["NumberOfDevices"]:
							self.addToStatesUpdateDict(dev, "sensorValue", nDevices,uiValue = f"Devs :{nDevices:0d}")
							self.addToStatesUpdateDict(dev, "NumberOfDevices", nDevices)
					except	Exception as e:
						if "{}".format(e).find("None") == -1: self.indiLOG.log(40,"", exc_info=True)
		except	Exception as e:
			if "{}".format(e).find("None") == -1: self.indiLOG.log(40,"", exc_info=True)
		self.newDevice = False
		return



	####-----------------	 ---------
	def upDateSysvar(self, link, allValues, dtNow):
				### sysvar ----------------------------------
			lastDevStatesTemp = copy.copy(self.lastDevStates)
			try:	
				#if link.find("/3392") > -1: self.indiLOG.log(20,"upDateSysvar:     found 3392: link:{}, data:{}".format(link, allValues[link]) )
				updsystodev = False

				address   = link.split("/")[-1]
				if allValues[link].get("s",0) > 0: return  updsystodev# not valid
				homematicType =  "sysvar"
				if address not in self.homematicAllDevices: return updsystodev
				newdevTypeId = self.homematicAllDevices[address]["indigoDevType"]
				devIdNew = self.homematicAllDevices[address]["indigoId"]
				chState = "value"
				newValue = allValues[link].get("v","")

				if devIdNew > 0: 
					tso = allValues[link].get("ts",0)

					## check if we need to update:
					upd = 0
					if devIdNew not in lastDevStatesTemp:
						lastDevStatesTemp[devIdNew] = {}
					if chState not in lastDevStatesTemp[devIdNew]:
						lastDevStatesTemp[devIdNew][chState] = [newValue, tso]
						upd = 1
					else:
						if lastDevStatesTemp[devIdNew][chState][0] != newValue or lastDevStatesTemp[devIdNew][chState][1] != tso: 
							#self.indiLOG.log(20,"upDateSysvar:  devIdNew:{:12},   v: {}=={}?  tso:{}=={}?".format( devIdNew, lastDevStatesTemp[devIdNew][chState][0] , newValue, lastDevStatesTemp[devIdNew][chState][1] ,tso))
							lastDevStatesTemp[devIdNew][chState] = [newValue, tso] 
							upd = 2

					if upd:
						dev = indigo.devices[devIdNew]
						#if address == "14739": self.indiLOG.log(20,"upDateDeviceValues  sysvar  address:{:5s}, dev:{},{} , states:{} allValues:{},".format(address,  devIdNew, dev.name, dev.states, allValues[link]) )
						if   "sensorValue" 			in dev.states:	
							unit = dev.states.get("unit","")
							try: 	
									if  dev.pluginProps.get("offset-sensorValue","0") != "0":
										newValue +=  float(dev.pluginProps.get("offset-sensorValue",0))
									#self.indiLOG.log(20,"upDateSysvar: {}    offset:{}, value:{},".format( dev.name, dev.pluginProps.get("offset-sensorValue",0), newValue))
							except	Exception as e:
								if "{}".format(e).find("None") == -1: self.indiLOG.log(40,"", exc_info=True)
							if unit !="":
								self.addToStatesUpdateDict(dev, "sensorValue", round(newValue,1), f"{newValue:.1f}{unit:}")
							else:
								self.addToStatesUpdateDict(dev, "sensorValue", round(newValue,1), f"{newValue:.1f}")

						elif "onOffState" 			in dev.states:
							self.addToStatesUpdateDict(dev, "onOffState", newValue)

						elif "value" 				in dev.states:
							self.addToStatesUpdateDict(dev, "value", newValue)

						if upd > 1 and  "lastSensorChange" 	in dev.states:
							#self.indiLOG.log(20,"upDateDeviceValues  sysvar  address:{:5s}, dev:{},{} , states:{}, upd:{}, allValues:{},".format(address,  devIdNew, dev.name, dev.states, upd, allValues[link]) )
							self.addToStatesUpdateDict(dev, "lastSensorChange", dtNow)

				# fill syvar to dev/state dict , then do updsystodev if any change
				found = 0
				for linkAdr in self.variablesToDevices:
					if linkAdr not in self.variablesToDevicesLast: break
					if found: break
					devInfo = self.variablesToDevices[linkAdr]
					for stateType in devInfo["type"]:
						if found: break
						for typeCounter in devInfo["type"][stateType]["values"]:
							try:
								oldValue = devInfo["type"][stateType]["values"][typeCounter]["value"]
								sysAddress = devInfo["type"][stateType]["values"][typeCounter]["sysAddress"]
							except:
								self.indiLOG.log(20,"upDateSysvar  error sysvar  address:{:5s}, typeCounter:{},".format(address,  devInfo["type"][stateType]["values"]) )
								break
							#if address == "3392": self.indiLOG.log(20," upDateSysvar sysAddress:{}, address:{}<".format(sysAddress, address ))
							if  sysAddress == address: 
								if oldValue != newValue: updsystodev = True
								devInfo["type"][stateType]["updateSource"] 	= "upDateSysvar"
								#if address == "3392": self.indiLOG.log(20," upDateSysvar  sysvar  address:{:5s}, stateType:{:15},  value:{:5}, new:{:5}, typeCounter:{}<,  updsystodev:{}".format(address, stateType,  newValue, oldValue, updsystodev, updsystodev))
								devInfo["type"][stateType]["values"][typeCounter]["value"] = newValue
								found = True
								break

							
			except	Exception as e:
				if "{}".format(e).find("None") == -1: self.indiLOG.log(40,"", exc_info=True)

			if  time.time() - self.resetlastDevStates > 0:
				self.resetlastDevStates = time.time() + 70
				self.lastDevStates = {}
			else:
				self.lastDevStates = copy.copy(lastDevStatesTemp)
			return updsystodev




	####-----------------	 ---------
	def doallSysVar(self, doit):
		try:
			if not self.pluginPrefs.get("accept_SYSVAR",True): return 

			if doit and "address" in self.allDataFromHomematic["allSysvar"]:  
				doDutyCycle = self.pluginPrefs.get("accept_DutyCycle",True)
				doWatchDog = self.pluginPrefs.get("accept_WatchDog",True)

				self.numberOfVariables = 0
				#self.indiLOG.log(20,"createDevicesFromCompleteUpdate,  variablesToDevices:{}".format( json.dumps(self.variablesToDevices,sort_keys=True, indent=2) ))
				for address in self.allDataFromHomematic["allSysvar"]["address"]:
					try:
						thisDev = self.allDataFromHomematic["allSysvar"]["address"][address]
						self.numberOfVariables +=1

						
						vType = thisDev.get("type","string")
						indigoType = "HMIP-SYSVAR-"+vType
						title = thisDev.get("title","")
						if "value" in thisDev:	sValue = thisDev["value"].get("s",100)
						else: 					sValue = 100
						unit = thisDev.get("unit","")

						if not doWatchDog and title.find("WatchDog") == 0: continue
						if not doDutyCycle and title.find("DutyCycle") == 0: continue


						if title.find("OldVal") >= 0: continue

						if address not in self.homematicAllDevices: 
							self.fixAllhomematic(address=address)
						self.homematicAllDevices[address]["homemtaticStatus"] 			= "active"
						self.homematicAllDevices[address]["lastmessageFromHomematic"] 	= time.time()
						self.homematicAllDevices[address]["sValue"] 	= sValue
	
						if self.homematicAllDevices[address]["indigoStatus"] not in ["active","create"]: continue


						if title.find("sv") == 0:  #  fill sysvar to dev/state dict, this info should go into dev/states not into variables
							# eg: "svEnergyCounter_3375_0034DF29B93F79:6",
							useThis = title.strip("sv").strip("HmiIP").split("_") #title = "svHmIPSunshineCounter_6568_001860C98C9E3E:1" or svHmIPSunshineCounterYesterday_6568
							if len(useThis) == 3: 	linkedDevAddress = useThis[2].split(":") #== 0034DF29B93F79:6
							else:					linkedDevAddress = []
							linkAdr = useThis[1]											 #== 6568
							stateType = useThis[0].split("Counter")[0]						 #== Sunshine

							# k_mapTheseVariablesToDevices = {"Energy": {"Counter":["EnergyTotal", 1., "{:.1f}[mm]"],"CounterToday":["EnergyToday", 1., "{:.1f}[mm]"],"CounterYesterday":["EnergyYesterday", 1., "{:.1f}[mm]"]...
							if stateType in k_mapTheseVariablesToDevices:
								if linkAdr not in self.variablesToDevices:
									self.variablesToDevices[linkAdr]    = {"devAddress":"","type":{}}
									self.variablesToDevicesLast[linkAdr] = {"devAddress":"","type":{}}

								devInfo = self.variablesToDevices[linkAdr]
								typeCounter = useThis[0].split(stateType)[1] # == EnergyCounter
								if stateType not in devInfo["type"]:	#  [] = [value, sysVar address]
									devInfo["type"][stateType]                              = {"values":{"CounterToday":{"value":-999,"sysAddress":""}, "CounterYesterday": {"value":-999,"sysAddress":""}, "Counter":{"value":-999,"sysAddress":""}}, "updateSource":"doallSysVar"}
									self.variablesToDevicesLast[linkAdr]["type"][stateType] = {"values":{"CounterToday":{"value":-999,"sysAddress":""}, "CounterYesterday": {"value":-999,"sysAddress":""}, "Counter":{"value":-999,"sysAddress":""}}, "updateSource":"doallSysVar"}
								devInfo["type"][stateType] ["values"][typeCounter]["value"] 	= thisDev["value"].get("v",0)
								devInfo["type"][stateType] ["values"][typeCounter]["sysAddress"] 	= address
								devInfo["type"][stateType] ["updateSource"] = "doallSysVar"

								if linkAdr in self.variablesToDevices and linkedDevAddress != []:		
									if devInfo["devAddress"] == "":			
										devInfo["devAddress"] 				= linkedDevAddress[0]
									devInfo["type"][stateType]["channel"] 	= linkedDevAddress[1]
							#continue

							#if linkAdr == "6568": self.indiLOG.log(20,"createDevicesFromCompleteUpdate,  title:{:45};  linkAdr:{}, stateType:{}; variablesToDevices:{}".format( title, linkAdr, stateType, self.variablesToDevices[linkAdr]))

						name = "Sysvar-"+title +"-"+ address		
						value = thisDev["value"].get("v",0)

						devFound = False
						try:
							dev = indigo.devices[self.homematicAllDevices[address]["indigoId"]]
							devFound = True
						except: pass

						if not devFound:
							for dev in indigo.devices.iter(self.pluginId):
								if self.pluginState == "stop": return
								if dev.deviceTypeId != indigoType: continue
								if dev.states["address"] == address: 
									devFound = True
									break

							if not devFound:
								try: 
									dev = indigo.devices[name]
									devFound = True
								except: pass

						newprops = {}
						if indigoType in k_mapHomematicToIndigoDevTypeStateChannelProps:
							newprops = k_mapHomematicToIndigoDevTypeStateChannelProps[indigoType]["props"]

						if self.decideMyLog("Digest"): self.indiLOG.log(10,"createDevicesFromCompleteUpdate,  devFound:{};  address:{}, desc:{}, htype:{}, thisdev:\n{}".format( devFound, address, thisDev.get("description"), thisDev.get("type",""), thisDev ))
						if not devFound:
							if self.pluginPrefs.get("ignoreNewDevices", False): continue
							self.newDevice	= True							
							dev = indigo.device.create(
								protocol		= indigo.kProtocol.Plugin,
								address			= address,
								name			= name,
								description		= "",
								pluginId		= self.pluginId,
								deviceTypeId	= indigoType,
								folder			= self.folderNameDevicesID,
								props			= newprops
								)
							self.newDevice	= False							
						if not dev.enabled: continue
						
						self.fixAllhomematic(address=address)
						self.homematicAllDevices[address]["type"]			= vType
						self.homematicAllDevices[address]["title"]			= "Sysvar-"+title
						self.homematicAllDevices[address]["indigoId"]		= dev.id
						self.homematicAllDevices[address]["indigoDevType"]	= dev.deviceTypeId

						if len(dev.states["created"]) < 5:
							self.addToStatesUpdateDict(dev, "created", datetime.datetime.now().strftime(_defaultDateStampFormat))
						if len(dev.states["address"]) < 5:
							self.addToStatesUpdateDict(dev, "address", address)
						self.addToStatesUpdateDict(dev, "title", title)
						if "unit" in dev.states:
							self.addToStatesUpdateDict(dev, "unit",unit)
						self.addToStatesUpdateDict(dev, "description", thisDev.get("description",""))
						self.addToStatesUpdateDict(dev, "homematicType", thisDev.get("type",""))
						if vType == "FLOAT":
							try: 	
									if  dev.pluginProps.get("offset-sensorValue","0") != "0":
										value +=  float(dev.pluginProps.get("offset-sensorValue",0))
									#self.indiLOG.log(20,"doallSysVar:     offset:{}, value:{},".format(  dev.pluginProps.get("offset-sensorValue",0),  value))
							except	Exception as e:
								if "{}".format(e).find("None") == -1: self.indiLOG.log(40,"", exc_info=True)
							if unit !="":
								self.addToStatesUpdateDict(dev, "sensorValue", round(value,1), f"{value:.1f}{unit:}")
							else:
								self.addToStatesUpdateDict(dev, "sensorValue", round(value,1), f"{value:.1f}")

						elif vType == "BOOL" and value is not None:
							self.addToStatesUpdateDict(dev, "onOffState", value)
						elif vType == "ALARM":
							self.addToStatesUpdateDict(dev, "onOffState", value)
						elif vType == "STRING":
							self.addToStatesUpdateDict(dev, "value", value)

					except	Exception as e:
						if "{}".format(e).find("None") == -1: self.indiLOG.log(40,"", exc_info=True)
		except	Exception as e:
			if "{}".format(e).find("None") == -1: self.indiLOG.log(40,"", exc_info=True)

		"""
	variablesToDevices looks like ths after 2 rounds:
'6568': {
	'devAddress': '001860C98C9E3E', 'type': {
		'Rain': {
			'values': {
				'CounterToday': [2.7, '6612'], 'CounterYesterday': [0, '6624'], 'Counter': [2.7, '6611']}, 'updateSource': 'upDateSysvar', 'channel': '1'}, 
			'Sunshine': {
				'values': {
					'CounterToday': [612, '6596'], 'CounterYesterday': [678, '6610'], 'Counter': [3191, '6597']}, 'updateSource': 'upDateSysvar', 'channel': '1'}}}, 
		"""
		#self.indiLOG.log(20,"doallSysVar:     variablesToDevices:{},".format(  json.dumps(self.variablesToDevices, sort_keys=True, indent=2)))


		self.newDevice = False
		return


	####-----------------	 ---------
	def doallVarToDev(self, doit):
		# soem dev states are calculated on hometic and stored in avriables, thsi will take the info from teh sys vars and update the indigo dev/states
		try:
			if not doit: return 
			devChild = {}
			dev = {}
			dt = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
			
			for linkAdr in self.variablesToDevices:
				changed = 0
				devInfo = self.variablesToDevices[linkAdr]
				if linkAdr  not in self.variablesToDevicesLast: changed += 1; self.variablesToDevicesLast[linkAdr] = {}
				address = devInfo["devAddress"]
				if address not in self.homematicAllDevices: continue
				if self.homematicAllDevices[address]["indigoId"] < 1 or self.homematicAllDevices[address]["indigoStatus"]  != "active": continue

				for stateType in devInfo["type"]:
					if stateType not in k_mapTheseVariablesToDevices: continue
						
					for typeCounter in devInfo["type"][stateType]["values"]:

						if devInfo["type"][stateType]["values"][typeCounter]["value"] == -999: continue
						if typeCounter in k_mapTheseVariablesToDevices[stateType]:
							key = k_mapTheseVariablesToDevices[stateType][typeCounter][0]
							norm = k_mapTheseVariablesToDevices[stateType][typeCounter][1]
							form = k_mapTheseVariablesToDevices[stateType][typeCounter][2]
							value0 = devInfo["type"][stateType]["values"][typeCounter]["value"]
							sysAddress = devInfo["type"][stateType]["values"][typeCounter]["sysAddress"]
							updateSource = devInfo["type"][stateType]["updateSource"]

							if self.variablesToDevicesLast[linkAdr] != {} and value0 != self.variablesToDevicesLast[linkAdr]["type"][stateType]["values"][typeCounter]["value"]: 
								changed += 2

							if changed > 0:
								value = round(value0/norm,1) 
								if devInfo["devAddress"]  not in dev:
									dev[address] = indigo.devices[self.homematicAllDevices[address]["indigoId"]]	

								if dev[address].states.get("enabledChildren","") != "": # check if child 
									enabledChildren = dev[address].states.get("enabledChildren","").split(",")
									childInfo = json.loads(dev[address].states.get("childInfo","{}"))

									if stateType in childInfo: #   right child ?
										devId = childInfo[stateType][0]
										if devId > 1 and devId in indigo.devices: # exists?

											if devId not in devChild:  # did we get it already, some have multiple state to update, only get once 
												devChild[devId] = indigo.devices[devId]

											if key in devChild[devId].states: # update child  now 
												self.addToStatesUpdateDict(devChild[devId], key, value, uiValue=form.format(value))
												if devChild[devId].pluginProps.get("displayS","--") == key and "sensorValue" in devChild[devId].states:
													self.addToStatesUpdateDict(devChild[devId], "sensorValue", value, uiValue= form.format(value))
												resetState = key.split("Total")[0]+"_reset"
												if (resetState in devChild[devId].states) and (value < 1 and ( dt[0:-5] > devChild[devId].states[resetState][0:-5]  or len(devChild[devId].states[resetState]) < 5) ): # only reset once in 60 minutes 
													self.addToStatesUpdateDict(devChild[devId], resetState, dt)

												continue
										
								if key in dev[address].states: # update parent if it was not child 
									self.addToStatesUpdateDict(dev[address], key, value, uiValue= form.format(value))
								
			self.variablesToDevicesLast = copy.deepcopy(self.variablesToDevices)
		except	Exception as e:
			if "{}".format(e).find("None") == -1: self.indiLOG.log(40,"", exc_info=True)
		return

	####-----------------	 ---------
	def getIndigoDevTypeIdFromHometicDevType(self, homematicTypeUpper):
		try:
			indigoType = ""
			for xx in k_supportedDeviceTypesFromHomematicToIndigo:
				if "||" in xx:  # must be exactely homematic == indigo  w/o any extra characters like -2 abc V2 ... || is at the end
					if homematicTypeUpper+"||" == xx:  # ad || to the end and check if it matches.
						indigoType =  k_supportedDeviceTypesFromHomematicToIndigo[xx]
						break
				else: # this is how the characters appear in
					if homematicTypeUpper.find(xx) == 0:
						indigoType =  k_supportedDeviceTypesFromHomematicToIndigo[xx]
						break
		except	Exception as e:
			if "{}".format(e).find("None") == -1: self.indiLOG.log(40,"", exc_info=True)
		return indigoType


	####-----------------	 ---------
	def doallDevices(self, doit):
		try:
			if not doit: return 
			startTime = time.time()
			if  "allDevice" not in self.allDataFromHomematic:  return 
			if  "address" not in self.allDataFromHomematic["allDevice"]:  return 
			doHeating = self.pluginPrefs.get("accept_HEATING",True)
			deviceFound = {}
			theDict = {}
			self.numberOfDevices = 0
			allValueLinks = self.allDataFromHomematic["allDevice"].get("allValueLinks",{})
			#self.indiLOG.log(20,"doallDevices, valuelinks: {}...<".format( str(allValueLinks)[0:100] ) )

			for address in self.allDataFromHomematic["allDevice"]["address"]:
				if self.pluginState == "stop": return 
				if len(address) < 2: continue
				devinfoForChild = {}
				deviceFound[address] = True
				doPrint = False  #  address.find("0052E3C0003026") > -1
				try:
					thisDev = self.allDataFromHomematic["allDevice"]["address"][address]

					if "type" not in thisDev: continue
					thisType = thisDev["type"].upper()
					title = thisDev.get("title","")

					if address not in self.homematicAllDevices: 
						self.fixAllhomematic(address=address)
						self.homematicAllDevices[address]["type"]	= thisType
					if self.homematicAllDevices[address]["homemtaticStatus"] == "deleted":
						if self.homematicAllDevices[address]["indigoId"] in indigo.devices:
							self.indiLOG.log(20,"doallDevices, #:{};  title:{}, enabling device in indigo, was added back on homematic".format( address, title) )
							dev = indigo.devices[self.homematicAllDevices[address]["indigoId"]]
							indigo.device.enable(dev, value=True)
						
	
					self.homematicAllDevices[address]["homemtaticStatus"] = "active"
					self.homematicAllDevices[address]["lastmessageFromHomematic"] = time.time()

					if self.homematicAllDevices[address]["indigoStatus"] not in ["active","create"]: 
						continue

					name = title 
					if name.find(address) == -1:
						name += "-"+ address	
	
					self.numberOfDevices += 1

					homematicType = thisDev.get("type","").split()[0]
					homematicTypeUpper = homematicType.upper()
					firmware = thisDev.get("firmware","")
					availableFirmware = thisDev.get("availableFirmware","")

					indigoType = self.getIndigoDevTypeIdFromHometicDevType(homematicTypeUpper)
					if doPrint:  self.indiLOG.log(20,"doallDevices, :{}; homematicTypeUpper:{}; indigoType:{} pass 1".format( address, homematicTypeUpper, indigoType) )
					#if doPrint:  self.indiLOG.log(20,"doallDevices,k_createStates:\n{}".format( k_createStates) )

					if k_createStates.get(indigoType,"") == "": continue 
					if doPrint:  self.indiLOG.log(20,"doallDevices, :{};  pass 2".format( address) )

					devFound = False
					if address in self.homematicAllDevices and self.homematicAllDevices[address]["indigoId"] != 0:
						try:
							dev = indigo.devices[self.homematicAllDevices[address]["indigoId"] ]
							props = dev.pluginProps
							devFound = True
							self.fixAllhomematic(address=address)
							self.homematicAllDevices[address]["type"] 			= homematicType
							self.homematicAllDevices[address]["title"] 			= title
							self.homematicAllDevices[address]["indigoId"] 		= dev.id
							self.homematicAllDevices[address]["indigoDevType"] 	= dev.deviceTypeId
						except: pass

					if not devFound:
						for dev in indigo.devices.iter(self.pluginId):
							if self.pluginState == "stop": return  
							if dev.deviceTypeId != indigoType: continue
							if "address" not in dev.states:
								continue
							if dev.states["address"] == address: 
								devFound = True
								self.fixAllhomematic(address=address)
								self.homematicAllDevices[address]["type"] 			= homematicType
								self.homematicAllDevices[address]["title"] 			= title
								self.homematicAllDevices[address]["indigoId"] 		= dev.id
								self.homematicAllDevices[address]["indigoDevType"]	= dev.deviceTypeId
								break
					if doPrint: self.indiLOG.log(20,"doallDevices, :{};  devFound:{}; pass 3".format( address, devFound) )

					if not devFound:
						try: 
							dev = indigo.devices[name]
							props = dev.pluginProps
							devFound = True
							self.fixAllhomematic(address=address)
							self.homematicAllDevices[address]["type"] 			= homematicType
							self.homematicAllDevices[address]["title"]			= title
							self.homematicAllDevices[address]["indigoId"] 		= dev.id
							self.homematicAllDevices[address]["indigoDevType"] 	= dev.deviceTypeId
						except: pass

					if doPrint:   self.indiLOG.log(20,"doallDevices, :{};  devFound:{}; pass 4".format( address, devFound) )

					if not devFound and not self.pluginPrefs.get("ignoreNewDevices", False): 
							if indigoType not in k_mapHomematicToIndigoDevTypeStateChannelProps: continue

							newprops = {}
							if indigoType in k_mapHomematicToIndigoDevTypeStateChannelProps:
								newprops = k_mapHomematicToIndigoDevTypeStateChannelProps[indigoType]["props"]
							if "numberOfPhysicalChannels" in newprops:
								Nch = homematicTypeUpper.split("-C")[1]
								newprops["numberOfPhysicalChannels"] = Nch

					
							indigoStates = k_mapHomematicToIndigoDevTypeStateChannelProps[indigoType]["states"]

							testStates = []
							for st in indigoStates:
								for chkIf in k_checkIfPresentInValues: 
									if st.upper().find(chkIf) > -1: 
										testStates.append( chkIf)
										break

							if testStates != []:
								for chkIf in testStates:
									for test in allValueLinks:
										if test.find(address) == -1: continue
		
										if test.find(chkIf) > -1: 
											#if name == "HmIP-DRSI1-0029DD89A1358F": self.indiLOG.log(20,"doallDevices, pass 2, chkIf:{},  links:{}" .format(chkIf,  test))
											newprops[chkIf+"_Ignore"] = False
											break
										newprops[chkIf+"_Ignore"] = True

							if indigoType in k_indigoDeviceisThermostatDevice:
								newprops["heatIsOn"] = True

							if doPrint:   self.indiLOG.log(20,"doallDevices, :{};  pass 5".format( address) )
							if self.pluginPrefs.get("ignoreNewDevices", False): continue
							self.newDevice	= True							
							#self.indiLOG.log(20,"doallDevices, :{}; indigoType:{}, addr:{}, \nprops:{}, \nstates:{}".format( name, indigoType, address, newprops, k_mapHomematicToIndigoDevTypeStateChannelProps[indigoType]["states"]) )
							dev = indigo.device.create(
								protocol		= indigo.kProtocol.Plugin,
								address			= address,
								name			= name,
								description		= "",
								pluginId		= self.pluginId,
								deviceTypeId	= indigoType,
								folder			= self.folderNameDevicesID,
								props			= newprops
								)
							self.newDevice	= False							
							self.homematicAllDevices[address]["indigoId"] = dev.id

							self.addToStatesUpdateDict(dev, "created", datetime.datetime.now().strftime(_defaultDateStampFormat))
							self.addToStatesUpdateDict(dev, "address", address)
							if dev.deviceTypeId in k_indigoDeviceisThermostatDevice and dev.hvacMode == indigo.kHvacMode.Off:
								indigo.thermostat.setHvacMode(dev, indigo.kHvacMode.Heat)
	
							if indigoType in k_mapHomematicToIndigoDevTypeStateChannelProps:
								for zz in k_mapHomematicToIndigoDevTypeStateChannelProps[indigoType]["states"]:
									yy = k_mapHomematicToIndigoDevTypeStateChannelProps[indigoType]["states"][zz]
									#if indigoType.find("SCTH") > -1: self.indiLOG.log(20,"created Device:{}; ==> map info:{}".format( dev.name, yy ) )
									#self.indiLOG.log(20,"doallDevices, :{};  zz:{} - yy:{}".format( dev.name, zz, yy) )
									if "init" in yy:
										self.addToStatesUpdateDict(dev, yy["indigoState"], yy["init"])
							self.executeUpdateStatesList()
							self.sleep(0.1)
							dev = indigo.devices[dev.id]
							props = dev.pluginProps
							devFound = True
							self.fixAllhomematic(address=address)
							self.homematicAllDevices[address]["type"] = homematicType
							self.homematicAllDevices[address]["title"] = title
							self.homematicAllDevices[address]["indigoId"] = dev.id
							self.homematicAllDevices[address]["indigoDevType"] = dev.deviceTypeId
							for st in dev.states:
								if st.find("enabledChildren"):
									if dev.id not in self.devsWithenabledChildren: self.devsWithenabledChildren.append(dev.id)
									break

					if doPrint:   self.indiLOG.log(20,"doallDevices, :{}; devFound:{}; pass 6".format( address, devFound) )
					if not devFound: continue

					if not dev.enabled: continue
					self.homematicAllDevices[address]["indigoId"]	= dev.id
					self.homematicAllDevices[address]["indigoDevType"]	= dev.deviceTypeId

					if indigoType in k_systemAP: continue
					hprops = k_mapHomematicToIndigoDevTypeStateChannelProps[indigoType]["props"]

					#if address =="002EA0C98EEE0B":  self.indiLOG.log(20,"doallDevices, :{};  pass 7, t:{}, id:{}, name:{}, homematicType:{} ".format( address, title, dev.id, dev.name, homematicType) )
					if "roomId" not in hprops.get("ignoreStates","") :
						self.addToStatesUpdateDict(dev, "roomId", str(sorted(self.roomMembers.get(address,""))).strip("[").strip("]").replace("'",'') )
					if "firmware" not in hprops.get("ignoreStates","") :
						self.addToStatesUpdateDict(dev, "firmware", firmware)
					if "availableFirmware" not in hprops.get("ignoreStates","") :
						self.addToStatesUpdateDict(dev, "availableFirmware", availableFirmware)

					self.addToStatesUpdateDict(dev, "title", title)
					self.addToStatesUpdateDict(dev, "homematicType", homematicType)


					if indigoType in k_devTypeHasChildren and devFound:

						childInfo0 = dev.states.get("childInfo", "{}")
						if childInfo0 in ["{}",""]: continue
						try:	
							childInfo = json.loads(childInfo0)
						except:
							self.indiLOG.log(20,"doallDevices, error in json decoding for 1 {}; childInfo0:>>{}<<".format( dev.name, childInfo0))
							continue

						enabledChildren = ""
						#if indigoType.find("INT000") > -1: self.indiLOG.log(20,"createDevicesFromCompleteUpdate,1 {}; childInfo:{}".format( dev.name, childInfo))
						anyChange = False
						if childInfo != {}: 
							parentProps = dev.pluginProps
							for mType in copy.copy(childInfo):

								#  {childInfo = childInfo:{'Temperature': [429389644, '4', 'HMIP-Temperature'], 'Humidity': [1093019429, '4', 'HMIP-Humidity'], 'Relay': [1422531914, '7', 'HMIP-Relay'], 'Dimmer': [738580295, '11', 'HMIP-Dimmer']}
								if mType not in childInfo:
									continue
								try:
									chId, chn, childDevType = childInfo[mType]
								except:
									childInfo[mType] = [0,"-99",mType] # set to default channel =-99 = all 
									continue
								#if address == "000720C999113C" : self.indiLOG.log(20,"doallDevices, 1   :{}; mType:{};  enable:{},  childInfo:{}".format( dev.name, mType, parentProps.get("enable-"+mType, False), childInfo) )
								if not parentProps.get("enable-"+mType, False): 
									if chId > 0:
										if chId in indigo.devices:
											delDev = indigo.devices[chId]
											indigo.device.delete(delDev)
										childInfo[mType] = [0, chn, childInfo[mType][2]]
										anyChange = True
									chId = 0
									continue
								if chId > 0: 
									try:
										#if address == "000720C999113C" :self.indiLOG.log(20,"doallDevices, :{}; exists: chId:{}".format( dev.name, chId ))
										dev1 = indigo.devices[chId]
										chId = dev1.id
									except:
										#if address == "000720C999113C" :self.indiLOG.log(30,"doallDevices, 3 {}; child w channel:{} , id:{}  does not exist, recreating ".format( dev.name, chn, chId ))
										chId = 0 
										del childInfo[mType]
										anyChange = True
								childAddress	= address+"-child-"+mType

								if chId == 0: 
									try: 	ii = int(mType)
									except: ii = -1
									#if address == "000720C999113C" :self.indiLOG.log(20,"doallDevices, 4 :{};  address:{}-child, indigoType:{}, mType:{}, childDevType:{}".format( dev.name, address, indigoType, mType, childDevType  ) )
									self.newDevice	= True
									if name+"-child-{} of {}".format(mType, dev.id) in indigo.devices:
										dev1 = indigo.devices[name+"-child-{} of {}".format(mType, dev.id) ]
									else:
										if childDevType not in k_mapHomematicToIndigoDevTypeStateChannelProps:
											#self.indiLOG.log(20,"doallDevices, 5 childDevType:{} not in k_mapHomematicToIndigoDevTypeStateChannelProps".format( childDevType  ) )
											continue

										props			 =  copy.copy(k_mapHomematicToIndigoDevTypeStateChannelProps[childDevType]["props"])
	
										for pp in parentProps:
											for vv in k_checkIfPresentInValues:
												if pp.upper().find(vv+"_IGNORE") == 0:
													props[pp] = parentProps[pp]
			
										props["isChild"] = True					
										dev1 = indigo.device.create(
											protocol		= indigo.kProtocol.Plugin,
											address			= address,
											name			= name+"-child-{} of {}".format(mType, dev.id),
											description		= "",
											pluginId		= self.pluginId,
											deviceTypeId	= childDevType,
											folder			= self.folderNameDevicesID,
											props			= k_mapHomematicToIndigoDevTypeStateChannelProps[childDevType]["props"]
											)
										self.newDevice	= False	
										self.sleep(0.1)
										dev1 = indigo.devices[dev1.id]  # get a fresh copy
										#if True: self.indiLOG.log(20,"doallDevices, 6 :{};  add state address =={}".format( dev1.name, address+"-child-"+mType) )
										self.addToStatesUpdateDict(dev1, "created", datetime.datetime.now().strftime(_defaultDateStampFormat))
										self.addToStatesUpdateDict(dev1, "address", childAddress)
										anyChange = True
										childInfo[mType] = [dev1.id, chn, childDevType]
										enabledChildren += mType+","
									self.addToStatesUpdateDict(dev1, "channelNumber", chn)
								self.addToStatesUpdateDict(dev1, "title", title)
								self.addToStatesUpdateDict(dev1, "homematicType", homematicType)
								self.addToStatesUpdateDict(dev1, "childOf", dev.id)
								self.executeUpdateStatesList()					

								if childAddress not in self.homematicAllDevices:
									self.homematicAllDevices[childAddress] = {}

								self.homematicAllDevices[childAddress]["homemtaticStatus"] = "active"
								self.homematicAllDevices[childAddress]["indigoId"] = dev1.id
								self.homematicAllDevices[childAddress]["indigoDevType"] = dev1.deviceTypeId
								self.homematicAllDevices[childAddress]["indigoStatus"] = "active"
								self.homematicAllDevices[childAddress]["childInfo"] = {}
								self.homematicAllDevices[childAddress]["title"] = title
								self.homematicAllDevices[childAddress]["type"] = thisType
								if "lastErrorMsg" not in self.homematicAllDevices[childAddress]: 
									self.homematicAllDevices[childAddress]["lastErrorMsg"] = 0
								if "lastmessageFromHomematic" not in self.homematicAllDevices[childAddress]: 
									self.homematicAllDevices[childAddress]["lastmessageFromHomematic"] = 0
								if "sValue" not in self.homematicAllDevices[childAddress]: 
									self.homematicAllDevices[childAddress]["sValue"] = 0

								if self.decideMyLog("Digest"): self.indiLOG.log(10,"doallDevices, :{};  address:{}-child, indigoType-child".format( dev1.name, address) )
								deviceFound[childAddress] = True

						if anyChange: 
							#if address == "000720C999113C" : self.indiLOG.log(20,"doallDevices, anychange :{};  childInfo:{}".format( dev.name, childInfo) )
							self.addToStatesUpdateDict(dev, "childInfo",  json.dumps(childInfo))
							self.addToStatesUpdateDict(dev, "enabledChildren",  enabledChildren.strip(","))
							for mType in childInfo:
								chId , chn, childDevType  =  childInfo[mType]
								if childDevType not in k_mapHomematicToIndigoDevTypeStateChannelProps: continue
								if "states" not in k_mapHomematicToIndigoDevTypeStateChannelProps[childDevType]: continue
								homematicStateNames = k_mapHomematicToIndigoDevTypeStateChannelProps[childDevType]["states"]

								if chn not in  self.homematicAllDevices[address]["childInfo"]:
									self.homematicAllDevices[address]["childInfo"][chn] = {}
								for homematicStateName in homematicStateNames:
									if homematicStateName not in k_dontUseStatesForOverAllList:
										self.homematicAllDevices[address]["childInfo"][chn][homematicStateName] = chId
							self.executeUpdateStatesList()					
						#if address == "000720C999113C" : self.indiLOG.log(20,"createDevicesFromCompleteUpdate finish , {}  childInfo:{}".format( dev.name, childInfo) )
					

				except	Exception as e:
					if "{}".format(e).find("None") == -1: self.indiLOG.log(40,"", exc_info=True)
					if self.pluginState == "stop": return  
		except	Exception as e:
			if "{}".format(e).find("None") == -1: self.indiLOG.log(40,"", exc_info=True)
		self.newDevice = False
		self.executeUpdateStatesList()					
		self.sleep(1)

		if  not self.firstReadAll:
			for address in self.homematicAllDevices:
				devId =  self.homematicAllDevices[address]["indigoId"]

				if  self.homematicAllDevices[address]["indigoStatus"] not in ["active"]: continue
				
				if devId not in indigo.devices: continue

				dev = indigo.devices[devId]
				states = dev.states
				#self.indiLOG.log(20,"dev.name: {}, chid{}".format(dev.name,  states.get("childInfo","") ))
				if not "childInfo" in states: continue
				try:	childInfo = json.loads(states["childInfo"]) 
				except: continue
				#if address == "000720C999113C" : self.indiLOG.log(20,"createDevicesFromCompleteUpdate not firstread , {}  childInfo:{}".format( address, childInfo ))
				for mType in childInfo:
					#if address == "000720C999113C" : self.indiLOG.log(20,"....  mType? {}".format(mType))
					chId , chn, childDevType  =  childInfo[mType]
					if childDevType not in k_mapHomematicToIndigoDevTypeStateChannelProps: continue
					if "states" not in k_mapHomematicToIndigoDevTypeStateChannelProps[childDevType]: continue
					homematicStateNames = k_mapHomematicToIndigoDevTypeStateChannelProps[childDevType]["states"]
					#if address == "000720C999113C" :self.indiLOG.log(20,"address:{}, homematicStateNames:{} ".format(address, homematicStateNames ))
					if chn not in  self.homematicAllDevices[address]["childInfo"]:
						self.homematicAllDevices[address]["childInfo"][chn] = {}
					for homematicStateName in homematicStateNames:
						#if address == "000720C999113C" :self.indiLOG.log(20,"address:{}, homematicStateName:{:15}, mType:{}, chId:{} , chn:{}, childDevType:{}, self.homematicAllDevices[address][..chn]:{} ".format(address, homematicStateName, mType, chId , chn, childDevType, self.homematicAllDevices[address]["childInfo"][chn] ))
						if homematicStateName not in k_dontUseStatesForOverAllList:
							self.homematicAllDevices[address]["childInfo"][chn][homematicStateName] = chId


		#self.indiLOG.log(20,"doallDevices deviceFound , {} ".format( deviceFound ))
		for address in copy.deepcopy(self.homematicAllDevices):
			doPrint = address.find("xxx001860C98C9E3E") > -1
			if doPrint : self.indiLOG.log(20,"doallDevices lastloop , {}  childInfo:{}".format( address, self.homematicAllDevices[address]["childInfo"] ))
			if deviceFound != {} and address not in deviceFound :
				if  address.find("INT00") == -1 and self.homematicAllDevices[address]["type"] not in ["ROOM","STRING","FLOAT","BOOL","ALARM",""]:
					self.homematicAllDevices[address]["homemtaticStatus"] = "deleted"
					if self.homematicAllDevices[address]["indigoStatus"] == "active":
						try: 
							dev = indigo.devices[self.homematicAllDevices[address]["indigoId"]]
							if dev.enabled:
								self.indiLOG.log(20,"doallDevices  it looks as if HomeMatic-address#:{}, devId:{}, type:{} was deleted on Homematic, disabling in indigo".format(address, self.homematicAllDevices[address]["indigoId"] , self.homematicAllDevices[address]["type"] ))
								indigo.device.enable(dev, value=False)
						except	Exception as e:
							eee =  "{}".format(e)
							if eee.find("None") == -1:
								if eee.lower().find("timeout") > -1: self.indiLOG.log(30,"address:{}".format(address), exc_info=True)
								else: 
									self.indiLOG.log(20,"doallDevices  it looks as if HomeMatic-address#:{}, devId:{}, type:{} was deleted in indigo , removing from internal tables".format(address, self.homematicAllDevices[address]["indigoId"] , self.homematicAllDevices[address]["type"] ))
									del self.homematicAllDevices[address]


		if self.decideMyLog("Time"):
			self.indiLOG.log(20,"doallDevices  elapsed time: {:.1f} secs".format(time.time()-startTime))

		self.firstReadAll = True


		self.executeUpdateStatesList()					

		return

	

	####-----------------	 ---------
	def createEverythingFromCompleteUpdate(self):
		try:
			
			if self.allDataFromHomematic == {} or self.allDataFromHomematic == "": return 

			doRooms = True
			doProgram = True
			doVendor = True
			doSysvar = True
			doVariablesToDevices = True
			doDevices = True


			##self.indiLOG.log(20,self.listOfprograms)
			self.makeListOfallPrograms(doProgram)
			self.makeListOfallVendors(doVendor)
			self.doallRooms(doRooms)
			self.doallSysVar(doSysvar)
			self.doallVarToDev(doVariablesToDevices)
			self.doallDevices(doDevices)

			self.oneCycleComplete = True
			self.executeUpdateStatesList()

		except	Exception as e:
			if "{}".format(e).find("None") == -1: self.indiLOG.log(40,"", exc_info=True)





	####-----------------	 ---------
	def getDeviceData(self):

		try:
			getHomematicClass = "" 
			getValuesLast = 0
			# make sure theat get all data is finished
			time.sleep(2) 
			for iii in range(20):
				if self.firstReadAll: break
				self.sleep(1)

			self.devCounter = 0
			self.threads["getDeviceData"]["status"] = "running"

			getValuesLast ={"1":0,"2":0,"3":0}
			while self.threads["getDeviceData"]["status"]  == "running":
					self.sleep(0.3)
					repeatLevel = "0"
					if   time.time() - self.getDataNow > 0:  										repeatLevel = "1"
					elif time.time() - getValuesLast["3"] > self.getValuesEvery * k_repeatGet["3"]:	repeatLevel = "3"
					elif time.time() - getValuesLast["2"] > self.getValuesEvery * k_repeatGet["2"]:	repeatLevel = "2"
					elif time.time() - getValuesLast["1"] > self.getValuesEvery * k_repeatGet["1"]:	repeatLevel = "1"
						#if self.decideMyLog("Special"): self.indiLOG.log(20,"getting getDataNow :{}, getDataNow :{}".format(time.time() - getValuesLast > self.getValuesEvery,  time.time() - self.getDataNow ))
					if repeatLevel != "0":
						startTime = time.time()
						if self.testPing(self.ipNumber) != 0:
							self.indiLOG.log(30,"getDeviceData ping to {} not sucessfull".format(self.ipNumber))
							self.sleep(5)
							getValuesLast[repeatLevel]  = time.time()			
							continue
	
						if  getHomematicClass == "" or "getDeviceData" in self.restartHomematicClass:
							#self.indiLOG.log(20,f" .. (re)starting   class  for getDeviceData   {self.restartHomematicClass:}" )
							self.sleep(0.9)
							# initiate class using getHomematicData
							getHomematicClass = getHomematicData(self.ipNumber, self.portNumber, kTimeout = self.requestTimeout, calling="getDeviceData" )
							try: 	del self.restartHomematicClass["getDeviceData"] 
							except: pass
	
						# reset fast get after exp of time only before contiue to check  
						NumberOfhttpcalls, allValues = getHomematicClass.execGetDeviceValues(self.allDataFromHomematic, repeatLevel)
						if repeatLevel == "3" and self.pluginPrefs.get("writeInfoToFile", False):
							self.writeJson( allValues, fName=self.indigoPreferencesPluginDir + "allValues.json", sort = True, doFormat=True, singleLines=True )

						if allValues != "" and allValues != {}:
							self.upDateDeviceValues(allValues, NumberOfhttpcalls, repeatLevel)

						if time.time() - self.getDataNow > 0: self.getDataNow = time.time() + 9999999999
						if repeatLevel =="3": getValuesLast["1"]  = time.time(); getValuesLast["2"]  = time.time();	getValuesLast["3"]  = time.time()			
						if repeatLevel =="2": getValuesLast["1"]  = time.time(); getValuesLast["2"]  = time.time()			
						if repeatLevel =="1": getValuesLast["1"]  = time.time()		
						#if self.decideMyLog("Special"): self.indiLOG.log(20,"received data, dt:{:.2f}  repeatLevel:{}, len(allValues):{}".format(time.time()-startTime, repeatLevel, len(allValues)))
	

			time.sleep(0.1)
			if self.threads["getDeviceData"]["status"] == "running": self.indiLOG.log(30,f" .. getDeviceData ended, please restart plugin  end of while state: {self.threads['getDeviceData']['status']:}")
			self.threads["getDeviceData"]["status"] = "stop" 
			return 

		except	Exception as e:
			if "{}".format(e).find("None") == -1: self.indiLOG.log(40,"", exc_info=True)
			#self.indiLOG.log(30,"getDeviceData forced or error exiting getDeviceData, due to stop ")
		time.sleep(0.1)
		if self.threads["getDeviceData"]["status"] == "running": self.indiLOG.log(30,f" .. getDeviceData ended, please restart plugin  exit at error;  state: {self.threads['getDeviceData']['status']:}")
		self.threads["getDeviceData"]["status"] = "stop" 
		return 

	####-----------------	 ---------
	def getCompleteupdate(self):

		getHomematicClassALLData = ""
		self.getcompleteUpdateLast  = 0
		self.threads["getCompleteupdate"]["status"] = "running"
		numberOfhttpCalls = 0
		while self.threads["getCompleteupdate"]["status"]  == "running":
			try:
				self.sleep(0.3)
				try:
					if time.time() - self.getcompleteUpdateLast < self.getCompleteUpdateEvery: continue 
					if  getHomematicClassALLData == "" or "getCompleteupdate" in self.restartHomematicClass:
						self.sleep(0.1)
						# init calls using getHomematicData
						getHomematicClassALLData = getHomematicData(self.ipNumber, self.portNumber, kTimeout =self.requestTimeout, calling="getCompleteupdate" )
						#self.indiLOG.log(20,f" .. (re)starting   class  for getCompleteupdate  {self.restartHomematicClass:}" )
						self.firstReadAll = False
						try: 	del self.restartHomematicClass["getCompleteupdate"]
						except: pass

					if self.testPing(self.ipNumber) != 0:
						self.indiLOG.log(30,"getAllVendor ping to {} not sucessfull".format(self.ipNumber))
						self.sleep(5)
						self.getcompleteUpdateLast  = time.time()
						continue

					#self.indiLOG.log(20,f"getCompleteupdate .. time for complete update " )


					self.getcompleteUpdateLast  = time.time()

					objects = {
						"allDevice":		[True,0,0], 
						"allRoom":			[True,0,0], 
						"allFunction":		[True,0,0], 
						"allSysvar":		[True,0,0], 
						"allProgram":		[True,0,0], 
						"allVendor":		[True,0,0]
					}
					out = ""
					t0= time.time()
					ncallsThisTime = numberOfhttpCalls
					for xx in objects:
						if self.threads["getCompleteupdate"]["status"] != "running": return 
						if objects[xx][0]:
							#self.indiLOG.log(20,"testing  {:}".format(xx) )
							tt = time.time()
							if self.threads["getCompleteupdate"]["status"] != "running": break
							numberOfhttpCalls, self.allDataFromHomematic[xx] = getHomematicClassALLData.getInfo(xx)
							if self.threads["getCompleteupdate"]["status"] != "running": break
							objects[xx][1] = time.time() - tt
					
							ll = 0
							for yy in self.allDataFromHomematic[xx]:
								#self.indiLOG.log(20,"testing  {:}, yy:{}".format("address" in yy, str(allInfo[xx][yy])[0:30]) )
								if yy == "address": 
									ll = len(self.allDataFromHomematic[xx][yy])
									break
								else:
									ll = 0.5

							objects[xx][2] = ll
							out += "{}:{:.2f}[secs] #{:} items;  ".format(xx, objects[xx][1], objects[xx][2])

					if self.pluginPrefs.get("writeInfoToFile", False):
						self.writeJson(self.allDataFromHomematic, fName=self.indigoPreferencesPluginDir + "allData.json")

					if self.decideMyLog("Digest"): self.indiLOG.log(20,"written new allInfo file  {:}, # of http calls:{:}, Tot # http Calls: {:}, total time:{:.1f}[secs]".format(out, numberOfhttpCalls - ncallsThisTime, numberOfhttpCalls, time.time()- t0) )
					self.createEverythingFromCompleteUpdate()

				except	Exception as e:
					if "{}".format(e).find("None") == -1: self.indiLOG.log(40,"", exc_info=True)
					self.getHomematicClass  = ""

			except	Exception as e:
				#self.indiLOG.log(40,"", exc_info=True)
				#self.indiLOG.log(30,"getCompleteupdate forced or error exiting getCompleteupdate, due to stop ")
				pass
		if self.threads["getCompleteupdate"]["status"] == "running": self.indiLOG.log(30,f" .. getCompleteupdate ended, please restart plugin")
		self.threads["getCompleteupdate"]["status"] = "stop" 
		return 


	###########################	   MAIN LOOP  ## END ######################
	###########################	   MAIN LOOP  ## END ######################
	###########################	   MAIN LOOP  ## END ######################
	###########################	   MAIN LOOP  ## END ######################

	####-----------------	 ---------
	def checkOnDelayedActions(self):
		try:
			if self.delayedAction == {}: return 
			newD = {}
			for devId in copy.deepcopy(self.delayedAction):
				newD[devId] = []
				for nn in range(len(self.delayedAction[devId])):
					actionItems = self.delayedAction[devId][nn]
					if actionItems[0] == "updateState" and time.time() - actionItems[1] > 0:
						try:
							if len(actionItems) == 5:
								self.addToStatesUpdateDict(indigo.devices[devId], actionItems[2], actionItems[3], uiValue=actionItems[4] )
							else:
								self.addToStatesUpdateDict(indigo.devices[devId], actionItems[2], actionItems[3] )
						except: 
							continue
					else:
						newD[devId].append(actionItems)
				if newD[devId] == {}: del newD[devId] 
			self.delayedAction = newD

		except	Exception as e:
			if "{}".format(e).find("None") == -1: self.indiLOG.log(40,"", exc_info=True)
		return 


	####-----------------	 ---------
	def processPendingCommands(self):
		try:
			if self.pendingCommand == {}: return 

			if self.pendingCommand.get("restartHomematicClass", False): 
				self.restartHomematicClass = {"getDeviceData":True, "getCompleteupdate":True}
				self.indiLOG.log(20,"processPendingCommands: restarting connect ")
				del  self.pendingCommand["restartHomematicClass"] 

			if self.pendingCommand.get("getFolderId", False): 
				self.getFolderId()
				del  self.pendingCommand["getFolderId"]

			if self.pendingCommand.get("setDebugFromPrefs", False): 
				self.setDebugFromPrefs(self.pluginPrefs)
				del  self.pendingCommand["setDebugFromPrefs"]

			if self.pendingCommand.get("createHometicHostDev", False): 
				del self.pendingCommand["createHometicHostDev"]
				found = False
				for dev in indigo.devices.iter(self.pluginId):
					if dev.deviceTypeId == "Homematic-Host":
						found = True
						self.hostDevId = dev.id
						break

				if not found:
					newProps = k_mapHomematicToIndigoDevTypeStateChannelProps["Homematic-Host"]["props"]
					newProps["ipNumber"] = self.pluginPrefs.get("ipNumber","") 
					newProps["portNumber"] = self.pluginPrefs.get("portNumber","") 
					self.newDevice	= True							
					dev = indigo.device.create(
						protocol		= indigo.kProtocol.Plugin,
						address			= self.pluginPrefs.get("ipNumber","")+":"+self.pluginPrefs.get("portNumber","") ,
						name			= "homematic host",
						description		= "",
						pluginId		= self.pluginId,
						deviceTypeId	= "Homematic-Host",
						folder			= self.folderNameDevicesID,
						props			= newProps
						)
					self.newDevice	= False							
					self.addToStatesUpdateDict(dev, "created", datetime.datetime.now().strftime(_defaultDateStampFormat))
					self.hostDevId = dev.id



		except	Exception as e:
			if "{}".format(e).find("None") == -1: self.indiLOG.log(40,"", exc_info=True)
		self.newDevice = False
		return 


	####-----------------	 ---------
	def isBool2(self, v, doInverse, vInverse):

		if doInverse:
			if vInverse in [1,True,"1","true","True","T","t"]: return True
			return False
		else:
			if v in [1,True,"1","true","True","T","t"]: return True
			return False

	########################################
	########################################
	####-----------------  logging ---------
	########################################
	########################################

	####-----------------	 ---------
	def writeErrorToLog( self, address, text, logLevel = 20):
		if address not in self.homematicAllDevices: return 
		if time.time() - self.homematicAllDevices[address]["lastErrorMsg"] > self.writeToLogAfter:
			self.indiLOG.log(logLevel, text)
			self.homematicAllDevices[address]["lastErrorMsg"] = time.time()
		return 

	####-----------------	 ---------
	def decideMyLog(self, msgLevel, MAC=""):
		try:
			if MAC != "" and MAC in self.MACloglist:				return True
			if msgLevel	 == "All" or "All" in self.debugAreas:		return True
			if msgLevel	 == ""  and "All" not in self.debugAreas:	return False
			if msgLevel in self.debugAreas:							return True

		except	Exception as e:
			if "{}".format(e).find("None") == -1: self.indiLOG.log(40,"", exc_info=True)
		return False
#
###-----------------  valiable formatter for differnt log levels ---------
# call with: 
# formatter = LevelFormatter(fmt='<default log format>', level_fmts={logging.INFO: '<format string for info>'})
# handler.setFormatter(formatter)
class LevelFormatter(logging.Formatter):
	def __init__(self, fmt=None, datefmt=None, level_fmts={}, level_date={}):
		self._level_formatters = {}
		self._level_date_format = {}
		for level, format in level_fmts.items():
			# Could optionally support level names too
			self._level_formatters[level] = logging.Formatter(fmt=format, datefmt=level_date[level])
		# self._fmt will be the default format
		super(LevelFormatter, self).__init__(fmt=fmt, datefmt=datefmt)
		return

	####-----------------	 ---------
	def format(self, record):
		if record.levelno in self._level_formatters:
			return self._level_formatters[record.levelno].format(record)

		return super(LevelFormatter, self).format(record)



########################################
########################################
####-----------------  get homematic data class ---------
########################################
########################################

class getHomematicData:
	def __init__(self, ip, port, kTimeout=10, calling=""):
		self.ip = ip
		self.port = port
		self.kTimeout = kTimeout
		self.requestSession	 = requests.Session()
		self.LastHTTPerror = 0
		self.delayHttpfterError = 5
		self.suppressErrorsForSecs = 20 # secs
		self.LastErrorLog  = 0
		indigo.activePlugin.indiLOG.log(20,f"getHomematicData starting class ip:{ip:}, port:{port:},  called from:{calling:20s}, @ {datetime.datetime.now()}")
		self.connectCounter = 0
		self.doGetIndividualValuesDevices = False
		return 

	####-----------------	 ---------

	####-----------------	 ---------
	def getInfo(self, area):
		try:
			if indigo.activePlugin.pluginState == "stop": return ""
			if   area == "allDevice": 		return self.connectCounter, self.getAllDevice() 
			elif area == "allRoom": 		return self.connectCounter, self.getAllRoom() 
			elif area == "allFunction": 	return self.connectCounter, self.getAllFunction() 
			elif area == "allProgram": 		return self.connectCounter, self.getAllProgram() 
			elif area == "allVendor": 		return self.connectCounter, self.getAllVendor() 
			elif area == "allSysvar": 		return self.connectCounter, self.getAllSysvar() 
			
		except	Exception as e:
			if "{}".format(e).find("None") == -1: indigo.activePlugin.indiLOG.log(40,"", exc_info=True)
		return {area:"empty"}

	####-----------------	 ---------
	def doConnect(self, page, getorput="get", data="", logText=""):
		self.connectCounter += 1
		try:
			if indigo.activePlugin.decideMyLog("Connect"):  indigo.activePlugin.indiLOG.log(20,"doConnect: {}  {}  page:{}< data:{}...<".format(logText, getorput, page, str(data)[0:100]))
			if time.time() - self.LastHTTPerror < self.delayHttpfterError:
				time.sleep(self.delayHttpfterError - (time.time() - self.LastHTTPerror))
			if getorput == "get":
				r = self.requestSession.get(page, timeout=self.kTimeout)
			else:
				r = self.requestSession.put(page, data=data, timeout=self.kTimeout, headers={'Connection':'close',"Content-Type": "application/json"})
			self.LastHTTPerror = 0
			return  r
		except:
			if time.time()- self.LastErrorLog > self.suppressErrorsForSecs: 
				indigo.activePlugin.indiLOG.log(30,"connect to hometic did not work for {}  page={}".format(getorput, page))
				self.LastErrorLog = time.time()
			self.LastHTTPerror = time.time()
		return ""

	####-----------------	 ---------
	def execGetDeviceValues(self, allData, repeatLevel):
		try:
			tStart = time.time()
			if allData == "" or allData == {}: 					return self.connectCounter, {}
			if "allDevice" 		not in allData: 				return self.connectCounter, {}
			if "allValueLinks"	not in allData["allDevice"]: 	return self.connectCounter, {}
			if "allSysvar"		not in allData: 				return self.connectCounter, {}
			if "allValueLinks"	not in allData["allSysvar"]:	return self.connectCounter, {}

			allValues = {}
			theList = []
			if len(allData["allSysvar"]["allValueLinks"][repeatLevel]) > 0:	theList = allData["allDevice"]["allValueLinks"][repeatLevel] + allData["allSysvar"]["allValueLinks"][repeatLevel]
			else: 															theList = allData["allDevice"]["allValueLinks"][repeatLevel]

			#indigo.activePlugin.indiLOG.log(20,"execGetDeviceValues  repeatLevel:{}, theList len:{}, dev len{}, var len:{} ".format(repeatLevel, len(theList), len(allData["allDevice"]["allValueLinks"][repeatLevel]), len(allData["allSysvar"]["allValueLinks"][repeatLevel]) ))

			baseHtml = "http://{}:{}".format(self.ip , self.port)
			linkHtml = "http://{}:{}/{}".format(self.ip , self.port, "~exgdata")
			dataJson = json.dumps({"readPaths":theList })

			r = self.doConnect(linkHtml, getorput="put", data=dataJson, logText="execGetDeviceValues  ")
			if r == "": return self.connectCounter, allValues

			valesReturnedJson = r.content.decode('ISO-8859-1')
			valesReturnedDict = json.loads(valesReturnedJson)

			for nn in range(len(theList)):
				link  = theList[nn]
				if "pv" not in valesReturnedDict["readResults"][nn]: continue
				if "v"	not in valesReturnedDict["readResults"][nn]["pv"]: continue

				allValues[link] = valesReturnedDict["readResults"][nn]["pv"]
			if indigo.activePlugin.decideMyLog("Time"):  indigo.activePlugin.indiLOG.log(20,"execGetDeviceValues time used ={:.3f}[secs]".format( time.time()- tStart))
			return self.connectCounter, allValues

		except	Exception as e:
			if "{}".format(e).find("None") == -1: indigo.activePlugin.indiLOG.log(40,"", exc_info=True)
		return self.connectCounter, {"allValues":"empty"}

	####-----------------	 ---------
	def getAllDevice(self):
		try:
			tStart = time.time()
			if indigo.activePlugin.testPing(self.ip) != 0:
				if indigo.activePlugin.decideMyLog("Connect"): indigo.activePlugin.indiLOG.log(20,"getAllDevice ping to {} not sucessfull".format(self.ip))
				return {}

			theDict = {"address":{}, "values": {}, "allValueLinks":{"1":[], "2":[], "3":[]}}
			page = "device"
			pageQ = "~query?~path=device"
			baseHtml = "http://{}:{}/".format(self.ip , self.port)
			devices0Html = baseHtml+pageQ+"/*"
			if indigo.activePlugin.decideMyLog("GetData"): indigo.activePlugin.indiLOG.log(10,"getAllDevice base Accessing URL: {}".format(devices0Html))

			r = self.doConnect(devices0Html, logText="getAllDevice base ")
			if r == "": return {}
			if indigo.activePlugin.pluginState == "stop": return {}
			

			content = r.content.decode('ISO-8859-1')
			devices = json.loads(content)
			for dev in devices:
				theDict["address"][dev["address"]] = dev

			if indigo.activePlugin.pluginState == "stop": return theDict 

			devices1Html = baseHtml + pageQ+"/*/*"
			if indigo.activePlugin.decideMyLog("GetData"): indigo.activePlugin.indiLOG.log(10,"getAllDevice devices Accessing URL: {}".format(devices1Html))
	
			r = self.doConnect(devices1Html, logText="getAllDevice devices ")
			if r == "": return {}
			if indigo.activePlugin.pluginState == "stop": return {}

			content = r.content.decode('ISO-8859-1')
			if indigo.activePlugin.decideMyLog("GetDataReturn"): indigo.activePlugin.indiLOG.log(10,"getAllDevice {}".format(content[0:100]))

			devices = json.loads(content)
			for dev in  devices:
				if indigo.activePlugin.threads["getCompleteupdate"]["status"] != "running": return theDict
				if indigo.activePlugin.decideMyLog("GetDataReturn"): indigo.activePlugin.indiLOG.log(10," getAllDevice dev {}".format(dev))
				if "parent" not in dev: continue # skip master  
				address = dev["parent"]
				if dev["parent"] not in theDict["address"]: 
					if indigo.activePlugin.decideMyLog("GetData"): indigo.activePlugin.indiLOG.log(10," getAllDevice  aaddress not in detailed devs {}".format(dev["parent"] ))
					continue 

				if "channels" not in theDict["address"][address]:
					theDict["address"][address]["channels"] = {}

				channelNumber = str(dev["index"])
				theDict["address"][address]["channels"][channelNumber] = dev
				indigoType = indigo.activePlugin.getIndigoDevTypeIdFromHometicDevType(theDict["address"][address].get("type").upper())

				# now the details for the channel
				if "~links" not in dev: continue
				for prop in dev["~links"]:
					if indigo.activePlugin.pluginState == "stop": return theDict 
					if "href" not in prop: continue
					hrefProp = prop["href"]
					if hrefProp == "..": continue
					if hrefProp == "$MASTER": continue

					if hrefProp.find("room/") > -1: 
						theDict["address"][address]["channels"][channelNumber]["room"] = hrefProp.split("room/")[1]
						continue

					if hrefProp.find("function/") > -1: 
						theDict["address"][address]["channels"][channelNumber]["function"] = hrefProp.split("function/")[1]
						continue

					# get values
					link = "/device/{}/{}/{}".format(address,channelNumber,hrefProp)

					# this is all, slow only every xx secs
					theDict["allValueLinks"]["3"].append(link)

					if indigoType in k_mapHomematicToIndigoDevTypeStateChannelProps:
						homeaticState = link.split("/")[-1]
						refresh = "3"
						if homeaticState in k_mapHomematicToIndigoDevTypeStateChannelProps[indigoType].get("states",""):
							refresh = k_mapHomematicToIndigoDevTypeStateChannelProps[indigoType]["states"][homeaticState].get("refresh",{})

						elif homeaticState in k_mapHomematicToIndigoDevTypeStateChannelProps[indigoType].get("noIndigoState",{}):
							refresh = k_mapHomematicToIndigoDevTypeStateChannelProps[indigoType]["noIndigoState"][homeaticState].get("refresh","")

						# fast
						if refresh == "1":  
											theDict["allValueLinks"]["1"].append(link)

						# medium, also get #1
						if refresh == "2": 	
											theDict["allValueLinks"]["1"].append(link)
											theDict["allValueLinks"]["2"].append(link)

					# not used is always false
					if self.doGetIndividualValuesDevices:
						if indigo.activePlugin.decideMyLog("GetData"): indigo.activePlugin.indiLOG.log(10,"getAllDevice allValueLinks Accessing URL: {}".format(link))
						r = self.doConnect(baseHtml+link, logText="getAllDevice valueLink ")
						if r == "": return {}
						propDict= json.loads(r.content)
						if indigo.activePlugin.decideMyLog("GetDataReturn"): indigo.activePlugin.indiLOG.log(10,"getAllDevice valueLink  dict: {}".format(propDict))

					if "values" not in theDict["address"][address]["channels"][channelNumber]:
						theDict["address"][address]["channels"][channelNumber]["values"] = {}
					theDict["address"][address]["channels"][channelNumber]["values"][hrefProp] = {"link":link,"value":""}
					theDict["values"][link] = {}


			linkHtml = "http://{}:{}/{}".format(self.ip , self.port, "~exgdata")
			dataJson = json.dumps({"readPaths":theDict["allValueLinks"]["3"] })
			if indigo.activePlugin.decideMyLog("GetDataReturn"): indigo.activePlugin.indiLOG.log(10,"getAllDevice Accessing URL: {}, dataJ{}".format(linkHtml, dataJson))

			r = self.doConnect(linkHtml, getorput="put", data=dataJson, logText="getAllDevice data ")
			if r == "": return {}
			if indigo.activePlugin.pluginState == "stop": return {}

			valesReturnedJson = r.content.decode('ISO-8859-1')
			valesReturnedDict = json.loads(valesReturnedJson)
			
			if indigo.activePlugin.decideMyLog("GetDataReturn"): indigo.activePlugin.indiLOG.log(10,"getAllDevice theDict:\n{}".format(json.dumps(theDict, sort_keys=True, indent=2)))

			for nn in range(len(theDict["allValueLinks"]["3"])):
				if indigo.activePlugin.pluginState == "stop": return theDict 
				link  = theDict["allValueLinks"]["3"][nn]
				try:	dummy, device, address, channelNumber, hrefProp  = link.split("/")
				except: continue
				theDict["address"][address]["channels"][channelNumber]["values"][hrefProp]["value"] = valesReturnedDict["readResults"][nn]
				theDict["values"][link] = valesReturnedDict["readResults"][nn]

			#if indigo.activePlugin.decideMyLog("Special"): indigo.activePlugin.indiLOG.log(20,"received\n1:{}--{}\n2:{}--{}\n3:{}--{}".format(len(theDict["allValueLinks"]["1"]), theDict["allValueLinks"]["1"], len(theDict["allValueLinks"]["2"]), theDict["allValueLinks"]["2"], len(theDict["allValueLinks"]["3"]), theDict["allValueLinks"]["3"]))


		except	Exception as e:
			if "{}".format(e).find("None") == -1: indigo.activePlugin.indiLOG.log(40,"", exc_info=True)
			return {}
		if indigo.activePlugin.decideMyLog("Time"):  indigo.activePlugin.indiLOG.log(20,"getAllDevice time used ={:.3f}[secs], #of httpCalls: {}".format( time.time()- tStart, self.connectCounter))
		return theDict


	####-----------------	 ---------
	def getAllRoom(self):
		try:
			if indigo.activePlugin.testPing(self.ip) != 0:
				if indigo.activePlugin.decideMyLog("Connect"): indigo.activePlugin.indiLOG.log(20,"getAllRoom ping to {} not sucessfull".format(self.ip))
				return {}
			theDict = {"address":{}}
			page = "room"
			baseHtml = "http://{}:{}/{}".format(self.ip , self.port,  page)

			if indigo.activePlugin.decideMyLog("GetData"): indigo.activePlugin.indiLOG.log(10,"getAllRoom Accessing URL: {}".format(baseHtml))

			r = self.doConnect(baseHtml, logText="getAllRoom  base")
			if r == "": return {}
			if indigo.activePlugin.pluginState == "stop": return {}

			content = r.content.decode('ISO-8859-1')
			if indigo.activePlugin.decideMyLog("GetDataReturn"): indigo.activePlugin.indiLOG.log(10,"getAllRoom all {}:{}".format(page, content))
			objects = json.loads(content)

			if "~links" in objects: 
				objectsLink = objects["~links"]
				theDict["links"] = objects["~links"]

				for room in objectsLink:
					if indigo.activePlugin.decideMyLog("GetDataReturn"): indigo.activePlugin.indiLOG.log(10,"getAllRoom  {},".format(room))
					if room.get("rel","")  !="room": continue
					if "href" not in room: continue

					address = room["href"]
					if address == "..": continue
					roomDevicesHref = "{}/{}".format(baseHtml, address)
					theDict["address"][address] = {"title":room["title"],"devices":[],"link":roomDevicesHref}
					if indigo.activePlugin.decideMyLog("GetData"): indigo.activePlugin.indiLOG.log(10,"getAllRoom room Accessing URL: {},".format(roomDevicesHref))

					r = self.doConnect(roomDevicesHref, logText="getAllRoom data ")
					if r == "": return {}
					if indigo.activePlugin.pluginState == "stop": return {}

					roomDevicesDict = json.loads(r.content)
					if indigo.activePlugin.decideMyLog("GetDataReturn"): indigo.activePlugin.indiLOG.log(10,"getAllRoom dict: {}".format(roomDevicesDict))
					if "~links" not in roomDevicesDict: continue

					for detail in roomDevicesDict["~links"]:
						if indigo.activePlugin.decideMyLog("GetDataReturn"): indigo.activePlugin.indiLOG.log(10,"getAllRoom  detail: {}".format(detail))
						if "href" not in detail: continue
						if detail.get("rel","") != "channel": continue
						if detail["href"] == "..": continue 
						theDict["address"][address]["devices"].append({"link":detail["href"],"title":detail["title"]})

		except Exception as e:
			if "{}".format(e).find("None") == -1: indigo.activePlugin.indiLOG.log(40,"", exc_info=True)
			return {}
		return theDict

	####-----------------	 ---------
	def getAllFunction(self):
		try:
			if indigo.activePlugin.testPing(self.ip) != 0:
				if indigo.activePlugin.decideMyLog("Connect"): indigo.activePlugin.indiLOG.log(20,"getAllFunction ping to {} not sucessfull".format(self.ip))
				return {}
			theDict = {"address":{}}
			page = "function"
			baseHtml = "http://{}:{}/{}".format(self.ip , self.port,  page)

			if indigo.activePlugin.decideMyLog("GetData"): indigo.activePlugin.indiLOG.log(10,"getAllFunction Accessing URL: {}".format(baseHtml))

			r = self.doConnect(baseHtml, logText="getAllFunction base ")
			if r == "": return {}
			if indigo.activePlugin.pluginState == "stop": return {}

			content = r.content.decode('ISO-8859-1')
			if indigo.activePlugin.decideMyLog("GetDataReturn"): indigo.activePlugin.indiLOG.log(10,"getAllFunction all {}:{}".format(page, content))
			objects = json.loads(content)

			if "~links" in objects: 
				objectsLink = objects["~links"]

				for item in objectsLink:
					if indigo.activePlugin.decideMyLog("GetDataReturn"): indigo.activePlugin.indiLOG.log(10,"getAllFunction {} {},".format(page, item))
					if item.get("rel","") != page: continue
					if "href" not in item: continue

					address = item["href"]
					if address == "..": continue

					roomDevicesHref = "{}/{}".format(baseHtml, address)
					theDict["address"][address] = {"title":item["title"],"devices":[],"link":roomDevicesHref}
					if indigo.activePlugin.decideMyLog("GetData"): indigo.activePlugin.indiLOG.log(10," getAllFunction  Accessing URL: {},".format(roomDevicesHref))

					r = self.doConnect(roomDevicesHref, logText="getAllFunction data ")
					if r == "": return {}
					if indigo.activePlugin.pluginState == "stop": return {}

					roomDevicesDict = json.loads(r.content)
					if indigo.activePlugin.decideMyLog("GetDataReturn"): indigo.activePlugin.indiLOG.log(10," getAllFunction dict: {}".format(roomDevicesDict))
					if "~links" not in roomDevicesDict: continue

					for detail in roomDevicesDict["~links"]:
						if indigo.activePlugin.decideMyLog("GetDataReturn"): indigo.activePlugin.indiLOG.log(10,"getAllFunction detail: {}".format(detail))
						if "href" not in detail: continue
						if detail.get("rel","") != "channel": continue
						if detail["href"] == "..": continue 
						theDict["address"][address]["devices"].append({"link":detail["href"],"title":detail["title"]})

		except Exception as e:
			if "{}".format(e).find("None") == -1: indigo.activePlugin.indiLOG.log(40,"", exc_info=True)
			return {}
		return theDict



	####-----------------	 ---------
	def getAllSysvar(self):
		try:
			if indigo.activePlugin.testPing(self.ip) != 0:
				if indigo.activePlugin.decideMyLog("Connect"): indigo.activePlugin.indiLOG.log(20,"getAllSysvar ping to {} not sucessfull".format(self.ip))
				return {}
			theDict = {"address":{},"allValueLinks":{"1":[],"2":[],"3":[]} }
			page = "sysvar"
			baseHtml = "http://{}:{}/{}".format(self.ip , self.port,  page)

			if indigo.activePlugin.decideMyLog("GetData"): indigo.activePlugin.indiLOG.log(10,"getAllSysvar Accessing URL: {}".format(baseHtml))
			r = self.doConnect(baseHtml, logText="getAllSysvar base ")
			if r == "": return {}
			if indigo.activePlugin.pluginState == "stop": return {}

			content = r.content.decode('ISO-8859-1')
			if indigo.activePlugin.decideMyLog("GetDataReturn"): indigo.activePlugin.indiLOG.log(10,"getAllSysvar all {}:{}".format(page, content))
			objects = json.loads(content)


			if "~links" in objects: 
				objectsLink = objects["~links"]

				for item in objectsLink:
					if indigo.activePlugin.decideMyLog("GetDataReturn"): indigo.activePlugin.indiLOG.log(10,"getAllSysvar {} {},".format(page,item))
					if item.get("rel","")  != page: continue
					if "href" not in item: continue

					address = item["href"]
					if address == "..": continue
					theDict["address"][address] = {}

					itemsHref = "{}/{}".format(baseHtml, address)
					theDict["address"][address]["link"] = itemsHref
					theDict["allValueLinks"]["3"].append("/sysvar/"+itemsHref.split("/sysvar/")[1])
					
					if indigo.activePlugin.decideMyLog("GetData"): indigo.activePlugin.indiLOG.log(10,"getAllSysvar  {} Accessing URL: {},".format(page, itemsHref))

					r = self.doConnect(itemsHref, logText="getAllSysvar data ")
					if r == "": return {}
					if indigo.activePlugin.pluginState == "stop": return {}

					itemsDict = json.loads(r.content)
					if indigo.activePlugin.decideMyLog("GetDataReturn"): indigo.activePlugin.indiLOG.log(10,"getAllSysvar  {} dict: {}".format(page, itemsDict))
					for xx in itemsDict:
						if xx =="~links" : continue
						if xx =="identifier" : continue
						theDict["address"][address][xx] = itemsDict[xx]
					if "~links" not in itemsDict: continue

					valueHref = "{}/{}/~pv".format(baseHtml, address)
					if indigo.activePlugin.decideMyLog("GetData"): indigo.activePlugin.indiLOG.log(10,"getAllSysvar  {} Accessing URL: {},".format(page, valueHref))

					r = self.doConnect(valueHref)
					if r == "": return {}
					if indigo.activePlugin.pluginState == "stop": return {}

					valueDict = json.loads(r.content)
					if indigo.activePlugin.decideMyLog("GetDataReturn"): indigo.activePlugin.indiLOG.log(10,"getAllSysvar  {} dict: {}".format(page, valueDict))
					theDict["address"][address]["value"] = valueDict

		except Exception as e:
			if "{}".format(e).find("None") == -1: indigo.activePlugin.indiLOG.log(40,"", exc_info=True)
			return {}
		return theDict



	####-----------------	 ---------
	def getAllProgram(self):
		try:
			if indigo.activePlugin.testPing(self.ip) != 0:
				if indigo.activePlugin.decideMyLog("Connect"): indigo.activePlugin.indiLOG.log(20,"getAllProgram ping to {} not sucessfull".format(self.ip))
				return {}

			theDict = {"address":{}}
			page = "program"
			baseHtml = "http://{}:{}/{}".format(self.ip , self.port,  page)

			if indigo.activePlugin.decideMyLog("GetData"): indigo.activePlugin.indiLOG.log(10,"getAllProgram Accessing URL: {}".format(baseHtml))

			r = self.doConnect(baseHtml, logText="getAllProgram base ")
			if r == "": return {}
			if indigo.activePlugin.pluginState == "stop": return {}

			content = r.content.decode('ISO-8859-1')
			if indigo.activePlugin.decideMyLog("GetDataReturn"): indigo.activePlugin.indiLOG.log(10,"getAllProgram all {}:{}".format(page, content))
			objects = json.loads(content)


			if "~links" in objects: 
				objectsLink = objects["~links"]

				for item in objectsLink:
					if indigo.activePlugin.pluginState == "stop": return theDict 
					if indigo.activePlugin.decideMyLog("GetDataReturn"): indigo.activePlugin.indiLOG.log(10,"getAllProgram {} {},".format(page,item))
					if item.get("rel","")  != page: continue
					if "href" not in item: continue

					address = item["href"]
					if address == "..": continue
					theDict["address"][address] ={}


					itemsHref = "{}/{}".format(baseHtml, address)
					if indigo.activePlugin.decideMyLog("GetDataReturn"): indigo.activePlugin.indiLOG.log(10,"getAllProgram {} Accessing URL: {},".format(page, itemsHref))

					r = self.doConnect(itemsHref, logText="getAllProgram data ")
					if r == "": return {}
					if indigo.activePlugin.pluginState == "stop": return {}

					itemsDict = json.loads(r.content)
					if indigo.activePlugin.decideMyLog("GetDataReturn"): indigo.activePlugin.indiLOG.log(10,"getAllProgram {} dict: {}".format(page, itemsDict))
					for xx in itemsDict:
						if xx == "~links": continue
						if xx == "identifier": continue
						theDict["address"][address][xx] = itemsDict[xx]

					if "~links" not in itemsDict: continue
					valueHref = "{}/{}/~pv".format(baseHtml, address)
					if indigo.activePlugin.decideMyLog("GetData"): indigo.activePlugin.indiLOG.log(10,"getAllProgram {} Accessing URL: {},".format(page, valueHref))

					r = self.doConnect(valueHref)
					if r == "": return {}
					if indigo.activePlugin.pluginState == "stop": return {}

					valueDict = json.loads(r.content)
					if indigo.activePlugin.decideMyLog("GetDataReturn"): indigo.activePlugin.indiLOG.log(10,"getAllProgram {} dict: {}".format(page, valueDict))
					theDict["address"][address]["value"] = valueDict
					theDict["address"][address]["link"] = valueHref

		except Exception as e:
			if "{}".format(e).find("None") == -1: indigo.activePlugin.indiLOG.log(40,"", exc_info=True)
			return {}
		return theDict




	####-----------------	 ---------
	def getAllVendor(self):
		try:
			if indigo.activePlugin.testPing(self.ip) != 0:
				if indigo.activePlugin.decideMyLog("Connect"): indigo.activePlugin.indiLOG.log(20,"getAllVendor ping to {} not sucessfull".format(self.ip))
				return {}
			theDict = {"address":{}}
			page = "~vendor"
			baseHtml = "http://{}:{}/{}".format(self.ip , self.port,  page)
				

			if indigo.activePlugin.decideMyLog("GetData"): indigo.activePlugin.indiLOG.log(10,"getAllVendor Accessing URL: {}".format(baseHtml))

			r = self.doConnect(baseHtml, logText="getAllVendor base ")
			if r == "": return {}
			if indigo.activePlugin.pluginState == "stop": return {}

			content = r.content.decode('ISO-8859-1')
			if indigo.activePlugin.decideMyLog("GetDataReturn"): indigo.activePlugin.indiLOG.log(10,"getAllVendor all {}:{}".format(page, content))
			objects = json.loads(content)

			if "~links" in objects: 
				objectsLink = objects["~links"]

				for item in objectsLink:
					if indigo.activePlugin.decideMyLog("GetData"): indigo.activePlugin.indiLOG.log(10,"getAllVendor  {} {},".format(page,item))
					if item.get("rel","")  != "item": continue
					if "href" not in item: continue

					address = item["href"]
					if address == "..": continue

					itemsHref = "{}/{}".format(baseHtml, address)
					if indigo.activePlugin.decideMyLog("GetDataReturn"): indigo.activePlugin.indiLOG.log(10,"getAllVendor  {} 1 Accessing URL: {},".format(page, itemsHref))
					try:

						r = self.doConnect(itemsHref, logText="getAllVendor data ")
						if r == "": return {}
						if indigo.activePlugin.pluginState == "stop": return {}

					except Exception as e:
						if "{}".format(e).find("None") == -1: indigo.activePlugin.indiLOG.log(40,"", exc_info=True)
						continue

					itemsDict = json.loads(r.content)
					if indigo.activePlugin.decideMyLog("GetDataReturn"): indigo.activePlugin.indiLOG.log(10,"getAllVendor {} dict: {}".format(page, itemsDict))
					theDict["address"][address] = {
							"title":itemsDict.get("title","")}

					if "~links" not in itemsDict: continue
					for valueLinks in itemsDict["~links"]:
						if indigo.activePlugin.pluginState == "stop": return theDict 
						if "href" not in valueLinks: continue
						href1 = valueLinks["href"]
						if href1 == "..": continue
						if href1 == "~pv": 
							valueHref = "{}/{}".format(itemsHref, href1)
							if indigo.activePlugin.decideMyLog("GetData"): indigo.activePlugin.indiLOG.log(10," getAllVendor {} 2 Accessing URL: {},".format(page, valueHref))

							r = self.doConnect(valueHref, logText="getAllVendor data1 ")
							if r == "": return {}
							if indigo.activePlugin.pluginState == "stop": return {}

							valueDict = json.loads(r.content)
							if indigo.activePlugin.decideMyLog("GetDataReturn"): indigo.activePlugin.indiLOG.log(10," getAllVendor {} dict: {}".format(page, valueDict))
							theDict["address"][address]["value"] = valueDict
							theDict["address"][address]["link"] = valueHref

						else:
							theDict["address"][address][href1] = {}
							itemsHref2 = "{}/{}".format(itemsHref, href1)
							if indigo.activePlugin.decideMyLog("GetData"): indigo.activePlugin.indiLOG.log(10,"getAllVendor  {} 3 Accessing URL: {},".format(page, itemsHref2))

							r = self.doConnect(itemsHref2, logText="getAllVendor data2 ")
							if r == "": return {}

							itemsDict2 = json.loads(r.content)
							if indigo.activePlugin.decideMyLog("GetDataReturn"): indigo.activePlugin.indiLOG.log(10," getAllVendor {} dict: {}".format(page, itemsDict2))
							if "~links" not in itemsDict2: continue
							theDict["address"][address][href1] = {}
							for valueLinks2 in itemsDict2["~links"]:
								if indigo.activePlugin.pluginState == "stop": return theDict 
								if "href" not in valueLinks2: continue
								href3 = valueLinks2["href"]
								if href3 == "~pv": 
									itemsHref3 = "{}/{}".format(itemsHref2, href3)
									if indigo.activePlugin.decideMyLog("GetData"): indigo.activePlugin.indiLOG.log(10,"getAllVendor  {} 4 Accessing URL: {},".format(page, itemsHref3))

									r = self.doConnect(itemsHref3, logText="getAllVendor data3 ")
									if r == "": return {}

									itemsDict3 = json.loads(r.content)
									if indigo.activePlugin.decideMyLog("GetDataReturn"): indigo.activePlugin.indiLOG.log(10," getAllVendor {} dict: {}".format(page, itemsDict3))
									theDict["address"][address][href1]["value"] = itemsDict3
									theDict["address"][address][href1]["link"] = itemsHref3


		except Exception as e:
			if "{}".format(e).find("None") == -1: indigo.activePlugin.indiLOG.log(40,"", exc_info=True)
			return {}
		return theDict


