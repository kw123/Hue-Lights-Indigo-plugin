#! /usr/local/bin/python
# -*- coding: utf-8 -*-
####################
# Some code borrowed from the "Hue.indigoPlugin" (Hue Lighting Control) plugin
#   originally developed by Alistair Galbraith (alistairg on Gitbridge,
#   https://github.com/alistairg ).
#
#   His comment:
#   "This is UNSUPPORTED, AS-IS, open source code - do with it as you wish. Don't
#   blame me if it breaks! :)"
#
# His code base was forked on Gitbridge and completely rewritten by Nathan Sheldon
#   (nathan@nathansheldon.com)
#   http://www.nathansheldon.com/files/Hue-Lights-Plugin.php
#   All modificiations are open source.
#
#	Version 1.8.8
#
#	See the "VERSION_HISTORY.txt" file in the same location as this plugin.py
#	file for a complete version change history.
#
# taken over by Karl Wachs
# since v 1.8.1
# see file version_history.txt for detailed changes.
# since v 2022.x.y requires py3 and api>=3.0.
#
#
################################################################################

import os
import sys
import pwd
import logging
import time
import datetime
import inspect
import traceback 
import platform
import copy
import threading
import codecs
import subprocess
import requests
requests.adapters.DEFAULT_RETRIES = 3
kTimeout = 4		# seconds

from colormath.color_objects import RGBColor, xyYColor, HSVColor
from math import ceil, floor, pow

import json

from supportedDevices import *

logging.getLogger('requests').setLevel(logging.WARNING)

_debugAreas = ['Init','Loop','EditSetup','ReadFromBridge','SendCommandsToBridge','UpdateIndigoDevices','FindHueBridge','Special','all']


_defaultDateStampFormat = "%Y-%m-%d %H:%M:%S"

# new plugin prefs props has to be set here
kDefaultPluginPrefs = {
				'hubNumber':							'0',
				'gwAction':								'keep',
				'selecthubNumber':						'0',
				'ipvisible':							False,
				'timeScaleFactor':						'1.0',
				'sendDeviceUpdatesTo':					'20',
				'autoCreatedNewDevices':				False,
				'folderNameForNewDevices':				'Hue New Devices',
				"showLoginTest":						True,
				"debugInit":							False,
				"debugLoop":							False,
				"debugEditSetup":						False,
				"debugReadFromBridge":					False,
				"debugSendCommandsToBridge":			False,
				"debugUpdateIndigoDevicese":			False,
				"debugFindHueBridge":					False,
				"debugSpecial":							False,
				"debugall":								False,
				"searchForStringinFindHueBridge":		'Hue Bridge',
				'logAnyChanges':						'leaveToDevice' # can be leaveToDevice / no / yes
				}
kmaxHueItems = {'lights':50, 'sensors':50, 'groups':64, 'scenes':200, 'rules':200, 'schedules':100, 'resourcelinks':64}


################################################################################
class Plugin(indigo.PluginBase):
	########################################
	# Loading and Starting Methods
	########################################

	# Load Plugin
	########################################
	def __init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs):
		super(Plugin, self).__init__(pluginId, pluginDisplayName, pluginVersion, pluginPrefs)
		indigo.server.log('Starting plugin initialization.')
		self.hostId 					= pluginPrefs.get('hostId', '')	# Username/key used to access Hue bridge Old
		self.hostIds 					= json.loads(pluginPrefs.get('hostIds', '{"0":""}'))	# Username/key used to access Hue bridge for multiple bridge
		self.pluginShortName 			= "Hue Lights"

		### one list for all devices on all bridges related to indigo devices 
		self.deviceList 				= dict()			# list of device IDs to monitor (one list for all devices on all bridges)
		self.controlDeviceList 			= dict()	    # list of virtual dimmer device IDs that control bulb devices
		self.brighteningList 			= []	    # list of device IDs being brightened
		self.dimmingList 				= []			# list of device IDs being dimmed
		### one for each bridge read from bridge
		self.paired 					= {"0":False}		# if paired with Hue bridge or not
		self.notPairedMsg 				= {"0":0}
		self.hueConfigDict 				= {"0":{}}   # Entire Hue bridge configuration dictionary.
		self.ipAddresses 				= {"0":{}}	    # Hue bridge IP addresses 

		self.hubNumberSelected 			= "0"    # default hub number 
		self.lastErrorMessage 			= ""	    # last error message displayed in log
		self.selHubNumberLast			= 0
		self.unsupportedDeviceWarned 	= False	# Boolean. Was user warned this device isn't supported?
		self.usersListSelection 		= ""	# String. The Hue whilelist user ID selected in action UIs.
		self.sceneListSelection 		= ""	# String. The Hue scene ID selected in action UIs.
		self.groupListSelection 		= ""	# String. The Hue group ID selected in action UIs.
		self.maxPresetCount 			= int(pluginPrefs.get('maxPresetCount', "30"))	# Integer. The maximum number of Presets to use and store.

		self.lastReminderHubNumberNotPresent = time.time()
		self.lastGWConfirmClick 		= 0

		self.updateList 				= dict()
		self.bridgeRequestsSession		= dict()
		self.bridgesAvailable 			= dict()
		self.bridgesAvailableSelected	= ""
		self.findHueBridgesNowForce		= 0
		self.tryAutoCreateTimeWindow 	= 0
		self.tryAutoCreateValuesDict 	= dict()
		self.pairedBridgeExec 			= ""
		self.missingOnHubs				= dict()
		self.printMissingOnHubeverySecs = 600 # check every 10 minutes and print if missing
		self.hubNumberSelectedTo		= ""
		self.hubNumberSelectedFrom		= ""

##############  common for all plugins ############
		self.getInstallFolderPath		= indigo.server.getInstallFolderPath()+"/"
		self.indigoPath					= indigo.server.getInstallFolderPath()+"/"
		self.indigoRootPath 			= indigo.server.getInstallFolderPath().split("Indigo")[0]
		self.pathToPlugin 				= self.completePath(os.getcwd())
		self.showLoginTest 				= pluginPrefs.get('showLoginTest',True)

		major, minor, release 			= map(int, indigo.server.version.split("."))
		self.indigoVersion 				= float(major)+float(minor)/10.
		self.indigoRelease 				= release

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
		self.indigoPluginDirOld			= self.userIndigoDir + self.pluginShortName+"/"
		self.PluginLogFile				= indigo.server.getLogsFolderPath(pluginId=self.pluginId) +"/plugin.log"
		self.bridgeBusy = {"max delay":0.}



		formats=	{   logging.THREADDEBUG: "%(asctime)s %(msg)s",
						logging.DEBUG:       "%(asctime)s %(msg)s",
						logging.INFO:        "%(asctime)s %(msg)s",
						logging.WARNING:     "%(asctime)s %(msg)s",
						logging.ERROR:       "%(asctime)s.%(msecs)03d\t%(levelname)-12s\t%(name)s.%(funcName)-25s %(msg)s",
						logging.CRITICAL:    "%(asctime)s.%(msecs)03d\t%(levelname)-12s\t%(name)s.%(funcName)-25s %(msg)s" }

		date_Format = { logging.THREADDEBUG: "%Y-%m-%d %H:%M:%S",		# 5
						logging.DEBUG:       "%Y-%m-%d %H:%M:%S",		# 10
						logging.INFO:        "%Y-%m-%d %H:%M:%S",		# 20
						logging.WARNING:     "%Y-%m-%d %H:%M:%S",		# 30
						logging.ERROR:       "%Y-%m-%d %H:%M:%S",		# 40
						logging.CRITICAL:    "%Y-%m-%d %H:%M:%S" }		# 50
		formatter = LevelFormatter(fmt="%(msg)s", datefmt="%Y-%m-%d %H:%M:%S", level_fmts=formats, level_date=date_Format)

		self.plugin_file_handler.setFormatter(formatter)
		self.indiLOG = logging.getLogger("Plugin")
		self.indiLOG.setLevel(logging.THREADDEBUG)

		self.indigo_log_handler.setLevel(logging.INFO)

		self.indiLOG.log(20,"initializing  ... ")
		self.indiLOG.log(20,"path To files:          =================")
		self.indiLOG.log(10,"indigo                  {}".format(self.indigoRootPath))
		self.indiLOG.log(10,"installFolder           {}".format(self.indigoPath))
		self.indiLOG.log(10,"plugin.py               {}".format(self.pathToPlugin))
		self.indiLOG.log(20,"detailed logging        {}".format(self.PluginLogFile))
		if self.showLoginTest:
			self.indiLOG.log(20,"testing logging levels, for info only: ")
			self.indiLOG.log( 0,"logger  enabled for     0 ==> TEST ONLY ")
			self.indiLOG.log( 5,"logger  enabled for     THREADDEBUG    ==> TEST ONLY ")
			self.indiLOG.log(10,"logger  enabled for     DEBUG          ==> TEST ONLY ")
			self.indiLOG.log(20,"logger  enabled for     INFO           ==> TEST ONLY ")
			self.indiLOG.log(30,"logger  enabled for     WARNING        ==> TEST ONLY ")
			self.indiLOG.log(40,"logger  enabled for     ERROR          ==> TEST ONLY ")
			self.indiLOG.log(50,"logger  enabled for     CRITICAL       ==> TEST ONLY ")
		self.indiLOG.log(10,"Plugin short Name       {}".format(self.pluginShortName))
		self.indiLOG.log(10,"my PID                  {}".format(self.myPID))	 
		self.indiLOG.log(10,"Achitecture             {}".format(platform.platform()))	 
		self.indiLOG.log(10,"OS                      {}".format(platform.mac_ver()[0]))	 
		self.indiLOG.log(10,"indigo V                {}".format(indigo.server.version))	 
		self.indiLOG.log(10,"python V                {}.{}.{}".format(sys.version_info[0], sys.version_info[1] , sys.version_info[2]))	 

###############  END common for all plugins ############

		return

	# Unload Plugin
	########################################
	def __del__(self):
		indigo.PluginBase.__del__(self)
		return
	# Startup
	########################################
	def startup(self):

		self.getDebugLevels()
		if self.decideMyLog("Init"): self.indiLOG.log(10,"Startup called.")
		# Perform an initial version check.
		if self.decideMyLog("Init"): self.indiLOG.log(10,"Running plugin version check (if enabled).")


		# Prior to version 1.2.0, the "presets" property did not exist in the plugin preferences.
		#   If that property does not exist, add it.
		# As of version 1.2.6, there were 30 presets instead of 10.
		# As of 1.6.11, the maximum number of presets is now a global variable that can be changed later.
		if not self.pluginPrefs.get('presets', False):
			if self.decideMyLog("Init"): self.indiLOG.log(10,"pluginPrefs lacks presets.  Adding.")
			# Add the empty presets list to the prefs.
			self.pluginPrefs['presets'] = list()
			# Start a new list of empty presets.
			presets = list()
			for aNumber in range(1,self.maxPresetCount + 1):
				# Create a blank sub-list for storing preset name and preset states.
				preset = list()
				# Add the preset name.
				preset.append("Preset {}".format(aNumber))
				# Add the empty preset states Indigo dictionary
				preset.append(indigo.Dict())
				# Add the sub-list to the empty presets list.
				presets.append(preset)
			# Add the new list of empty presets to the prefs.
			self.pluginPrefs['presets'] = presets
			if self.decideMyLog("Init"): self.indiLOG.log(10,"pluginPrefs now contains {} Presets.".format(self.maxPresetCount) )
		# If presets exist, make sure there are the correct number of them.
		else:
			presets = self.pluginPrefs.get('presets', "")
			presetCount = len(presets)
			if self.decideMyLog("Init"): self.indiLOG.log(10,"pluginPrefs contains {} presets.".format(presetCount))
			# If there are fewer Presets in the prefs than the maxPresetCount, add the reset.
			if presetCount < self.maxPresetCount:
				self.indiLOG.log(20,"Preset Memories number increased to .".format(self.maxPresetCount))
				if self.decideMyLog("Init"): self.indiLOG.log(10,"... Adding {} presets to bring total to {}.".format(self.maxPresetCount - presetCount, self.maxPresetCount) )
				for aNumber in range(presetCount + 1,self.maxPresetCount + 1):
					# Add ever how many presets are needed to make a total of the maximum presets allowed.
					# Create a blank sub-list for storing preset name and preset states.
					preset = list()
					# Add the preset name.
					preset.append('Preset {}'.format(aNumber))
					# Add the empty preset states Indigo dictionary
					preset.append(indigo.Dict())
					# Add the sub-list to the empty presets list.
					presets.append(preset)
				# Replace the list of Presets in the prefs with the new list.
				self.pluginPrefs['presets'] = presets
				self.indiLOG.log(20,"... {} Presets added.  There are now {} Presets.".format(self.maxPresetCount - presetCount, self.maxPresetCount) )
			# If there are more presets than are allowed by maxPresetCount, remove the extra Presets.
			elif presetCount > self.maxPresetCount:
				if self.decideMyLog("Init"): self.indiLOG.log(10,"... Deleting the last {} Presets to bring the total to {}.".format(presetCount - self.maxPresetCount, self.maxPresetCount))
				self.indiLOG.log(30,"WARNING:  You've decreased the number of Preset Memories, so we're deleting the last {} Presets to bring the total to {}.  This cannot be undone.".format(presetCount - self.maxPresetCount, self.maxPresetCount) )
				for aNumber in range(presetCount - 1,self.maxPresetCount - 1,-1):
					# Remove every Preset after the maxPresetCount limit, starting from the last Preset and moving backward up the list of Presets.
					# If this Preset has data in it, log it in the Indigo log before deleting it.
					preset = presets[aNumber]
					presetName = preset[0]
					presetData = preset[1]
					if len(presetData) > 0:
						# Preset has data in it.
						try:
							# Prior to version 1.2.4, this key did not exist in the presets.
							presetRate = self.pluginPrefs['presets'][aNumber][2]
							# Round the saved preset ramp rate to the nearest 10th.
							presetRate = round(presetRate, 1)
						except Exception:
							# Key probably doesn't exist. Proceed as if no rate was saved.
							presetRate = -1
							pass

						# Display the Preset data in the Indigo log.
						logRampRate = "{} sec.".format(presetRate)
						if presetRate == -1:
							logRampRate = "(none specified)"
						self.indiLOG.log(20,"... Preset {} ({}) has data. The following data will be deleted:\nRamp Rate: {}\n{}".format(aNumber + 1, presetName, logRampRate, presetData))
					# Now delete the Preset.
					del presets[aNumber]
					self.indiLOG.log(20,"... Preset {} deleted.".format(aNumber + 1))

		if self.decideMyLog("Init"): self.indiLOG.log(10,"pluginPrefs are:\n{}".format(self.pluginPrefs))

		self.timeScaleFactor = float(self.pluginPrefs.get('timeScaleFactor',"1.0"))
		self.sendDeviceUpdatesTo = int(self.pluginPrefs.get('sendDeviceUpdatesTo',20))
		self.trackSpecificDevice = 0
		self.updateAllHueLists()
		self.searchForStringinFindHueBridge = self.pluginPrefs.get('searchForStringinFindHueBridge', kDefaultPluginPrefs["searchForStringinFindHueBridge"])

		self.findHueBridgesDict = {"status":"init"}
		self.findHueBridgesDict['thread']  = threading.Thread(name=u'findHueBridges', target=self.findHueBridges)
		self.findHueBridgesDict['thread'].start()

		return 



	# Start Devices
	########################################
	def deviceStartComm(self, device):
		if self.decideMyLog("Init"): self.indiLOG.log(10,"Starting device: {}".format(device.name))
		try:
			# Clear any device error states first.
			device.setErrorStateOnServer("")

			# Rebuild the device if needed (fixes missing states and properties).
			self.rebuildDevice(device)

			# Update the device lists and the device states and props.

			pluginProps = device.pluginProps
			# Hue Device Attribute Controller
			if device.deviceTypeId == "hueAttributeController":
				if device.id not in self.controlDeviceList:
					try:
						if self.decideMyLog("Init"): self.indiLOG.log(10,"Attribute Control device definition:\n{}".format(device))
					except Exception:
						self.indiLOG.log(30,"Attribute Control device definition cannot be displayed", exc_info=True)
					self.controlDeviceList[device.id] = [device.deviceTypeId, '0','0']
			# Hue Groups
			elif device.deviceTypeId in kGroupDeviceTypeIDs:
				if device.id not in self.deviceList:
					try:
						if self.decideMyLog("Init"): self.indiLOG.log(10,"Hue Group device definition:\n{}".format(device))
					except Exception:
						self.indiLOG.log(30,"Hue Group device definition cannot be displayed", exc_info=True)
					if "groupId" in pluginProps:
						self.deviceList[device.id] = {'typeId':device.deviceTypeId, 'hubNumber':pluginProps.get('hubNumber','0'), 'groupId':pluginProps.get('groupId','0')}
					else:
						self.deviceList[device.id] = {'typeId':device.deviceTypeId, 'hubNumber':'0', 'groupId':'0'}
					if self.decideMyLog("Init"): self.indiLOG.log(10,"Hue device deviceList:\n{}".format(device.id, self.deviceList[device.id] ))
			# Other Hue Devices, bulbs, sensors
			else:
				if device.id not in self.deviceList:
					try:
						if self.decideMyLog("Init"): self.indiLOG.log(10,"Hue device definition:\n{}".format(device))
					except Exception:
						# With versions of Indigo sometime prior to 6.0, if any device name had
						#   non-ASCII characters, the above "try" will fail, so we have to show
						#   this error instead of the actual bulb definition.
						self.indiLOG.log(30,"Hue Group device definition cannot be displayed", exc_info=True)
					#self.indiLOG.log(20,"Hue adding devid for light {}, #:{}".format(device.name, device.id ))
					if "bulbId" in pluginProps:
						self.deviceList[device.id] = {'typeId':device.deviceTypeId, 'hubNumber':pluginProps.get('hubNumber','0'), 'bulbId':pluginProps.get('bulbId','0')}
					elif "sensorId" in pluginProps:
						self.deviceList[device.id] = {'typeId':device.deviceTypeId, 'hubNumber':pluginProps.get('hubNumber','0'), 'sensorId':pluginProps.get('sensorId','0')}
					elif "groupId" in pluginProps:
						self.deviceList[device.id] = {'typeId':device.deviceTypeId, 'hubNumber':pluginProps.get('groupId','0'), 'bulbId':pluginProps.get('groupId','0')}
					else:
						self.deviceList[device.id] = {'typeId':device.deviceTypeId, 'hubNumber':'-1', '':'0'}
					if self.decideMyLog("Init"): self.indiLOG.log(10,"Hue device deviceList:\n{}".format(device.id, self.deviceList[device.id] ))
		except Exception:
			self.indiLOG.log(30,"", exc_info=True)
		return 


	# Stop Devices
	########################################
	def deviceStopComm(self, device):
		if self.decideMyLog("Init"): self.indiLOG.log(10,"Stopping device: {}".format(device.name) )
		if device.deviceTypeId == "hueAttributeController":
			if device.id in self.controlDeviceList:
				del self.controlDeviceList[device.id]
		else:
			if device.id in self.deviceList:
				del self.deviceList[device.id]
			## must also be removed from control dev list KW
			if device.id in self.controlDeviceList:
				del self.controlDeviceList[device.id]

	# Shutdown
	########################################
	def shutdown(self):
		if self.decideMyLog("Init"): self.indiLOG.log(10,"Plugin shutdown called.")


	########################################
	# Standard Plugin Methods
	########################################

	# Run a Concurrent Thread for Status Updates
	########################################
	def runConcurrentThread(self):
		if self.decideMyLog("Init"): self.indiLOG.log(10,"Starting runConcurrentThread.")

		self.pluginState = "loop"
		# Set initial values for activity flags
		goBrightenDim			= 0.4 ## sec delay between reads
		lastTimeForBrightenDim	= 0	#
		goSensorRefresh			= 1.1 
		lastTimeForSensorRefresh= 0	# 
		goLightsRefresh			= 5.1
		lastTimeForLightsRefresh= 0  
		goGroupsRefresh			= 5.15 
		lastTimeForGroupsRefresh= 0    
		goErrorReset			=300.1 
		lastTimeForErrorReset	= 0  # 
		goexcecStatesUpdate		= 0.5
		lastTimeForexcecStatesUpdate = 0
		self.goAllRefresh		= 200.1 # is used in self.restartPairing() after pairing to force reload of all info from hub
		self.lastTimeForAll		= 0  	#  that is why this is not a local variable, but self....
		self.lastTimeForCheck		= 0 
		# Set the maximum loop counter value based on the highest of the above activity threshold variables.
		lasttryAutoCreateValuesDict = 0
		self.printHueData({"whatToPrint":"NoHudevice", "sortBy":""},"")
		self.printHueData({"whatToPrint":"NoIndigoDevice", "sortBy":""},"OnlySupportedDevices")

		self.indiLOG.log(20,"... initialized")


		try:
			while True:
				# We're using time sharing techniques here based on

				## Give Indigo Some Time ##
				self.sleep(0.1)

				## Brightening and Dimming Devices ##
				# Go through the devices waiting to be brightened
				if time.time() - lastTimeForBrightenDim >= goBrightenDim:
					lastTimeForBrightenDim = time.time()
					for brightenDeviceId in self.brighteningList:
						# Make sure the device is in the deviceList.
						if brightenDeviceId in self.deviceList:
							# Increase the brightness level by 10 percent.
							brightenDevice = indigo.devices[brightenDeviceId]
							hubNumber = brightenDevice.pluginProps['hubNumber']
							brightness = brightenDevice.states['brightnessLevel']
							if self.decideMyLog("Loop"): self.indiLOG.log(10,"Brightness: {}".format(brightness))
							brightness += 12
							if self.decideMyLog("Loop"): self.indiLOG.log(10,"Updated to: {}".format(brightness))
							if brightness >= 100:
								brightness = 100
								# Log the event to Indigo log.
								self.indiLOG.log(20,"Sent Hue Lights  \"{}\" stop brightening".format(brightenDevice.name))
								self.brighteningList.remove(brightenDeviceId)
								# Get the bulb status (but only if paired with the bridge).
								if self.paired[hubNumber]:
									self.getBulbStatus(brightenDeviceId)
									# Log the new brightness.
									self.indiLOG.log(20,"Sent Hue Lights  \"{}\" status request (received: 100)".format(brightenDevice.name))
								else:
									if self.checkForLastNotPairedMessage(hubNumber):
										if self.decideMyLog("Loop"): self.indiLOG.log(10,"Not currently paired with Hue bridge. Status update skipped.")
							# Convert percent-based brightness to 255-based brightness.
							brightness = int(round(brightness * 255.0 / 100.0))
							# Set brightness to new value, with 0.5 sec ramp rate and no logging.
							self.doBrightness(brightenDevice, brightness, 0.5, False)
						# End if brightenDeviceId is in self.deviceList.
					# End loop through self.brighteningList.

					# Go through the devices waiting to be dimmed.
					for dimDeviceId in self.dimmingList:
						# Make sure the device is in the deviceList.
						if dimDeviceId in self.deviceList:
							# Decrease the brightness level by 10 percent.
							dimDevice = indigo.devices[dimDeviceId]
							hubNumber = dimDevice.pluginProps['hubNumber']
							brightness = dimDevice.states['brightnessLevel']
							brightness -= 12
							if brightness <= 0:
								brightness = 0
								# Log the event to Indigo log.
								self.indiLOG.log(20,"Sent Hue Lights  \"{}\" stop dimming".format(dimDevice.name ))
								self.dimmingList.remove(dimDeviceId)
								# Get the bulb status (but only if we're paired with the bridge).
								if self.paired[hubNumber]:
									self.getBulbStatus(dimDeviceId)
									# Log the new brightness.
									self.indiLOG.log(20,"Sent Hue Lights \"{}\" status request (received: 0)".format(dimDevice.name ))
								else:
									if self.checkForLastNotPairedMessage(hubNumber):
										if self.decideMyLog("Loop"): self.indiLOG.log(10,"Not currently paired with Hue bridge. Status update skipped.")

							# Convert percent-based brightness to 255-based brightness.
							brightness = int(round(brightness * 255.0 / 100.0))
							# Set brightness to new value, with 0.5 sec ramp rate and no logging.
							self.doBrightness(dimDevice, brightness, 0.5, False)
						# End if dimDeviceId is in self.deviceList.
					# End loop through self.dimmingList.
					# Reset the action flag.
				# End it's time to go through brightening and dimming loops.

				# for get hub complete dict = all data
				if time.time() - self.lastTimeForAll >= max(30., self.goAllRefresh * self.timeScaleFactor):
					self.updateAllHueLists()
					self.lastTimeForAll = time.time()
					if time.time() - self.lastTimeForCheck >= self.printMissingOnHubeverySecs:
						self.checkMissing()
						self.lastTimeForCheck = time.time()

				if time.time() - lastTimeForSensorRefresh >= max(0.2, goSensorRefresh * self.timeScaleFactor):
					lastTimeForSensorRefresh = time.time()
					self.updateTheTypeList("sensors")
					self.parseAllHueSensorsData()

				if time.time() - lastTimeForLightsRefresh >= max(0.5, goLightsRefresh * self.timeScaleFactor):
					lastTimeForLightsRefresh = time.time()
					self.updateTheTypeList("lights")
					self.parseAllHueLightsData()

				if time.time() - lastTimeForGroupsRefresh >= max(0.5, goGroupsRefresh * self.timeScaleFactor):
					lastTimeForGroupsRefresh = time.time()
					self.updateTheTypeList("groups")
					self.parseAllHueGroupsData()

				# for error message supressing 
				if time.time() - lastTimeForErrorReset >=  goErrorReset:
					lastTimeForErrorReset = time.time()
					self.lastErrorMessage = ""

				if time.time() - lastTimeForexcecStatesUpdate >= goexcecStatesUpdate:
					lastTimeForexcecStatesUpdate = time.time()
					self.excecStatesUpdate()

				if time.time() - self.tryAutoCreateTimeWindow < 0 and time.time() - lasttryAutoCreateValuesDict > 5:
					if self.tryAutoCreateValuesDict != dict():
						lasttryAutoCreateValuesDict = time.time()
						self.restartPairing(self.tryAutoCreateValuesDict)
					else:
						self.tryAutoCreateTimeWindow = 0



			# End While True loop.

		except self.StopThread:
			if self.decideMyLog("Init"): self.indiLOG.log(10,"runConcurrentThread stopped.")
			pass
		self.pluginState = "stop"
		self.findHueBridgesDict['status'] = "stop"
		self.sleep(1)
		if self.decideMyLog("Init"): self.indiLOG.log(10,"runConcurrentThread exiting.")
		return 



	# start search for new sensors 
	########################################
	def startSearchNewSwitches(self, valuesDict, y):

		try:
			hubNumber = valuesDict.get('hubNumber', "")
			if hubNumber == "":
				return 


			command = "http://{}/api/{}/sensors".format(self.ipAddresses[hubNumber], self.hostIds[hubNumber])
			self.indiLOG.log(20,"Sending search request to {} (via HTTP POST).".format(command))
			self.setBridgeBusy(hubNumber, calledfrom="startSearchNewSwitches")
			r = requests.post(command, data="", timeout=kTimeout, headers={'Connection':'close'})
			self.resetBridgeBusy(hubNumber)
			responseData = json.loads(r.content)
			try: 
				if "success" in responseData[0]:
					self.indiLOG.log(20,"search started {}".format(responseData))
				else:
					self.indiLOG.log(30,"search not started {}".format(responseData))
			except:
					self.indiLOG.log(30,"search not started {}".format(responseData))
		except Exception:
			self.indiLOG.log(30,"", exc_info=True)
		self.resetBridgeBusy(hubNumber)

		return 
	# start search for new lights 
	########################################
	def startSearchNewLights(self, valuesDict,y):

		try:
			hubNumber = valuesDict.get('hubNumber', "")
			if hubNumber == "":
				return 

			command = "http://{}/api/{}/lights".format(self.ipAddresses[hubNumber], self.hostIds[hubNumber])
			self.indiLOG.log(20,"Sending search request to {} (via HTTP POST).".format(command))
			self.setBridgeBusy(hubNumber, calledfrom="startSearchNewLights")
			r = requests.post(command, data="", timeout=kTimeout, headers={'Connection':'close'})
			self.resetBridgeBusy(hubNumber)
			responseData = json.loads(r.content)
			try: 
				if "success" in responseData[0]:
					self.indiLOG.log(20,"search started {}".format(responseData))
				else:
					self.indiLOG.log(30,"search not started {}".format(responseData))
			except:
					self.indiLOG.log(30,"search not started {}".format(responseData))
		except Exception:
			self.indiLOG.log(30,"", exc_info=True)
		self.resetBridgeBusy(hubNumber)
		return 

	# Validate Device Configuration
	########################################
	def autocreateNewDevices(self, valuesDict, mode):

		if len(valuesDict['hueFolderName']) < 2:
			valuesDict['hueFolderName'] = self.pluginPrefs.get("folderNameForNewDevices","")
		try:
			hueFolderID = indigo.devices.folders[valuesDict['hueFolderName']].id
			if mode != "background":
				 self.indiLOG.log(20,"folder:\"{}\" already exists, id = {} ".format(valuesDict['hueFolderName'] , hueFolderID))
		except Exception:
			hueFolderID = 0

		if hueFolderID == 0:
			try:
				ff = indigo.devices.folder.create(valuesDict['hueFolderName'])
				hueFolderID = ff.id
				self.indiLOG.log(20,"folder:\"{}\" created, id = {} ".format(valuesDict['hueFolderName']  , hueFolderID))
			except:
				self.indiLOG.log(30,"folder:\"{}\" creation did not work, will use root folder ".format(valuesDict['hueFolderName']))
				hueFolderID = 0

		createdLights = 0
		createdSensors = 0
		createdGroups = 0
		if valuesDict.get('createLights',False):
			for hubNumber in self.hueConfigDict:
				if "lights" not in self.hueConfigDict[hubNumber]: continue
				theDict = self.hueConfigDict[hubNumber]['lights']
				for theID in theDict:
					deviceTypeId = ""
					for typId in kmapHueTypeToIndigoDevType:
						ll = len(typId)
						if theDict[theID]['type'][0:ll].find(typId) == 0:
							deviceTypeId = kmapHueTypeToIndigoDevType[typId][0]
							break

					if deviceTypeId  == "":
						if  mode != "background":
							self.indiLOG.log(10,"autocreateNewDevices light  Bridge:{:>2s}; id:{:>3s}, type:{:25s}      not supported".format(hubNumber, theID, theDict[theID]['type']))
						continue

					found = False
					for dev in indigo.devices.iter(self.pluginId):
						#f dev.deviceTypeId != deviceTypeId: continue
						if str(theID) == str(dev.pluginProps.get('bulbId', "xx")) and  hubNumber == str(dev.pluginProps.get('hubNumber', "xx")): 
							found = True
							if  mode != "background":
								self.indiLOG.log(10,"autocreateNewDevices light  Bridge:{:>2s}; id:{:>3s}, type:{:25s}      already exists".format(hubNumber, theID, theDict[theID]['type']))
							break
					
					if not found:
						name = "Hue_light_{}_{}_{}".format(hubNumber, theID, theDict[theID]['name'])
						address = ""
						props = dict()
						props['hubNumber'] = hubNumber
						props['bulbId'] = theID
						props['type'] = theDict[theID]['type']
						props['modelId'] = theDict[theID]['modelid']
						props['defaultBrightness'] = ""
						props['rate'] = "1"
						props['noOnRampRate'] = False
						props['noOffRampRate'] = False
						props['logChanges'] = self.pluginPrefs.get('logDefaultForNewDevices', "off") == "on"
						#props = self.validateDeviceConfigUi(props, deviceTypeId, 0)[1]
						try:
							dev = indigo.device.create(
								protocol		= indigo.kProtocol.Plugin,
								address			= address,
								name			= name,
								description		= "created by bridge scan",
								pluginId		= self.pluginId,
								deviceTypeId	= deviceTypeId,
								folder			= hueFolderID,
								props			= props
								)
							props = dev.pluginProps
							newProps = self.validateDeviceConfigUi(props, deviceTypeId, dev.id)
							dev.replacePluginPropsOnServer(newProps[1])
							self.indiLOG.log(30,"autocreateNewDevices light  Bridge:{:>2s}; hue-id:{:>3s}, hue-type:{:25s}, mapped to indigo-deviceTypeId:{:27} create {:40s} (details in plugin.log)".format( hubNumber, theID, theDict[theID]['type'], deviceTypeId, name))
							self.indiLOG.log(10,"props:{}".format( props))
							createdLights +=1
						except Exception:
							self.logger.error("", exc_info=True)
							self.logger.error("name:{}, deviceTypeId:{}, dict:{}".format(name, deviceTypeId, theDict[theID]))
							oldDev = indigo.devices[name]
							self.logger.error("existing deviceTypeId:{}, props:{}".format(oldDev.deviceTypeId, str(oldDev.pluginProps)))


		if valuesDict.get('createSensors',False):
			for hubNumber in self.hueConfigDict:
				if "sensors" not in self.hueConfigDict[hubNumber]: continue
				theDict = self.hueConfigDict[hubNumber]['sensors']
				for theID in theDict:
					deviceTypeIdCandidates = []
					theType = theDict[theID]['type'] # eg ZLLRelativeRotary, ZLLSwitch, ..
					for indigoTypes in kmapIndigoDevTypeToSensorType: #  eg: "hueDimmerSwitch": 			['RWL020', 'RWL021', 'RWL022'],
						if theType.find(kmapIndigoDevTypeToSensorType[indigoTypes]) == 0:
							deviceTypeIdCandidates.append(indigoTypes)

					if deviceTypeIdCandidates == []:
						if  mode != "background":
							self.indiLOG.log(10,"autocreateNewDevices sensor Bridge:{:>2s}; id:{:>3s}; type:{:25s}      not supported(1)".format(hubNumber, theID, theDict[theID]['type']))
						continue
					found = ""
					for devT in deviceTypeIdCandidates: # eg: "runLessWireSwitch"
						if devT in kmapSensordevTypeToModelId: # eg: ['FOHSWITCH', 'PTM215Z']
							for modelid in kmapSensordevTypeToModelId[devT] :
								if modelid == theDict[theID]['modelid']:
									found = devT
									break
					if found == "":
						if  mode != "background":
							self.indiLOG.log(10,"autocreateNewDevices sensor Bridge:{:>2s}; id:{:>3s}; type:{:25s}      not supported(2)".format(hubNumber, theID, theDict[theID]['type']))
						continue
					deviceTypeId = found

					found = False
					for dev in indigo.devices.iter(self.pluginId):
						if dev.deviceTypeId != deviceTypeId: continue
						if str(theID) == str(dev.pluginProps.get('sensorId', "xx")) and  hubNumber == str(dev.pluginProps.get('hubNumber', "xx")): 
							found = True
							if  mode != "background":
								self.indiLOG.log(10,"autocreateNewDevices sensor Bridge:{:>2s}; id:{:>3s}; type:{:25s}      already exists".format(hubNumber, theID, theDict[theID]['type']))
							break
					
					if not found:
						name = "Hue_sensor_{}_{}_{}".format(hubNumber, theID, theDict[theID]['name'])
						address = ""
						props ={}
						props['hubNumber'] = hubNumber
						props['sensorId'] = theID
						props['modelId'] = theDict[theID]['modelid']
						props['type'] = theDict[theID]['type']
						props['logChanges'] = self.pluginPrefs.get('logDefaultForNewDevices', "off") == "on"

						try:
							dev = indigo.device.create(
								protocol		= indigo.kProtocol.Plugin,
								address			= address,
								name			= name,
								description		= "created by bridge scan",
								pluginId		= self.pluginId,
								deviceTypeId	= deviceTypeId,
								folder			= hueFolderID,
								props			= props
								)
							props = dev.pluginProps
							newProps = self.validateDeviceConfigUi(props, deviceTypeId, dev.id)
							dev.replacePluginPropsOnServer(newProps[1])
							self.indiLOG.log(30,"autocreateNewDevices sensor Bridge:{:>2s}; hue-id:{:>3s}, hue-type:{:25s}, mapped to indigo-deviceTypeId:{:27} create {:40s} (details in plugin.log)".format( hubNumber, theID, theDict[theID]['type'], deviceTypeId, name))
							self.indiLOG.log(10,"props:{}".format( props))
							createdSensors +=1
						except Exception:
							self.logger.error("", exc_info=True)
							self.logger.error("name:{}, deviceTypeId:{}, dict:{}".format(name, deviceTypeId, theDict[theID]))
							oldDev = indigo.devices[name]
							self.logger.error("existing deviceTypeId:{}, props:{}".format(oldDev.deviceTypeId, str(oldDev.pluginProps)))

		if valuesDict.get('createGroups',False):
			deviceTypeId = "hueGroup" 
			for hubNumber in self.hueConfigDict:
				if "groups" not in self.hueConfigDict[hubNumber]: continue
				theDict = self.hueConfigDict[hubNumber]['groups']
				for theID in theDict:
					found = False
					for dev in indigo.devices.iter(self.pluginId):
						if dev.deviceTypeId != deviceTypeId: continue
						if str(theID) == str(dev.pluginProps.get('groupId', "xx")) and  hubNumber == str(dev.pluginProps.get('hubNumber', "xx")): 
							found = True
							if  mode != "background":
								self.indiLOG.log(10,"autocreateNewDevices group  Bridge:{:>2s}; id:{:>3s}; type:{:25s}      already exists".format(hubNumber, theID, theDict[theID]['type']))
							break

					if not found:
						name = "Hue_group_{}_{}_{}".format(hubNumber, theID, theDict[theID]['name'])
						address = ""
						props ={}
						props['hubNumber'] = hubNumber
						props['groupId'] = theID
						props['type'] = theDict[theID]['type']
						props['rate'] = "1"
						props['noOnRampRate'] = False
						props['noOffRampRate'] = False
						props['savedBrightness'] = ""
						props['groupClass'] = ""
						props['logChanges'] = self.pluginPrefs.get('logDefaultForNewDevices', "off") == "on"
						try:
							dev = indigo.device.create(
								protocol		= indigo.kProtocol.Plugin,
								address			= address,
								name			= name,
								description		= "created by bridge scan",
								pluginId		= self.pluginId,
								deviceTypeId	= deviceTypeId,
								folder			= hueFolderID,
								props			= props
								)
							props = dev.pluginProps
							newProps = self.validateDeviceConfigUi(props, deviceTypeId, dev.id)
							dev.replacePluginPropsOnServer(newProps[1])
							self.indiLOG.log(30,"autocreateNewDevices group  Bridge:{:>2s}; hue-id:{:>3s}, hue-type:{:25s}, mapped to indigo-deviceTypeId:{:27} create {:40s} (details in plugin.log)".format( hubNumber, theID, theDict[theID]['type'], deviceTypeId, name))
							self.indiLOG.log(10,"props:{}".format(props))
							createdGroups +=1
						except Exception:
							self.logger.error("", exc_info=True)
							self.logger.error("name:{}, deviceTypeId:{}, dict:{}".format(name, deviceTypeId, theDict[theID]))
							oldDev = indigo.devices[name]
							self.logger.error("existing deviceTypeId:{}, props:{}".format(oldDev.deviceTypeId, str(oldDev.pluginProps)))

		if (mode == "background" and (createdLights > 0 or createdSensors > 0 or createdGroups > 0)   ) or mode != "background":
			self.indiLOG.log(30,"autocreateNewDevices Lights  --  #of NEW Indigo devices created:{} ".format(createdLights))
			self.indiLOG.log(30,"autocreateNewDevices Sensors --  #of NEW Indigo devices created:{} ".format(createdSensors))
			self.indiLOG.log(30,"autocreateNewDevices Groups  --  #of NEW Indigo devices created:{} ".format(createdGroups))
		return


	# general get http command 
	def commandToHub_HTTP(self, hubNumber, cmd, errorsDict=None, errDict1="", errDict2=""):
		# Make sure the device selected is a Hue device.
		#   Get the device info directly from the bridge.

		try:
			if errorsDict is None:
				errorsDict = dict()
			jsonData = dict()
			ipAddress = self.ipAddresses[hubNumber]
			if not self.isValidIP(ipAddress):
				if ipAddress == "": 
					return (False, "", errorsDict) # this happens during setup of hub, for some time ip number is not defined, suppress error msg
				errorText = self.doErrorLog("hub#:{} no valid IP number: >>{}<<".format(hubNumber, ipAddress))
				errorsDict[errDict1] = errorText
				errorsDict[errDict2] += errorsDict[errDict1]
				return (False, "", errorsDict)

			command = "http://{}/api/{}/{}" .format(ipAddress, self.hostIds[hubNumber], cmd)
			if self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(10,"Sending URL request: {}".format(command) )
			if hubNumber not in self.bridgeRequestsSession:
				self.bridgeRequestsSession[hubNumber] = {"lastInit": 0, "session" : ""}
			#self.connectToBridge(hubNumber)
			try:
				self.setBridgeBusy(hubNumber, calledfrom="commandToHub_HTTP")
				r = requests.get(command, timeout=kTimeout, headers={'Connection':'close'})
				self.resetBridgeBusy(hubNumber)
			except requests.exceptions.Timeout:
				if self.checkForLastNotPairedMessage(hubNumber):
					errorText = self.doErrorLog("Failed to connect to the Hue bridge at {} after {} seconds. - Check that the bridge is connected and turned on.".format(ipAddress, kTimeout),force=True)
					errorsDict[errDict1] = errorText
					errorsDict[errDict2] += errorsDict[errDict1]
					self.resetBridgeBusy(hubNumber)
				return (False, "", errorsDict)
			except requests.exceptions.ConnectionError:
				if self.checkForLastNotPairedMessage(hubNumber):
					errorText = self.doErrorLog("Failed to connect to the Hue bridge at {}. - Check that the bridge is connected and turned on.".format(ipAddress, force=True))
					errorsDict[errDict1] = errorText
					errorsDict[errDict2] += errorsDict[errDict1]
				self.resetBridgeBusy(hubNumber)
				return (False, "", errorsDict)
			except Exception :
				self.logger.error("", exc_info=True)
				self.resetBridgeBusy(hubNumber)
				return (False, "", errorsDict)

			if self.decideMyLog("ReadFromBridge"): self.indiLOG.log(10,"Data from bridge: {}".format(r.content.decode("utf-8")) )
			# Convert the response to a Python object.
			try:
				jsonData = json.loads(r.content)
			except Exception:
				# There was an error in the returned data.
				self.logger.error("", exc_info=True)
				errorsDict[errDict1] = "Error retrieving Hue device data from bridge. See Indigo log."
				errorsDict[errDict2] += errorsDict[errDict1]
				return (False, "",  errorsDict)
			self.notPairedMsg[hubNumber] = time.time() - 90
			self.resetBridgeBusy(hubNumber)
			return True, jsonData, errorsDict
		except Exception:
			self.logger.error("", exc_info=True)
		self.resetBridgeBusy(hubNumber)
		return False, jsonData, errorsDict
			
	# start or reconnect session to bridge 
	########################################
	def connectToBridge(self, hubNumber, force=False):
		return  # not yet implemented, will keep sessions alive 
		try:
			if hubNumber not in self.bridgeRequestsSession or force:
				self.bridgeRequestsSession[hubNumber] = {"lastConnect": 0, "session" : ""}
			
			if self.bridgeRequestsSession[hubNumber]['session'] == "" or time.time() - self.bridgeRequestsSession[hubNumber]['lastConnect'] > 120.:
				self.bridgeRequestsSession[hubNumber]['session'] = requests.Session()
				self.bridgeRequestsSession[hubNumber]['lastConnect'] = time.time()
		except Exception:
			self.logger.error("", exc_info=True)
		return 


	# Validate Device Configuration

	# Validate  rgb .. props
	########################################
	def validateRGBWhiteOnOffetc(self, props, deviceTypeId ="", devId="" , devName=""):
		newProps = copy.deepcopy(props)
		try:

			if "modelId" 	not in props:							newProps['modelId'] 							= ""
			if "hubNumber" 	not in props:							newProps['hubNumber'] 							= "0"
			if "logChanges" not in newProps: 						newProps['logChanges'] 							= self.pluginPrefs.get('logDefaultForNewDevices', "off") == "on"
			if deviceTypeId in ksupportsSensorValue:				newProps['SupportsSensorValue']					= ksupportsSensorValue[deviceTypeId]
			if deviceTypeId in ksupportsBatteryLevel:				newProps['SupportsBatteryLevel']				= ksupportsBatteryLevel[deviceTypeId]
			if deviceTypeId in ksupportsOnState:					newProps['SupportsOnState']						= ksupportsOnState[deviceTypeId]
			if deviceTypeId in kSupportsColor:						newProps['SupportsColor']						= kSupportsColor[deviceTypeId]
			if deviceTypeId in kSupportsRGB: 		 				newProps['SupportsRGB']							= kSupportsRGB[deviceTypeId]
			if deviceTypeId in kSupportsWhite:	 					newProps['SupportsWhite']						= kSupportsWhite[deviceTypeId]
			if deviceTypeId in kSupportsWhiteTemperature:			newProps['SupportsWhiteTemperature'] 			= kSupportsWhiteTemperature[deviceTypeId]
			if deviceTypeId in kWhiteTemperatureMin:				newProps['WhiteTemperatureMin']					= kWhiteTemperatureMin[deviceTypeId]
			if deviceTypeId in kWhiteTemperatureMax:				newProps['WhiteTemperatureMax']					= kWhiteTemperatureMax[deviceTypeId]
			if deviceTypeId in kSupportsRGBandWhiteSimultaneously: 	newProps['SupportsRGBandWhiteSimultaneously']	= kSupportsRGBandWhiteSimultaneously[deviceTypeId]
			if deviceTypeId in kIsDimmerDevice: 					newProps['isDimmerDevice']						= kIsDimmerDevice[deviceTypeId]
			if deviceTypeId in kSupportsStatusRequest:				newProps['SupportsStatusRequest']				= kSupportsStatusRequest[deviceTypeId]
			if deviceTypeId in kAllowOnStateChange:					newProps['AllowOnStateChange']					= kAllowOnStateChange[deviceTypeId]

			if deviceTypeId in kTemperatureSensorTypeIDs :
				if not newProps.get('sensorOffset', False):			newProps['sensorOffset'] 						= ""
				if not newProps.get('temperatureScale', False):		newProps['temperatureScale'] 					= "c"

			hubNumber = newProps['hubNumber']
			if hubNumber not in self.ipAddresses:
				for ID in ['bulbId','groupId','sensorId','bulbDeviceId']:
					if ID in newProps:
						self.indiLOG.log(30,"dev Bridge:{}, HueId:{}, type:{}  not correctly setup ---  ipaddress has not been setup for bridge #Hub{}".format(hubNumber, newProps[ID], ID[:-2],  hubNumber) )
						return newProps
						

			if   'bulbId'		in newProps:						newProps['address'] 							= "{} (Lid:{}-{})".format(self.ipAddresses[hubNumber], hubNumber, newProps['bulbId'])
			elif 'groupId'		in newProps:						newProps['address'] 							= "{} (Gid:{}-{})".format(self.ipAddresses[hubNumber], hubNumber, newProps['groupId'])
			elif 'sensorId'		in newProps:						newProps['address'] 							= "{} (Sid:{}-{})".format(self.ipAddresses[hubNumber], hubNumber, newProps['sensorId'])
			elif 'bulbDeviceId'	in newProps:						newProps['address'] 							= "{} (Aid:{}-{})".format(devId, 						hubNumber, newProps['bulbDeviceId'])
			else:													newProps['address'] 							= ""

			#self.indiLOG.log(20,"validateRGBWhiteOnOffetc: {}, devtype {} props:{}".format(devName, deviceTypeId, newProps ))

		except Exception:
			self.logger.error("", exc_info=True)
		return newProps


	# Validate  ... brightness settings
	########################################
	def checkBrightness(self, valuesDict, isError, errorsDict):
			# Validate the default BRIGHTNESS is reasonable.
		try:
			if "defaultBrightness" in valuesDict and valuesDict.get('defaultBrightness', "") != "":
				try:
					defaultBrightness = int(valuesDict['defaultBrightness'])
					if defaultBrightness < 1 or defaultBrightness > 100:
						isError = True
						errorsDict['defaultBrightness'] = "The Default Brightness must be a number between 1 and 100."
						errorsDict['showAlertText'] += errorsDict['defaultBrightness'] + "\n\n"
				except ValueError:
					isError = True
					errorsDict['defaultBrightness'] = "The Default Brightness must be a number between 1 and 100."
					errorsDict['showAlertText'] += errorsDict['defaultBrightness'] + "\n\n"
				except Exception as e:
					isError = True
					errorsDict['defaultBrightness'] = "The Default Brightness must be a number between 1 and 100. Error: {}  @line#:{})".format(e,sys.exc_info()[2].tb_lineno)
					errorsDict['showAlertText'] += errorsDict['defaultBrightness'] + "\n\n"
		except Exception:
			self.logger.error("", exc_info=True)
		return isError, errorsDict


	# Validate  ... rate settings
	########################################
	def checkRate(self, valuesDict, isError, errorsDict):
		# Validate the default RATE is reasonable.
		try:
			if "rate" in valuesDict and valuesDict.get('rate', "") != "":
				try:
					rampRate = float(valuesDict['rate'])
					if rampRate < 0 or rampRate > 540:
						isError = True
						errorsDict['rate'] = "The Ramp Rate must be a number between 0 and 540 in increments of 0.1 seconds."
						errorsDict['showAlertText'] += errorsDict['rate'] + "\n\n"
				except ValueError:
					isError = True
					errorsDict['rate'] = "The Ramp Rate must be a number between 0 and 540 in increments of 0.1 seconds."
					errorsDict['showAlertText'] += errorsDict['rate'] + "\n\n"
				except Exception as e:
					isError = True
					errorsDict['rate'] = "The Ramp Rate must be a number between 0 and 540 in increments of 0.1 seconds. Error: {}  @line#:{})".format(e,sys.exc_info()[2].tb_lineno)
					errorsDict['showAlertText'] += errorsDict['rate'] + "\n\n"
		except Exception:
			self.logger.error("", exc_info=True)
		return isError, errorsDict


	def checkTypeOk(self, theDict, typeId, checkType, errorsDict):
		try: 
			if theDict.get('type', "")[0:len(checkType)] != checkType:
				errorsDict[typeId] = "The selected device is not a {} device. Please select a {} device to control.".format(typeId, checkType)
				errorsDict['showAlertText'] += errorsDict[typeId]
				return (True,  errorsDict)
			return False, errorsDict
		except Exception:
			self.logger.error("", exc_info=True)
		return (True,  errorsDict)


	def setDefaultSensorProps(self, valuesDict, sensor):
		try:
			valuesDict['enabledOnHub'] 		= True
			valuesDict['manufacturerName'] 	= sensor.get('manufacturername', "")
			valuesDict['modelId'] 			= sensor.get('modelid', "")
			valuesDict['productId'] 		= sensor.get('productname', "")
			valuesDict['nameOnHub'] 		= sensor.get('name', "")
			valuesDict['swVersion'] 		= sensor.get('swversion', "")
			valuesDict['type'] 				= sensor.get('type', "")
			valuesDict['uniqueId'] 			= sensor.get('uniqueid', "")
		except Exception:
			self.logger.error("", exc_info=True)
		return valuesDict



	########################################
	def validateDeviceConfigUi(self, valuesDict, typeId, deviceId):
		if self.decideMyLog("UpdateIndigoDevices"): self.indiLOG.log(10,"Starting validateDeviceConfigUi.\n  valuesDict: {}\n  typeId: {}\n  deviceId: {}".format(valuesDict, typeId, deviceId))
		errorsDict = indigo.Dict()
		errorsDict['showAlertText'] = ""
		isError = False

		hubNumber = valuesDict['hubNumber']
		ipAddress = self.ipAddresses[hubNumber]
		hostId = self.hostIds[hubNumber]
		deviceAction =  valuesDict.get("deviceAction","EditExisting")

		# Make sure we're still paired with the Hue bridge.
		if not self.paired[hubNumber]:
			isError = True
			errorsDict['bulbId'] = "Not currently paired with the Hue bridge. Close this window and use the Configure... option in the Plugins -> Hue Lights menu to pair with the Hue bridge first."
			errorsDict['showAlertText'] += errorsDict['bulbId']
			self.notPairedMsg[hubNumber] = time.time()
			return (False, valuesDict, errorsDict)

		valuesDict = self.validateRGBWhiteOnOffetc(valuesDict, deviceTypeId=typeId, devId=deviceId, devName="")
		# Check data based on which device config UI was returned.
		#  -- Lights and On/Off Devices --
		if typeId in kLightDeviceTypeIDs:
			# Make sure a bulb was selected.
			if valuesDict.get('bulbId', "") == "":
				errorsDict['bulbId'] = "Please select a Hue device to control."
				errorsDict['showAlertText'] += errorsDict['bulbId']
				return (False, valuesDict, errorsDict)

			bulbId = valuesDict['bulbId']

			# Make sure the device selected is a Hue device.
			#   Get the device info directly from the bridge.

			retCode, bulb, errorsDict =  self.commandToHub_HTTP( hubNumber, "lights/{}".format(bulbId), errorsDict, errDict1="bulbId", errDict2="showAlertText")
			if not retCode:
				return (False, valuesDict, errorsDict)
			
			# Populate the appropriate values in the valuesDict.
			valuesDict['manufacturerName'] = bulb.get('manufacturername', "")
			valuesDict['modelId'] = bulb.get('modelid', "")
			valuesDict['nameOnHub'] = bulb.get('name', "")
			valuesDict['swVersion'] = bulb.get('swversion', "")
			valuesDict['type'] = bulb.get('type', "")
			valuesDict['uniqueId'] = bulb.get('uniqueid', "")

			# Make sure the bulb ID isn't used by another device.
			if deviceAction in ["Replace_with_new_Hue_device","EditExisting"]:
				for otherDeviceId in self.deviceList:
					if otherDeviceId != deviceId:
						otherDevice = indigo.devices[otherDeviceId]
						if valuesDict['bulbId'] == otherDevice.pluginProps.get('bulbId', 0) and hubNumber == otherDevice.pluginProps.get('hubNumber', 0):
							otherDevice = indigo.devices[otherDeviceId]
							errorsDict['bulbId'] = "This Hue device is already being controlled by the \"{}\" Indigo device. Choose a different Hue bulb to control.".format(otherDevice.name)
							errorsDict['showAlertText'] += errorsDict['bulbId'] + "\n\n"
							return (False, valuesDict, errorsDict)

		#  -- Hue Bulb --
		if typeId == "hueBulb":
			# Make sure this is a Hue color/ambiance light.
			retErr, errorsDict = self.checkTypeOk(bulb, typeId, kHueBulbDeviceIDType, errorsDict)
			if retErr: return (False, valuesDict, errorsDict)

			isError, errorsDict = self.checkBrightness(valuesDict, isError, errorsDict)
			isError, errorsDict = self.checkRate(valuesDict, isError, errorsDict)

			# Show errors if there are any.
			if isError:
				errorsDict['showAlertText'] = errorsDict['showAlertText'].strip()
				return (False, valuesDict, errorsDict)
			else:
				return (True, valuesDict)

		#  -- Ambiance Lights --
		if typeId == "hueAmbiance":
			# Make sure an ambiance light was selected.
			retErr, errorsDict = self.checkTypeOk(bulb, typeId, kAmbianceDeviceIDType, errorsDict)
			if retErr: return (False, valuesDict, errorsDict)
			isError, errorsDict = self.checkBrightness(valuesDict, isError, errorsDict)
			isError, errorsDict = self.checkRate(valuesDict, isError, errorsDict)

			# Show errors if there are any.
			if isError:
				errorsDict['showAlertText'] = errorsDict['showAlertText'].strip()
				return (False, valuesDict, errorsDict)

			else:
				return (True, valuesDict)

		#  -- LightStrips Device --
		elif typeId == "hueLightStrips":
			# Make sure it's a Light Strip device.
			retErr, errorsDict = self.checkTypeOk(bulb, typeId, kLightStripsDeviceIDType, errorsDict)
			if retErr: return (False, valuesDict, errorsDict)
			isError, errorsDict = self.checkBrightness(valuesDict, isError, errorsDict)
			isError, errorsDict = self.checkRate(valuesDict, isError, errorsDict)

			# Show errors if there are any.
			if isError:
				errorsDict['showAlertText'] = errorsDict['showAlertText'].strip()
				return (False, valuesDict, errorsDict)

			else:
				return (True, valuesDict)

		#  -- LivingColors Bloom Device --
		elif typeId == "hueLivingColorsBloom":
			# Make sure a Living Colors device was selected.
			retErr, errorsDict = self.checkTypeOk(bulb, typeId, kLivingColorsDeviceIDType, errorsDict)
			if retErr: return (False, valuesDict, errorsDict)
			isError, errorsDict = self.checkBrightness(valuesDict, isError, errorsDict)
			isError, errorsDict = self.checkRate(valuesDict, isError, errorsDict)

			# Show errors if there are any.
			if isError:
				errorsDict['showAlertText'] = errorsDict['showAlertText'].strip()
				return (False, valuesDict, errorsDict)

			else:
				return (True, valuesDict)

		#  -- LivingWhites Device --
		elif typeId == "hueLivingWhites":
			# Make sure a Living Whites device was selected.
			retErr, errorsDict = self.checkTypeOk(bulb, typeId, kLivingWhitesDeviceIDType, errorsDict)
			if retErr: return (False, valuesDict, errorsDict)
			isError, errorsDict = self.checkBrightness(valuesDict, isError, errorsDict)
			isError, errorsDict = self.checkRate(valuesDict, isError, errorsDict)

			# Show errors if there are any.
			if isError:
				errorsDict['showAlertText'] = errorsDict['showAlertText'].strip()
				return (False, valuesDict, errorsDict)

			else:
				return (True, valuesDict)

		#  -- On/Off Device --
		elif typeId == "hueOnOffDevice":
			retErr, errorsDict = self.checkTypeOk(bulb, typeId, kOnOffOnlyDeviceIDType, errorsDict)
			if retErr: return (False, valuesDict, errorsDict)

			return (True, valuesDict)

		#  -- Hue Group --
		elif typeId == "hueGroup":
			# Make sure a group was selected.
			if valuesDict.get('groupId', "") == "":
				isError = True
				errorsDict['groupId'] = "Please select a Hue Group to control."
				errorsDict['showAlertText'] += errorsDict['groupId']
				return (False, valuesDict, errorsDict)

			groupId = valuesDict['groupId']

			# Make sure the device selected is a Hue group.
			#   Get the group info directly from the bridge.
			retCode, group, errorsDict =  self.commandToHub_HTTP( hubNumber, "groups/{}".format(groupId), errorsDict, errDict1="groupId", errDict2="showAlertText")
			if not retCode:
				return (False, valuesDict, errorsDict)

			# Populate the appropriate values in the valuesDict.
			valuesDict['groupClass'] = group.get('class', "")
			valuesDict['nameOnHub'] = group.get('name', "")
			valuesDict['type'] = group.get('type', "")
			# Make sure the group ID isn't used by another device.
			for otherDeviceId in self.deviceList:
				if otherDeviceId != deviceId:
					otherDevice = indigo.devices[otherDeviceId]
					if valuesDict['groupId'] == otherDevice.pluginProps.get('groupId', 0) and hubNumber == otherDevice.pluginProps.get('hubNumber', 0):
						otherDevice = indigo.devices[otherDeviceId]
						isError = True
						errorsDict['groupId'] = "This Hue group is already being controlled by the \"{}\" Indigo device. Choose a different Hue group to control.".format(otherDevice.name)
						errorsDict['showAlertText'] += errorsDict['groupId'] + "\n\n"

			isError, errorsDict = self.checkBrightness(valuesDict, isError, errorsDict)
			isError, errorsDict = self.checkRate(valuesDict, isError, errorsDict)

			# Show errors if there are any.
			if isError:
				errorsDict['showAlertText'] = errorsDict['showAlertText'].strip()
				return (False, valuesDict, errorsDict)

			else:
				return (True, valuesDict)

		# -- Hue Device Attribute Controller (Virtual Dimmer Device) --
		elif typeId == "hueAttributeController":
			# Make sure a Hue device was selected.
			if valuesDict.get('bulbDeviceId', "") == "":
				isError = True
				errorsDict['bulbDeviceId'] = "Please select a Hue device whose attribute will be controlled."
				errorsDict['showAlertText'] += errorsDict['bulbDeviceId']
			elif valuesDict.get('type', "") == kLivingWhitesDeviceIDType:
				isError = True
				errorsDict['bulbDeviceId'] = "LivingWhites type devices have no attributes that can be controlled. Please select a Hue device that supports color or color temperature."
				errorsDict['showAlertText'] += errorsDict['bulbDeviceId']
			elif valuesDict.get('type', "")[0:len(kOnOffOnlyDeviceIDType)] == kOnOffOnlyDeviceIDType:
				isError = True
				errorsDict['bulbDeviceId'] = "On/Off Only type devices have no attributes that can be controlled. Please select a Hue device that supports color or color temperature."
				errorsDict['showAlertText'] += errorsDict['bulbDeviceId']
			# Make sure an Attribute to Control is selected.
			if valuesDict.get('attributeToControl', "") == "":
				isError = True
				errorsDict['attributeToControl'] = "Please select an Attribute to Control."
				errorsDict['showAlertText'] += errorsDict['attributeToControl']

			isError, errorsDict = self.checkRate(valuesDict, isError, errorsDict)

			# Show errors if there are any.
			if isError:
				errorsDict['showAlertText'] = errorsDict['showAlertText'].strip()
				return (False, valuesDict, errorsDict)

			else:
				return (True, valuesDict)

		#  -- Hue Motion Sensor (Motion) --
		elif typeId == "hueMotionSensor":
			# Make sure a motion sensor was selected.
			if valuesDict.get('sensorId', "") == "":
				isError = True
				errorsDict['sensorId'] = "Please select a Hue Motion Sensor."
				errorsDict['showAlertText'] += errorsDict['sensorId']
				return (False, valuesDict, errorsDict)
			sensorId = valuesDict['sensorId']

			# Make sure the device selected is a Hue sensor device.
			#   Get the device info directly from the bridge.
			retCode, sensor, errorsDict =  self.commandToHub_HTTP( hubNumber, "sensors/{}".format(sensorId), errorsDict, errDict1="sensorId", errDict2="showAlertText")
			if not retCode:
				return (False, valuesDict, errorsDict)


			if sensor.get('modelid', "")[0:len(kMotionSensorDeviceIDs)] != kMotionSensorDeviceIDs:
				isError = True
				errorsDict['sensorId'] = "The selected device is not a Hue Motion Sensor. Please select a Hue Motion Sensor device."
				errorsDict['showAlertText'] += errorsDict['sensorId']
				return (False, valuesDict, errorsDict)

			# Make sure the sensor ID isn't used by another device.
			for otherDeviceId in self.deviceList:
				if otherDeviceId != deviceId:
					otherDevice = indigo.devices[otherDeviceId]
					if sensorId == otherDevice.pluginProps.get('sensorId', 0) and hubNumber == otherDevice.pluginProps.get('hubNumber', 0):
						otherDevice = indigo.devices[otherDeviceId]
						isError = True
						errorsDict['sensorId'] = "This Hue device is already being controlled by the \"{}\" Indigo device. Choose a different Hue Motion Sensor.".format(otherDevice.name)
						errorsDict['showAlertText'] += errorsDict['sensorId'] + "\n\n"

			# Show errors if there are any.
			if isError:
				errorsDict['showAlertText'] = errorsDict['showAlertText'].strip()
				return (False, valuesDict, errorsDict)

			else:
				if valuesDict.get('sensorOffset', False):
					valuesDict['sensorOffset'] = ""
				if valuesDict.get('temperatureScale', False):
					valuesDict['temperatureScale'] = ""
				return (True, self.setDefaultSensorProps(valuesDict, sensor))

		#  -- Hue Motion Sensor (Temperature) --
		elif typeId == "hueMotionTemperatureSensor":
			# Make sure a motion sensor was selected.
			if valuesDict.get('sensorId', "") == "":
				isError = True
				errorsDict['sensorId'] = "Please select a temperature sensor."
				errorsDict['showAlertText'] += errorsDict['sensorId']
				return (False, valuesDict, errorsDict)

			sensorId = valuesDict.get('sensorId', "0")

			# Make sure the device selected is a Hue sensor device.
			#   Get the device info directly from the bridge.
			retCode, sensor, errorsDict =  self.commandToHub_HTTP( hubNumber, "sensors/{}".format(sensorId), errorsDict, errDict1="sensorId", errDict2="showAlertText")
			if not retCode:
				return (False, valuesDict, errorsDict)

			if sensor.get('modelid', "")[0:len(kTemperatureSensorDeviceIDs)] != kTemperatureSensorDeviceIDs:
				isError = True
				errorsDict['sensorId'] = "The selected device is not a temperature sensor. Please select a temperature sensor device."
				errorsDict['showAlertText'] += errorsDict['sensorId']
				return (False, valuesDict, errorsDict)

			# Make sure the sensor ID isn't used by another device.
			for otherDeviceId in self.deviceList:
				if otherDeviceId != deviceId:
					otherDevice = indigo.devices[otherDeviceId]
					if valuesDict['sensorId'] == otherDevice.pluginProps.get('sensorId', 0) and hubNumber == otherDevice.pluginProps.get('hubNumber', 0):
						otherDevice = indigo.devices[otherDeviceId]
						isError = True
						errorsDict['sensorId'] = "This Hue device is already being controlled by the \"{}\" Indigo device. Choose a different temperature sensor.".format(otherDevice.name)
						errorsDict['showAlertText'] += errorsDict['sensorId'] + "\n\n"

			# Validate the sensor offset (calibration offset).
			if valuesDict.get('sensorOffset', "") != "":
				try:
					sensorOffset = round(float(valuesDict.get('sensorOffset', 0)), 1)
					if sensorOffset < -10.0 or sensorOffset > 10.0:
						isError = True
						errorsDict['sensorOffset'] = "The Calibration Offset must be a number between -10 and 10."
						errorsDict['showAlertText'] += errorsDict['sensorOffset'] + "\n\n"
				except ValueError:
					isError = True
					errorsDict['sensorOffset'] = "The Calibration Offset must be a number between -10 and 10."
					errorsDict['showAlertText'] += errorsDict['sensorOffset'] + "\n\n"
				except Exception as e:
					isError = True
					errorsDict['sensorOffset'] = "The Calibration Offset must be a number between -10 and 10. Error: {}  @line#:{})".format(e,sys.exc_info()[2].tb_lineno)
					errorsDict['showAlertText'] += errorsDict['sensorOffset'] + "\n\n"

			# Validate the temperature scale.
			if valuesDict.get('temperatureScale', "") != "":
				try:
					temperatureScale = valuesDict.get('temperatureScale', "c")
				except Exception as e:
					isError = True
					errorsDict['temperatureScale'] = "The Temperature Scale must be either Celsius or Fahrenheit. Error: {}  @line#:{})".format(e,sys.exc_info()[2].tb_lineno)
					errorsDict['showAlertText'] += errorsDict['temperatureScale'] + "\n\n"
			else:
				valuesDict['temperatureScale'] = "c"

			# Show errors if there are any.
			if isError:
				errorsDict['showAlertText'] = errorsDict['showAlertText'].strip()
				return (False, valuesDict, errorsDict)

			return (True, self.setDefaultSensorProps(valuesDict, sensor))

		#  -- Hue Motion Sensor (Luminance) --
		elif typeId == "hueMotionLightSensor":
			# Make sure a motion sensor was selected.
			if valuesDict.get('sensorId', "") == "":
				isError = True
				errorsDict['sensorId'] = "Please select a light sensor."
				errorsDict['showAlertText'] += errorsDict['sensorId']
				return (False, valuesDict, errorsDict)

			sensorId = valuesDict['sensorId']

			# Make sure the device selected is a Hue sensor device.
			#   Get the device info directly from the bridge.
			retCode, sensor, errorsDict =  self.commandToHub_HTTP( hubNumber, "sensors/{}".format(sensorId), errorsDict, errDict1="sensorId", errDict2="showAlertText")
			if not retCode:
				return (False, valuesDict, errorsDict)

			if sensor.get('modelid', "")[0:len(kLightSensorDeviceIDs)] != kLightSensorDeviceIDs:
				isError = True
				errorsDict['sensorId'] = "The selected device is not a light sensor. Please select a light sensor device."
				errorsDict['showAlertText'] += errorsDict['sensorId']
				return (False, valuesDict, errorsDict)

			# Make sure the sensor ID isn't used by another device.
			for otherDeviceId in self.deviceList:
				if otherDeviceId != deviceId:
					otherDevice = indigo.devices[otherDeviceId]
					if valuesDict['sensorId'] == otherDevice.pluginProps.get('sensorId', 0) and hubNumber == otherDevice.pluginProps.get('hubNumber', 0):
						otherDevice = indigo.devices[otherDeviceId]
						isError = True
						errorsDict['sensorId'] = "This Hue device is already being controlled by the \"{}\" Indigo device. Choose a different light sensor.".format(otherDevice.name)
						errorsDict['showAlertText'] += errorsDict['sensorId'] + "\n\n"

			# Show errors if there are any.
			if isError:
				errorsDict['showAlertText'] = errorsDict['showAlertText'].strip()
				return (False, valuesDict, errorsDict)

			else:
				if valuesDict.get('sensorOffset', False):
					valuesDict['sensorOffset'] = ""
				if valuesDict.get('temperatureScale', False):
					valuesDict['temperatureScale'] = ""
				return (True, self.setDefaultSensorProps(valuesDict, sensor))

		#  -- Hue Tap Switch --
		elif typeId == "hueTapSwitch":
			# Make sure a tap switch was selected.
			if valuesDict.get('sensorId', "") == "":
				isError = True
				errorsDict['sensorId'] = "Please select a Hue Tap Switch."
				errorsDict['showAlertText'] += errorsDict['sensorId']
				return (False, valuesDict, errorsDict)

			sensorId = valuesDict['sensorId']

			# Make sure the device selected is a Hue sensor device.
			#   Get the device info directly from the bridge.
			retCode, sensor, errorsDict =  self.commandToHub_HTTP( hubNumber, "sensors/{}".format(sensorId), errorsDict, errDict1="sensorId", errDict2="showAlertText")
			if not retCode:
				return (False, valuesDict, errorsDict)

			# Make sure the sensor ID isn't used by another device.
			for otherDeviceId in self.deviceList:
				if otherDeviceId != deviceId:
					otherDevice = indigo.devices[otherDeviceId]
					if sensorId == otherDevice.pluginProps.get('sensorId', 0) and hubNumber == otherDevice.pluginProps.get('hubNumber', 0):
						otherDevice = indigo.devices[otherDeviceId]
						isError = True
						errorsDict['sensorId'] = "This Hue device is already being controlled by the \"{}\" Indigo device. Choose a different Hue Tap Switch.".format(otherDevice.name)
						errorsDict['showAlertText'] += errorsDict['sensorId'] + "\n\n"

			# Show errors if there are any.
			if isError:
				errorsDict['showAlertText'] = errorsDict['showAlertText'].strip()
				return (False, valuesDict, errorsDict)

			return True,  self.setDefaultSensorProps(valuesDict, sensor)

		#  -- Hue Dimmer Switch --
		elif typeId == "hueDimmerSwitch":
			# Make sure a dimmer switch was selected.
			if valuesDict.get('sensorId', "") == "":
				isError = True
				errorsDict['sensorId'] = "Please select a Hue Dimmer Switch."
				errorsDict['showAlertText'] += errorsDict['sensorId']
				return (False, valuesDict, errorsDict)

			sensorId = valuesDict['sensorId']

			# Make sure the device selected is a Hue sensor device.
			#   Get the device info directly from the bridge.
			retCode, sensor, errorsDict =  self.commandToHub_HTTP( hubNumber, "sensors/{}".format(sensorId), errorsDict, errDict1="sensorId", errDict2="showAlertText")
			if not retCode:
				return (False, valuesDict, errorsDict)

			# Make sure the sensor ID isn't used by another device.
			for otherDeviceId in self.deviceList:
				if otherDeviceId != deviceId:
					otherDevice = indigo.devices[otherDeviceId]
					if sensorId == otherDevice.pluginProps.get('sensorId', 0) and hubNumber == otherDevice.pluginProps.get('hubNumber', 0):
						otherDevice = indigo.devices[otherDeviceId]
						isError = True
						errorsDict['sensorId'] = "This Hue device is already being controlled by the \"{}\" Indigo device. Choose a different Hue Dimmer Switch.".format(otherDevice.name)
						errorsDict['showAlertText'] += errorsDict['sensorId'] + "\n\n"

			# Show errors if there are any.
			if isError:
				errorsDict['showAlertText'] = errorsDict['showAlertText'].strip()
				return (False, valuesDict, errorsDict)

			return True,  self.setDefaultSensorProps(valuesDict, sensor)

		#  -- Hue Smart Button --
		elif typeId == "hueSmartButton":
			# Make sure a smart button was selected.
			if valuesDict.get('sensorId', "") == "":
				isError = True
				errorsDict['sensorId'] = "Please select a Hue Smart Button."
				errorsDict['showAlertText'] += errorsDict['sensorId']
				return (False, valuesDict, errorsDict)

			sensorId = valuesDict['sensorId']

			# Make sure the device selected is a Hue sensor device.
			#   Get the device info directly from the bridge.
			retCode, sensor, errorsDict =  self.commandToHub_HTTP( hubNumber, "sensors/{}".format(sensorId), errorsDict, errDict1="sensorId", errDict2="showAlertText")
			if not retCode:
				return (False, valuesDict, errorsDict)

			# Make sure the sensor ID isn't used by another device.
			for otherDeviceId in self.deviceList:
				if otherDeviceId != deviceId:
					otherDevice = indigo.devices[otherDeviceId]
					if sensorId == otherDevice.pluginProps.get('sensorId', 0) and hubNumber == otherDevice.pluginProps.get('hubNumber', 0):
						otherDevice = indigo.devices[otherDeviceId]
						isError = True
						errorsDict['sensorId'] = "This Hue device is already being controlled by the \"{}\" Indigo device. Choose a different Hue Smart Button.".format(otherDevice.name)
						errorsDict['showAlertText'] += errorsDict['sensorId'] + "\n\n"

			# Show errors if there are any.
			if isError:
				errorsDict['showAlertText'] = errorsDict['showAlertText'].strip()
				return (False, valuesDict, errorsDict)

			return True,  self.setDefaultSensorProps(valuesDict, sensor)

		#  -- Hue Wall Switch Module --
		elif typeId == "hueWallSwitchModule":
			# Make sure a smart button was selected.
			if valuesDict.get('sensorId', "") == "":
				isError = True
				errorsDict['sensorId'] = "Please select a Hue Wall Switch Module."
				errorsDict['showAlertText'] += errorsDict['sensorId']
				return (False, valuesDict, errorsDict)

			sensorId = valuesDict['sensorId']

			# Make sure the device selected is a Hue sensor device.
			#   Get the device info directly from the bridge.
			retCode, sensor, errorsDict =  self.commandToHub_HTTP( hubNumber, "sensors/{}".format(sensorId), errorsDict, errDict1="sensorId", errDict2="showAlertText")
			if not retCode:
				return (False, valuesDict, errorsDict)

			# Make sure the sensor ID isn't used by another device.
			for otherDeviceId in self.deviceList:
				if otherDeviceId != deviceId:
					otherDevice = indigo.devices[otherDeviceId]
					if sensorId == otherDevice.pluginProps.get('sensorId', 0) and hubNumber == otherDevice.pluginProps.get('hubNumber', 0):
						otherDevice = indigo.devices[otherDeviceId]
						isError = True
						errorsDict['sensorId'] = "This Hue device is already being controlled by the \"{}\" Indigo device. Choose a different Hue Wall Switch Module.".format(otherDevice.name)
						errorsDict['showAlertText'] += errorsDict['sensorId'] + "\n\n"

			# Show errors if there are any.
			if isError:
				errorsDict['showAlertText'] = errorsDict['showAlertText'].strip()
				return (False, valuesDict, errorsDict)

			else:
				valuesDict['deviceMode'] = sensor.get('devicemode', "")
				return True,  self.setDefaultSensorProps(valuesDict, sensor)

		#  -- Run Less Wire or Niko Switch --
		elif typeId == "runLessWireSwitch":
			# Make sure a Run Less Wire or Niko switch was selected.
			if valuesDict.get('sensorId', "") == "":
				isError = True
				errorsDict['sensorId'] = "Please select a Run Less Wire or Niko Switch."
				errorsDict['showAlertText'] += errorsDict['sensorId']
				return (False, valuesDict, errorsDict)

			sensorId = valuesDict['sensorId']

			# Make sure the device selected is a Hue sensor device.
			#   Get the device info directly from the bridge.
			retCode, sensor, errorsDict =  self.commandToHub_HTTP( hubNumber, "sensors/{}".format(sensorId), errorsDict, errDict1="sensorId", errDict2="showAlertText")
			if not retCode:
				return (False, valuesDict, errorsDict)

			# Make sure the sensor ID isn't used by another device.
			for otherDeviceId in self.deviceList:
				if otherDeviceId != deviceId:
					otherDevice = indigo.devices[otherDeviceId]
					if sensorId == otherDevice.pluginProps.get('sensorId', 0) and hubNumber == otherDevice.pluginProps.get('hubNumber', 0):
						otherDevice = indigo.devices[otherDeviceId]
						isError = True
						errorsDict['sensorId'] = "This Hue connected device is already being controlled by the \"{}\" Indigo device. Choose a different Run Less Wire Switch.".format(otherDevice.name)
						errorsDict['showAlertText'] += errorsDict['sensorId'] + "\n\n"

			# Show errors if there are any.
			if isError:
				errorsDict['showAlertText'] = errorsDict['showAlertText'].strip()
				return (False, valuesDict, errorsDict)

			self.hubNumberSelected = ""
			return (True, self.setDefaultSensorProps(valuesDict, sensor))


		#  -- hueRotaryWallRing --
		elif typeId == "hueRotaryWallRing":
			# 
			if valuesDict.get('sensorId', "") == "":
				isError = True
				errorsDict['sensorId'] = "Please select a Rotary Wall Ring."
				errorsDict['showAlertText'] += errorsDict['sensorId']
				return (False, valuesDict, errorsDict)

			sensorId = valuesDict['sensorId']

			# Make sure the device selected is a Hue sensor device.
			#   Get the device info directly from the bridge.
			retCode, sensor, errorsDict =  self.commandToHub_HTTP( hubNumber, "sensors/{}".format(sensorId), errorsDict, errDict1="sensorId", errDict2="showAlertText")
			if not retCode:
				return (False, valuesDict, errorsDict)

			# Make sure the sensor ID isn't used by another device.
			for otherDeviceId in self.deviceList:
				if otherDeviceId != deviceId:
					otherDevice = indigo.devices[otherDeviceId]
					if sensorId == otherDevice.pluginProps.get('sensorId', 0) and hubNumber == otherDevice.pluginProps.get('hubNumber', 0):
						otherDevice = indigo.devices[otherDeviceId]
						isError = True
						errorsDict['sensorId'] = "This Hue connected device is already being controlled by the \"{}\" Indigo device. Choose a different Rotary Wall Ring.".format(otherDevice.name)
						errorsDict['showAlertText'] += errorsDict['sensorId'] + "\n\n"

			# Show errors if there are any.
			if isError:
				errorsDict['showAlertText'] = errorsDict['showAlertText'].strip()
				return (False, valuesDict, errorsDict)

			self.hubNumberSelected = ""
			return (True, self.setDefaultSensorProps(valuesDict, sensor))

		#  -- hueRotaryWallRing --
		elif typeId == "hueRotaryWallSwitches":
			# 
			if valuesDict.get('sensorId', "") == "":
				isError = True
				errorsDict['sensorId'] = "Please select a Rotary Wall ring - Switch."
				errorsDict['showAlertText'] += errorsDict['sensorId']
				return (False, valuesDict, errorsDict)

			sensorId = valuesDict['sensorId']

			# Make sure the device selected is a Hue sensor device.
			#   Get the device info directly from the bridge.
			retCode, sensor, errorsDict =  self.commandToHub_HTTP( hubNumber, "sensors/{}".format(sensorId), errorsDict, errDict1="sensorId", errDict2="showAlertText")
			if not retCode:
				return (False, valuesDict, errorsDict)

			# Make sure the sensor ID isn't used by another device.
			for otherDeviceId in self.deviceList:
				if otherDeviceId != deviceId:
					otherDevice = indigo.devices[otherDeviceId]
					if sensorId == otherDevice.pluginProps.get('sensorId', 0) and hubNumber == otherDevice.pluginProps.get('hubNumber', 0):
						otherDevice = indigo.devices[otherDeviceId]
						isError = True
						errorsDict['sensorId'] = "This Hue connected device is already being controlled by the \"{}\" Indigo device. Choose a different Rotary Wall Ring-Switch.".format(otherDevice.name)
						errorsDict['showAlertText'] += errorsDict['sensorId'] + "\n\n"

			# Show errors if there are any.
			if isError:
				errorsDict['showAlertText'] = errorsDict['showAlertText'].strip()
				return (False, valuesDict, errorsDict)

			self.hubNumberSelected = ""
			return (True, self.setDefaultSensorProps(valuesDict, sensor))


		else:
			isError = True
			errorsDict['showAlertText'] = "No compatible device type was selected. Please cancel the device setup and try selecting the device type again."
			errorsDict['showAlertText'] = errorsDict['showAlertText'].strip()
			self.logger.error( errorsDict['showAlertText'])
			return (False, valuesDict, errorsDict)

	# Closed Device Configuration.
	########################################
	def closedDeviceConfigUi(self, valuesDict, userCancelled, typeId, deviceId):
		if self.decideMyLog("EditSetup"): self.indiLOG.log(20,"Starting closedDeviceConfigUi.  valuesDict: {}, userCancelled: {}, typeId: {}, deviceId: {}".format(valuesDict, userCancelled, typeId, deviceId))
		# If the user didn't cancel the changes, take any needed actions as a result of the changes made.
		if not userCancelled:
			# Configuration was saved.  Rebuild the device if needed.
			device = indigo.devices[deviceId]
			self.rebuildDevice(device, vd=valuesDict)

	# Validate Action Configuration.
	########################################
	def validateActionConfigUi(self, valuesDict, typeId, deviceId):
		if self.decideMyLog("EditSetup"): self.indiLOG.log(20,"Starting validateActionConfigUi.  valuesDict: {}, typeId: {}, deviceId: {}".format(valuesDict,  typeId, deviceId))
		hubNumber = "0"
		isError = False
		errorsDict = indigo.Dict()
		errorsDict['showAlertText'] = ""
		descString = ""

		if typeId == "actionEnableDisableSensor": return True, valuesDict

		if deviceId == 0:
			device = None
			modelId = 0
			# not used:   type = 0
			if "hubNumber" in valuesDict: hubNumber = valuesDict['hubNumber']
		else:
			device = indigo.devices[deviceId]
			modelId = device.pluginProps.get('modelId', False)
			# not used:   type = device.pluginProps.get('type', False)
			hubNumber = device.pluginProps.get('hubNumber', "0")

		if hubNumber not in self.hueConfigDict:
			errorsDict = indigo.Dict()
			errorsDict['showAlertText'] = "hubNumber in device not in hue bridge dict {}".format(hubNumber)
			return (False, valuesDict, errorsDict)

		# Make sure we're still paired with the Hue bridge.
		if not self.paired[hubNumber]:
			self.notPairedMsg[hubNumber] = time.time()
			isError = True
			errorsDict['device'] = "Not currently paired with the Hue bridge. Use the Configure... option in the Plugins -> Hue Lights menu to pair with the Hue bridge first."
			errorsDict['showAlertText'] += errorsDict['device'] + "\n\n"
			return (False, valuesDict, errorsDict)

		### RECALL HUE SCENE ###
		if typeId == "recallScene":
			descString = "recall hue scene"
			sceneId = valuesDict.get('sceneId', "")
			userId = valuesDict.get('userId', "")
			groupId = valuesDict.get('groupId', "")
			sceneLights = self.sceneLightsListGenerator("", valuesDict, typeId, deviceId)

			if sceneId != "":
				sceneName = self.hueConfigDict[hubNumber]['scenes'][sceneId]['name']
				descString += " " + sceneName
			else:
				isError = True
				errorsDict['sceneId'] = "A Scene must be selected."
				errorsDict['showAlertText'] += errorsDict['sceneId'] + "\n\n"

			if userId != "":
				if userId != "all":
					if userId in self.hueConfigDict[hubNumber]['users'] :
						userName = self.hueConfigDict[hubNumber]['users'][userId]['name'].replace("#", " app on ")
					else:
						userName = "(a removed scene creator)"
					descString += " from " + userName
				else:
					if sceneId != "":
						userId = self.hueConfigDict[hubNumber]['scenes'][sceneId]['owner']
						if userId in self.hueConfigDict[hubNumber]['users'] :
							userName = self.hueConfigDict[hubNumber]['users'][userId]['name'].replace("#", " app on ")
						else:
							userName = "(a removed scene creator)"
						descString += " from " + userName
			else:
				isError = True
				errorsDict['userId'] = "A Scene Creator must be selected."
				errorsDict['showAlertText'] += errorsDict['userId'] + "\n\n"

			if groupId != "":
				if groupId == "0":
					groupName = "All Hue Lights"
					descString += " for " + groupName
				else:
					groupName = self.hueConfigDict[hubNumber]['groups'][groupId]['name']
					descString += " for the " + groupName + " hue group"
			else:
				isError = True
				errorsDict['groupId'] = "A Group must be selected."
				errorsDict['showAlertText'] += errorsDict['userId'] + "\n\n"

			if len(sceneLights) < 1:
				isError = True
				errorsDict['sceneLights'] = "The selected Scene and Group Limit combination will prevent any lights from changing when this scene is recalled. Change the Scene or Group Limit selection and make sure at least 1 light is listed in the Lights Affected list."
				errorsDict['showAlertText'] += errorsDict['sceneLights'] + "\n\n"

			if isError:
				errorsDict['showAlertText'] = errorsDict['showAlertText'].strip()
				return (False, valuesDict, errorsDict)

		### SET BRIGHTNESS WITH RAMP RATE ###
		elif typeId == "setBrightness":
			brightnessSource = valuesDict.get('brightnessSource', False)
			brightness = valuesDict.get('brightness', False)
			brightnessVarId = valuesDict.get('brightnessVariable', False)
			brightnessDevId = valuesDict.get('brightnessDevice', False)
			useRateVariable = valuesDict.get('useRateVariable', False)
			rate = valuesDict.get('rate', False)
			rateVarId = valuesDict.get('rateVariable', False)

			# First make sure this is a Hue device and not an attribute controller.
			if device.deviceTypeId == "hueAttributeController":
				isError = True
				errorsDict['device'] = "This action cannot be applied to Hue Device Attribute Controllers. Please cancel the configuration dialog and select a Hue device to control."
				errorsDict['showAlertText'] += errorsDict['device'] + "\n\n"
			# If it is a valid device, check everything else.
			elif not brightnessSource:
				isError = True
				errorsDict['brightnessSource'] = "Please specify a Brightness Source."
				errorsDict['showAlertText'] += errorsDict['brightnessSource'] + "\n\n"
			elif brightnessSource == "custom":
				if not brightness:
					isError = True
					errorsDict['brightness'] = "Please specify a brightness level."
					errorsDict['showAlertText'] += errorsDict['brightness'] + "\n\n"
				else:
					try:
						brightness = int(brightness)
						if brightness < 0 or brightness > 100:
							isError = True
							errorsDict['brightness'] = "Brightness levels must be a number between 0 and 100."
							errorsDict['showAlertText'] += errorsDict['brightness'] + "\n\n"
					except ValueError:
						isError = True
						errorsDict['brightness'] = "Brightness levels must be a number between 0 and 100."
						errorsDict['showAlertText'] += errorsDict['brightness'] + "\n\n"
				descString += "set brightness of {} to {}%".format(device.name, brightness)
			elif brightnessSource == "variable":
				if not brightnessVarId:
					isError = True
					errorsDict['brightnessVariable'] = "Please specify a variable to use for brightness level."
					errorsDict['showAlertText'] += errorsDict['brightnessVariable'] + "\n\n"
				else:
					try:
						brightnessVar = indigo.variables[int(brightnessVarId)]
						descString += "set brightness of {} to value in variable{}".format( device.name , brightnessVar.name)
					except IndexError:
						isError = True
						errorsDict['brightnessVariable'] = "The specified variable does not exist in the Indigo database. Please choose a different variable."
						errorsDict['showAlertText'] += errorsDict['brightnessVariable'] + "\n\n"
			elif brightnessSource == "dimmer":
				if not brightnessDevId:
					isError = True
					errorsDict['brightnessDevice'] = "Please specify a dimmer device to use as the source for brightness level."
					errorsDict['showAlertText'] += errorsDict['brightnessDevice'] + "\n\n"
				else:
					try:
						brightnessDev = indigo.devices[int(brightnessDevId)]
						if brightnessDev.id == device.id:
							isError = True
							errorsDict['brightnessDevice'] = "You cannot select the same dimmer as the one for which you're setting the brightness."
							errorsDict['showAlertText'] += errorsDict['brightnessDevice'] + "\n\n"
						else:
							descString += "set brightness of {} to current brightness of \"{}\"".format( device.name , brightnessDev.name)
					except IndexError:
						isError = True
						errorsDict['brightnessDevice'] = "The specified device does not exist in the Indigo database. Please choose a different device."
						errorsDict['showAlertText'] += errorsDict['brightnessDevice'] + "\n\n"

			if not useRateVariable:
				if not rate and rate.__class__ != bool:
					isError = True
					errorsDict['rate'] = "Please enter a Ramp Rate."
					errorsDict['showAlertText'] += errorsDict['rate'] + "\n\n"
				else:
					try:
						rate = round(float(rate), 1)
						if rate < 0 or rate > 540:
							isError = True
							errorsDict['rate'] = "Ramp Rate times must be between 0 and 540 seconds."
							errorsDict['showAlertText'] += errorsDict['rate'] + "\n\n"
					except ValueError:
						isError = True
						errorsDict['rate'] = "Ramp Rates must be between 0 and 540 seconds and cannot contain non-numeric characters."
						errorsDict['showAlertText'] += errorsDict['rate'] + "\n\n"
				descString += " using ramp rate {} sec".format(rate) 
			else:
				if not rateVarId:
					isError = True
					errorsDict['rateVariable'] = "Please select a variable to use for the ramp rate."
					errorsDict['showAlertText'] += errorsDict['rateVariable'] + "\n\n"
				else:
					try:
						rateVar = indigo.variables[int(rateVarId)]
						descString += " using ramp rate in variable \"{}\"".format(rateVar.name)
					except IndexError:
						isError = True
						errorsDict['rateVariable'] = "The specified variable does not exist in the Indigo database. Please choose a different variable."
						errorsDict['showAlertText'] += errorsDict['rateVariable'] + "\n\n"

		### SET RGB LEVELS ###
		elif typeId == "setRGB":
			# Check the RGB values.
			red = valuesDict.get('red', 0)
			if red == "":
				red = 0
				valuesDict['red'] = red
			green = valuesDict.get('green', 0)
			if green == "":
				green = 0
				valuesDict['green'] = green
			blue = valuesDict.get('blue', 0)
			if blue == "":
				blue = 0
				valuesDict['blue'] = blue
			useRateVariable = valuesDict.get('useRateVariable', False)
			rateVariable = valuesDict.get('rateVariable', "")
			rampRate = valuesDict.get('rate', "")

			# First make sure this is a Hue device and not an attribute controller.
			if device.deviceTypeId == "hueAttributeController":
				isError = True
				errorsDict['device'] = "This action cannot be applied to Hue Device Attribute Controllers. Please cancel the configuration dialog and select a Hue device to control."
				errorsDict['showAlertText'] += errorsDict['device'] + "\n\n"
			# If it is a valid device, check everything else.
			# Make sure this device can handle color.
			elif not device.pluginProps.get('SupportsRGB', False):
				isError = True
				errorsDict['device'] = "The \"{}\" device does not support color. Choose a different device.".format(device.name)
				errorsDict['showAlertText'] += errorsDict['device'] + "\n\n"

			# Validate red value.
			try:
				red = int(red)
				if (red < 0) or (red > 255):
					isError = True
					errorsDict['red'] = "Red values must be a whole number between 0 and 255."
					errorsDict['showAlertText'] += errorsDict['red'] + "\n\n"
			except ValueError:
				isError = True
				errorsDict['red'] = "Red values must be a whole number between 0 and 255."
				errorsDict['showAlertText'] += errorsDict['red'] + "\n\n"
			except Exception as e:
				isError = True
				errorsDict['red'] = "Invalid Red value: {}  @line#:{})".format(e,sys.exc_info()[2].tb_lineno)
				errorsDict['showAlertText'] += errorsDict['red'] + "\n\n"

			# Validate green value.
			try:
				green = int(green)
				if (green < 0) or (green > 255):
					isError = True
					errorsDict['green'] = "Green values must be a whole number between 0 and 255."
					errorsDict['showAlertText'] += errorsDict['green'] + "\n\n"
			except ValueError:
				isError = True
				errorsDict['green'] = "Green values must be a whole number between 0 and 255."
				errorsDict['showAlertText'] += errorsDict['green'] + "\n\n"
			except Exception as e:
				isError = True
				errorsDict['green'] = "Invalid Green value: {}  @line#:{})".format(e,sys.exc_info()[2].tb_lineno)
				errorsDict['showAlertText'] += errorsDict['green'] + "\n\n"

			# Validate blue value.
			try:
				blue = int(blue)
				if (blue < 0) or (blue > 255):
					isError = True
					errorsDict['blue'] = "Blue values must be a whole number between 0 and 255."
					errorsDict['showAlertText'] += errorsDict['blue'] + "\n\n"
			except ValueError:
				isError = True
				errorsDict['blue'] = "Blue values must be a whole number between 0 and 255."
				errorsDict['showAlertText'] += errorsDict['blue'] + "\n\n"
			except Exception as e:
				isError = True
				errorsDict['blue'] = "Invalid Blue value: {}  @line#:{})".format(e,sys.exc_info()[2].tb_lineno)
				errorsDict['showAlertText'] += errorsDict['blue'] + "\n\n"

			# Validate Ramp Rate.
			if not useRateVariable:
				# User entered a ramp rate value.
				if len(rampRate) > 0:
					try:
						rampRate = float(rampRate)
						if (rampRate < 0) or (rampRate > 540):
							isError = True
							errorsDict['rate'] = "Ramp Rate must be a number between 0 and 540 seconds and can be in increments of 0.1 seconds."
							errorsDict['showAlertText'] += errorsDict['rate'] + "\n\n"
					except ValueError:
						isError = True
						errorsDict['rate'] = "Ramp Rate must be a number between 0 and 540 seconds and can be in increments of 0.1 seconds."
						errorsDict['showAlertText'] += errorsDict['rate'] + "\n\n"
					except Exception as e:
						isError = True
						errorsDict['rate'] = "Invalid Ramp Rate value: {}  @line#:{})".format(e,sys.exc_info()[2].tb_lineno)
						errorsDict['showAlertText'] += errorsDict['rate'] + "\n\n"
			else:
				# User specified that they'd select a variable as the ramp rate source.
				# Make sure they actually selected one.
				if rateVariable == "":
					isError = True
					errorsDict['rateVariable'] = "No variable was selected. Please select an Indigo variable as the ramp rate source."
					errorsDict['showAlertText'] += errorsDict['rateVariable'] + "\n\n"
				else:
					# Since a variable ID was given, convert it to an integer.
					rateVariable = int(rateVariable)

			if not isError:
				descString += "set hue device:\"{}\"  RGB levels to {}, {}, {}".format(device.name, red, green, blue)
				if useRateVariable :
					descString += " using ramp rate in variable \"{}\".".format(indigo.variables[rateVariable].name)
				else:
					if len(valuesDict.get('rate', "")) > 0:
						descString += " with ramp rate {} sec".format(rampRate)

		### SET HSB ###
		elif typeId == "setHSB":
			# Check the HSB values.
			hue = valuesDict.get('hue', 0)
			if hue == "":
				hue = 0
				valuesDict['hue'] = hue
			saturation = valuesDict.get('saturation', 100)
			if saturation == "":
				saturation = 100
				valuesDict['saturation'] = saturation
			brightnessSource = valuesDict.get('brightnessSource', "custom")
			brightnessVariable = valuesDict.get('brightnessVariable', "")
			brightnessDevice = valuesDict.get('brightnessDevice', "")
			if brightnessSource == "":
				brightnessSource = "custom"
				valuesDict['brightnessSource'] = brightnessSource
			brightness = valuesDict.get('brightness', "")
			if brightness == "":
				brightness = device.states['brightnessLevel']
				valuesDict['brightness'] = brightness
			useRateVariable = valuesDict.get('useRateVariable', False)
			rateVariable = valuesDict.get('rateVariable', "")
			rampRate = valuesDict.get('rate', "")

			# First make sure this is a Hue device and not an attribute controller.
			if device.deviceTypeId == "hueAttributeController":
				isError = True
				errorsDict['device'] = "This action cannot be applied to Hue Device Attribute Controllers. Please cancel the configuration dialog and select a Hue device to control."
				errorsDict['showAlertText'] += errorsDict['device'] + "\n\n"
			# If it is a valid device, check everything else.
			# Make sure this device can handle color.
			elif not device.pluginProps.get('SupportsRGB', False):
				isError = True
				errorsDict['device'] = "The \"{}\" device does not support color. Choose a different device.".format(device.name)
				errorsDict['showAlertText'] += errorsDict['device'] + "\n\n"

			# Validate hue value.
			try:
				hue = int(hue)
				if (hue < 0) or (hue > 360):
					isError = True
					errorsDict['hue'] = "Hue values must be a whole number between 0 and 360 degrees."
					errorsDict['showAlertText'] += errorsDict['hue'] + "\n\n"
			except ValueError:
				isError = True
				errorsDict['hue'] = "Hue values must be a whole number between 0 and 360 degrees."
				errorsDict['showAlertText'] += errorsDict['hue'] + "\n\n"
			except Exception as e:
				isError = True
				errorsDict['hue'] = "Invalid Hue value: {}  @line#:{})".format(e,sys.exc_info()[2].tb_lineno)
				errorsDict['showAlertText'] += errorsDict['hue'] + "\n\n"

			# Validate saturation value.
			try:
				saturation = int(saturation)
				if (saturation < 0) or (saturation > 100):
					isError = True
					errorsDict['saturation'] = "Saturation values must be a whole number between 0 and 100 percent."
					errorsDict['showAlertText'] += errorsDict['saturation'] + "\n\n"
			except ValueError:
				isError = True
				errorsDict['saturation'] = "Saturation values must be a whole number between 0 and 100 percent."
				errorsDict['showAlertText'] += errorsDict['saturation'] + "\n\n"
			except Exception as e:
				isError = True
				errorsDict['saturation'] = "Invalid Saturation value: {}  @line#:{})".format(e,sys.exc_info()[2].tb_lineno)
				errorsDict['showAlertText'] += errorsDict['saturation'] + "\n\n"

			# Validate the brightness value.
			if brightnessSource == "custom":
				try:
					brightness = int(brightness)
					if (brightness < 0) or (brightness > 100):
						isError = True
						errorsDict['brightness'] = "Brightness values must be a whole number between 0 and 100 percent."
						errorsDict['showAlertText'] += errorsDict['brightness'] + "\n\n"
				except ValueError:
					isError = True
					errorsDict['brightness'] = "Brightness values must be a whole number between 0 and 100 percent."
					errorsDict['showAlertText'] += errorsDict['brightness'] + "\n\n"
				except Exception as e:
					isError = True
					errorsDict['brightness'] = "Invalid Brightness value: {}  @line#:{})".format(e,sys.exc_info()[2].tb_lineno)
					errorsDict['showAlertText'] += errorsDict['brightness'] + "\n\n"
			elif brightnessSource == "variable":
				# Make sure the variable selection is valid.
				if brightnessVariable == "":
					isError = True
					errorsDict['brightnessVariable'] = "No source variable selected. Please select an Indigo variable from the list."
					errorsDict['showAlertText'] += errorsDict['brightnessVariable'] + "\n\n"
				else:
					# Since a variable ID was given, convert it to an integer.
					brightnessVariable = int(brightnessVariable)
			elif brightnessSource == "dimmer":
				# Make sure the device selection is valid.
				if brightnessDevice == "":
					isError = True
					errorsDict['brightnessDevice'] = "No source device selected. Please select an Indigo dimmer device from the list."
					errorsDict['showAlertText'] += errorsDict['brightnessDevice'] + "\n\n"
				else:
					# Since a device ID was given, convert it to an integer.
					brightnessDevice = int(brightnessDevice)

			# Validate Ramp Rate.
			if not useRateVariable:
				# User entered a ramp rate value.
				if len(rampRate) > 0:
					try:
						rampRate = float(rampRate)
						if (rampRate < 0) or (rampRate > 540):
							isError = True
							errorsDict['rate'] = "Ramp Rate must be a number between 0 and 540 seconds and can be in increments of 0.1 seconds."
							errorsDict['showAlertText'] += errorsDict['rate'] + "\n\n"
					except ValueError:
						isError = True
						errorsDict['rate'] = "Ramp Rate must be a number between 0 and 540 seconds and can be in increments of 0.1 seconds."
						errorsDict['showAlertText'] += errorsDict['rate'] + "\n\n"
					except Exception as e:
						isError = True
						errorsDict['rate'] = "Invalid Ramp Rate value: {}  @line#:{})".format(e,sys.exc_info()[2].tb_lineno)
						errorsDict['showAlertText'] += errorsDict['rate'] + "\n\n"
			else:
				# User specified that they'd select a variable as the ramp rate source.
				# Make sure they actually selected one.
				if rateVariable == "":
					isError = True
					errorsDict['rateVariable'] = "No variable was selected. Please select an Indigo variable as the ramp rate source."
					errorsDict['showAlertText'] += errorsDict['rateVariable'] + "\n\n"
				else:
					# Since a variable ID was given, convert it to an integer.
					rateVariable = int(rateVariable)

			if not isError:
				descString += "set hue device:\"{}\"  hue to {}, saturation to {}  and brightness to".format(device.name, hue, saturation)
				if brightnessSource == "custom":
					descString += "{}".format(brightness)
				elif brightnessSource == "variable":
					descString += " value in variable \"{}\"".format(indigo.variables[brightnessVariable].name)
				elif brightnessSource == "dimmer":
					descString += " brightness of device \"{}\"".format(indigo.devices[brightnessDevice].name)

				if useRateVariable :
					descString += " using ramp rate in variable \"{}\".".format(indigo.variables[rateVariable].name )
				else:
					if len(valuesDict.get('rate', "")) > 0:
						descString += " with ramp rate {} sec".format(rampRate)

		### SET xyY ###
		elif typeId == "setXYY":
			# Check the xyY values.
			colorX = valuesDict.get('xyy_x', 0.0)
			if colorX == "":
				colorX = 0
				valuesDict['xyy_x'] = colorX
			colorY = valuesDict.get('xyy_y', 0.0)
			if colorY == "":
				colorY = 0
				valuesDict['xyy_y'] = colorY
			brightness = valuesDict.get('xyy_Y', 0)
			if brightness == "":
				brightness = float(device.states['brightnessLevel']) / 100.0
				valuesDict['xyy_Y'] = brightness
			useRateVariable = valuesDict.get('useRateVariable', False)
			rateVariable = valuesDict.get('rateVariable', "")
			rampRate = valuesDict.get('rate', "")

			# First make sure this is a Hue device and not an attribute controller.
			if device.deviceTypeId == "hueAttributeController":
				isError = True
				errorsDict['device'] = "This action cannot be applied to Hue Device Attribute Controllers. Please cancel the configuration dialog and select a Hue device to control."
				errorsDict['showAlertText'] += errorsDict['device'] + "\n\n"
			# If it is a valid device, check everything else.
			# Make sure this device can handle color.
			elif not device.pluginProps.get('SupportsRGB', False):
				isError = True
				errorsDict['device'] = "The \"{}\" device does not support color. Choose a different device.".format(device.name)
				errorsDict['showAlertText'] += errorsDict['device'] + "\n\n"

			# Validate x chromatisity value.
			try:
				colorX = float(colorX)
				if (colorX < 0.0) or (colorX > 1.0):
					isError = True
					errorsDict['xyy_x'] = "x Chromatisety values must be a number between 0 and 1.0."
					errorsDict['showAlertText'] += errorsDict['xyy_x'] + "\n\n"
			except ValueError:
				isError = True
				errorsDict['xyy_x'] = "x Chromatisety values must be a number between 0 and 1.0."
				errorsDict['showAlertText'] += errorsDict['xyy_x'] + "\n\n"
			except Exception as e:
				isError = True
				errorsDict['xyy_x'] = "Invalid x Chromatisety value: {}  @line#:{})".format(e,sys.exc_info()[2].tb_lineno)
				errorsDict['showAlertText'] += errorsDict['xyy_x'] + "\n\n"

			# Validate y chromatisity value.
			try:
				colorY = float(colorY)
				if (colorY < 0) or (colorY > 1):
					isError = True
					errorsDict['xyy_y'] = "y Chromatisety values must be a number between 0 and 1.0."
					errorsDict['showAlertText'] += errorsDict['xyy_y'] + "\n\n"
			except ValueError:
				isError = True
				errorsDict['xyy_y'] = "y Chromatisety values must be a number between 0 and 1.0."
				errorsDict['showAlertText'] += errorsDict['xyy_y'] + "\n\n"
			except Exception as e:
				isError = True
				errorsDict['xyy_y'] = "Invalid y Chromatisety value: {}  @line#:{})".format(e,sys.exc_info()[2].tb_lineno)
				errorsDict['showAlertText'] += errorsDict['xyy_y'] + "\n\n"

			# Validate Y luminosity value.
			try:
				brightness = float(brightness)
				if (brightness < 0) or (brightness > 1):
					isError = True
					errorsDict['xyy_Y'] = "Y Luminosity values must be a number between 0 and 1.0."
					errorsDict['showAlertText'] += errorsDict['xyy_Y'] + "\n\n"
			except ValueError:
				isError = True
				errorsDict['xyy_Y'] = "Y Luminosity values must be a number between 0 and 1.0."
				errorsDict['showAlertText'] += errorsDict['xyy_Y'] + "\n\n"
			except Exception as e:
				isError = True
				errorsDict['xyy_Y'] = "Invalid Y Luminosity value: {}  @line#:{})".format(e,sys.exc_info()[2].tb_lineno)
				errorsDict['showAlertText'] += errorsDict['xyy_Y'] + "\n\n"

			# Validate Ramp Rate.
			if not useRateVariable:
				# User entered a ramp rate value.
				if len(rampRate) > 0:
					try:
						rampRate = float(rampRate)
						if (rampRate < 0) or (rampRate > 540):
							isError = True
							errorsDict['rate'] = "Ramp Rate must be a number between 0 and 540 seconds and can be in increments of 0.1 seconds."
							errorsDict['showAlertText'] += errorsDict['rate'] + "\n\n"
					except ValueError:
						isError = True
						errorsDict['rate'] = "Ramp Rate must be a number between 0 and 540 seconds and can be in increments of 0.1 seconds."
						errorsDict['showAlertText'] += errorsDict['rate'] + "\n\n"
					except Exception as e:
						isError = True
						errorsDict['rate'] = "Invalid Ramp Rate value: {}  @line#:{})".format(e,sys.exc_info()[2].tb_lineno)
						errorsDict['showAlertText'] += errorsDict['rate'] + "\n\n"
			else:
				# User specified that they'd select a variable as the ramp rate source.
				# Make sure they actually selected one.
				if rateVariable == "":
					isError = True
					errorsDict['rateVariable'] = "No variable was selected. Please select an Indigo variable as the ramp rate source."
					errorsDict['showAlertText'] += errorsDict['rateVariable'] + "\n\n"
				else:
					# Since a variable ID was given, convert it to an integer.
					rateVariable = int(rateVariable)

			if not isError:
				descString += "set hue device:\"{}\"  xyY chromatisety to {}, {}, {}".format(device.name, colorX, colorY, brightness)
				if useRateVariable :
					descString += " using ramp rate in variable \"{}\".".format(indigo.variables[rateVariable].name)
				else:
					if len(valuesDict.get('rate', "")) > 0:
						descString += " with ramp rate {} sec".format(rampRate)

		### SET COLOR TEMPERATURE ###
		elif typeId == "setCT":
			# Check the Color Temperature values.
			preset = valuesDict.get('preset', False)
			# The "preset" designation is referred to as a "color recipe" by Phillips.
			if preset == "":
				preset = "relax"	# The "relax" recipe is the first in the list, so use it as default.
				valuesDict['preset'] = preset
			temperatureSource = valuesDict.get('temperatureSource', "custom")
			temperatureVariable = valuesDict.get('temperatureVariable', "")
			if temperatureSource == "":
				temperatureSource = "custom"
				valuesDict['temperatureSource'] = temperatureSource
			temperature = valuesDict.get('temperature', "")
			if temperature == "":
				temperature = 2800
				valuesDict['temperature'] = temperature
			brightnessSource = valuesDict.get('brightnessSource', "custom")
			brightnessVariable = valuesDict.get('brightnessVariable', "")
			brightnessDevice = valuesDict.get('brightnessDevice', "")
			if brightnessSource == "":
				brightnessSource = "custom"
				valuesDict['brightnessSource'] = brightnessSource
			brightness = valuesDict.get('brightness', "")
			if brightness == "":
				brightness = device.states['brightnessLevel']
				valuesDict['brightness'] = brightness
			useRateVariable = valuesDict.get('useRateVariable', False)
			rateVariable = valuesDict.get('rateVariable', "")
			rampRate = valuesDict.get('rate', "")

			# First make sure this is a Hue device and not an attribute controller.
			if device.deviceTypeId == "hueAttributeController":
				isError = True
				errorsDict['device'] = "This action cannot be applied to Hue Device Attribute Controllers. Please cancel the configuration dialog and select a Hue device to control."
				errorsDict['showAlertText'] += errorsDict['device'] + "\n\n"
			# If it is a valid device, check everything else.
			# Make sure this device can handle color temperature changes.
			elif not device.pluginProps.get('SupportsWhiteTemperature', False):
				isError = True
				errorsDict['device'] = "The \"{}\" device does not support variable color temperature. Choose a different device." .format(device.name)
				errorsDict['showAlertText'] += errorsDict['device'] + "\n\n"

			# Validate that a Preset Color Recipe item or Custom was selected.
			if not preset:
				isError = True
				errorsDict['preset'] = "Please select an item from the Preset Color Recipe menu."
				errorsDict['showAlertText'] += errorsDict['preset'] + "\n\n"
			elif preset == "custom":
				# Custom temperature and brightness.
				# Validate the temperature value.
				if temperatureSource == "custom":
					try:
						temperature = int(temperature)
						if (temperature < 2000) or (temperature > 6500):
							isError = True
							errorsDict['temperature'] = "Color Temperature values must be a whole number between 2000 and 6500 Kelvin."
							errorsDict['showAlertText'] += errorsDict['temperature'] + "\n\n"
					except ValueError:
						isError = True
						errorsDict['temperature'] = "Color Temperature values must be a whole number between 2000 and 6500 Kelvin."
						errorsDict['showAlertText'] += errorsDict['temperature'] + "\n\n"
					except Exception as e:
						isError = True
						errorsDict['temperature'] = "Invalid Color Temperature value: {}  @line#:{})".format(e,sys.exc_info()[2].tb_lineno)
						errorsDict['showAlertText'] += errorsDict['temperature'] + "\n\n"
				elif temperatureSource == "variable":
					# Make sure the variable selection is valid.
					if temperatureVariable == "":
						isError = True
						errorsDict['temperatureVariable'] = "No source variable selected. Please select an Indigo variable from the list."
						errorsDict['showAlertText'] += errorsDict['temperatureVariable'] + "\n\n"
					else:
						# Since a variable ID was given, convert it to an integer.
						temperatureVariable = int(temperatureVariable)
				# Validate the brightness value.
				if brightnessSource == "custom":
					try:
						brightness = int(brightness)
						if (brightness < 0) or (brightness > 100):
							isError = True
							errorsDict['brightness'] = "Brightness values must be a whole number between 0 and 100 percent."
							errorsDict['showAlertText'] += errorsDict['brightness'] + "\n\n"
					except ValueError:
						isError = True
						errorsDict['brightness'] = "Brightness values must be a whole number between 0 and 100 percent."
						errorsDict['showAlertText'] += errorsDict['brightness'] + "\n\n"
					except Exception as e:
						isError = True
						errorsDict['brightness'] = "Invalid Brightness value: {}  @line#:{})".format(e,sys.exc_info()[2].tb_lineno)
						errorsDict['showAlertText'] += errorsDict['brightness'] + "\n\n"
				elif brightnessSource == "variable":
					# Make sure the variable selection is valid.
					if brightnessVariable == "":
						isError = True
						errorsDict['brightnessVariable'] = "No source variable selected. Please select an Indigo variable from the list."
						errorsDict['showAlertText'] += errorsDict['brightnessVariable'] + "\n\n"
					else:
						# Since a variable ID was given, convert it to an integer.
						brightnessVariable = int(brightnessVariable)
				elif brightnessSource == "dimmer":
					# Make sure the device selection is valid.
					if brightnessDevice == "":
						isError = True
						errorsDict['brightnessDevice'] = "No source device selected. Please select an Indigo dimmer device from the list."
						errorsDict['showAlertText'] += errorsDict['brightnessDevice'] + "\n\n"
					else:
						# Since a device ID was given, convert it to an integer.
						brightnessDevice = int(brightnessDevice)
			# Validate Ramp Rate.
			if not useRateVariable:
				# User entered a ramp rate value.
				if len(rampRate) > 0:
					try:
						rampRate = float(rampRate)
						if (rampRate < 0) or (rampRate > 540):
							isError = True
							errorsDict['rate'] = "Ramp Rate must be a number between 0 and 540 seconds and can be in increments of 0.1 seconds."
							errorsDict['showAlertText'] += errorsDict['rate'] + "\n\n"
					except ValueError:
						isError = True
						errorsDict['rate'] = "Ramp Rate must be a number between 0 and 540 seconds and can be in increments of 0.1 seconds."
						errorsDict['showAlertText'] += errorsDict['rate'] + "\n\n"
					except Exception as e:
						isError = True
						errorsDict['rate'] = "Invalid Ramp Rate value: {}  @line#:{})".format(e,sys.exc_info()[2].tb_lineno)
						errorsDict['showAlertText'] += errorsDict['rate'] + "\n\n"
			else:
				# User specified that they'd select a variable as the ramp rate source.
				# Make sure they actually selected one.
				if rateVariable == "":
					isError = True
					errorsDict['rateVariable'] = "No variable was selected. Please select an Indigo variable as the ramp rate source."
					errorsDict['showAlertText'] += errorsDict['rateVariable'] + "\n\n"
				else:
					# Since a variable ID was given, convert it to an integer.
					rateVariable = int(rateVariable)

			# If there were no errors...
			if not isError:
				descString += "set hue device:\"{}\" color temperature to".format(device.name)
				if preset != "custom":
					descString += " preset color recipe \"{}\"".format(preset) 
				else:
					if temperatureSource == "custom":
						descString += " custom value {}K".format(temperature)
					elif temperatureSource == "variable":
						descString += " value in variable \"{}\"".format(indigo.variables[temperatureVariable].name)

					if brightnessSource == "custom":
						descString += " at {} % brightness".format(brightness)
					elif brightnessSource == "variable":
						descString += " using brightness value in variable \"{}\"".format(indigo.variables[brightnessVariable].name)
					elif brightnessSource == "dimmer":
						descString += " using brightness of device \"{}\"".format(indigo.devices[brightnessDevice].name)

				if useRateVariable :
					descString += " using ramp rate in variable \"{}\"".format(indigo.variables[rateVariable].name)
				else:
					if len(valuesDict.get('rate', "")) > 0:
						descString += " with ramp rate {} sec".format(rampRate) 

		### EFFECT ###
		elif typeId == "effect":
			# First make sure this is a Hue device and not an attribute controller.
			if device.deviceTypeId == "hueAttributeController":
				isError = True
				errorsDict['device'] = "This action cannot be applied to Hue Device Attribute Controllers. Please cancel the configuration dialog and select a Hue device to control."
				errorsDict['showAlertText'] += errorsDict['device'] + "\n\n"
			# If it is a valid device, check everything else.
			# Make sure this device can handle the color effect.
			elif not device.pluginProps.get('SupportsRGB', False):
				isError = True
				errorsDict['device'] = "The \"{}\" device does not support color effects. Choose a different device.".format(device.name)
				errorsDict['showAlertText'] += errorsDict['device'] + "\n\n"

			# Make sure an effect was specified.
			effect = valuesDict.get('effect', "")
			if not effect:
				isError = True
				errorsDict['effect'] = "No effect setting was selected."
				errorsDict['showAlertText'] += errorsDict['effect'] + "\n\n"
			else:
				descString = "set hue device:\"{}\"  effect to \"{}\"".format(device.name, effect )

		### SAVE PRESET ###
		elif typeId == "savePreset":
			# First make sure this is a Hue device and not an attribute controller.
			if device.deviceTypeId == "hueAttributeController":
				isError = True
				errorsDict['device'] = "This action cannot be applied to Hue Device Attribute Controllers. Please cancel the configuration dialog and select a Hue device to control."
				errorsDict['showAlertText'] += errorsDict['device'] + "\n\n"
			# If it is a valid device, check everything else.
			elif device.deviceTypeId in kLightDeviceTypeIDs:
				if type not in kCompatibleDeviceIDType:
				#if modelId not in kCompatibleDeviceIDs:
					isError = True
					errorsDict['device'] = "The \"{}\" device is not a compatible Hue device. Please choose a different device.".format(device.name)
					errorsDict['showAlertText'] += errorsDict['device'] + "\n\n"

			# Make sure the Preset Name isn't too long.
			if len(valuesDict.get('presetName', "")) > 50:
				isError = True
				errorsDict['presetName'] = "The Preset Name is too long. Please use a name that is no more than 50 characters long."
				errorsDict['showAlertText'] += errorsDict['presetName'] + "\n\n"

			# Make sure a Preset was selected.
			presetId = valuesDict.get('presetId', "")
			if presetId == "":
				isError = True
				errorsDict['presetId'] = "No Preset was selected."
				errorsDict['showAlertText'] += errorsDict['presetId'] + "\n\n"
			else:
				descString = "save hue device:\"{}\" settings to preset {}".format(device.name,presetId)

			# Validate Ramp Rate.
			rampRate = valuesDict.get('rate', "")
			if len(rampRate) > 0:
				try:
					rampRate = float(rampRate)
					if (rampRate < 0) or (rampRate > 540):
						isError = True
						errorsDict['rate'] = "Ramp Rate must be a number between 0 and 540 seconds and can be in increments of 0.1 seconds."
						errorsDict['showAlertText'] += errorsDict['rate'] + "\n\n"
				except ValueError:
					isError = True
					errorsDict['rate'] = "Ramp Rate must be a number between 0 and 540 seconds and can be in increments of 0.1 seconds."
					errorsDict['showAlertText'] += errorsDict['rate'] + "\n\n"
				except Exception as e:
					isError = True
					errorsDict['rate'] = "Invalid Ramp Rate value: {}  @line#:{})".format(e,sys.exc_info()[2].tb_lineno)
					errorsDict['showAlertText'] += errorsDict['rate'] + "\n\n"

		### RECALL PRESET ###
		elif typeId == "recallPreset":
			# First make sure this is a Hue device and not an attribute controller.
			if device.deviceTypeId == "hueAttributeController":
				isError = True
				errorsDict['device'] = "This action cannot be applied to Hue Device Attribute Controllers. Please cancel the configuration dialog and select a Hue device to control."
				errorsDict['showAlertText'] += errorsDict['device'] + "\n\n"
			# Make sure the model is a supported light model and the device is a light (as opposed to a sensor, etc).
			elif device.deviceTypeId not in kLightDeviceTypeIDs and device.deviceTypeId not in kGroupDeviceTypeIDs:
				isError = True
				errorsDict['device'] = "The \"{}\" wrong dev type. Please choose a Hue light or group device.".format(device.name)
				errorsDict['showAlertText'] += errorsDict['device'] + "\n\n"
				self.indiLOG.log(30,"recallPreset(1E)  valuesDict: {}\n  typeId: {}, name:{}; types accepted:{}; {}.".format(valuesDict, device.deviceTypeId, device.name, kLightDeviceTypeIDs, kGroupDeviceTypeIDs))

			# Make sure a Preset was selected.
			presetId = valuesDict.get('presetId', "")
			if presetId == "":
				isError = True
				errorsDict['presetId'] = "No Preset was selected."
				errorsDict['showAlertText'] += errorsDict['presetId'] + "\n\n"
			else:
				# Make sure the preset isn't empty.
				if len(self.pluginPrefs['presets'][int(presetId) - 1][1]) < 1:
					isError = True
					errorsDict['presetId'] = "This Preset is empty. Please choose a Preset with data already saved to it (one with an asterisk (*) next to the number)."
					errorsDict['showAlertText'] += errorsDict['presetId'] + "\n\n"
				else:
					descString = "recall hue device:\"{}\" settings from preset {}".format(device.name, presetId)

			# Validate Ramp Rate.
			rampRate = valuesDict.get('rate', "")
			if len(rampRate) > 0:
				try:
					rampRate = float(rampRate)
					if (rampRate < 0) or (rampRate > 540):
						isError = True
						errorsDict['rate'] = "Ramp Rate must be a number between 0 and 540 seconds and can be in increments of 0.1 seconds."
						errorsDict['showAlertText'] += errorsDict['rate'] + "\n\n"
				except ValueError:
					isError = True
					errorsDict['rate'] = "Ramp Rate must be a number between 0 and 540 seconds and can be in increments of 0.1 seconds."
					errorsDict['showAlertText'] += errorsDict['rate'] + "\n\n"
				except Exception as e:
					isError = True
					errorsDict['rate'] = "Invalid Ramp Rate value: {}  @line#:{})".format(e,sys.exc_info()[2].tb_lineno)
					errorsDict['showAlertText'] += errorsDict['rate'] + "\n\n"

		### CATCH ALL ###
		else:
			isError = True
			errorsDict['presetId'] = "The typeId \"{}\" wasn't recognized.".format(typeId)
			errorsDict['showAlertText'] += errorsDict['presetId'] + "\n\n"

		# Define the description value.
		valuesDict['description'] = descString
		# Return an error if one exists.
		if isError:
			errorsDict['showAlertText'] = errorsDict['showAlertText'].strip()
			return (False, valuesDict, errorsDict)

		return (True, valuesDict)




	# HUB List Generator
	########################################
	def gwListGenerator(self, filter="", valuesDict=None, typeId="", targetId=0):
		# Used in actions and device configuration windows that need a list of sensor devices.
		if self.decideMyLog("EditSetup"): self.indiLOG.log(20,"Starting gwListGeneratorPrefs.\n  filter: {}\n  valuesDict: {}\n  typeId: {}\n  targetId: {}".format(filter, valuesDict, typeId, targetId))

		xList = list()
		availableIPHubs = []
		self.bridgesAvailableSelected = ""
		for bridgeId in self.bridgesAvailable:
			if not self.bridgesAvailable[bridgeId]['linked']:
				found = False 
				for hubNumber in self.ipAddresses:
					if self.ipAddresses[hubNumber] == self.bridgesAvailable[bridgeId]['ipAddress']:
						found = True
				if not found:
					availableIPHubs.append([self.bridgesAvailable[bridgeId]['ipAddress'], bridgeId])
			else:
				found = False 
				for hubNumber in self.ipAddresses:
					if self.ipAddresses[hubNumber] == self.bridgesAvailable[bridgeId]['ipAddress']:
						found = True
				if not found:
					availableIPHubs.append([self.bridgesAvailable[bridgeId]['ipAddress'], bridgeId])
				

		for hubNumber in khubNumbersAvailable:
			if hubNumber in self.ipAddresses and  hubNumber in self.hueConfigDict and "lights" in self.hueConfigDict[hubNumber]:
				if filter == "" or filter in['active', 'notEmpty']:
					xList.append((hubNumber, "{}-{} fully configured and used".format(hubNumber, self.ipAddresses[hubNumber])))
			elif hubNumber in self.ipAddresses and  hubNumber in self.hueConfigDict:
				if filter == "":
					xList.append((hubNumber, "{}-{} configured, not contacted ".format(hubNumber, self.ipAddresses[hubNumber])))
			elif hubNumber in self.ipAddresses:
				if filter == "" or filter == "notEmpty":
					xList.append((hubNumber,  "{}-{} ip# set, not configured yet".format(hubNumber, self.ipAddresses[hubNumber])))
			elif len(availableIPHubs) > 0 and self.isValidIP(availableIPHubs[0][0]):
					xList.append((hubNumber,  "{}  detected, IP#{}, id:{} ".format(hubNumber, availableIPHubs[0][0], availableIPHubs[0][1])) )
					self.bridgesAvailableSelected = availableIPHubs[0][1]
					del availableIPHubs[0]
			else:
				if filter == "":
					xList.append((hubNumber,  "{} empty, can be used manually".format(hubNumber)))

		if self.decideMyLog("EditSetup"): self.indiLOG.log(20,"gwListGenerator: Return hubNumber list is {}".format(xList) )

		return xList



	# set default Preferences Configuration.
	########################################
	def getPrefsConfigUiValues(self):
		valuesDict = indigo.Dict()
		(valuesDict, errorsDict) = super(Plugin, self).getPrefsConfigUiValues()
		try:
			if self.decideMyLog("EditSetup"): self.indiLOG.log(20,'Starting  getPrefsConfigUiValues(self):')
			valuesDict['hubNumber'] 				= "0"
			valuesDict['address'] 					= self.ipAddresses.get('0',"")
			valuesDict['labelHostId'] 				= self.hostIds.get('0',"")
			valuesDict['gwAction'] 					= "keep"
			valuesDict['refreshCallbackMethod'] 	= "refreshPrefs"
			valuesDict['changeGW'] 					= False
			valuesDict['showGwAdd'] 				= False
			valuesDict['showGwMod'] 				= False
			valuesDict['showGwDel'] 				= False
			valuesDict['pairMsg'] 					= ""
			valuesDict['gwModNewIp'] 				= ""
			#valuesDict['maxPresetCount'] 			= self.pluginPrefs.get('maxPresetCount', "30")
			#valuesDict['timeScaleFactor'] 			= self.pluginPrefs.get('timeScaleFactor',"1.0")
			#valuesDict['debugInit'] 				= self.pluginPrefs.get('debugInit',False)
			#valuesDict['debugLoop'] 				= self.pluginPrefs.get('debugLoop',False)
			#valuesDict['debugEditSetup'] 			= self.pluginPrefs.get('debugEditSetup',False)
			#valuesDict['debugReadFromBridge'] 		= self.pluginPrefs.get('debugReadFromBridge',False)
			#valuesDict['debugSendCommandsToBridge']	= self.pluginPrefs.get('debugSendCommandsToBridge',False)
			#valuesDict['debugUpdateIndigoDevices']	= self.pluginPrefs.get('debugUpdateIndigoDevices',False)
			#valuesDict['debugSpecial']				= self.pluginPrefs.get('debugSpecial',False)
			#valuesDict['debugall']					= self.pluginPrefs.get('debugall',False)
		except Exception:
				self.indiLOG.log(30,"", exc_info=True)

		return (valuesDict, errorsDict)



	# set hubNumber etc after button press 
	########################################
	def refreshPrefs(self, valuesDict):
		errorsDict = indigo.Dict()

		try:
			if self.findHueBridgesAreBeingupdated == "updating":
				valuesDict['showbridgesUpdateText'] = "bridges candidates are being updated"
			elif time.time() - self.findHueBridgesNowForce < 20 and time.time() - self.timeWhenNewBridgeRunFinished < 15:
				valuesDict['showbridgesUpdateText'] = "bridges candidates update finished"
			elif time.time() - self.timeWhenNewBridgeRunFinished < 60:
				valuesDict['showbridgesUpdateText'] = "bridges candidates updated last:{}s ago".format(int(time.time()-self.timeWhenNewBridgeRunFinished))
			else:
				valuesDict['showbridgesUpdateText'] = "bridges candidates might need update"



			valuesDict['showGWAction']					= False
			valuesDict['showGwAdd']						= False
			valuesDict['showGwClick']					= False
			valuesDict['showGwClickConfirm']			= False
			valuesDict['showGwMod']						= False
			valuesDict['showGwDel']						= False
			valuesDict['gwModNewIp']					= ""
					
			if  valuesDict['changeGW']:
				valuesDict['showGWAction']					= True

				if valuesDict['gwAction'] == "modify":
					valuesDict['showGwMod']					= True

				elif valuesDict['gwAction'] == "add":
					valuesDict['showGwAdd']					= True
					valuesDict['showGwClickConfirm']		= True
					if time.time() - self.lastGWConfirmClick < 0:
						valuesDict['showGwClick']			= True
						valuesDict['showGwClickConfirm']	= False
					if self.pairedBridgeExec == "success":
						errorsDict['showAlertText'] = "gateway paired successfully, don't forget to <Save>"
						self.pairedBridgeExec = ""
						return valuesDict, errorsDict

				elif valuesDict['gwAction'] == "delete":
					valuesDict['showGwDel']					= True

		except Exception:
				self.indiLOG.log(30,"", exc_info=True)
		return valuesDict




	# delete existing gateway
	########################################
	def confirmGWDel(self, valuesDict):

		isError = False
		errorsDict = indigo.Dict()
		errorsDict['showAlertText'] = ""
		try:
			#self.indiLOG.log(10,"confirmGWMod valuesDict:{}".format(valuesDict))
			self.pairedBridgeExec = ""
			if valuesDict['delGWList'] not in khubNumbersAvailable:
				errorsDict['showAlertText'] = "bridge# not selected"
				return valuesDict, errorsDict

			self.hubNumberSelected = valuesDict['delGWList']

			if self.hubNumberSelected in self.ipAddresses:
				for bridgeId in self.bridgesAvailable:
					if self.ipAddresses[self.hubNumberSelected] == self.bridgesAvailable[bridgeId]['ipAddress']:
						self.bridgesAvailable[bridgeId]['linked'] = False
				del self.ipAddresses[self.hubNumberSelected]

			if self.hubNumberSelected in self.hueConfigDict:
				del self.hueConfigDict[self.hubNumberSelected]

			if self.hubNumberSelected in self.paired:
				del self.paired[self.hubNumberSelected]

			if self.hubNumberSelected in self.hueConfigDict:
				del self.hueConfigDict[self.hubNumberSelected]

			if self.hubNumberSelected in self.notPairedMsg:
				del self.notPairedMsg[self.hubNumberSelected]

			if self.hubNumberSelected != "0":
				self.hubNumberSelected = "0"

			self.printHueData({"whatToPrint":"NoHudevice", "sortBy":""},"")
			errorsDict['showAlertText'] = "bridge deleted from indigo. Dont forget to <Save> at exit"
			valuesDict['gwAction'] = "keep"

			return valuesDict, errorsDict
		except Exception:
				self.indiLOG.log(30,"", exc_info=True)
		valuesDict['gwDelResponse'] = "check logfile"
		errorsDict['showAlertText'] = "check logfile for error message"
		return valuesDict, errorsDict


	# modify existing gateway
	########################################
	def confirmGWMod(self, valuesDict):
		try:
			errorsDict = indigo.Dict()
			errorsDict['showAlertText'] = ""
			self.indiLOG.log(10,"confirmGWMod valuesDict:{}".format(valuesDict))
			if valuesDict['modGWList'] not in khubNumbersAvailable:
				errorsDict['showAlertText'] = "bridge# not selected"
				return valuesDict, errorsDict

			self.hubNumberSelected = valuesDict['modGWList']
			newIpNumber = valuesDict['gwModNewIp']

			if not self.isValidIP(newIpNumber):
				valuesDict['gwModNewIp'] = "not a valid Ip address"
				self.indiLOG.log(10,"confirmGWMod not a valid Ip address")
				errorsDict['showAlertText'] = "Not a valid IP# entered"
				return valuesDict, errorsDict

			if self.hubNumberSelected in self.ipAddresses:
				self.ipAddresses[self.hubNumberSelected] = newIpNumber
				errorsDict['showAlertText'] = "IP# changed successfully, dont forget to <Save> at exit"
				valuesDict['gwAction'] = "keep"
				return valuesDict, errorsDict

			else:
				errorsDict['showAlertText'] = "Not a valid IP# entered"
				return valuesDict, errorsDict

			return valuesDict
		except Exception:
				self.indiLOG.log(30,"", exc_info=True)

		errorsDict['showAlertText'] = "check logfile for error message"
		return valuesDict, errorsDict

	
	# set hubNumber etc after button press 
	########################################
	def selHubNumberGWPair(self, valuesDict):
		try:
			errorsDict = indigo.Dict()
			errorsDict['showAlertText'] = ""
			valuesDict['hostId'] = ""

			if self.decideMyLog("EditSetup"): self.indiLOG.log(20,"selHubNumberGWPair: Values passed:\n{}".format(valuesDict))
			self.hubNumberSelected = valuesDict['hubNumber']
			if self.hubNumberSelected  not in khubNumbersAvailable: 
				if self.decideMyLog("Init"): self.indiLOG.log(10,"selHubNumberGWPair bad hubNumber given {}".format(self.hubNumberSelected ))
				valuesDict['showAlertText'] = "Bridge# wrong"
				return valuesDict, errorsDict

			self.tryAutoCreateTimeWindow = 0
			self.tryAutoCreateValuesDict = dict()
			## option keep / create
			if self.bridgesAvailableSelected == "":
				if self.hubNumberSelected in self.ipAddresses:
					valuesDict['address'] = self.ipAddresses[self.hubNumberSelected]
					self.selHubNumberLast = time.time() + 180
					if self.hubNumberSelected in self.hostIds:
						valuesDict['hostId'] = self.hostIds[self.hubNumberSelected] 
				else:
					valuesDict['address'] = ""
					valuesDict['showAlertText'] = "Enter IP # Manually"
					self.selHubNumberLast = time.time() + 180
			else:
					bridgeId = self.bridgesAvailableSelected
					if self.isValidIP(self.bridgesAvailable[bridgeId]['ipAddress']):
						valuesDict['address'] = self.bridgesAvailable[bridgeId]['ipAddress']
						self.selHubNumberLast = time.time() + 120
						if self.hubNumberSelected in self.hostIds:
							valuesDict['hostId'] = self.hostIds[self.hubNumberSelected] 
						self.tryAutoCreateTimeWindow = time.time() + 60
						self.tryAutoCreateValuesDict = copy.copy(valuesDict)
						self.tryAutoCreateValuesDict['autoSearch'] = True
					else:
						valuesDict['address'] = ""
						valuesDict['showAlertText'] = "Enter IP # Manually"
						self.selHubNumberLast = time.time() + 180

					self.findHueBridgesNow = time.time() + 10
			self.lastGWConfirmClick  = time.time() + 180

			
		except Exception:
				self.indiLOG.log(30,"", exc_info=True)
		return valuesDict

	########################################
	# Hue bridge Pairing Methods
	########################################

	# Start/Restart Pairing with Hue bridge
	########################################
	def restartPairing(self, valuesDict):
		# This method should only be used as a callback method from the
		#   plugin configuration dialog's "Pair Now" button.
		if self.decideMyLog("Init"): self.indiLOG.log(10,"Starting restartPairing.")
		isError = False
		errorsDict = indigo.Dict()
		errorsDict['showAlertText'] = ""
		self.pairedBridgeExec = "starting"

		if "autoSearch" in valuesDict and valuesDict['autoSearch'] == True:
			autoSearch = True
		else:
			autoSearch = False
			self.tryAutoCreateTimeWindow = 0
			self.tryAutoCreateValuesDict = dict()

		if not self.isValidIP(valuesDict['address']):
			self.indiLOG.log(20,"starting restartPairing. not a valid ip address \"{}\".".format(valuesDict['address']))
			errorsDict['showAlertText'] = "ip number is wrong"
			return valuesDict, errorsDict

		if (self.hubNumberSelected not in khubNumbersAvailable)  or ((time.time() - self.selHubNumberLast) > 0): 
			self.indiLOG.log(20,"Starting restartPairing. Bridge not confirmed #{}, type:{}, (cond:{}? ) available bridge slots:{}, time window:{} >0?".format(self.hubNumberSelected, type(self.hubNumberSelected), self.hubNumberSelected  not in khubNumbersAvailable,  khubNumbersAvailable, time.time() - self.selHubNumberLast))
			if not autoSearch: errorsDict['showAlertText'] = "\"Select Bridge\" not confirmed (or last select is expired), click on CONFIRM (again) to select the bridge # you like to add , see log for details"
			return valuesDict, errorsDict

		# If there haven't been any errors so far, try to connect to the Hue bridge to see
		#   if it's actually a Hue bridge.
		try:
			if self.decideMyLog("Init"): self.indiLOG.log(10,"Verifying that a Hue bridge exists at IP address \"{}\".".format(valuesDict['address']))
			command = "http://{}/description.xml".format(valuesDict['address'])
			if self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(10,"Accessing URL: {}".format(command))
			self.setBridgeBusy(self.hubNumberSelected, calledfrom="restartPairing")
			r = requests.get(command, timeout=kTimeout, headers={'Connection':'close'})
			self.resetBridgeBusy(self.hubNumberSelected)
			if self.decideMyLog("ReadFromBridge"): self.indiLOG.log(10,"Got response:\n{}".format(r.content))

			# Quick and dirty check to see if this is a Philips Hue bridge.
			if b"Philips hue bridge" not in r.content:
				# If "Philips hue bridge" doesn't exist in the response, it's not a Hue bridge.
				self.indiLOG.log(20,"No \"Philips hue bridge\" string found in response. This isn't a Hue bridge.")
				if not autoSearch: errorsDict['showAlertText'] = "hue response string not found, not Hue Bridge"
				return valuesDict, errorsDict
			else:
				# This is likely a Hue bridge.
				if self.decideMyLog("Init"): self.indiLOG.log(10,"Verified that this is a Hue bridge.")

		except requests.exceptions.Timeout:
			self.resetBridgeBusy(self.hubNumberSelected)
			self.doErrorLog("Connection to {} timed out after {} seconds.".format(valuesDict['address'], kTimeout))
			if not autoSearch: errorsDict['showAlertText'] = "timeout connecting to bridge"
			return valuesDict, errorsDict

		except requests.exceptions.ConnectionError:
			self.resetBridgeBusy(self.hubNumberSelected)
			self.doErrorLog("Connection to {} failed. There was a connection error.".format(valuesDict['address']))
			isError = True
			if not autoSearch: errorsDict['showAlertText'] = "error connecting to bridge"
			return valuesDict, errorsDict

		except Exception:
			self.resetBridgeBusy(self.hubNumberSelected)
			self.logger.error("", exc_info=True)
			if not autoSearch: errorsDict['showAlertText'] = "general error  connecting to bridge"
			return valuesDict, errorsDict

		# There weren't any errors, so...
		# Request a username/key.
		try:
	
			self.indiLOG.log(20,"Attempting to pair with the Hue bridge at \"{}\".".format(valuesDict['address']))
			requestData = json.dumps({"devicetype": "Indigo Hue Lights"})
			if self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(10,"SEND is {}".format(requestData) )
			command = "http://{}/api".format(valuesDict['address'])
			if self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(10,"SEND is {}, {}".format(command, requestData) )
			self.setBridgeBusy(self.hubNumberSelected, calledfrom="restartPairing-2")
			r = requests.post(command, data=requestData, timeout=kTimeout, headers={'Connection':'close'})
			self.resetBridgeBusy(self.hubNumberSelected)
			responseData = json.loads(r.content)
			if self.decideMyLog("ReadFromBridge"): self.indiLOG.log(10,"Got response {}".format(responseData))

			# We should have a single response item
			if len(responseData) == 1:
				# Get the first item
				firstResponseItem = responseData[0]

				# See if we got an error.
				errorDict = firstResponseItem.get('error', None)
				if errorDict is not None:
					# We got an error.
					errorCode = errorDict.get('type', None)

					if errorCode == 101:
						# Center link button wasn't pressed on bridge yet.
						errorText = self.doErrorLog("Unable to pair with the Hue bridge. Press the center button on the Hue bridge, then click the \"Pair Now\" button.", level=30)
						isError = True
						errorsDict['startPairingButton'] = errorText
						if not autoSearch: errorsDict['showAlertText'] += errorsDict['startPairingButton'] + "\n\n"
						return valuesDict, errorsDict

					else:
						errorText = self.doErrorLog("Error #{} from the Hue bridge. Description: \"{}\".".format(errorCode, errorDict.get('description', "(No Description)")), level=30)
						errorsDict['showAlertText'] += errorText
						return valuesDict, errorsDict

				# See if we got a success response.
				successDict = firstResponseItem.get('success', None)
				if successDict is not None:
					# Pairing was successful.
					self.indiLOG.log(20,"Paired with Hue bridge successfully.")
					# The plugin was paired with the Hue bridge.
					self.paired[self.hubNumberSelected] = True
					self.notPairedMsg[self.hubNumberSelected] = time.time() - 90
					# Get the username provided by the bridge.
					hueUsername = successDict['username']
					if self.decideMyLog("Init"): self.indiLOG.log(10,"Username (a.k.a. key) assigned by Hue bridge to Hue Lights plugin: {}".format(hueUsername))
					# Set the plugin's hostId to the new username.
					self.hostIds[self.hubNumberSelected] = hueUsername
					# Make sure the new username is returned to the config dialog.
					valuesDict['hostId'] = hueUsername
					valuesDict['hostIds'] = json.dumps(self.hostIds)
					self.pluginPrefs['hostIds'] = valuesDict['hostIds']
					self.pluginPrefs['hostId'] = valuesDict['hostId']
					self.ipAddresses[self.hubNumberSelected ] = valuesDict['address']
			else:
				# The Hue bridge is acting weird.  There should have been only 1 response.
				errorText = self.doErrorLog("Invalid response from Hue bridge. Check the IP address and try again.")
				if self.decideMyLog("ReadFromBridge"): self.indiLOG.log(20,"Response from Hue bridge contained {} items.".format(len(responseData)))
				if not autoSearch: errorsDict['showAlertText'] += errorText
				return valuesDict, errorsDict

		except requests.exceptions.Timeout:
			self.resetBridgeBusy(self.hubNumberSelected)
			self.logger.error("Connection to {}  failed,timed out after {} seconds.".format(valuesDict['address'], kTimeout), exc_info=True)
			errorText = "Unable to reach the bridge. Please check the IP address and ensure that the Indigo server and Hue bridge are connected to the network."
			if not autoSearch: errorsDict['showAlertText'] += errorText
			return valuesDict, errorsDict

		except requests.exceptions.ConnectionError:
			self.resetBridgeBusy(self.hubNumberSelected)
			self.logger.error("Connection to ip#:{} There was a connection error".format( valuesDict['address']), exc_info=True)
			errorsDict['startPairingButton'] = "Connection error. Please check the IP address and ensure that the Indigo server and Hue bridge are connected to the network."
			if not autoSearch: errorsDict['showAlertText'] += errorsDict['startPairingButton'] + "\n\n"
			return valuesDict, errorsDict

		except Exception:
			self.resetBridgeBusy(self.hubNumberSelected)
			self.logger.error("Connection to  ip#:{}  failed".format(valuesDict['address']), exc_info=True)
			errorsDict['startPairingButton'] = "Connection error. Please check the IP address and ensure that the Indigo server and Hue bridge are connected to the network."
			if not autoSearch: errorsDict['showAlertText'] += errorsDict['startPairingButton'] + "\n\n"
			return valuesDict, errorsDict

		try:
			if self.decideMyLog("EditSetup"): self.indiLOG.log(20,"validatePrefsConfigUi: Verifying that a Hue bridge exists at IP address \"{}\".".format(valuesDict['address']) )
			command = "http://{}/description.xml".format(valuesDict['address'])
			if self.decideMyLog("EditSetup"): self.indiLOG.log(20,"validatePrefsConfigUi: Accessing URL: {}".format(command))
			self.setBridgeBusy(self.hubNumberSelected, calledfrom="restartPairing-3")
			r = requests.get(command, timeout=kTimeout, headers={'Connection':'close'})
			self.resetBridgeBusy(self.hubNumberSelected)
			if self.decideMyLog("ReadFromBridge"): self.indiLOG.log(10,"validatePrefsConfigUi: Got response:\n{}".format(r.content) )

			# Quick and dirty check to see if this is a Philips Hue bridge.
			if b"Philips hue bridge" not in r.content:
				# If "Philips hue bridge" doesn't exist in the response, it's not a Hue bridge.
				if self.decideMyLog("EditSetup"): self.indiLOG.log(20,"validatePrefsConfigUi: No \"Philips hue bridge\" string found in response. This isn't a Hue bridge.")
				isError = True
				errorsDict['address'] = "This doesn't appear to be a Philips Hue bridge.  Please verify the IP address."
				if not autoSearch: errorsDict['showAlertText'] += errorsDict['address'] + "\n\n"
				return valuesDict, errorsDict

			else:  # ********** This is likely a Hue bridge. ********** 
				self.indiLOG.log(20,"validatePrefsConfigUi: Verified that this is a Hue bridge. Dont forget to <Save> at exit")
				errorsDict['showAlertText'] = "parring done successfully. Dont forget to <Save> at exit"
				valuesDict['addresses'] = json.dumps(self.ipAddresses)
				valuesDict['gwAction'] = "keep"
				self.pluginPrefs['addresses'] = valuesDict['addresses']
				self.lastGWConfirmClick  = 0
				self.tryAutoCreateTimeWindow = 0
				self.tryAutoCreateValuesDict = dict()
				self.pairedBridgeExec = "success"
				self.lastTimeForAll = time.time() - (self.goAllRefresh-25)
				return valuesDict, errorsDict

		except requests.exceptions.Timeout:
			self.resetBridgeBusy(self.hubNumberSelected)
			if self.decideMyLog("EditSetup"): self.indiLOG.log(20,"validatePrefsConfigUi: Connection to {} timed out after {} seconds.".format(valuesDict['address'], kTimeout))
			isError = True
			errorsDict['address'] = "Unable to reach the bridge. Please check the IP address and ensure that the Indigo server and Hue bridge are connected to the network."
			if not autoSearch: errorsDict['showAlertText'] += errorsDict['address'] + "\n\n"
			return valuesDict, errorsDict

		except requests.exceptions.ConnectionError:
			self.resetBridgeBusy(self.hubNumberSelected)
			if self.decideMyLog("EditSetup"): self.indiLOG.log(20,"validatePrefsConfigUi: Connection to {} failed. There was a connection error.".format(valuesDict['address']) )
			isError = True
			errorsDict['address'] = "Connection error. Please check the IP address and ensure that the Indigo server and Hue bridge are connected to the network."
			if not autoSearch: errorsDict['showAlertText'] += errorsDict['address'] + "\n\n"
			return valuesDict, errorsDict

		except Exception:
			self.resetBridgeBusy(self.hubNumberSelected)
			self.indiLOG.log(30,"validatePrefsConfigUi: Connection error", exc_info=True)
			isError = True
			errorsDict['address'] = "Connection error. Please check the IP address and ensure that the Indigo server and Hue bridge are connected to the network."
			if not autoSearch: errorsDict['showAlertText'] += errorsDict['address'] + "\n\n"

		self.resetBridgeBusy(self.hubNumberSelected)
		return valuesDict, errorsDict



	# Validate Preferences Configuration.
	########################################
	def validatePrefsConfigUi(self, valuesDict):
		if self.decideMyLog("EditSetup"): self.indiLOG.log(20,"validatePrefsConfigUi: Values passed:\n{}".format(valuesDict))
		isError = False
		errorsDict = indigo.Dict()
		errorsDict['showAlertText'] = ""

		maxPresetCount = valuesDict.get('maxPresetCount', "")

		self.timeScaleFactor = float(valuesDict['timeScaleFactor'])

		self.searchForStringinFindHueBridge = valuesDict['searchForStringinFindHueBridge']


		self.getDebugLevels(valuesDict)

		if maxPresetCount == "":
			# The field was left blank.
			if self.decideMyLog("EditSetup"): self.indiLOG.log(20,"validatePrefsConfigUi: maxPresetCount was left blank. Setting value to 30.")
			maxPresetCount = "30"
			valuesDict['maxPresetCount'] = maxPresetCount
		else:
			# Make sure this is a valid number.
			try:
				maxPresetCount = int(maxPresetCount)
				if maxPresetCount < 1 or maxPresetCount > 100:
					isError = True
					errorsDict['maxPresetCount'] = "Preset Memories must be a number between 1 and 100."
					errorsDict['showAlertText'] += errorsDict['maxPresetCount'] + "\n\n"
			except ValueError:
				isError = True
				errorsDict['maxPresetCount'] = "The Preset Memories must be a number between 1 and 100."
				errorsDict['showAlertText'] += errorsDict['maxPresetCount'] + "\n\n"
			except Exception as e:
				isError = True
				errorsDict['maxPresetCount'] = "The Preset Memories must be a number between 1 and 100. Error: {}  @line#:{})".format(e,sys.exc_info()[2].tb_lineno)
				errorsDict['showAlertText'] += errorsDict['maxPresetCount'] + "\n\n"


		# Return an error if one exists.
		if isError:
			errorsDict['showAlertText'] = errorsDict['showAlertText'].strip()
			self.findHueBridgesNow = time.time()  +10
			return (False, valuesDict, errorsDict)
		else:
			self.findHueBridgesNow = time.time()  +10
			self.lastTimeForAll = time.time() - (self.goAllRefresh-25)# force rereading hub config in 5 secs, wait for dialog to save 
			return (True, valuesDict)




	# Plugin Configuration Dialog Closed
	########################################
	def closedPrefsConfigUi(self, valuesDict, userCancelled):
		if self.decideMyLog("EditSetup"): self.indiLOG.log(20,"closedPrefsConfigUi: Starting closedPrefsConfigUi.")

		# If the user didn't cancel the changes, take any needed actions as a result of the changes made.
		if not userCancelled:
			# Configuration was saved.

			try: 	self.sendDeviceUpdatesTo	= int(valuesDict['sendDeviceUpdatesTo'])
			except:	self.sendDeviceUpdatesTo	= 20  # in case its is not a number
			valuesDict['sendDeviceUpdatesTo']   = "{}".format(self.sendDeviceUpdatesTo)

			self.logAnyChanges			= valuesDict['logAnyChanges']

			try: 	self.timeScaleFactor	= float(valuesDict['timeScaleFactor'])
			except:	self.timeScaleFactor	= 1.0  # in case its is not a number
			valuesDict['timeScaleFactor']   = "{}".format(self.timeScaleFactor)

			self.pluginPrefs['addresses'] = json.dumps(self.ipAddresses)
			self.pluginPrefs['hostIds'] = json.dumps(self.hostIds)

			# If the number of Preset Memories was changed, add or remove Presets as needed.
			self.maxPresetCount = int(valuesDict.get('maxPresetCount', "30"))
			presets = self.pluginPrefs.get('presets', "")
			presetCount = len(presets)
			if self.decideMyLog("EditSetup"): self.indiLOG.log(20,"closedPrefsConfigUi: pluginPrefs contains {} presets.".format(presetCount))
			# If there are fewer Presets in the prefs than the maxPresetCount, add the reset.
			if presetCount < self.maxPresetCount:
				self.indiLOG.log(20,"Preset Memories number increased to {}.".format(self.maxPresetCount))
				if self.decideMyLog("EditSetup"): self.indiLOG.log(20,"closedPrefsConfigUi: ... Adding {} presets to bring total to {}.".format(self.maxPresetCount - presetCount, self.maxPresetCount))
				for aNumber in range(presetCount + 1,self.maxPresetCount + 1):
					# Add ever how many presets are needed to make a total of the maximum presets allowed.
					# Create a blank sub-list for storing preset name and preset states.
					preset = list()
					# Add the preset name.
					preset.append('Preset {}'.format(aNumber))
					# Add the empty preset states Indigo dictionary
					preset.append(indigo.Dict())
					# Add the sub-list to the empty presets list.
					presets.append(preset)
				# Replace the list of Presets in the prefs with the new list.
				self.pluginPrefs['presets'] = presets
				self.indiLOG.log(20,"... {} Presets added.  There are now {} Presets.".format(self.maxPresetCount - presetCount, self.maxPresetCount))
			# If there are more presets than are allowed by maxPresetCount, remove the extra Presets.
			elif presetCount > self.maxPresetCount:
				if self.decideMyLog("EditSetup"): self.indiLOG.log(20,"closedPrefsConfigUi: ... Deleting the last {} Presets to bring the total to {}.".format(presetCount - self.maxPresetCount, self.maxPresetCount) )
				self.indiLOG.log(30,"WARNING:  You've decreased the number of Preset Memories, so we're deleting the last {} Presets to bring the total to {}.  This cannot be undone.".format(presetCount - self.maxPresetCount, self.maxPresetCount) )
				for aNumber in range(presetCount - 1,self.maxPresetCount - 1,-1):
					# Remove every Preset after the maxPresetCount limit, starting from the last Preset and moving backward up the list of Presets.
					# If this Preset has data in it, log it in the Indigo log before deleting it.
					preset = presets[aNumber]
					presetName = preset[0]
					presetData = preset[1]
					if len(presetData) > 0:
						# Preset has data in it.
						try:
							# Prior to version 1.2.4, this key did not exist in the presets.
							presetRate = self.pluginPrefs['presets'][aNumber][2]
							# Round the saved preset ramp rate to the nearest 10th.
							presetRate = round(presetRate, 1)
						except Exception:
							# Key probably doesn't exist. Proceed as if no rate was saved.
							presetRate = -1
							pass

						# Display the Preset data in the Indigo log.
						logRampRate = "{} sec".format(presetRate)
						if presetRate == -1:
							logRampRate = "(none specified)"
						self.indiLOG.log(20,"... Preset {} ({}) has data. The following data will be deleted:\nRamp Rate: {}\n{}".format(aNumber + 1, presetName, logRampRate, presetData))
					# Now delete the Preset.
					del presets[aNumber]
					self.indiLOG.log(20,"... Preset {} deleted.".format(aNumber + 1) )

				# Replace the list of Presets in the prefs with the new list.
				self.pluginPrefs['presets'] = presets
				if self.decideMyLog("EditSetup"): self.indiLOG.log(20,"closedPrefsConfigUi: pluginPrefs now contains {} Presets.".format(self.maxPresetCount) )
		else:
			self.indiLOG.log(30,"Configuration changes not saved! ie any bridge add/del/mod not saved")
		return 



	# Did Device Communications Properties Change?
	########################################
	#
	# Overriding default method to reduce the number of times a device
	#   automatically recreated by Indigo.
	#
	def didDeviceCommPropertyChange(self, origDev, newDev):
		# Automatically called by plugin host when device properties change.
		# We only want to reload the device if the Hue device associated with it has chnaged.
		# For Hue bulbs and lights...
		if origDev.deviceTypeId in kLightDeviceTypeIDs:
			if origDev.pluginProps['bulbId'] != newDev.pluginProps['bulbId']:
				return True
			return False
		# For Hue groups...
		elif origDev.deviceTypeId in kGroupDeviceTypeIDs:
			if origDev.pluginProps['groupId'] != newDev.pluginProps['groupId']:
				return True
			return False
		# For sensors...
		## changed KW
		elif origDev.deviceTypeId in kMotionSensorTypeIDs+kTemperatureSensorTypeIDs+kLightSensorTypeIDs+kSwitchTypeIDs:
			if origDev.pluginProps['sensorId'] != newDev.pluginProps['sensorId']:
				return True
			return False
		else:
			# This is some device type other than a supported device type, so do the
			#   default action of returning True if anything has changed.
			if origDev.pluginProps != newDev.pluginProps:
				return True
			return False

	# Get Device State List
	########################################
	#
	# Overriding default method to get a dynamically generated device state list
	#    based on the device properties (namely, for lighting type devices, if
	#    it supports color and/or color temperature).
	#
	def getDeviceStateList(self, device):
		# This method is automatically called by the plugin host every time the Indigo server needs
		#    to know anything about the device, so when a trigger or control page is shown and whenever
		#    a list of device states needs to be populated in some UI menu or to trigger an action.
		if self.decideMyLog("Loop"): self.indiLOG.log(10,"Starting getDeviceStateList for the \"{}\" device".format(device.name) )
		# Get the default state list (based on the Devices.xml file in the plugin).
		stateList = indigo.PluginBase.getDeviceStateList(self, device)
		# Only proceed to modify the state list if it isn't empty.
		if stateList is not None:
			# Modify the state list based on device type.
			# -- LightStrips --
			if device.deviceTypeId == "hueLightStrips" and device.configured:
				# Iterate through the default state list and remove states that aren't appropriate
				#    for this specific device's capabilities (based on device properties).
				if self.decideMyLog("Loop"): self.indiLOG.log(10,"Modifying default hueLightStrips Indigo device states to reflect actual states supported by this specific Hue device.")
				item = -10
				while True:
					for item in range (0, len (stateList)):
						stateDict = stateList[item]
						# Remove all color attributes if the device doesn't support any color.
						if not device.pluginProps.get('SupportsColor', False):
							if stateDict['Key'] in ['colorMode', 'colorMode.ui', 'colorTemp', 'colorTemp.ui', 'whiteLevel', 'whiteLevel.ui', 'whiteTemperature', 'whiteTemperature.ui', 'colorRed', 'colorRed.ui', 'colorGreen', 'colorGreen.ui', 'colorBlue', 'colorBlue.ui', 'colorX', 'colorX.ui', 'colorY', 'colorY.ui', 'hue', 'hue.ui', 'saturation', 'saturation.ui', 'redLevel', 'redLevel.ui', 'greenLevel', 'greenLevel.ui', 'blueLevel', 'blueLevel.ui']:
								if self.decideMyLog("Loop"): self.indiLOG.log(10,"\"{}\" does not support any color. Removing the \"{}\" state from the device.".format(device.name, stateDict['Key']) )
								del stateList[item]
								# Break out of the for loop to restart it with the new length of the stateList.
								break

						# Remove RGB color related states.
						if not device.pluginProps.get('SupportsRGB', False):
							if stateDict['Key'] in ['colorRed', 'colorRed.ui', 'colorGreen', 'colorGreen.ui', 'colorBlue', 'colorBlue.ui', 'colorX', 'colorX.ui', 'colorY', 'colorY.ui', 'hue', 'hue.ui', 'saturation', 'saturation.ui', 'redLevel', 'redLevel.ui', 'greenLevel', 'greenLevel.ui', 'blueLevel', 'blueLevel.ui']:
								if self.decideMyLog("Loop"): self.indiLOG.log(10,"\"{}\" does not support RGB color. Removing the \"{}\" state from the device.".format(device.name, stateDict['Key']) )
								del stateList[item]
								# Break out of the for loop to restart it with the new length of the stateList.
								break

						# Remove color temperature related states.
						if not device.pluginProps.get('SupportsWhiteTemperature', False):
							if stateDict['Key'] in ['colorTemp', 'colorTemp.ui', 'whiteLevel', 'whiteLevel.ui', 'whiteTemperature', 'whiteTemperature.ui']:
								if self.decideMyLog("Loop"): self.indiLOG.log(10,"\"{}\" does not support color temperature. Removing the \"{}\" state from the device.".format(device.name, stateDict['Key']) )
								del stateList[item]
								# Break out of the for loop to restart it with the new length of the stateList.
								break

					# If the for loop wasn't broken before all the items were tested, then all states
					#    that should be removed have been and we can break out of the while loop.
					if item == len (stateList) - 1:
						break

			# The below commented out lines are an example of how to add states if needed.
			## if SomeOtherDeviceCondition:
				## someNumState = self.getDeviceStateDictForNumberType("someNumState", "Some Level Label", "Some Level Label")
				## someStringState = self.getDeviceStateDictForStringType("someStringState", "Some Level Label", "Some Level Label")
				## someOnOffBoolState = self.getDeviceStateDictForBoolOnOffType("someOnOffBoolState", "Some Level Label", "Some Level Label")
				## someYesNoBoolState = self.getDeviceStateDictForBoolYesNoType("someYesNoBoolState", "Some Level Label", "Some Level Label")
				## someOneZeroBoolState = self.getDeviceStateDictForBoolOneZeroType("someOneZeroBoolState", "Some Level Label", "Some Level Label")
				## someTrueFalseBoolState = self.getDeviceStateDictForBoolTrueFalseType("someTrueFalseBoolState", "Some Level Label", "Some Level Label")
				## stateList.append(someNumState)
				## stateList.append(someStringState)
				## stateList.append(someOnOffBoolState)
				## stateList.append(someYesNoBoolState)
				## stateList.append(someOneZeroBoolState)
				## stateList.append(someTrueFalseBoolState)

		# Return the updated state list.
		return stateList


	########################################
	# Indigo Control Methods
	########################################

	# Dimmer/Relay Control Actions
	########################################
	def actionControlDimmerRelay(self, action, device):
		try:
			if self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(10,"Starting actionControlDimmerRelay for device {}. action: {}\n\ndevice: {}".format(device.name, action, device))
		except Exception:
				self.indiLOG.log(30,"Starting actionControlDimmerRelay for device {}. (Unable to display action or device data".format(device.name), exc_info=True)

		# Get the current brightness (if it's not an on/off only device) and on/off state of the device.
		if device.deviceTypeId != "hueOnOffDevice":
			currentBrightness = device.states['brightnessLevel']

		currentOnState = device.states['onOffState']
		# Get key variables
		command = action.deviceAction

		logChanges =  (self.pluginPrefs['logAnyChanges'] == "yes")   or   self.trackSpecificDevice == device.id   or   (self.pluginPrefs['logAnyChanges'] == "leaveToDevice" and device.pluginProps.get('logChanges', True)) 
		if self.trackSpecificDevice == device.id:	sendLog = 20
		else: 										sendLog = self.sendDeviceUpdatesTo
		#self.indiLOG.log(20,"action: {}".format(command))

		bulbId = device.pluginProps.get('bulbId', None)
		
		# Act based on the type of device.
		#
		# -- Hue Bulbs --
		#
		if device.deviceTypeId == "hueBulb":
			hubNumber, ipAddress, hostId, paired = self.getIdsFromDevice(device)
			if not paired: return 
			if self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(10,"Command is {}, Bulb is {}".format(command, bulbId))

			##### TURN ON #####
			if command == indigo.kDeviceAction.TurnOn:
				try:
					if self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(10,"device on:\n{}".format(action))
				except Exception:
					self.indiLOG.log(30,"device on: Unable to display action data", exc_info=True)
				# Turn it on.
				self.doOnOff(device, True)

			##### TURN OFF #####
			elif command == indigo.kDeviceAction.TurnOff:
				try:
					if self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(10,"device off:\n{}".format(action))
				except Exception:
					self.indiLOG.log(30,"device off: Unable to display action data", exc_info=True)
				# Turn it off by setting the brightness to minimum.
				self.doOnOff(device, False)

			##### TOGGLE #####
			elif command == indigo.kDeviceAction.Toggle:
				try:
					if self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(10,"device toggle:\n{}".format(action) )
				except Exception:
					self.indiLOG.log(30,"device toggle: Unable to display action data", exc_info=True)
				if currentOnState :
					# It's on. Turn it off.
					self.doOnOff(device, False)
				else:
					# It's off. Turn it on.
					self.doOnOff(device, True)

			##### SET BRIGHTNESS #####
			elif command == indigo.kDeviceAction.SetBrightness:
				try:
					if self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(10,"device set brightness:\n{}".format(action) )
				except Exception:
					self.indiLOG.log(30,"device set brightness: Unable to display action data", exc_info=True)
				brightnessLevel = int(round(action.actionValue * 255.0 / 100.0))
				# Save the new brightness level into the device properties.
				tempProps = device.pluginProps
				tempProps['savedBrightness'] = brightnessLevel
				self.updateDeviceProps(device, tempProps)
				# Set the new brightness level on the bulb.
				self.doBrightness(device, brightnessLevel)

			##### BRIGHTEN BY #####
			elif command == indigo.kDeviceAction.BrightenBy:
				try:
					if self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(10,"device increase brightness by:\n{}".format(action) )
				except Exception:
					self.indiLOG.log(30,"device increase brightness by: Unable to display action data", exc_info=True)
				brightnessLevel = currentBrightness + action.actionValue
				if brightnessLevel > 100:
					brightnessLevel = 100
				# Save the new brightness level into the device properties.
				tempProps = device.pluginProps
				tempProps['savedBrightness'] = int(round(brightnessLevel * 255.0 / 100.0))
				self.updateDeviceProps(device, tempProps)
				# Set the new brightness level on the bulb.
				self.doBrightness(device, int(round(brightnessLevel * 255.0 / 100.0)))

			##### DIM BY #####
			elif command == indigo.kDeviceAction.DimBy:
				try:
					if self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(10,"device decrease brightness by:\n{}".format(action) )
				except Exception:
					self.indiLOG.log(30,"device decrease brightness: Unable to display action data", exc_info=True)
				brightnessLevel = currentBrightness - action.actionValue
				if brightnessLevel < 0:
					brightnessLevel = 0
				# Save the new brightness level into the device properties.
				tempProps = device.pluginProps
				tempProps['savedBrightness'] = int(round(brightnessLevel * 255.0 / 100.0))
				self.updateDeviceProps(device, tempProps)
				# Set the new brightness level on the bulb.
				self.doBrightness(device, int(round(brightnessLevel * 255.0 / 100.0)))

			##### SET COLOR LEVELS #####
			elif command == indigo.kDimmerRelayAction.SetColorLevels:
				try:
					if self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(10,"device request status:\n{}".format(action))
				except Exception:
					self.indiLOG.log(30,"device request status: Unable to display action data", exc_info=True)

				actionColorVals = action.actionValue

				# Construct a list of channel keys that are possible for what this device
				# supports. It may not support RGB or may not support white levels, for
				# example, depending on how the device's properties (SupportsColor, SupportsRGB,
				# SupportsWhite, SupportsTwoWhiteLevels, SupportsWhiteTemperature) have
				# been specified.
				channelKeys = []
				if device.supportsRGB:
					channelKeys.extend(['redLevel', 'greenLevel', 'blueLevel'])
				if device.supportsWhiteTemperature:
					channelKeys.extend(['whiteTemperature', 'whiteLevel'])
				redLevel = 0
				greenLevel = 0
				blueLevel = 0
				whiteLevel = 0
				colorTemp = 0

				# Enumerate through the possible color channels and extract each
				# value from the actionValue (actionColorVals).
				for channel in channelKeys:
					if channel in actionColorVals:
						channelValue = float(actionColorVals[channel])
						channelValueByte = int(round(255.0 * (channelValue / 100.0)))

						if channel in device.states:
							if channel == "redLevel":
								redLevel = channelValueByte
							elif channel == "greenLevel":
								greenLevel = channelValueByte
							elif channel == "blueLevel":
								blueLevel = channelValueByte
							elif channel == "whiteLevel":
								whiteLevel = channelValueByte
							elif channel == "whiteTemperature":
								# The Indigo 7 interface allows users to select color temperature
								#   values over 6500 and (with Indigo 7.0) below 2000. Correct
								#   out of range values here.
								# The "brightness" variable contains the color temperature value in this case.
								if channelValue > 6500.0:
									channelValue = 6500.0
								if channelValue < 2000.0:
									channelValue = 2000.0
								colorTemp = channelValue
				if self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(10,"actionControlDimmerRelay: Detected color change values of redLevel: {}, greenLevel: {}, blueLevel: {}, whiteLevel: {}, whiteTemperature: {}.".format(redLevel, greenLevel, blueLevel, whiteLevel, colorTemp))
				# The "Set RGBW Levels" action in Indigo 7.0 can have Red, Green, Blue and White levels, as well as
				#   White Temperature for devices that support both RGB and White levels (even if the device doesn't
				#   support simultaneous RGB and W settings).  We have to, therefor, make assumptions based on which
				#   keys are passed and what values are in those keys.
				#
				# Start with whiteTemperature.  If it was the only key passed, the user is making changes to the
				#   light via the Indigo UI.
				if actionColorVals.get('whiteTemperature', None) is not None:
					if self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(10,"actionControlDimmerRelay: whiteTemperature is not empty.")
					if actionColorVals.get('whiteLevel', None) is None and actionColorVals.get('redLevel', None) is None and actionColorVals.get('greenLevel', None) is None and actionColorVals.get('blueLevel', None) is None:
						if self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(10,"actionControlDimmerRelay: red, green, blue and white levels are all empty")
						# Since the whiteLevel was not sent, use the existing brightness as the whiteLevel.
						self.doColorTemperature(device, colorTemp, int(round(currentBrightness * 255.0 / 100.0)))
					# If both whiteTemperature and whiteLevel keys were sent at the same time, the Indigo Set RGBW
					#    Levels action is being used, in which case, we still want to use the color temperature method,
					#    but use the whiteLevel as the brightness instead of the current brightness if it's over zero.
					elif actionColorVals.get('whiteLevel', None) is not None and float(actionColorVals.get('whiteLevel')) > 0:
						if self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(10,"actionControlDimmerRelay: whiteLevel is not empty and is greater than zero")
						self.doColorTemperature(device, colorTemp, whiteLevel)
					# Otherwise, use RGB to set the color of the light.
					else:
						if self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(10,"actionControlDimmerRelay: using RGB to change device color.")
						self.doRGB(device, redLevel, greenLevel, blueLevel)
				# Now see if we're only being sent whiteLevel.  If so, the White level slider in the Indigo UI is being
				#   used.  Treat the white level like an inverse saturation slider (100 = zero saturation).
				elif actionColorVals.get('whiteLevel', None) is not None and actionColorVals.get('redLevel', None) is None and actionColorVals.get('greenLevel', None) is None and actionColorVals.get('blueLevel', None) is None:
					if self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(10,"actionControlDimmerRelay: whiteLevel is not empty, but red, green and blue levels are.")
					newSaturation = 255 - whiteLevel
					if newSaturation < 0:
						newSaturation = 0
					self.doHSB(device, device.states['hue'], newSaturation, int(round(currentBrightness * 255.0 / 100.0)))
				# If we're not changing color temperature or saturation (white level), use RGB.
				else:
					if self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(10,"actionControlDimmerRelay: using RGB to change device color.")
					self.doRGB(device, redLevel, greenLevel, blueLevel)

			##### REQUEST STATUS #####
			elif command == indigo.kDeviceAction.RequestStatus:
				try:
					if self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(10,"device request status:\n{}".format(action) )
				except Exception:
					self.indiLOG.log(30,"device request status: Unable to display action data ", exc_info=True)
				# Log the new brightness.
				self.indiLOG.log(20,"Sent Hue Lights  \"{}\" status request (received: {})".format( device.name, device.states['brightnessLevel']))

			#### CATCH ALL #####
			else:
				self.indiLOG.log(20,"Unhandled command \"{}\"".format(command))
		#
		# -- Hue Ambiance --
		#
		if device.deviceTypeId == "hueAmbiance":
			hubNumber, ipAddress, hostId, paired = self.getIdsFromDevice(device)
			if not paired: return 
			if self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(10,"Command is {}, Bulb is {}".format(command, bulbId))

			##### TURN ON #####
			if command == indigo.kDeviceAction.TurnOn:
				try:
					if self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(10,"device on:\n{}".format(action) )
				except Exception:
					self.indiLOG.log(30,"device on: Unable to display action data", exc_info=True)
				# Turn it on.
				self.doOnOff(device, True)

			##### TURN OFF #####
			elif command == indigo.kDeviceAction.TurnOff:
				try:
					if self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(10,"device off:\n{}".format(action) )
				except Exception:
					self.indiLOG.log(30,"device off: Unable to display action data", exc_info=True)
				# Turn it off by setting the brightness to minimum.
				self.doOnOff(device, False)

			##### TOGGLE #####
			elif command == indigo.kDeviceAction.Toggle:
				try:
					if self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(10,"device toggle:\n{}".format(action) )
				except Exception:
					self.indiLOG.log(30,"device toggle: Unable to display action data", exc_info=True)
				if currentOnState :
					# It's on. Turn it off.
					self.doOnOff(device, False)
				else:
					# It's off. Turn it on.
					self.doOnOff(device, True)

			##### SET BRIGHTNESS #####
			elif command == indigo.kDeviceAction.SetBrightness:
				try:
					if self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(10,"device set brightness:\n{}".format(action) )
				except Exception:
					self.indiLOG.log(30,"device set brightness: Unable to display action data", exc_info=True)
				brightnessLevel = int(round(action.actionValue * 255.0 / 100.0))
				# Save the new brightness level into the device properties.
				tempProps = device.pluginProps
				tempProps['savedBrightness'] = brightnessLevel
				self.updateDeviceProps(device, tempProps)
				# Set the new brightness level on the bulb.
				self.doBrightness(device, brightnessLevel)

			##### BRIGHTEN BY #####
			elif command == indigo.kDeviceAction.BrightenBy:
				try:
					if self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(10,"device increase brightness by:\n{}".format(action) )
				except Exception:
					self.indiLOG.log(30,"device increase brightness by: Unable to display action data", exc_info=True)
				brightnessLevel = currentBrightness + action.actionValue
				if brightnessLevel > 100:
					brightnessLevel = 100
				# Save the new brightness level into the device properties.
				tempProps = device.pluginProps
				tempProps['savedBrightness'] = int(round(brightnessLevel * 255.0 / 100.0))
				self.updateDeviceProps(device, tempProps)
				# Set the new brightness level on the bulb.
				self.doBrightness(device, int(round(brightnessLevel * 255.0 / 100.0)))

			##### DIM BY #####
			elif command == indigo.kDeviceAction.DimBy:
				try:
					if self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(10,"device decrease brightness by:\n{}".format(action) )
				except Exception:
					self.indiLOG.log(30,"device decrease brightness by: Unable to display action data", exc_info=True)
				brightnessLevel = currentBrightness - action.actionValue
				if brightnessLevel < 0:
					brightnessLevel = 0
				# Save the new brightness level into the device properties.
				tempProps = device.pluginProps
				tempProps['savedBrightness'] = int(round(brightnessLevel * 255.0 / 100.0))
				self.updateDeviceProps(device, tempProps)
				# Set the new brightness level on the bulb.
				self.doBrightness(device, int(round(brightnessLevel * 255.0 / 100.0)))

			##### SET COLOR LEVELS #####
			elif command == indigo.kDimmerRelayAction.SetColorLevels:
				try:
					if self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(10,"device request status:\n{}".format(action) )
				except Exception:
					self.indiLOG.log(30,"device request status: Unable to display action data", exc_info=True)

				actionColorVals = action.actionValue

				# Construct a list of channel keys that are possible for what this device
				# supports. It may not support RGB or may not support white levels, for
				# example, depending on how the device's properties (SupportsColor, SupportsRGB,
				# SupportsWhite, SupportsTwoWhiteLevels, SupportsWhiteTemperature) have
				# been specified.
				channelKeys = []
				if device.supportsRGB:
					channelKeys.extend(['redLevel', 'greenLevel', 'blueLevel'])
				if device.supportsWhiteTemperature:
					channelKeys.extend(['whiteTemperature', 'whiteLevel'])
				redLevel = 0
				greenLevel = 0
				blueLevel = 0
				whiteLevel = 0
				colorTemp = 0

				# Enumerate through the possible color channels and extract each
				# value from the actionValue (actionColorVals).
				for channel in channelKeys:
					if channel in actionColorVals:
						channelValue = float(actionColorVals[channel])
						channelValueByte = int(round(255.0 * (channelValue / 100.0)))

						if channel in device.states:
							if channel == "redLevel":
								redLevel = channelValueByte
							elif channel == "greenLevel":
								greenLevel = channelValueByte
							elif channel == "blueLevel":
								blueLevel = channelValueByte
							elif channel == "whiteLevel":
								whiteLevel = channelValueByte
							elif channel == "whiteTemperature":
								# The Indigo 7 interface allows users to select color temperature
								#   values over 6500 and (with Indigo 7.0) below 2000. Correct
								#   out of range values here.
								# The "brightness" variable contains the color temperature value in this case.
								if channelValue > 6500.0:
									channelValue = 6500.0
								if channelValue < 2000.0:
									channelValue = 2000.0
								colorTemp = channelValue
				if self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(10,"actionControlDimmerRelay: Detected color change values of redLevel: {}, greenLevel: {}, blueLevel: {}, whiteLevel: {}, whiteTemperature: {}.".format(redLevel, greenLevel, blueLevel, whiteLevel, colorTemp))
				# The "Set RGBW Levels" action in Indigo 7.0 can have Red, Green, Blue and White levels, as well as
				#   White Temperature for devices that support both RGB and White levels (even if the device doesn't
				#   support simultaneous RGB and W settings).  We have to, therefor, make assumptions based on which
				#   keys are passed and what values are in those keys.
				#
				# Start with whiteTemperature.  If it was the only key passed, the user is making changes to the
				#   light via the Indigo UI.
				if actionColorVals.get('whiteTemperature', None) is not None:
					if self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(10,"actionControlDimmerRelay: whiteTemperature is not empty.")
					if actionColorVals.get('whiteLevel', None) is None:
						if self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(10,"actionControlDimmerRelay: white level is empty")
						# Since the whiteLevel was not sent, use the existing brightness as the whiteLevel.
						self.doColorTemperature(device, colorTemp, int(round(currentBrightness * 255.0 / 100.0)))
					# If both whiteTemperature and whiteLevel keys were sent at the same time, it must be a Python
					#    script call, in which case, we still want to use the color temperature method, but use
					#    the whiteLevel as the brightness instead of the current brightness if it's over zero.
					else:
						if float(actionColorVals.get('whiteLevel', 0)) > 0:
							if self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(10,"actionControlDimmerRelay: whiteLevel is not empty and is greater than zero.")
							self.doColorTemperature(device, colorTemp, whiteLevel)
						else:
							# A whiteLevel of 0 (or lower) is the same as a brightness of 0. Turn off the light.
							if self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(10,"actionControlDimmerRelay: whiteLevel is not empty but is equal to zero.")
							self.doOnOff(device, False)
				# Now see if we're only being sent whiteLevel.  If so, the White level slider in the Indigo UI is being
				#   used.  Treat the white level like the brightness level for ambiance lights.
				elif actionColorVals.get('whiteLevel', None) is not None:
					if self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(10,"actionControlDimmerRelay: whiteTemperature is empty but whiteLevel is not empty.")
					# Save the new brightness level into the device properties.
					tempProps = device.pluginProps
					tempProps['savedBrightness'] = int(round(actionColorVals.get('whiteLevel', 0) * 255.0 / 100.0))
					self.updateDeviceProps(device, tempProps)
					# Set the new brightness level on the bulb.
					self.doBrightness(device, int(round(actionColorVals.get('whiteLevel', 0) * 255.0 / 100.0)))

			##### REQUEST STATUS #####
			elif command == indigo.kDeviceAction.RequestStatus:
				try:
					if self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(10,"device request status:\n{}".format(action) )
				except Exception:
					self.indiLOG.log(30,"device request status: Unable to display action data", exc_info=True)
				# Log the new brightness.
				if logChanges: self.indiLOG.log(sendLog,"Sent Hue Lights  \"{}\" status request (received: {})".format( device.name, device.states['brightnessLevel']))

			#### CATCH ALL #####
			else:
				self.indiLOG.log(20,"Unhandled command \"{}\"".format(command))

		#
		# -- Light Strips --
		#
		elif device.deviceTypeId == "hueLightStrips":
			hubNumber, ipAddress, hostId, paired = self.getIdsFromDevice(device)
			if not paired: return 
			if self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(10,"Command is {}, Light Strip device is {}".format(command, bulbId))

			##### TURN ON #####
			if command == indigo.kDeviceAction.TurnOn:
				try:
					if self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(10,"device on:\n{}".format(action) )
				except Exception:
					self.indiLOG.log(30,"device on: Unable to display action data", exc_info=True)
				# Turn it on.
				self.doOnOff(device, True)

			##### TURN OFF #####
			elif command == indigo.kDeviceAction.TurnOff:
				try:
					if self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(10,"device off:\n{}".format(action) )
				except Exception:
					self.indiLOG.log(30,"device off: Unable to display action data", exc_info=True)
				# Turn it off by setting theSendCommandsToBridgebrightness to minimum.
				self.doOnOff(device, False)

			##### TOGGLE #####
			elif command == indigo.kDeviceAction.Toggle:
				try:
					if self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(10,"device toggle:\n{}".format(action) )
				except Exception:
					self.indiLOG.log(30,"device toggle: Unable to display action data", exc_info=True)
				if currentOnState :
					# It's on. Turn it off.
					self.doOnOff(device, False)
				else:
					# It's off. Turn it on.
					self.doOnOff(device, True)

			##### SET BRIGHTNESS #####
			elif command == indigo.kDeviceAction.SetBrightness:
				try:
					if self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(10,"device set brightness:\n{}".format(action) )
				except Exception:
					self.indiLOG.log(30,"device set brightness: Unable to display action data", exc_info=True)
				brightnessLevel = int(round(action.actionValue * 255.0 / 100.0))
				# Save the new brightness level into the device properties.
				tempProps = device.pluginProps
				tempProps['savedBrightness'] = brightnessLevel
				self.updateDeviceProps(device, tempProps)
				# Set the new brightness level on the bulb.
				self.doBrightness(device, brightnessLevel)

			##### BRIGHTEN BY #####
			elif command == indigo.kDeviceAction.BrightenBy:
				try:
					if self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(10,"device increase brightness by:\n{}".format(action) )
				except Exception:
					self.indiLOG.log(30,"device increase brightness by: Unable to display action data", exc_info=True)
				brightnessLevel = currentBrightness + action.actionValue
				if brightnessLevel > 100:
					brightnessLevel = 100
				# Save the new brightness level into the device properties.
				tempProps = device.pluginProps
				tempProps['savedBrightness'] = int(round(brightnessLevel * 255.0 / 100.0))
				self.updateDeviceProps(device, tempProps)
				# Set the new brightness level on the bulb.
				self.doBrightness(device, int(round(brightnessLevel * 255.0 / 100.0)))

			##### DIM BY #####
			elif command == indigo.kDeviceAction.DimBy:
				try:
					if self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(10,"device decrease brightness by:\n{}".format(action) )
				except Exception:
					self.indiLOG.log(30,"device decrease brightness by: Unable to display action data", exc_info=True)
				brightnessLevel = currentBrightness - action.actionValue
				if brightnessLevel < 0:
					brightnessLevel = 0
				# Save the new brightness level into the device properties.
				tempProps = device.pluginProps
				tempProps['savedBrightness'] = int(round(brightnessLevel * 255.0 / 100.0))
				self.updateDeviceProps(device, tempProps)
				# Set the new brightness level on the device.
				self.doBrightness(device, int(round(brightnessLevel * 255.0 / 100.0)))

			##### SET COLOR LEVELS #####
			elif command == indigo.kDimmerRelayAction.SetColorLevels:
				try:
					if self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(10,"device request status:\n{}".format(action) )
				except Exception:
					self.indiLOG.log(30,"device request status: Unable to display action data", exc_info=True)

				actionColorVals = action.actionValue

				# Construct a list of channel keys that are possible for what this device
				# supports. It may not support RGB or may not support white levels, for
				# example, depending on how the device's properties (SupportsColor, SupportsRGB,
				# SupportsWhite, SupportsTwoWhiteLevels, SupportsWhiteTemperature) have
				# been specified.
				channelKeys = []
				if device.supportsRGB:
					channelKeys.extend(['redLevel', 'greenLevel', 'blueLevel'])
				if device.supportsWhiteTemperature:
					channelKeys.extend(['whiteTemperature', 'whiteLevel'])
				redLevel = 0
				greenLevel = 0
				blueLevel = 0
				whiteLevel = 0
				colorTemp = 0

				# Enumerate through the possible color channels and extract each
				# value from the actionValue (actionColorVals).
				for channel in channelKeys:
					if channel in actionColorVals:
						channelValue = float(actionColorVals[channel])
						channelValueByte = int(round(channelValue * 255.0 / 100.0))

						if channel in device.states:
							if channel == "redLevel":
								redLevel = channelValueByte
							elif channel == "greenLevel":
								greenLevel = channelValueByte
							elif channel == "blueLevel":
								blueLevel = channelValueByte
							elif channel == "whiteLevel":
								whiteLevel = channelValueByte
							elif channel == "whiteTemperature":
								# The Indigo 7 interface allows users to select color temperature
								#   values over 6500 and (with Indigo 7.0) below 2000. Correct
								#   out of range values here.
								# The "brightness" variable contains the color temperature value in this case.
								if channelValue > 6500.0:
									channelValue = 6500.0
								if channelValue < 2000.0:
									channelValue = 2000.0
								colorTemp = channelValue
				if self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(10,"actionControlDimmerRelay: Detected color change values of redLevel: {}, greenLevel: {}, blueLevel: {}, whiteLevel: {}, whiteTemperature: {}.".format(redLevel, greenLevel, blueLevel, whiteLevel, colorTemp))
				# The "Set RGBW Levels" action in Indigo 7.0 can have Red, Green, Blue and White levels, as well as
				#   White Temperature for devices that support both RGB and White levels (even if the device doesn't
				#   support simultaneous RGB and W settings).  We have to, therefor, make assumptions based on which
				#   keys are passed and what values are in those keys.
				#
				# Start with whiteTemperature.  If it was the only key passed, the user is making changes to the
				#   light via the Indigo UI.
				if actionColorVals.get('whiteTemperature', None) is not None:
					self.indiLOG.log(20,"actionControlDimmerRelay: whiteTemperature is not empty.")
					if actionColorVals.get('whiteLevel', None) is None and actionColorVals.get('redLevel', None) is None and actionColorVals.get('greenLevel', None) is None and actionColorVals.get('blueLevel', None) is None:
						self.indiLOG.log(20,"actionControlDimmerRelay: red, green, blue and white levels are all empty")
						# Since the whiteLevel was not sent, use the existing brightness as the whiteLevel.
						if device.supportsWhiteTemperature:
							self.doColorTemperature(device, colorTemp, int(round(currentBrightness * 255.0 / 100.0)))
						else:
							self.doErrorLog("The \"{}\" device does not support color temperature. The requested change was not applied.".format(device.name))
					# If both whiteTemperature and whiteLevel keys were sent at the same time, the Indigo Set RGBW
					#    Levels action is being used, in which case, we still want to use the color temperature method,
					#    but use the whiteLevel as the brightness instead of the current brightness if it's over zero.
					elif actionColorVals.get('whiteLevel', None) is not None and float(actionColorVals.get('whiteLevel')) > 0:
						self.indiLOG.log(20,"actionControlDimmerRelay: whiteLevel is not empty and is greater than zero")
						if device.supportsWhiteTemperature:
							self.doColorTemperature(device, colorTemp, whiteLevel)
						else:
							self.doErrorLog("The \"{}\" device does not support color temperature. The requested change was not applied.".format(device.name))
					# Otherwise, use RGB to set the color of the light.
					else:
						if self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(10,"actionControlDimmerRelay: using RGB to change device color.")
						self.doRGB(device, redLevel, greenLevel, blueLevel)
				# Now see if we're only being sent whiteLevel.  If so, the White level slider in the Indigo UI is being
				#   used.  Treat the white level like an inverse saturation slider (100 = zero saturation).
				elif actionColorVals.get('whiteLevel', None) is not None and actionColorVals.get('redLevel', None) is None and actionColorVals.get('greenLevel', None) is None and actionColorVals.get('blueLevel', None) is None:
					self.indiLOG.log(20,"actionControlDimmerRelay: whiteLevel is not empty, but red, green and blue levels are.")
					newSaturation = 255 - whiteLevel
					if newSaturation < 0:
						newSaturation = 0
					self.doHSB(device, device.states['hue'], newSaturation, int(round(currentBrightness * 255.0 / 100.0)))
				# If we're not changing color temperature or saturation (white level), use RGB.
				else:
					if self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(10,"actionControlDimmerRelay: using RGB to change device color.")
					self.doRGB(device, redLevel, greenLevel, blueLevel)

			##### REQUEST STATUS #####
			elif command == indigo.kDeviceAction.RequestStatus:
				try:
					if self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(10,"device request status:\n{}".format(action) )
				except Exception:
					self.indiLOG.log(30,"device request status: Unable to display action data", exc_info=True)
				# Log the new brightness.
				if self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(10,"Sent Hue Lights  \"{}\" status request (received: {})".format( device.name, device.states['brightnessLevel']))

			#### CATCH ALL #####
			else:
				self.indiLOG.log(20,"Unhandled command \"{}\"" .format(command))

		#
		# -- LivingColors Bloom --
		#
		elif device.deviceTypeId == "hueLivingColorsBloom":
			hubNumber, ipAddress, hostId, paired = self.getIdsFromDevice(device)
			if not paired: return 
			if self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(10,"Command is {}, LivingColors Bloom device is {}".format(command, bulbId))

			##### TURN ON #####
			if command == indigo.kDeviceAction.TurnOn:
				try:
					if self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(10,"device on:\n{}".format(action) )
				except Exception:
					self.indiLOG.log(30,"device on: Unable to display action data", exc_info=True)
				# Turn it on.
				self.doOnOff(device, True)

			##### TURN OFF #####
			elif command == indigo.kDeviceAction.TurnOff:
				try:
					if self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(10,"device off:\n{}".format(action) )
				except Exception:
					self.indiLOG.log(30,"device off: Unable to display action data", exc_info=True)
				# Turn it off by setting the brightness to minimum.
				self.doOnOff(device, False)

			##### TOGGLE #####
			elif command == indigo.kDeviceAction.Toggle:
				try:
					if self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(10,"device toggle:\n{}".format(action) )
				except Exception:
					self.indiLOG.log(30,"device toggle: Unable to display action data", exc_info=True)
				if currentOnState :
					# It's on. Turn it off.
					self.doOnOff(device, False)
				else:
					# It's off. Turn it on.
					self.doOnOff(device, True)

			##### SET BRIGHTNESS #####
			elif command == indigo.kDeviceAction.SetBrightness:
				try:
					if self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(10,"device set brightness:\n{}".format(action) )
				except Exception:
					self.indiLOG.log(30,"device set brightness: Unable to display action data", exc_info=True)
				brightnessLevel = int(round(action.actionValue * 255.0 / 100.0))
				# Save the new brightness level into the device properties.
				tempProps = device.pluginProps
				tempProps['savedBrightness'] = brightnessLevel
				self.updateDeviceProps(device, tempProps)
				# Set the new brightness level on the bulb.
				self.doBrightness(device, brightnessLevel)

			##### BRIGHTEN BY #####
			elif command == indigo.kDeviceAction.BrightenBy:
				try:
					if self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(10,"device increase brightness by:\n{}".format(action) )
				except Exception:
					self.indiLOG.log(30,"device increase brightness by: Unable to display action data", exc_info=True)
				brightnessLevel = currentBrightness + action.actionValue
				if brightnessLevel > 100:
					brightnessLevel = 100
				# Save the new brightness level into the device properties.
				tempProps = device.pluginProps
				tempProps['savedBrightness'] = int(round(brightnessLevel * 255.0 / 100.0))
				self.updateDeviceProps(device, tempProps)
				# Set the new brightness level on the bulb.
				self.doBrightness(device, int(round(brightnessLevel * 255.0 / 100.0)))

			##### DIM BY #####
			elif command == indigo.kDeviceAction.DimBy:
				try:
					if self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(10,"device decrease brightness by:\n{}".format(action) )
				except Exception:
					self.indiLOG.log(30,"device decrease brightness by: Unable to display action data", exc_info=True)
				brightnessLevel = currentBrightness - action.actionValue
				if brightnessLevel < 0:
					brightnessLevel = 0
				# Save the new brightness level into the device properties.
				tempProps = device.pluginProps
				tempProps['savedBrightness'] = int(round(brightnessLevel * 255.0 / 100.0))
				self.updateDeviceProps(device, tempProps)
				# Set the new brightness level on the device.
				self.doBrightness(device, int(round(brightnessLevel * 255.0 / 100.0)))

			##### SET COLOR LEVELS #####
			elif command == indigo.kDimmerRelayAction.SetColorLevels:
				try:
					if self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(10,"device request status:\n{}".format(action) )
				except Exception:
					self.indiLOG.log(30,"device request status: Unable to display action data", exc_info=True)

				actionColorVals = action.actionValue

				# Construct a list of channel keys that are possible for what this device
				# supports. It may not support RGB or may not support white levels, for
				# example, depending on how the device's properties (SupportsColor, SupportsRGB,
				# SupportsWhite, SupportsTwoWhiteLevels, SupportsWhiteTemperature) have
				# been specified.
				channelKeys = []
				if device.supportsRGB:
					channelKeys.extend(['redLevel', 'greenLevel', 'blueLevel'])
				if device.supportsWhiteTemperature:
					channelKeys.extend(['whiteTemperature', 'whiteLevel'])
				redLevel = 0
				greenLevel = 0
				blueLevel = 0
				whiteLevel = 0
				colorTemp = 0

				# Enumerate through the possible color channels and extract each
				# value from the actionValue (actionColorVals).
				for channel in channelKeys:
					if channel in actionColorVals:
						channelValue = float(actionColorVals[channel])
						channelValueByte = int(round(255.0 * (channelValue / 100.0)))

						if channel in device.states:
							if channel == "redLevel":
								redLevel = channelValueByte
							elif channel == "greenLevel":
								greenLevel = channelValueByte
							elif channel == "blueLevel":
								blueLevel = channelValueByte
							elif channel == "whiteLevel":
								whiteLevel = channelValueByte
							elif channel == "whiteTemperature":
								# The Indigo 7 interface allows users to select color temperature
								#   values over 6500 and (with Indigo 7.0) below 2000. Correct
								#   out of range values here.
								# The "brightness" variable contains the color temperature value in this case.
								if channelValue > 6500.0:
									channelValue = 6500.0
								if channelValue < 2000.0:
									channelValue = 2000.0
								colorTemp = channelValue
				if self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(10,"actionControlDimmerRelay: Detected color change values of redLevel: {}, greenLevel: {}, blueLevel: {}, whiteLevel: {}, whiteTemperature: {}.".format(redLevel, greenLevel, blueLevel, whiteLevel, colorTemp))
				# The "Set RGBW Levels" action in Indigo 7.0 can have Red, Green, Blue and White levels, as well as
				#   White Temperature for devices that support both RGB and White levels (even if the device doesn't
				#   support simultaneous RGB and W settings).  We have to, therefor, make assumptions based on which
				#   keys are passed and what values are in those keys.
				#
				# Start with whiteTemperature.  If it was the only key passed, the user is making changes to the
				#   light via the Indigo UI.
				if actionColorVals.get('whiteTemperature', None) is not None:
					self.indiLOG.log(20,"actionControlDimmerRelay: whiteTemperature is not empty.")
					if actionColorVals.get('whiteLevel', None) is None and actionColorVals.get('redLevel', None) is None and actionColorVals.get('greenLevel', None) is None and actionColorVals.get('blueLevel', None) is None:
						self.indiLOG.log(20,"actionControlDimmerRelay: red, green, blue and white levels are all empty")
						# Since the whiteLevel was not sent, use the existing brightness as the whiteLevel.
						if device.supportsWhiteTemperature:
							self.doColorTemperature(device, colorTemp, int(round(currentBrightness * 255.0 / 100.0)))
						else:
							self.doErrorLog("The \"{}\" device does not support color temperature. The requested change was not applied.".format(device.name))
					# If both whiteTemperature and whiteLevel keys were sent at the same time, the Indigo Set RGBW
					#    Levels action is being used, in which case, we still want to use the color temperature method,
					#    but use the whiteLevel as the brightness instead of the current brightness if it's over zero.
					elif actionColorVals.get('whiteLevel', None) is not None and float(actionColorVals.get('whiteLevel')) > 0:
						self.indiLOG.log(20,"actionControlDimmerRelay: whiteLevel is not empty and is greater than zero")
						if device.supportsWhiteTemperature:
							self.doColorTemperature(device, colorTemp, whiteLevel)
						else:
							self.doErrorLog("The \"{}\" device does not support color temperature. The requested change was not applied".format(device.name))
					# Otherwise, use RGB to set the color of the light.
					else:
						if self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(10,"actionControlDimmerRelay: using RGB to change device color.")
						self.doRGB(device, redLevel, greenLevel, blueLevel)
				# Now see if we're only being sent whiteLevel.  If so, the White level slider in the Indigo UI is being
				#   used.  Treat the white level like an inverse saturation slider (100 = zero saturation).
				elif actionColorVals.get('whiteLevel', None) is not None and actionColorVals.get('redLevel', None) is None and actionColorVals.get('greenLevel', None) is None and actionColorVals.get('blueLevel', None) is None:
					self.indiLOG.log(20,"actionControlDimmerRelay: whiteLevel is not empty, but red, green and blue levels are.")
					newSaturation = 255 - whiteLevel
					if newSaturation < 0:
						newSaturation = 0
					self.doHSB(device, device.states['hue'], newSaturation, int(round(currentBrightness * 255.0 / 100.0)))
				# If we're not changing color temperature or saturation (white level), use RGB.
				else:
					if self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(10,"actionControlDimmerRelay: using RGB to change device color.")
					self.doRGB(device, redLevel, greenLevel, blueLevel)

			##### REQUEST STATUS #####
			elif command == indigo.kDeviceAction.RequestStatus:
				try:
					if self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(10,"device request status:\n{}".format(action) )
				except Exception:
					self.logger.error("device request status: Unable to display action data", exc_info=True)
				# Log the new brightness.
				if logChanges: self.indiLOG.log(sendLog,"Sent Hue Lights  \"{}\" status request (received: {})".format( device.name, device.states['brightnessLevel']))

			#### CATCH ALL #####
			else:
				self.indiLOG.log(20,"Unhandled command \"{}\"" .format(command))
			pass

		#
		# -- LivingWhites --
		#
		elif device.deviceTypeId == "hueLivingWhites":
			hubNumber, ipAddress, hostId, paired = self.getIdsFromDevice(device)
			if not paired: return 
			if self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(10,"Command is {}, LivingWhites device is {}".format(command, bulbId))

			##### TURN ON #####
			if command == indigo.kDeviceAction.TurnOn:
				try:
					if self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(10,"device on:\n{}".format(action) )
				except Exception:
					self.logger.error("device on: Unable to display action data", exc_info=True)
				# Turn it on.
				self.doOnOff(device, True)

			##### TURN OFF #####
			elif command == indigo.kDeviceAction.TurnOff:
				try:
					if self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(10,"device off:\n{}".format(action) )
				except Exception:
					self.logger.error("device off: Unable to display action data", exc_info=True)
				# Turn it off by setting the brightness to minimum.
				self.doOnOff(device, False)

			##### TOGGLE #####
			elif command == indigo.kDeviceAction.Toggle:
				try:
					if self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(10,"device toggle:\n{}".format(action) )
				except Exception:
					self.logger.error("device toggle: Unable to display action data", exc_info=True)
				if currentOnState :
					# It's on. Turn it off.
					self.doOnOff(device, False)
				else:
					# It's off. Turn it on.
					self.doOnOff(device, True)

			##### SET BRIGHTNESS #####
			elif command == indigo.kDeviceAction.SetBrightness:
				try:
					if self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(10,"device set brightness:\n{}".format(action) )
				except Exception:
					self.indiLOG.log(30,"device set brightness: Unable to display action data", exc_info=True)
				brightnessLevel = int(round(action.actionValue * 255.0 / 100.0))
				# Save the new brightness level into the device properties.
				tempProps = device.pluginProps
				tempProps['savedBrightness'] = brightnessLevel
				self.updateDeviceProps(device, tempProps)
				# Set the new brightness level on the bulb.
				self.doBrightness(device, brightnessLevel)

			##### BRIGHTEN BY #####
			elif command == indigo.kDeviceAction.BrightenBy:
				try:
					if self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(10,"device increase brightness by:\n{}".format(action) )
				except Exception:
					self.indiLOG.log(30,"device increase brightness by: Unable to display action data", exc_info=True)
				brightnessLevel = currentBrightness + action.actionValue
				if brightnessLevel > 100:
					brightnessLevel = 100
				# Save the new brightness level into the device properties.
				tempProps = device.pluginProps
				tempProps['savedBrightness'] = int(round(brightnessLevel * 255.0 / 100.0))
				self.updateDeviceProps(device, tempProps)
				# Set the new brightness level on the bulb.
				self.doBrightness(device, int(round(brightnessLevel * 255.0 / 100.0)))

			##### DIM BY #####
			elif command == indigo.kDeviceAction.DimBy:
				try:
					if self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(10,"device decrease brightness by:\n{}".format(action) )
				except Exception:
					self.indiLOG.log(30,"device decrease brightness by: Unable to display action data", exc_info=True)
				brightnessLevel = currentBrightness - action.actionValue
				if brightnessLevel < 0:
					brightnessLevel = 0
				# Save the new brightness level into the device properties.
				tempProps = device.pluginProps
				tempProps['savedBrightness'] = int(round(brightnessLevel * 255.0 / 100.0))
				self.updateDeviceProps(device, tempProps)
				# Set the new brightness level on the device.
				self.doBrightness(device, int(round(brightnessLevel * 255.0 / 100.0)))

			##### SET COLOR LEVELS #####
			elif command == indigo.kDimmerRelayAction.SetColorLevels:
				# This command should never be sent to this type of device because
				#   the LivingWhites devices shouldn't be defined as supporting color
				#   or variable color temperature.  But if, for some reason, they are,
				#   the code below should handle the call.
				try:
					if self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(10,"device request status:\n{}".format(action) )
				except Exception:
					self.indiLOG.log(30,"device request status: (Unable to display action data) ", exc_info=True)


				self.doErrorLog("The \"{}\" device does not support color. The requested change was not applied.".format(device.name))

			##### REQUEST STATUS #####
			elif command == indigo.kDeviceAction.RequestStatus:
				try:
					if self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(10,"device request status:\n{}".format(action) )
				except Exception:
					self.logger.error("device request status: Unable to display action data", exc_info=True)
				# Log the new brightness.
				if logChanges: self.indiLOG.log(sendLog,"Sent Hue Lights  \"{}\" status request (received: {})".format( device.name, device.states['brightnessLevel']))

		#
		# -- On/Off Only Device --
		#
		elif device.deviceTypeId == "hueOnOffDevice":
			hubNumber, ipAddress, hostId, paired = self.getIdsFromDevice(device)
			if not paired: return 
			if self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(10,"Command is {}, On/Off device is {}".format(command, bulbId))

			##### TURN ON #####
			if command == indigo.kDeviceAction.TurnOn:
				try:
					if self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(10,"device on:\n{}".format(action) )
				except Exception:
					self.logger.error("device on: Unable to display action data", exc_info=True)
				# Turn it on.
				self.doOnOff(device, True)

			##### TURN OFF #####
			elif command == indigo.kDeviceAction.TurnOff:
				try:
					if self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(10,"device off:\n{}".format(action) )
				except Exception:
					self.logger.error("device off: Unable to display action data", exc_info=True)
				# Turn it off by setting the brightness to minimum.
				self.doOnOff(device, False)

			##### TOGGLE #####
			elif command == indigo.kDeviceAction.Toggle:
				try:
					if self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(10,"device toggle:\n{}".format(action) )
				except Exception:
					self.logger.error("device toggle: Unable to display action data", exc_info=True)
				if currentOnState :
					# It's on. Turn it off.
					self.doOnOff(device, False)
				else:
					# It's off. Turn it on.
					self.doOnOff(device, True)

			##### SET BRIGHTNESS #####
			elif command == indigo.kDeviceAction.SetBrightness:
				# This command should never be sent to this type of device because
				#   the On/Off devices shouldn't be defined as a dimmable device
				#   But if, for some reason, they are, the code below should handle the call.
				try:
					if self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(10,"device set brightness:\n{}".format(action) )
				except Exception:
					self.logger.error("device set brightness: Unable to display action data", exc_info=True)
				brightnessLevel = int(action.actionValue)
				if brightnessLevel > 0:
					# Turn it on.
					self.doOnOff(device, True)
				else:
					# Turn it off.
					self.doOnOff(device, False)

			##### BRIGHTEN BY #####
			elif command == indigo.kDeviceAction.BrightenBy:
				# This command should never be sent to this type of device because
				#   the On/Off devices shouldn't be defined as a dimmable device
				#   But if, for some reason, they are, the code below should handle the call.
				try:
					if self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(10,"device increase brightness by:\n{}".format(action) )
				except Exception:
					self.indiLOG.log(30,"device increase brightness by: Unable to display action data", exc_info=True)
				brightnessLevel = int(action.actionValue)
				# If brightnessLevel (i.e. amount to brighten by) is greater than 0, turn on the device.
				if brightnessLevel > 0:
					# Turn it on.
					self.doOnOff(device, True)

			##### DIM BY #####
			elif command == indigo.kDeviceAction.DimBy:
				# This command should never be sent to this type of device because
				#   the On/Off devices shouldn't be defined as a dimmable device
				#   But if, for some reason, they are, the code below should handle the call.
				try:
					if self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(10,"device decrease brightness by:\n{}".format(action) )
				except Exception:
					self.indiLOG.log(30,"device decrease brightness by: Unable to display action data", exc_info=True)
				brightnessLevel = int(action.actionValue)
				# If brightnessLevel (i.e. amount to dim by) is greater than 0, turn off the device.
				if brightnessLevel > 0:
					# Turn it off.
					self.doOnOff(device, False)

			##### SET COLOR LEVELS #####
			elif command == indigo.kDimmerRelayAction.SetColorLevels:
				# This command should never be sent to this type of device because
				#   the On/Off devices shouldn't be defined as supporting color
				#   or variable color temperature.  But if, for some reason, they are,
				#   the code below should handle the call.
				try:
					if self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(10,"device set color:\n{}".format(action) )
				except Exception:
					self.indiLOG.log(30,"device set color: Unable to display action data", exc_info=True)

				self.doErrorLog("The \"{}\" device does not support color. The requested change was not applied.".format(device.name))

			##### REQUEST STATUS #####
			elif command == indigo.kDeviceAction.RequestStatus:
				try:
					if self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(10,"device request status:\n{}".format(action) )
				except Exception:
					self.logger.error("device request status: Unable to display action data", exc_info=True)
				# Log the new brightness.
				if logChanges: self.indiLOG.log(sendLog,"Sent Hue Lights  \"{}\" status request (received: {})".format(device.name, device.states['onOffState']))

			#### CATCH ALL #####
			else:
				self.indiLOG.log(20,"Unhandled command \"{}\"" .format(command))
			pass

		#
		# -- Hue Group --
		#
		if device.deviceTypeId == "hueGroup":
			bulbId = device.pluginProps.get('groupId', None)
			hubNumber, ipAddress, hostId, paired = self.getIdsFromDevice(device)
			if not paired: return 
			if self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(10,"Command is {}, On/Off Group is {}".format(command, bulbId))

			##### TURN ON #####
			if command == indigo.kDeviceAction.TurnOn:
				try:
					if self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(10,"device on:\n{}".format(action) )
				except Exception:
					self.logger.error("device on: Unable to display action data", exc_info=True)
				# Turn it on.
				self.doOnOff(device, True)

			##### TURN OFF #####
			elif command == indigo.kDeviceAction.TurnOff:
				try:
					if self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(10,"device off:\n{}".format(action) )
				except Exception:
					self.logger.error("device off: Unable to display action data", exc_info=True)
				# Turn it off by setting the brightness to minimum.
				self.doOnOff(device, False)

			##### TOGGLE #####
			elif command == indigo.kDeviceAction.Toggle:
				try:
					if self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(10,"device toggle:\n{}".format(action) )
				except Exception:
					self.logger.error("device toggle: Unable to display action data", exc_info=True)
				if currentOnState :
					# It's on. Turn it off.
					self.doOnOff(device, False)
				else:
					# It's off. Turn it on.
					self.doOnOff(device, True)

			##### SET BRIGHTNESS #####
			elif command == indigo.kDeviceAction.SetBrightness:
				try:
					if self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(10,"device set brightness:\n{}".format(action) )
				except Exception:
					self.logger.error("device set brightness: Unable to display action data", exc_info=True)
				brightnessLevel = int(round(action.actionValue * 255.0 / 100.0))
				# Save the new brightness level into the device properties.
				tempProps = device.pluginProps
				tempProps['savedBrightness'] = brightnessLevel
				self.updateDeviceProps(device, tempProps)
				# Set the new brightness level on the bulb.
				self.doBrightness(device, brightnessLevel)

			##### BRIGHTEN BY #####
			elif command == indigo.kDeviceAction.BrightenBy:
				try:
					if self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(10,"device increase brightness by:\n{}".format(action) )
				except Exception:
					self.indiLOG.log(30,"device increase brightness by: Unable to display action data ", exc_info=True)
				brightnessLevel = currentBrightness + action.actionValue
				if brightnessLevel > 100:
					brightnessLevel = 100
				# Save the new brightness level into the device properties.
				tempProps = device.pluginProps
				tempProps['savedBrightness'] = int(round(brightnessLevel * 255.0 / 100.0))
				self.updateDeviceProps(device, tempProps)
				# Set the new brightness level on the bulb.
				self.doBrightness(device, int(round(brightnessLevel * 255.0 / 100.0)))

			##### DIM BY #####
			elif command == indigo.kDeviceAction.DimBy:
				try:
					if self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(10,"device decrease brightness by:\n{}".format(action) )
				except Exception:
					self.indiLOG.log(30,"device decrease brightness by: Unable to display action data ", exc_info=True)
				brightnessLevel = currentBrightness - action.actionValue
				if brightnessLevel < 0:
					brightnessLevel = 0
				# Save the new brightness level into the device properties.
				tempProps = device.pluginProps
				tempProps['savedBrightness'] = int(round(brightnessLevel * 255.0 / 100.0))
				self.updateDeviceProps(device, tempProps)
				# Set the new brightness level on the bulb.
				self.doBrightness(device, int(round(brightnessLevel * 255.0 / 100.0)))

			##### SET COLOR LEVELS #####
			elif command == indigo.kDimmerRelayAction.SetColorLevels:
				try:
					if self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(10,"device request status:\n{}".format(action) )
				except Exception:
					self.logger.error("device request status: Unable to display action data", exc_info=True)

				actionColorVals = action.actionValue

				# Construct a list of channel keys that are possible for what this device
				# supports. It may not support RGB or may not support white levels, for
				# example, depending on how the device's properties (SupportsColor, SupportsRGB,
				# SupportsWhite, SupportsTwoWhiteLevels, SupportsWhiteTemperature) have
				# been specified.
				channelKeys = []
				if device.supportsRGB:
					channelKeys.extend(['redLevel', 'greenLevel', 'blueLevel'])
				if device.supportsWhiteTemperature:
					channelKeys.extend(['whiteTemperature', 'whiteLevel'])
				redLevel = 0
				greenLevel = 0
				blueLevel = 0
				whiteLevel = 0
				colorTemp = 0

				# Enumerate through the possible color channels and extract each
				# value from the actionValue (actionColorVals).
				for channel in channelKeys:
					if channel in actionColorVals:
						channelValue = float(actionColorVals[channel])
						channelValueByte = int(round(channelValue * 255.0 / 100.0))

						if channel in device.states:
							if channel == "redLevel":
								redLevel = channelValueByte
							elif channel == "greenLevel":
								greenLevel = channelValueByte
							elif channel == "blueLevel":
								blueLevel = channelValueByte
							elif channel == "whiteLevel":
								whiteLevel = channelValueByte
							elif channel == "whiteTemperature":
								# The Indigo 7 interface allows users to select color temperature
								#   values over 6500 and (with Indigo 7.0) below 2000. Correct
								#   out of range values here.
								# The "brightness" variable contains the color temperature value in this case.
								if channelValue > 6500.0:
									channelValue = 6500.0
								if channelValue < 2000.0:
									channelValue = 2000.0
								colorTemp = channelValue

				# The "Set RGBW Levels" action in Indigo 7.0 can have Red, Green, Blue and White levels, as well as
				#   White Temperature for devices that support both RGB and White levels (even if the device doesn't
				#   support simultaneous RGB and W settings).  We have to, therefor, make assumptions based on which
				#   keys are passed and what values are in those keys.
				#
				# Start with whiteTemperature.  If it was the only key passed, the user is making changes to the
				#   light via the Indigo UI.
				if device.supportsWhiteTemperature and actionColorVals.get('whiteTemperature', None) is not None:
					if actionColorVals.get('whiteLevel', None) is None and actionColorVals.get('redLevel', None) is None and actionColorVals.get('greenLevel', None) is None and actionColorVals.get('blueLevel', None) is None:
						# Since the whiteLevel was not sent, use the existing brightness as the whiteLevel.
						self.doColorTemperature(device, colorTemp, int(round(currentBrightness * 255.0 / 100.0)))
					# If both whiteTemperature and whiteLevel keys were sent at the same time, the Indigo Set RGBW
					#    Levels action is being used, in which case, we still want to use the color temperature method,
					#    but use the whiteLevel as the brightness instead of the current brightness.
					elif actionColorVals.get('whiteLevel', None) is not None and float(actionColorVals.get('whiteLevel')) > 0:
						self.doColorTemperature(device, colorTemp, whiteLevel)
				# If the user is trying to set color temperature on an older LightStrip that doesn't support color
				#   temperature, let them know in the error log.
				elif not device.supportsWhiteTemperature and actionColorVals.get('whiteTemperature', None) is not None:
					self.doErrorLog("The \"{}\" device does not support color temperature. The requested change was not applied.".format(device.name))
				# Now see if we're only being sent whiteLevel.  If so, the White level slider in the Indigo UI is being
				#   used.  Treat the white level like an inverse saturation slider (100 = zero saturation).
				elif actionColorVals.get('whiteLevel', None) is not None and actionColorVals.get('redLevel', None) is None and actionColorVals.get('greenLevel', None) is None and actionColorVals.get('blueLevel', None) is None:
					newSaturation = device.states['saturation'] - int(round(whiteLevel * 255.0 / 100.0))
					if newSaturation < 0:
						newSaturation = 0
					if device.supportsRGB:
						self.doHSB(device, device.states['hue'], newSaturation, int(round(currentBrightness * 255.0 / 100.0)))
					else:
						self.doErrorLog("The \"{}\" device does not support color. The requested change was not applied.".format(device.name))
				# If we're not changing color temperature or saturation (white level), use RGB.
				else:
					if device.supportsRGB:
						self.doRGB(device, redLevel, greenLevel, blueLevel)
					else:
						self.doErrorLog("The \"{}\" device does not support color. The requested change was not applied.".format(device.name))

			##### REQUEST STATUS #####
			elif command == indigo.kDeviceAction.RequestStatus:
				try:
					if self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(10,"device request status:\n{}".format(action) )
				except Exception:
					self.logger.error("device request status: Unable to display action data", exc_info=True)
				# Log the new brightness.
				if logChanges: self.indiLOG.log(sendLog,"Sent Hue Lights  \"{}\" status request (received: {})".format( device.name, device.states['brightnessLevel']))

			#### CATCH ALL #####
			else:
				self.indiLOG.log(20,"Unhandled command \"{}\"" .format(command))
				self.getGroupStatus(device.id)
			return 

		#
		# -- Hue Attribute Controller --
		#
		elif device.deviceTypeId == "hueAttributeController":
			bulbId = device.pluginProps.get('bulbDeviceId', None)
			attributeToControl = device.pluginProps.get('attributeToControl', None)
			rate = device.pluginProps.get('rate', "")
			onLevel = device.pluginProps.get('defaultOnLevel', "")



			if bulbId is None:
				self.indiLOG.log(20,"Hue Attribute Controller \"{}\" has no Hue Bulb device defined as the control destination. Action ignored.".format(device.name))
				return None
			else:
				# Define the control destination device object and related variables.
				bulbDevice = indigo.devices[int(bulbId)]
				bulbDeviceProps = bulbDevice.pluginProps
				brightnessLevel = int(bulbDevice.states.get('brightnessLevel', 0))
				saturation = bulbDevice.states.get('saturation', 0)
				hue = bulbDevice.states.get('hue', 0)
				colorRed = bulbDevice.states.get('colorRed', 0)
				colorGreen = bulbDevice.states.get('colorGreen', 0)
				colorBlue = bulbDevice.states.get('colorBlue', 0)
				colorTemp = bulbDevice.states.get('colorTemp', 2000)
				# Convert attribute scales to work with the doHSB method.
				brightnessLevel = int(round(brightnessLevel * 255.0 / 100.0))
				saturation = int(round(saturation * 255.0 / 100.0))
				hue = int(hue * 182.0)

			logChanges =  (self.pluginPrefs['logAnyChanges'] == "yes")   or   self.trackSpecificDevice == bulbDevice.id   or   (self.pluginPrefs['logAnyChanges'] == "leaveToDevice" and bulbDevice.pluginProps.get('logChanges', True)) 
			if self.trackSpecificDevice == device.id:	sendLog = 20
			else: 										sendLog = self.sendDeviceUpdatesTo

			if logChanges or self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(sendLog,"device set attribute:{}\n; attributeToControl:{}, current brightnessLevel:{} .. {}".format(str(action), attributeToControl, brightnessLevel, bulbDevice.states.get('brightnessLevel', 0)) )


			if attributeToControl is None:
				self.doErrorLog("Hue Attribute Controller \"{}\" has no Attribute to Control specified. Action ignored.".format(device.name))
				return None

			if rate == "":
				# If a ramp rate wasn't specified, set to -1 to use default rate.
				rate = -1
			else:
				# If it was specified, make sure it's a number. If not, set to default.
				try:
					rate = float(rate)
					if rate < 0 or rate > 540:
						# If the rate is less than 0 or greater than 540, that's an invalid value. Use default.
						rate = -1
				except Exception:
					self.indiLOG.log(30,"Invalid rate", exc_info=True)
					rate = -1

			if onLevel == "":
				# Default on level wasn't specified.  Use 100% as default.
				onLevel = 100
			else:
				# If it was specified, make sure it's a number. If not, set to 100% as default.
				try:
					onLevel = int(onLevel)
					if onLevel < 1 or onLevel > 100:
						# If the on level doesn't make sense, set it to 100%.
						onLevel = 100
				except Exception:
					onLevel = 100
			convertedOnLevel = onLevel

			if logChanges or self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(sendLog,"Command is {}, Bulb device ID is{}" .format(command, bulbId))

			##### TURN ON #####
			if command == indigo.kDeviceAction.TurnOn:
				try:
					if self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(sendLog,"device on:\n{}".format(action) )
				except Exception:
					self.logger.error("device on: Unable to display action data", exc_info=True)
				# Set the destination attribute to maximum.
				if attributeToControl == "hue":
					# Hue
					#   (65535 is the maximum value allowed by Hue and represents a hue of 360 degrees).
					# Convert onLevel to valid hue number.
					convertedOnLevel = int(onLevel / 100.0 * 360.0 * 182.0)
					self.doHSB(bulbDevice, convertedOnLevel, saturation, brightnessLevel, rate)
				elif attributeToControl == "saturation":
					# Saturation
					#   (255 is the maximum value allowed by Hue).
					# Convert onLevel to valid saturation number.
					convertedOnLevel = int(onLevel * 255.0 / 100.0)
					self.doHSB(bulbDevice, hue, convertedOnLevel, brightnessLevel, rate)
				elif attributeToControl == "colorRed":
					# RGB (Red)
					#   (255 is the maximum value allowed).
					# Convert onLevel to valid RGB number.
					convertedOnLevel = int(onLevel * 255.0 / 100.0)
					self.doRGB(bulbDevice, convertedOnLevel, colorGreen, colorBlue, rate)
				elif attributeToControl == "colorGreen":
					# RGB (Green)
					#   (255 is the maximum value allowed).
					# Convert onLevel to valid RGB number.
					convertedOnLevel = int(onLevel * 255.0 / 100.0)
					self.doRGB(bulbDevice, colorRed, convertedOnLevel, colorBlue, rate)
				elif attributeToControl == "colorBlue":
					# RGB (Blue)
					#   (255 is the maximum value allowed).
					# Convert onLevel to valid RGB number.
					convertedOnLevel = int(onLevel * 255.0 / 100.0)
					self.doRGB(bulbDevice, colorRed, colorGreen, convertedOnLevel, rate)
				elif attributeToControl == "colorTemp":
					# Color Temperature
					#   (6500 K is the highest value allowed).
					# Convert onLevel to valid color temperature number.
					convertedOnLevel = int(onLevel / 100.0 * 4500 + 2000)
					self.doColorTemperature(bulbDevice, convertedOnLevel, brightnessLevel, rate)
				# Update the virtual dimmer device.
				self.updateDeviceState(device, 'brightnessLevel', onLevel)

			##### TURN OFF #####
			elif command == indigo.kDeviceAction.TurnOff:
				try:
					if logChanges or self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(sendLog,"device off:\n{}".format(action) )
				except Exception:
					self.logger.error("device off: Unable to display action data", exc_info=True)
				# Set the destination attribute to minimum.
				if attributeToControl == "hue":
					# Hue
					#   (0 is the minimum value allowed by Hue and represents a hue of 0 degrees).
					self.doHSB(bulbDevice, 0, saturation, brightnessLevel, rate)
				elif attributeToControl == "saturation":
					# Saturation
					#   (0 is the minimum value allowed by Hue).
					self.doHSB(bulbDevice, hue, 0, brightnessLevel, rate)
				elif attributeToControl == "colorRed":
					# RGB (Red)
					#   (0 is the minimum value allowed).
					self.doRGB(bulbDevice, 0, colorGreen, colorBlue, rate)
				elif attributeToControl == "colorGreen":
					# RGB (Green)
					#   (0 is the minimum value allowed).
					self.doRGB(bulbDevice, colorRed, 0, colorBlue, rate)
				elif attributeToControl == "colorBlue":
					# RGB (Blue)
					#   (0 is the minimum value allowed).
					self.doRGB(bulbDevice, colorRed, colorGreen, 0, rate)
				elif attributeToControl == "colorTemp":
					# Color Temperature
					#   (2000 K is the lowest value allowed).
					self.doColorTemperature(bulbDevice, 2000, brightnessLevel, rate)
				# Update the virtual dimmer device.
				self.updateDeviceState(device, 'brightnessLevel', 0)

			##### TOGGLE #####
			elif command == indigo.kDeviceAction.Toggle:
				try:
					if logChanges or self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(sendLog,"device toggle:\n{}".format(action) )
				except Exception:
					self.logger.error("device toggle: Unable to display action data", exc_info=True)
				# Set the destination attribute to either maximum or minimum.
				if attributeToControl == "hue":
					# Hue
					#   (0 or 65535)
					if currentOnState :
						# It's something other than 0. Turn it off by setting the value to minimum.
						self.doHSB(bulbDevice, 0, saturation, brightnessLevel, rate)
					else:
						# It's 0. Turn it on by setting the value to maximum.
						# Convert onLevel to valid hue number.
						convertedOnLevel = int(onLevel / 100.0 * 360.0 * 182.0)
						self.doHSB(bulbDevice, convertedOnLevel, saturation, brightnessLevel, rate)
				elif attributeToControl == "saturation":
					# Saturation
					#   (0 to 255)
					if currentOnState :
						# It's something other than 0. Turn it off by setting the value to minimum.
						self.doHSB(bulbDevice, hue, 0, brightnessLevel, rate)
					else:
						# It's 0. Turn it on by setting the value to maximum.
						# Convert onLevel to valid saturation number.
						convertedOnLevel = int(onLevel * 255.0 / 100.0)
						self.doHSB(bulbDevice, hue, convertedOnLevel, brightnessLevel, rate)
				elif attributeToControl == "colorRed":
					# RGB (Red)
					#   (0 to 255)
					if currentOnState :
						# It's something other than 0. Turn it off by setting the value to minimum.
						self.doRGB(bulbDevice, 0, colorGreen, colorBlue, rate)
					else:
						# It's 0. Turn it on by setting the value to maximum.
						# Convert onLevel to valid RGB number.
						convertedOnLevel = int(onLevel * 255.0 / 100.0)
						self.doRGB(bulbDevice, convertedOnLevel, colorGreen, colorBlue, rate)
				elif attributeToControl == "colorGreen":
					# RGB (Green)
					#   (0 to 255)
					if currentOnState :
						# It's something other than 0. Turn it off by setting the value to minimum.
						self.doRGB(bulbDevice, colorRed, 0, colorBlue, rate)
					else:
						# It's 0. Turn it on by setting the value to maximum.
						# Convert onLevel to valid RGB number.
						convertedOnLevel = int(onLevel * 255.0 / 100.0)
						self.doRGB(bulbDevice, colorGreen, convertedOnLevel, colorBlue, rate)
				elif attributeToControl == "colorBlue":
					# RGB (Blue)
					#   (0 to 255)
					if currentOnState :
						# It's something other than 0. Turn it off by setting the value to minimum.
						self.doRGB(bulbDevice, colorRed, colorGreen, 0, rate)
					else:
						# It's 0. Turn it on by setting the value to maximum.
						# Convert onLevel to valid RGB number.
						convertedOnLevel = int(onLevel * 255.0 / 100.0)
						self.doRGB(bulbDevice, colorRed, colorGreen, convertedOnLevel, rate)
				elif attributeToControl == "colorTemp":
					# Color Temperature
					#   (2000 to 6500)
					if currentOnState :
						# It's something other than 0. Turn it off by setting the value to minimum.
						self.doColorTemperature(bulbDevice, 2000, brightnessLevel, rate)
					else:
						# It's 0. Turn it on by setting the value to maximum.
						# Convert onLevel to valid color temperature number.
						convertedOnLevel = int(onLevel / 100.0 * 4500 + 2000)
						self.doColorTemperature(bulbDevice, convertedOnLevel, brightnessLevel, rate)
				# Update the virtual dimmer device.
				if currentOnState :
					self.updateDeviceState(device, 'brightnessLevel', 0)
				else:
					self.updateDeviceState(device, 'brightnessLevel', onLevel)

			##### SET BRIGHTNESS #####
			elif command == indigo.kDeviceAction.SetBrightness:
				try:
					if logChanges or self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(sendLog,"device set attribute:{}\n; attributeToControl:{}, current brightnessLevel:{}".format(action, attributeToControl, brightnessLevel) )
				except Exception:
					self.logger.error("device set brightness: Unable to display action data", exc_info=True)
				# Set the destination attribute to maximum.
				if attributeToControl == "hue":
					# Hue
					#   (0 to 65535. actionValue will be in the range 0 to 100 though, so convert).
					self.doHSB(bulbDevice, int(round(action.actionValue / 100.0 * 360.0 * 182.0)), saturation, brightnessLevel, rate)
				elif attributeToControl == "saturation":
					# Saturation
					#   (0 to 255. actionValue will be in the range 0 to 100 though, so convert).
					self.doHSB(bulbDevice, hue, int(round(action.actionValue * 255.0 / 100.0)), brightnessLevel, rate)
				elif attributeToControl == "colorRed":
					# RGB (Red)
					#   (0 to 255. actionValue will be in the range 0 to 100 though, so convert).
					self.doRGB(bulbDevice, int(round(action.actionValue * 255.0 / 100.0)), colorGreen, colorBlue, rate)
				elif attributeToControl == "colorGreen":
					# RGB (Green)
					#   (0 to 255. actionValue will be in the range 0 to 100 though, so convert).
					self.doRGB(bulbDevice, colorRed, int(round(action.actionValue * 255.0 / 100.0)), colorBlue, rate)
				elif attributeToControl == "colorBlue":
					# RGB (Blue)
					#   (0 to 255. actionValue will be in the range 0 to 100 though, so convert).
					self.doRGB(bulbDevice, colorRed, colorGreen, int(round(action.actionValue * 255.0 / 100.0)), rate)
				elif attributeToControl == "colorTemp":
					# Color Temperature
					#   (2000 to 6500. actionValue will be in range 0 to 100 though, so convert).
					self.doColorTemperature(bulbDevice, int(round(action.actionValue / 100.0 * 4500.0 + 2000.0)), brightnessLevel, rate)
				# Update the virtual dimmer device.
				self.updateDeviceState(device, 'brightnessLevel', action.actionValue)

			##### BRIGHTEN BY #####
			elif command == indigo.kDeviceAction.BrightenBy:
				try:
					if logChanges or self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(sendLog,"device increase brightness by:{}\n; attributeToControl:{}".format(action, attributeToControl)  )
				except Exception:
					self.logger.error("device increase brightness by: Unable to display action data", exc_info=True)
				# Calculate the new brightness.
				newValue = currentBrightness + action.actionValue
				if newValue > 100:
					newValue = 100
				# Set the destination attribute to maximum.
				if attributeToControl == "hue":
					# Hue
					#   (0 to 65535. actionValue will be in the range 0 to 100 though, so convert).
					self.doHSB(bulbDevice, int(round(newValue / 100.0 * 360.0 * 182.0)), saturation, brightnessLevel, rate)
				elif attributeToControl == "saturation":
					# Saturation
					#   (0 to 255. actionValue will be in the range 0 to 100 though, so convert).
					self.doHSB(bulbDevice, hue, int(round(newValue * 255.0 / 100.0)), brightnessLevel, rate)
				elif attributeToControl == "colorRed":
					# RGB (Red)
					#   (0 to 255. actionValue will be in the range 0 to 100 though, so convert).
					self.doRGB(bulbDevice, int(round(newValue * 255.0 / 100.0)), colorGreen, colorBlue, rate)
				elif attributeToControl == "colorGreen":
					# RGB (Green)
					#   (0 to 255. actionValue will be in the range 0 to 100 though, so convert).
					self.doRGB(bulbDevice, colorRed, int(round(newValue * 255.0 / 100.0)), colorBlue, rate)
				elif attributeToControl == "colorBlue":
					# RGB (Blue)
					#   (0 to 255. actionValue will be in the range 0 to 100 though, so convert).
					self.doRGB(bulbDevice, colorRed, colorGreen, int(round(newValue * 255.0 / 100.0)), rate)
				elif attributeToControl == "colorTemp":
					# Color Temperature
					#   (2000 to 6500. actionValue will be in range 0 to 100 though, so convert).
					self.doColorTemperature(bulbDevice, int(round(newValue / 100.0 * 4500.0 + 2000.0)), brightnessLevel, rate)
				# Update the virtual dimmer device.
				self.updateDeviceState(device, 'brightnessLevel', newValue)

			##### DIM BY #####
			elif command == indigo.kDeviceAction.DimBy:
				try:
					if logChanges or self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(sendLog,"device decrease brightness by:{}\n; attributeToControl:{}".format(action, attributeToControl) )
				except Exception:
					self.logger.error("device decrease brightness by: Unable to display action data", exc_info=True)
				# Calculate the new brightness.
				newValue = currentBrightness - action.actionValue
				if newValue < 0:
					newValue = 0
				# Set the destination attribute to maximum.
				if attributeToControl == "hue":
					# Hue
					#   (0 to 65535. actionValue will be in the range 0 to 100 though, so convert).
					self.doHSB(bulbDevice, int(round(newValue / 100.0 * 360.0 * 182.0)), saturation, brightnessLevel, rate)
				elif attributeToControl == "saturation":
					# Saturation
					#   (0 to 255. actionValue will be in the range 0 to 100 though, so convert).
					self.doHSB(bulbDevice, hue, int(round(newValue * 255.0 / 100.0)), brightnessLevel, rate)
				elif attributeToControl == "colorRed":
					# RGB (Red)
					#   (0 to 255. actionValue will be in the range 0 to 100 though, so convert).
					self.doRGB(bulbDevice, int(round(newValue * 255.0 / 100.0)), colorGreen, colorBlue, rate)
				elif attributeToControl == "colorGreen":
					# RGB (Green)
					#   (0 to 255. actionValue will be in the range 0 to 100 though, so convert).
					self.doRGB(bulbDevice, colorRed, int(round(newValue * 255.0 / 100.0)), colorBlue, rate)
				elif attributeToControl == "colorBlue":
					# RGB (Blue)
					#   (0 to 255. actionValue will be in the range 0 to 100 though, so convert).
					self.doRGB(bulbDevice, colorRed, colorGreen, int(round(newValue * 255.0 / 100.0)), rate)
				elif attributeToControl == "colorTemp":
					# Color Temperature
					#   (2000 to 6500. actionValue will be in range 0 to 100 though, so convert).
					self.doColorTemperature(bulbDevice, int(round(newValue / 100.0 * 4500.0 + 2000.0)), brightnessLevel, rate)
				# Update the virtual dimmer device.
				self.updateDeviceState(device, 'brightnessLevel', newValue)

			##### REQUEST STATUS #####
			elif command == indigo.kDeviceAction.RequestStatus:
				try:
					if logChanges or self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(sendLog,"device request status:\n{}".format(action) )
				except Exception:
					self.logger.error("device request status: Unable to display action data", exc_info=True)
				# This actually requests the status of the virtual dimmer device's destination Hue device/group.
				# Show the current virtual dimmer level in the log.  There will likely be a delay for
				#   the destination Hue device status, so we're not going to wait for that status update.
				#   We'll just return the current virtual device brightness level in the log.
				self.indiLOG.log(20,"\"{}\" status request (currently:{})".format(device.name, currentBrightness))

			#### CATCH ALL #####
			else:
				self.indiLOG.log(20,"Unhandled Hue Attribute Controller command \"{}\"".format(command))


		#self.sleep(2) # give the bridge a little time to get done, before we check the new status
		#self.indiLOG.log(20,"requesting  status after action ")
		self.getBulbStatus(device.id, verbose = False) 

		return 

	# Sensor enable / disable 
	######################
	def actionEnableDisableSensor(self, actions=None, typeId=u"", devId=0):
		try:
			valuesDict = actions.props
			if self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(10,"Starting actionEnableDisableSensor with {}.".format(valuesDict))
			self.menuEnableDisableSensor(valuesDict=valuesDict, typeId=u"", devId=0)
		except Exception:
			self.indiLOG.log(30,"actionEnableDisableSensor  Unable to display action", exc_info=True)
		return actions

	######################
	def menuEnableDisableSensor(self, valuesDict, typeId=u"", devId=0):
		try:
			if self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(10,"Starting actionEnableDisableSensor with {}.".format(valuesDict))
			sensorId  = valuesDict.get('sensorId', "")
			hubNumber = valuesDict.get('hubNumber', "")
			onOff     = valuesDict.get('onOff', "")
			if onOff not in ['on','off']: 
				if self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(30,"actionEnableDisableSensor bad onoff command {}.".format(onOff))
				return valuesDict
			if hubNumber == "": return valuesDict


			for deviceId in copy.deepcopy(self.deviceList):
				## if self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(30,"actionEnableDisableSensor deviceId {}, hub#{}, sensorID:{}".format(self.deviceList[deviceId], hubNumber,sensorId))
				if self.deviceList[deviceId]['typeId'] not in kmapSensordevTypeToModelId:	continue
				if self.deviceList[deviceId]['hubNumber']  != hubNumber: 					continue
				if 'sensorId' not in self.deviceList[deviceId]:								continue
				if self.deviceList[deviceId]['sensorId']  != sensorId: 						continue
				device = indigo.devices[deviceId]
				devSensorId = device.pluginProps.get('sensorId', -1)

				if devSensorId != sensorId: continue

				hubNumber, ipAddress, hostId, paired = self.getIdsFromDevice(device)
				if not paired: continue 
				#if self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(10,"valuesDict is {}".format(valuesDict))

				
				command = "http://{}/api/{}/sensors/{}/config".format(ipAddress, self.hostIds[hubNumber], sensorId)
				if onOff == 'on':
					requestData = json.dumps({ "on": True})
				else:
					requestData = json.dumps({ "on": False})
				if self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(10,"Sending URL request: {}, data:{}".format(command, requestData))
				try:
					self.setBridgeBusy(hubNumber, calledfrom="menuEnableDisableSensor")
					r = requests.put(command, data=requestData, timeout=kTimeout, headers={'Connection':'close'})
					self.resetBridgeBusy(hubNumber)
				except requests.exceptions.Timeout:
					self.doErrorLog("Failed to connect to the Hue bridge at {} after {} seconds. - Check that the bridge is connected and turned on.".format(ipAddress, kTimeout))
					# Don't display the error if it's been displayed already.
					self.resetBridgeBusy(hubNumber)
					return valuesDict
				except requests.exceptions.ConnectionError:
					self.doErrorLog("Failed to connect to the Hue bridge at {}. - Check that the bridge is connected and turned on.".format(ipAddress))
					# Don't display the error if it's been displayed already.
					self.resetBridgeBusy(hubNumber)
					return valuesDict
				try:
					response = json.loads(r.content)
					if "success" in response[0]:
						if self.decideMyLog("SendCommandsToBridge"):
							self.indiLOG.log(20,"send {} to \"{}\" returned:OK".format(onOff, device.name ))
					else:
							self.indiLOG.log(20,"send {} to \"{}\" returned:{}".format(onOff, device.name, response ))
				except Exception as e:
					self.doErrorLog("Failed to switch {}. on/off, error:{}, Bridge response:{}".format(device.name,e , response))
					self.resetBridgeBusy(hubNumber)
				return valuesDict

			self.indiLOG.log(30,"actionEnableDisableSensor no matching device found, {}".format(valuesDict))
		except Exception:
			self.logger.error("", exc_info=True)
		self.resetBridgeBusy(hubNumber)
		return valuesDict

	######################
	def menuDeleteSensor(self, valuesDict, typeId=u"", devId=0):
		try:
			self.menuDeleteDevice(valuesDict, 'sensorId', 'sensors', kSwitchTypeIDs)
		except Exception:
			self.logger.error("", exc_info=True)
		return valuesDict


	######################
	def menuDeleteLight(self, valuesDict, typeId=u"", devId=0):
		try:
			self.menuDeleteDevice(valuesDict, 'bulbId', 'lights', kLightDeviceTypeIDs)
		except Exception:
			self.logger.error("", exc_info=True)
		return valuesDict


	######################
	def menuDeleteDevice(self, valuesDict, tag, devType, listOfDevices):
		try:
			self.indiLOG.log(10,"Starting menuDelete{} with {}.".format(devType, valuesDict))
			ID  = valuesDict.get('bulbId', "")
			hubNumber = valuesDict.get('hubNumber', "")
			if hubNumber == "": return valuesDict

			for deviceId in copy.deepcopy(self.deviceList):
				## if self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(30,"actionEnableDisableSensor deviceId {}, hub#{}, sensorID:{}".format(self.deviceList[deviceId], hubNumber,sensorId))
				if self.deviceList[deviceId]['typeId'] not in listOfDevices:	continue
				if self.deviceList[deviceId]['hubNumber']  != hubNumber: 		continue
				if tag not in self.deviceList[deviceId]:						continue
				if self.deviceList[deviceId][tag]  != bulbId: 					continue
				device = indigo.devices[deviceId]
				devId = device.pluginProps.get(tag, -1)

				if devId != ID: continue

				hubNumber, ipAddress, hostId, paired = self.getIdsFromDevice(device)
				#if self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(10,"valuesDict is {}".format(valuesDict))


				
				self.setBridgeBusy(hubNumber, calledfrom="menuDeleteDevice")
				command = "http://{}/api/{}/{}/{}".format(ipAddress, self.hostIds[hubNumber], devType, ID)
				self.indiLOG.log(20,"Sending URL request: {}".format(command))
				try:
					r = requests.delete(command, data="", timeout=kTimeout, headers={'Connection':'close'})
				except requests.exceptions.Timeout:
					self.doErrorLog("Failed to connect to the Hue bridge at {} after {} seconds. - Check that the bridge is connected and turned on.".format(ipAddress, kTimeout))
					# Don't display the error if it's been displayed already.
					self.resetBridgeBusy(hubNumber)
					return valuesDict
				except requests.exceptions.ConnectionError:
					self.doErrorLog("Failed to connect to the Hue bridge at {}. - Check that the bridge is connected and turned on.".format(ipAddress))
					# Don't display the error if it's been displayed already.
					self.resetBridgeBusy(hubNumber)
					return valuesDict
				try:
					response = json.loads(r.content)
					if "success" in response[0]:
						self.indiLOG.log(20,"send  returned:OK.. {}".format(response ))
					else:
						self.indiLOG.log(20,"send returned:{}".format(response ))
				except Exception as e:
					self.doErrorLog("Failed to delete {}  error:{}, Bridge response:{}".format(tag, e, response))
				self.resetBridgeBusy(hubNumber)
				return valuesDict

			self.indiLOG.log(30,"menuDelete{} no matching device found, {}".format(devType, valuesDict))
		except Exception:
			self.logger.error("", exc_info=True)
		self.resetBridgeBusy(hubNumber)
		return valuesDict



	######################
	def menuRenameSensorDevice(self, valuesDict, typeId=u"", devId=0):
		try:
			useId = "sensorId"
			tag = "sensors"
			if self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(30,"Starting rename{} with {}.".format(tag, valuesDict))
			hubNumber	= valuesDict.get('hubNumber', "")
			newName     = valuesDict.get('newName'+tag, "")
			if newName == "": 
				if self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(30,"rename{} bad newName command {}.".format(tag, newName))
				return valuesDict
			theID  		= valuesDict.get(useId, "")
			if valuesDict['removePrefixsensors']:	removePrefix = "Hue_sensor_"
			else:							 		removePrefix = ""
			stdPrefix = "Hue_sensor_"
			if newName == "*" or theID == "*":
				for allIDs in self.hueConfigDict[hubNumber][tag]:
					self.execRename(tag, useId, hubNumber, allIDs, "*", removePrefix, stdPrefix)
			else:
				self.execRename(tag, useId, hubNumber, theID, newName, removePrefix, stdPrefix)
		except Exception:
			self.logger.error("", exc_info=True)
		return valuesDict

	######################
	def menuRenameLightsDevice(self, valuesDict, typeId=u"", devId=0):
		try:
			useId = "bulbId"
			tag = "lights"
			if self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(10,"Starting rename{} with {}.".format(tag, valuesDict))
			hubNumber	= valuesDict.get('hubNumber', "")
			newName     = valuesDict.get('newName'+tag, "")
			if newName == "": 
				if self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(30,"rename{} bad newName command {}.".format(tag, newName))
				return valuesDict
			theID  		= valuesDict.get(useId, "")
			if valuesDict['removePrefixlights']: 	removePrefix = "Hue_light_"
			else:									removePrefix = ""
			stdPrefix = "Hue_light_"
			if newName == "*" or theID == "*":
				for allIDs in self.hueConfigDict[hubNumber][tag]:
					self.execRename(tag, useId, hubNumber, allIDs, "*", removePrefix, stdPrefix)
			else:
				self.execRename(tag, useId, hubNumber, theID, newName, removePrefix, stdPrefix)
		except Exception:
			self.logger.error("", exc_info=True)
		return valuesDict

	######################
	def execRename(self, tag, useId, hubNumber, theID, newName, removePrefix, stdPrefix):
		try:
			#self.indiLOG.log(30,"menu rename {} / {} / {} / {} / {}".format( tag, useId, hubNumber, theID, newName))
			for deviceId in copy.deepcopy(self.deviceList):
				if useId not in self.deviceList[deviceId]:				continue
				if self.deviceList[deviceId][useId]  != theID: 			continue
				device = indigo.devices[deviceId]
				if hubNumber != device.pluginProps.get('hubNumber', -1):	
					self.indiLOG.log(0,"not passed 4,{}:  hubNumber:{},ID:{}, pb-hubNumber:{}".format(device.name, hubNumber, theID,  device.pluginProps.get(hubNumber, -1) ))
					continue

				if theID != device.pluginProps.get(useId, -1):			continue

				hubNumber, ipAddress, hostId, paired = self.getIdsFromDevice(device)
				#if self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(10,"valuesDict is {}".format(valuesDict))
				if newName == "*": newName = device.name
				oldName = self.hueConfigDict[hubNumber][tag][theID]['name']

				#check if we need to shorten name, max len = 32, if std name: Hue_light
				newName = newName.strip()
				if len(newName) > 32 or removePrefix !="":
					xName = copy.copy(newName)
					if xName.find(stdPrefix) == 0:
						xName = xName.split(stdPrefix)[1]  # remove:  Hue_tag_Bridge#_Id#_
						if xName.find("_") >-1:  # remove bridge#_
							xName = xName[xName.find("_")+1:]
						if xName.find("_") >-1: # remove id#_
							xName = xName[xName.find("_")+1:]
						newName = xName[-32:].strip()
						if len(newName) > 32: self.indiLOG.log(30,"rename device:\"{}\", new name:\"{}\", is too long, max len is 32 char, reduced to:\"{}\".".format(device.name, newName, xName))
						else:				  self.indiLOG.log(30,"rename device:\"{}\", new name:\"{}\", remove std tag, changed to :\"{}\".".format(device.name, newName, xName))
					elif len(newName) > 32:
							self.indiLOG.log(30,"rename device for:{}, new name:{}, is too long, max len is 32 char".format(device.name, newName))
							continue
				
				command = "http://{}/api/{}/{}/{}/".format(ipAddress, self.hostIds[hubNumber], tag, theID)
				requestData = json.dumps({ "name": newName})
				if self.decideMyLog("Special") or self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(10,"Sending URL request: {}, data:{}".format(command, requestData))
				try:
					self.setBridgeBusy(hubNumber, calledfrom="execRename")
					r = requests.put(command, data=requestData, timeout=kTimeout, headers={'Connection':'close'})
					self.resetBridgeBusy(hubNumber)
				except requests.exceptions.Timeout:
					self.doErrorLog("Failed to connect to the Hue bridge at {} after {} seconds. - Check that the bridge is connected and turned on.".format(ipAddress, kTimeout))
					# Don't display the error if it's been displayed already.
					self.resetBridgeBusy(hubNumber)
					return 
				except requests.exceptions.ConnectionError:
					self.doErrorLog("Failed to connect to the Hue bridge at {}. - Check that the bridge is connected and turned on.".format(ipAddress))
					# Don't display the error if it's been displayed already.
					self.resetBridgeBusy(hubNumber)
					return 
				try:
					response = json.loads(r.content)
					if "success" in response[0]:
						self.indiLOG.log(20,"change: \"{}\" to \"{}\" for \"{}\" Bridge returned:OK".format(oldName, newName, device.name ))
					else:
						self.indiLOG.log(20,"change: \"{}\" to \"{}\" for \"{}\" Bridge returned:{}".format(oldName, newName, device.name, response ))
				except Exception as e:
					self.doErrorLog("Failed to change name \"{}\". error:{}, Bridge response:{}".format(device.name, e, response))
				self.resetBridgeBusy(hubNumber)
				return 

			self.indiLOG.log(30,"menu rename {} no matching device found; {} / {} / {} / \"{}\"".format( tag, useId, hubNumber, theID, newName))
		except Exception:
			self.logger.error("", exc_info=True)
		self.resetBridgeBusy(hubNumber)
		return 


	# Sensor Action callback
	######################
	def actionControlSensor(self, action, device):
		try:
			if self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(10,"Starting actionControlSensor for device {}. action: {}\n\ndevice: ".format(device.name, action, device))
		except Exception:
			self.indiLOG.log(30,"Starting actionControlSensor for device {}. Unable to display action or device data".format(device.name), exc_info=True)
		# Get the current sensor value and on-state of the device.
		sensorValue = device.states.get('sensorValue', None)
		sensorOnState = device.states.get('onOffState', None)

		# Act based on the type of device.
		#
		# -- Hue Sensor (Motion, Temperature, Luminance, Switch, Button, etc.) --
		#
		if device.deviceTypeId in kMotionSensorTypeIDs or device.deviceTypeId in kTemperatureSensorTypeIDs or device.deviceTypeId in kLightSensorTypeIDs or device.deviceTypeId in kSwitchTypeIDs:
			sensorId = device.pluginProps.get('sensorId', False)
			hubNumber, ipAddress, hostId, paired = self.getIdsFromDevice(device)
			if True or self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(10,"Command is {}, Sensor is {}".format(action, sensorId))


			###### TOGGLE ######
			# Ignore turn on/off/toggle requests from clients since this is a read-only sensor.
			elif action.sensorAction == indigo.kSensorAction.Toggle:
				self.indiLOG.log(20,"ignored \"{}\" {} request (sensor is read-only)".format(device.name, "toggle"))

			###### STATUS REQUEST ######
			elif action.sensorAction == indigo.kSensorAction.RequestStatus:
				# Query hardware module (device) for its current status here:
				self.indiLOG.log(20,"sent \"{}\" {}".format(device.name, "status request"))
				self.getSensorStatus(device.id)
			# End if/else sensor action checking.
		# End if this is a sensor device.

		return 



	########################################
	#     END STANDARD PLUGIN METHODS      #
	########################################



	########################################
	# Custom Methods
	########################################

	# Color Picker Dialog Methods
	#   (based on code from Matt Bendiksen)
	########################################
	#
	# isIntCompat (anything)
	#	Returns True if the passed value can
	#   be converted to an integer. False otherwise.
	# calcRgbHexValsFromRgbLevels (valuesDict)
	#   Calculates RGB Hex values based on
	#   RGB values (0 to 255).
	# calcRgbHexValsFromHsbLevels (valuesDict)
	#   Calculates RGB Hex values based on
	#   HSB values (0 to 360 for hue, 0 to 100 for
	#   saturation).
	# rgbColorPickerUpdated (valuesDict, typeId, devId)
	#   Called every time the color picker color
	#   is changed. Takes the Hex values from
	#   the color picker, converts then assigns
	#   those values to compatible valuesDict
	#   elements.
	# rgbColorFieldUpdated (valuesDict, typeId, devId)
	#   Called by the Set Red/Green/Blue Levels action.
	#   Calls calcRgbHexValsFromRgbLevels and combines
	#   the result into a single valuesDict element.
	# hsbColorFieldUpdated (valuesDict, typeId, devId)
	#   Called by the Set Hue/Saturation/Brightness
	#   action. Calls calcRgbHexValsFromHsbLevels and
	#   combines the result into a single valuesDict
	#   element.
	########################################
	def isIntCompat(self, someValue):
		if self.decideMyLog("Loop"): self.indiLOG.log(10,"Starting isIntCompat.")
		if self.decideMyLog("Loop"): self.indiLOG.log(10,"someValue: {}".format(someValue))
		# Check if a value is an integer or not.
		try:	
			int(someValue)
			return True
		except:	
			return False

	def calcRgbHexValsFromRgbLevels(self, valuesDict):
		if self.decideMyLog("Loop"): self.indiLOG.log(10,"Starting calcRgbHexValsFromRgbLevels.")
		if self.decideMyLog("Loop"): self.indiLOG.log(10,"valuesDict: {}".format(valuesDict))
		# Convert RGB integer values to RGB hex values.
		rgbHexVals = []
		for channel in ['red', 'green', 'blue']:
			fieldValue = 0
			# Make sure the field values are integers.
			if channel in valuesDict and self.isIntCompat(valuesDict[channel]):
				fieldValue = int(valuesDict[channel])
			# Make sure the values are within valid limits.
			if fieldValue < 0:
				fieldValue = 0
			elif fieldValue > 255:
				fieldValue = 255
		# Convert integers to hexadecimal values.
		rgbHexVals.append("%02X" % fieldValue)
		# Return all 3 values as a string separated by a single space.
		return ' '.join(rgbHexVals)

	def calcRgbHexValsFromHsbLevels(self, valuesDict):
		if self.decideMyLog("Loop"): 
			self.indiLOG.log(10,"Starting calcRgbHexValsFromHsbLevels.")
			self.indiLOG.log(10,"valuesDict: {}".format(valuesDict))
		# Convert HSB integer values to RGB hex values.
		rgbHexVals = []
		hue = 0
		saturation = 0
		brightness = 0
		brightnessSource = valuesDict.get('brightnessSource', "custom")
		brightnessDevId = valuesDict.get('brightnessDevice', 0)
		brightnessVarId = valuesDict.get('brightnessVariable', 0)
		# Make sure the values for device and variable IDs are integers to prevent
		#   errors during integer conversion.
		try:    brightnessDevId = int(brightnessDevId)
		except: brightnessDevId = 0
		try:    brightnessVarId = int(brightnessVarId)
		except: brightnessVarId = 0

		for channel in ['hue', 'saturation', 'brightness']:
			fieldValue = 0
			# Make sure the field values are integers.
			if channel in valuesDict and self.isIntCompat(valuesDict[channel]):
				fieldValue = int(valuesDict[channel])
			# Make sure the values are within valid limits.
			if fieldValue < 0:
				fieldValue = 0
			if channel == 'hue':
				if fieldValue > 360:
					fieldValue = 360
				hue = fieldValue
			elif channel == 'saturation':
				if fieldValue > 100:
					fieldValue = 100
				saturation = fieldValue
			elif channel == 'brightness':
				# If the brightnessSource is something other than "custom" get the current
				#   value of the device or variable to which the brightness should be derived.
				if brightnessSource == "variable":
					self.indiLOG.log(20,"brightnessVarId: {}".format(brightnessVarId))
					fieldValue =	 indigo.variables[brightnessVarId].value
					if self.isIntCompat(fieldValue):
						fieldValue = int(fieldValue)
				elif brightnessSource == "dimmer":
					fieldValue = indigo.devices[brightnessDevId].brightness
					if self.isIntCompat(fieldValue):
						fieldValue = int(fieldValue)
				if fieldValue > 100:
					fieldValue = 100
				brightness = fieldValue
		# Convert from HSB to RGB.
		hsb = HSVColor(hue, saturation / 100.0, brightness / 100.0)
		rgb = hsb.convert_to('rgb', rgb_type='wide_gamut_rgb')
		red = int(round(rgb.rgb_r))
		green = int(round(rgb.rgb_g))
		blue = int(round(rgb.rgb_b))
		# Convert integers to hexadecimal value while appending it to the rbgHexVals tuple.
		rgbHexVals.append("%02X" % red)
		rgbHexVals.append("%02X" % green)
		rgbHexVals.append("%02X" % blue)
		# Return all 3 values as a string separated by a single space.
		return ' '.join(rgbHexVals)

	def rgbColorPickerUpdated(self, valuesDict, typeId, devId):
		if self.decideMyLog("Loop"): self.indiLOG.log(10,"Starting rgbColorPickerUpdated.")
		if self.decideMyLog("Loop"): self.indiLOG.log(10,"typeId: {}\ndevId: {}\nvaluesDict: {}".format(typeId, devId, valuesDict))
		# Get the raw 3 byte, space-separated hex string from the color picker.
		rgbHexList = valuesDict['rgbColor'].split()
		# Assign the RGB values.
		red = int(rgbHexList[0], 16)
		green = int(rgbHexList[1], 16)
		blue = int(rgbHexList[2], 16)
		# Convert the RGB values to HSL/HSV for use in the HSB actions.
		rgb = RGBColor(red, green, blue, rgb_type='wide_gamut_rgb')
		hsb = rgb.convert_to('hsv')
		hue = int(round(hsb.hsv_h * 1.0))
		saturation = int(round(hsb.hsv_s * 100.0))
		brightness = int(round(hsb.hsv_v * 100.0))

		# Assign the values to the appropriate valuesDict items.
		valuesDict['red'] = red
		valuesDict['green'] = green
		valuesDict['blue'] = blue
		valuesDict['hue'] = hue
		valuesDict['saturation'] = saturation
		valuesDict['brightness'] = brightness

		# Can send a live update to the hardware here:
		#    self.sendSetRGBWCommand(valuesDict, typeId, devId)

		del valuesDict['rgbColor']
		return (valuesDict)

	def rgbColorFieldUpdated(self, valuesDict, typeId, devId):
		if self.decideMyLog("Loop"): self.indiLOG.log(10,"Starting rgbColorFieldUpdated.")
		if self.decideMyLog("Loop"): self.indiLOG.log(10,"typeId: {}\ndevId: {}\nvaluesDict: {}".format(typeId, devId, valuesDict))
		valuesDict['rgbColor'] = self.calcRgbHexValsFromRgbLevels(valuesDict)

		# Can send a live update to the hardware here:
		#    self.sendSetRGBWCommand(valuesDict, typeId, devId)

		del valuesDict['red']
		del valuesDict['green']
		del valuesDict['blue']
		return (valuesDict)

	def hsbColorFieldUpdated(self, valuesDict, typeId, devId):
		if self.decideMyLog("Loop"): self.indiLOG.log(10,"Starting hsbColorFieldUpdated.")
		if self.decideMyLog("Loop"): self.indiLOG.log(10,"typeId: {}\ndevId: {}\nvaluesDict: {}".format(typeId, devId, valuesDict))
		valuesDict['rgbColor'] = self.calcRgbHexValsFromHsbLevels(valuesDict)

		# Can send a live update to the hardware here:
		#    self.sendSetRGBWCommand(valuesDict, typeId, devId)

		del valuesDict['hue']
		del valuesDict['saturation']
		del valuesDict['brightness']
		return (valuesDict)



	########################################
	def getActionConfigUiValues(self, pluginProps, typeId, devId):
		valuesDict, errorsDict =  super(Plugin, self).getActionConfigUiValues(pluginProps, typeId, devId)
		if True or  typeId in ['actionEnableDisableSensor']:
			valuesDict['confirmHubNumberText'] = "first select hue bridge and click confirm"
		return (valuesDict, errorsDict)

	########################################
	def getMenuActionConfigUiValues(self, menuId):
		#self.indiLOG.log(10,u"getMenuActionConfigUiValues menuId".format(menuId) )

		valuesDict = indigo.Dict()
		errorMsgDict = indigo.Dict()
		if True or  menuId in ['menuEnableDisableSensor','menuRenameHueDevice','trackSpecificDevice']:
			valuesDict['confirmHubNumberText'] = "first select hue bridge and click confirm"
		return (valuesDict, errorMsgDict)


	########################################
	# List Generation and Support Methods
	########################################
	def getDeviceConfigUiValues(self, pluginProps, typeId="", devId=0):
		theDictList =  super(Plugin, self).getDeviceConfigUiValues(pluginProps, typeId, devId)
		if "hubNumber" in theDictList[0]:
			self.hubNumberSelected = theDictList[0]['hubNumber']
		else:
			self.hubNumberSelected = ""
		theDictList[0]['confirmHubNumberText'] = "first select hue bridge and click confirm"
		return theDictList

	# Users List Item Selected (callback from action UI)
	########################################
	def usersListItemSelected(self, valuesDict=None, typeId="", deviceId=0):
		if self.decideMyLog("Loop"): self.indiLOG.log(10,"Starting usersListItemSelected.  valuesDict: {}, typeId: {}, targetId: {}".format(valuesDict, typeId, deviceId))

		self.usersListSelection = valuesDict['userId']
		# Clear these dictionary elements so the sceneLights list will be blank if the sceneId is blank.
		valuesDict['sceneLights'] = list()
		valuesDict['sceneId'] = ""

		return valuesDict

	# Scenes List Item Selected (callback from action UI)
	########################################
	def scenesListItemSelected(self, valuesDict=None, typeId="", deviceId=0):
		if self.decideMyLog("Loop"): self.indiLOG.log(10,"Starting scenesListItemSelected.  valuesDict: {}, typeId: {}, targetId: {}".format(valuesDict, typeId, deviceId))

		self.sceneListSelection = valuesDict['sceneId']

		return valuesDict

	# Groups List Item Selected (callback from action UI)
	########################################
	def groupsListItemSelected(self, valuesDict=None, typeId="", deviceId=0):
		if self.decideMyLog("EditSetup"): self.indiLOG.log(20,"Starting groupsListItemSelected.  valuesDict: {}, typeId: {}, targetId: {}".format(valuesDict, typeId, deviceId))

		self.groupListSelection = valuesDict['groupId']

		return valuesDict

	# Bulb List Generator
	########################################
	def bulbListGenerator(self, filter="", valuesDict=None, typeId="", targetId=0):
		# Used in actions that need a list of Hue bridge devices.
		if self.decideMyLog("EditSetup"): self.indiLOG.log(20,"Starting bulbListGenerator.  filter:{}\n valuesDict: {}, typeId: {}, targetId: {}, hubNumberSelected:{}".format(filter, valuesDict, typeId, targetId, self.hubNumberSelected))

		xList = list()
		devType = "lights"
		devIdTypeId = "bulbId"
		hubNumber = "undefined"
		availableButWrongDevtype = ""
		try:
			if "hubNumber" not in valuesDict: return []
	

			if self.hubNumberSelected == "":
				hubNumbers = self.ipAddresses
			else:
				hubNumbers = {self.hubNumberSelected:True}

		
			deviceAction =  valuesDict.get("deviceAction","EditExisting")

			if deviceAction 	in ["Replace_with_new_Hue_device"]: 		addToString = "-newHueDev"
			elif deviceAction 	in ["Replace_with_other_Indigo_device"]:	addToString = "-replCandidate"
			else:															addToString = ""

			thisDeviceExists = dict()
			addAtEnd = ""
			otherExistingIndigoDevs = dict()
			for devId in self.deviceList:
				dev = indigo.devices[devId]
				props = dev.pluginProps
				if devIdTypeId not in props: continue
				if targetId == devId:
					thisDeviceExists[props['hubNumber']+"-"+props[devIdTypeId]] = devId
				elif "hubNumber" in props: 
					if props['hubNumber'] in hubNumbers:
						otherExistingIndigoDevs[props['hubNumber']+"-"+props[devIdTypeId]] = devId
					continue
				break
			
			if self.decideMyLog("EditSetup"): self.indiLOG.log(20,"bulbListGenerator: deviceAction:{},\n otherExistingIndigoDevs: {},\n thisDeviceExists:{}".format(deviceAction, otherExistingIndigoDevs, thisDeviceExists))
			# loop through devices on hub
			for hubNumber in hubNumbers:
				for memberId, details in sorted(self.hueConfigDict[hubNumber][devType].items(), key = lambda x: x[1]['name']):
					if self.decideMyLog("EditSetup"): self.indiLOG.log(20,"bulbListGenerator:  testing{}, thisdev:{} other:{}".format(hubNumber+"-"+memberId, hubNumber+"-"+memberId in thisDeviceExists, hubNumber+"-"+memberId in otherExistingIndigoDevs))
					if hubNumber+"-"+memberId in thisDeviceExists:
						if deviceAction == "EditExisting": 	 
							addAtEnd = [memberId, details['name']+'-..'+details['uniqueid'][-10:]+"-current"]
						continue

					elif hubNumber+"-"+memberId in otherExistingIndigoDevs:
						if deviceAction in ["EditExisting","Replace_with_new_Hue_device"]:
							if self.decideMyLog("EditSetup"): self.indiLOG.log(20,"bulbListGenerator:  skip, thisDeviceExists  already exixts in Indigo,{}-ID:{}".format(hubNumber+"-"+memberId, otherExistingIndigoDevs[hubNumber+"-"+memberId]))
							continue

					else:
						if deviceAction not in ["Replace_with_new_Hue_device"]:
							if self.decideMyLog("EditSetup"): self.indiLOG.log(20,"bulbListGenerator:  not a new hue device :{}".format(hubNumber+"-"+memberId))
							continue

					if typeId == "":
						# If no typeId exists, list all devices.
						xList.append([memberId, details['name']])

					elif typeId == "hueBulb" and details['type'] == kHueBulbDeviceIDType:
						xList.append([memberId, '{}-..{}{}'.format(details['name'], details['uniqueid'][-10:], addToString)])

					elif typeId == "hueAmbiance" and details['type'] == kAmbianceDeviceIDType:
						xList.append([memberId, '{}-..{}{}'.format(details['name'], details['uniqueid'][-10:], addToString)])

					elif typeId == "hueLightStrips" and details['type'] == kHueBulbDeviceIDType:
						xList.append([memberId, '{}-..{}{}'.format(details['name'], details['uniqueid'][-10:], addToString)])

					elif typeId == "hueLivingColorsBloom" and details['type'] == kLivingColorsDeviceIDType:
						xList.append([memberId, '{}-..{}{}'.format(details['name'], details['uniqueid'][-10:], addToString)])

					elif typeId == "hueLivingWhites" and details['type'] == kLivingWhitesDeviceIDType:
						xList.append([memberId, '{}-..{}{}'.format(details['name'], details['uniqueid'][-10:], addToString)])

					elif typeId == "hueOnOffDevice" and details['type'][0:len(kOnOffOnlyDeviceIDType)] == kOnOffOnlyDeviceIDType:
						xList.append([memberId, '{}-..{}{}'.format(details['name'], details['uniqueid'][-10:], addToString)])

					elif filter.find('anyLight') > -1:
						xList.append([memberId, '{}-..{}{}'.format(details['name'], details['uniqueid'][-10:], addToString)])

					if self.decideMyLog("EditSetup"): self.indiLOG.log(20,"bulbListGenerator:  xList {}".format(xList))
					availableButWrongDevtype += "name:\"{}\", GW#:{}, id:{}, hue-type:\"{}\" equivalent to indigoDev-type:\"{}\"\n ".format(details['name'],  hubNumber, memberId, details['type'], kmapHueTypeToIndigoDevType.get(details['type'],"") )

			if addAtEnd !="": 	xList.append(addAtEnd)
 
			# Debug
			if self.decideMyLog("EditSetup"): self.indiLOG.log(20,"bulbListGenerator: Return {} list is {}".format(devType, xList))

		except Exception:
			self.indiLOG.log(30,"Unable to obtain the configuration from the Hue bridge #{}".format(hubNumber), exc_info=True)

		if xList ==[]:
			self.indiLOG.log(20,"!!! no correntsponding light found, please check your selections !!!\nyour selection was: Bridge# {}, indigo devType:\"{}\"=\"{}\" maps to hue-type:\"{}\"\navailable on the Bridge# {} are:\n{}".format(
								hubNumber, typeId, kmapIndigodevTypeToIndigofulldevType.get(typeId,""),  kmapIndigoDevTypeToHueType.get(typeId,""), hubNumber, availableButWrongDevtype))
			self.printHueData({"whatToPrint":"mappingOfNames","sortBy":""},"")

		return xList

	# Group List Generator
	########################################
	def groupListGenerator(self, filter="", valuesDict=None, typeId="", targetId=0):
		# Used in actions that need a list of Hue bridge groups.
		if self.decideMyLog("EditSetup"): self.indiLOG.log(20,"Starting groupListGenerator.\n  filter: {}\n  valuesDict: {}\n  typeId: {}\n  targetId: {}" .format(filter, valuesDict, typeId, targetId, availableButWrongDevtype))

		xList = list()
		devType = "groups"
		devIdTypeId = "groupId"
		try:

			if "hubNumber" in valuesDict: 
				hubNumbers = {valuesDict['hubNumber']:True}
			else:
				if self.hubNumberSelected == "":
					hubNumbers = "0"
				else:
					hubNumbers = {self.hubNumberSelected:True}


			currentDev = dict()
			existing = dict()
			addAtEnd = ""
			excludeList = dict()
			for devId in self.deviceList:
				dev = indigo.devices[devId]
				props = dev.pluginProps
				if devIdTypeId not in props: continue
				if "hubNumber" not in props or ( props['hubNumber'] not in hubNumbers): 
					excludeList[props['hubNumber']+"-"+props[devIdTypeId]] = devId
					continue

				if targetId == devId:
					currentDev[props['hubNumber']+"-"+props[devIdTypeId]] = devId
				else:
					existing[props['hubNumber']+"-"+props[devIdTypeId]] = devId


			if self.decideMyLog("EditSetup"): self.indiLOG.log(20,"groupListGenerator  bf select existing: {}  excludeList: {}, hubNumbers:{}".format(existing, excludeList, hubNumbers))
			for hubNumber in hubNumbers:
				if hubNumber not in self.hueConfigDict: continue
				for memberId, details in sorted(self.hueConfigDict[hubNumber][devType].items(), key = lambda x: int(x[0])):
					if hubNumber+"-"+memberId in excludeList:
						continue
					if hubNumber+"-"+memberId in currentDev: 	 
						addAtEnd = [memberId, "{} -current".format(details['name'])]
					elif hubNumber+"-"+memberId in existing: 	 
						xList.append([memberId, "{} - already an indigo device".format(details['name'])])
					else:
						xList.append([memberId, "{}-{}:{}".format(hubNumber, memberId, details['name'])])

			if currentDev == dict():	xList.append((0,"all"))
			if addAtEnd !="":			xList.append(addAtEnd)
		except Exception:
			self.indiLOG.log(30,"Unable to obtain the configuration from the Hue bridge.{}".format(self.hubNumberSelected), exc_info=True)

	# Debug
		if self.decideMyLog("EditSetup"): self.indiLOG.log(20,"groupListGenerator: Return {} list is {}".format(devType, xList))

		return xList

	# Bulb Device List Generator
	########################################
	def bulbAndGroupDeviceListGenerator(self, filter="", valuesDict=None, typeId="", targetId=0):
		# Used in actions that need a list of Hue Lights plugin devices that aren't
		#   attribute controllers or groups.
		if self.decideMyLog("EditSetup"): self.indiLOG.log(20,"Starting bulbAndGroupDeviceListGenerator.\n  filter: {}\n  valuesDict: {}\n  typeId: {}\n  targetId: {}".format(filter, valuesDict, typeId, targetId))

		xList = list()

		# Iterate over our devices, and return the available devices as a 2-tuple list.
		for deviceId in copy.deepcopy(self.deviceList):
			device = indigo.devices[deviceId]
			if filter == "yes" and self.hubNumberSelected  != device.pluginProps.get('hubNumber','-xxx'): continue
			if device.pluginProps.get('type', "") in ['Extended color light', 'Color light', 'Color temperature light'] or device.deviceTypeId == "hueGroup":
				xList.append([deviceId, device.name])

		if False and filter != "yes": xList.append([0, "0: (All Hue Lights)"])
		# Sort the list.  Use the "lambda" Python inline function to use the 2nd item in the tuple list (device name) as the sorting key.
		xList = sorted(xList, key = lambda x: x[1])
		# Debug
		if self.decideMyLog("EditSetup"): self.indiLOG.log(20,"bulbAndGroupDeviceListGenerator: Return Hue device list is {}".format(xList))


		return xList

	# Generate Presets List
	########################################
	def presetListGenerator(self, filter="", valuesDict=None, typeId="", deviceId=0):
		# Used by action dialogs to generate a list of Presets saved in the Hue Lights plugin prefs.
		if self.decideMyLog("EditSetup"): self.indiLOG.log(20,"Starting presetListGenerator.\n  filter: {}\n  valuesDict: {}\n  typeId: {}\n  deviceId: {}".format(filter, valuesDict, typeId, deviceId))

		xList = list()	# Menu item list.

		presets = self.pluginPrefs.get('presets', None)
		if self.decideMyLog("EditSetup"): self.indiLOG.log(20,"presetListGenerator: Presets in plugin prefs:\n{}".format(presets))

		if presets is not None:
			presetNumber = 0

			for preset in presets:
				# Determine whether the Preset has saved data or not.
				hasData = ""
				if len(presets[presetNumber][1]) > 0:
					hasData = "*"

				presetNumber += 1
				presetName = preset[0]
				xList.append((presetNumber,  "{} {}: {}".format(hasData, presetNumber, presetName)))
		else:
			xList.append((0, "-- no presets --"))

		return xList

	# Generate Users List
	########################################
	def usersListGenerator(self, filter="", valuesDict=None, typeId="", deviceId=0):
		# Used by action dialogs to generate a list of Hue scene "owner" devices or "Creators".
		if self.decideMyLog("EditSetup"): self.indiLOG.log(20,"Starting usersListGenerator.\n  filter: {}\n  valuesDict: {}\n  typeId: {}\n  deviceId: {}".format(filter, valuesDict, typeId, deviceId))

		xList = list()	# Menu item list.

		# Add a list item at the top for all items.
		xList.append(('all', "All Scene Creators"))

		if "hubNumber" not in valuesDict: return xList
		hubNumber = valuesDict["hubNumber"]

		if hubNumber in self.hueConfigDict: 
			if self.hueConfigDict[hubNumber]['users'] is not None:
				for userId, userData in self.hueConfigDict[hubNumber]['users'].items():
					userName = userData.get('name', "(unknown)")
					# Hue API convention when registering an application (a.k.a. "user")
					#   is to name the "user" as <app name>#<device name>.  We'll translate that
					#   here to something more readable and descriptive for the list.
					userName = userName.replace("#", " app on ")
					if self.decideMyLog("EditSetup"): self.indiLOG.log(20,"usersListGenerator: usersListSelection value: {}, userId: {}, userData: {}".format(self.usersListSelection, userId, json.dumps(userData, indent=2)))
					# Don't display the "Indigo Hue Lights" user as that's this plugin which
					#   won't have any scenes associated with it, which could be confusing.
					if userName != "Indigo Hue Lights":
						xList.append((userId, hubNumber+"-"+userName))

		return xList

	# Generate Scenes List
	########################################
	def scenesListGenerator(self, filter="", valuesDict=None, typeId="", deviceId=0):
		# Used by action dialogs to list Hue scenes on the Hue bridge for a particular "owner" device.
		if self.decideMyLog("EditSetup"): self.indiLOG.log(20,"Starting scenesListGenerator.  filter: {}  valuesDict: {}  typeId: {}  deviceId: {}, self.hubNumberSelected:{}".format(filter, valuesDict, typeId, deviceId, self.hubNumberSelected))

		xList = list()	# Menu item list.

		if "hubNumber" not in valuesDict: return xList
		hubNumber = valuesDict["hubNumber"]
		if hubNumber in self.hueConfigDict: 
			if self.hueConfigDict[hubNumber]['scenes'] is not None:
				for sceneId, sceneData in self.hueConfigDict[hubNumber]['scenes'].items():
					sceneOwner = sceneData.get('owner', "")
					sceneName = sceneData.get('name', "(unknown)")
					if valuesDict.get('userId', "all") == "all":
						# In rare cases, a scene may not have an owner...
						if sceneOwner == "none" or sceneOwner == "":
							sceneDisplayName = sceneName + " (from an unknown scene creator)"
						else:
							# Make sure the scene owner still exists. In rare cases they may not.
							if sceneOwner in self.hueConfigDict[hubNumber]['users'] :
								sceneDisplayName = sceneName + " (from " + self.hueConfigDict[hubNumber]['users'][sceneOwner]['name'].replace("#", " app on ") + ")"
							else:
								sceneDisplayName = sceneName + " (from a removed scene creator)"
					else:
						# Don't add the "(from ... app on ...)" string to the scene name if that Scene Creator was selected.
						sceneDisplayName = sceneName
					sceneLights = sceneData.get('lights', list())
					if self.decideMyLog("EditSetup"): self.indiLOG.log(20,"scenesListGenerator: usersListSelection value: {}, sceneId: {}, sceneOwner: {}, sceneName: {}, sceneData: {}".format(self.usersListSelection, sceneId, sceneOwner, sceneName, json.dumps(sceneData, indent=2)))
					# Filter the list based on which Hue user (scene owner) is selected.
					if sceneOwner == self.usersListSelection or self.usersListSelection == "all" or self.usersListSelection == "":
						xList.append((sceneId, hubNumber+'-'+sceneDisplayName))

						# Create a descriptive list of the lights that are part of this scene.
						self.sceneDescriptionDetail = "Lights in this scene:\n"
						i = 0
						for light in sceneLights:
							if i > 0:
								self.sceneDescriptionDetail += ", "
							lightName = self.hueConfigDict[hubNumber]['lights'][light]['name']
							self.sceneDescriptionDetail += lightName
							i += 1

		return xList

	# Generate Lights List for a Scene
	########################################
	def sceneLightsListGenerator(self, filter="", valuesDict=None, typeId="", deviceId=0):
		# Used by action dialogs to generate a list of lights in a Hue scene, limited by Hue group.
		if self.decideMyLog("EditSetup"): self.indiLOG.log(20,"Starting sceneLightsListGenerator.\n  filter: {}\n  valuesDict: {}\n  typeId: {}\n  deviceId: {}".format(filter, valuesDict, typeId, deviceId))

		xList = list()	# List item list.

		sceneId = valuesDict.get('sceneId', "")
		groupId = valuesDict.get('groupId', "")

		for hubNumber in self.hueConfigDict:
			if "scenes" not in self.hueConfigDict[hubNumber]: continue
			if sceneId == "":
				# The sceneId is blank. This only happens when the action/menu dialog is
				#   called for the first time (or without any settings already saved). This
				#   means that the first item of both scene and group lists will be displayed
				#   in the action/menu dialog, set the sceneId based on that assumption.
				try:
					# We're using "try" here because it's possible there are 0 scenes
					#   on the bridge.  If so, this will throw an exception.
					sceneId = self.hueConfigDict[hubNumber]['scenes'].items()[0][0]
					if groupId == "":
						# If the groupId is blank as well (likely), set it to "0" so the
						#   intersectingLights list is populated properly below.
						groupId = "0"
				except Exception:
					# Just leave the sceneId blank.
					pass

			# If the sceneId isn't blank, get the list of lights.
			if sceneId != "" and sceneId in self.hueConfigDict[hubNumber]['scenes'] :
				# Get the list of lights in the scene.
				sceneLights = self.hueConfigDict[hubNumber]['scenes'][sceneId]['lights']
				if self.decideMyLog("EditSetup"): self.indiLOG.log(20,"sceneLightsListGenerator: sceneLights value:{}".format(sceneLights))
				# Get the list of lights in the group.
				# If the groupId is 0, then the all lights group was selected.
				if groupId != "0":
					groupLights = self.hueConfigDict[hubNumber]['groups'][groupId]['lights']
					if self.decideMyLog("EditSetup"): self.indiLOG.log(20,"sceneLightsListGenerator: groupLights value:{}".format(groupLights))
					# Get the intersection of scene lights and group lights.
					intersectingLights = list(set(sceneLights) & set(groupLights))
				else:
					# Since no group limit was selected, all lights in the scene
					#   should appear in the list.
					intersectingLights = sceneLights
				if self.decideMyLog("EditSetup"): self.indiLOG.log(20,"sceneLightsListGenerator: intersectingLights value:{}".format(intersectingLights))

				# Get the name on the Hue bridge for each light.
				for lightId in intersectingLights:
					lightName = self.hueConfigDict[hubNumber]['lights'][lightId]['name']
					xList.append((lightId, lightName))

		return xList

	# Generate Lights List for a Group
	########################################
	def groupLightsListGenerator(self, filter="", valuesDict=None, typeId="", deviceId=0):
		# Used by action dialogs to generate lists of lights in a Hue group.
		if self.decideMyLog("EditSetup"): self.indiLOG.log(20,"Starting groupLightsListGenerator.\n  filter: {}\n  valuesDict: {}\n  typeId: {}\n  deviceId: {}".format(filter, valuesDict, typeId, deviceId))

		xList = list()	# List item list.
		groupId = ""
		groupLights = dict()
		try:
			groupId = valuesDict.get('groupId', "")

			if self.hubNumberSelected == "":
				return xList
			# If the group ID is not blank, let's try to find the current selection in the valuesDict.
			if groupId != "":
				# Get the list of lights in the group.
				# If the groupId is 0, then the all lights group was selected.
				if groupId == "0":
					groupLights = self.hueConfigDict[self.hubNumberSelected ]['lights'].keys()
				else:
					if groupId in  self.hueConfigDict[self.hubNumberSelected ]['groups']:
						groupLights = self.hueConfigDict[self.hubNumberSelected ]['groups'][groupId]['lights']
				if self.decideMyLog("EditSetup"): self.indiLOG.log(20,"groupLightsListGenerator: groupLights value:{}".format(groupLights))

				# Get the name on the Hue bridge for each light.
				for lightId in groupLights:
					lightName = self.hueConfigDict[self.hubNumberSelected ]['lights'][lightId]['name']
					xList.append((lightId, lightName))

		except Exception:
			self.logger.error("", exc_info=True)
			self.logger.error("hubNumber:{}, groupId:{}, type:{}. ".format(self.hubNumberSelected , groupId, type(groupId)))
		if len(xList) == 0:
			xList.append((-1, "no lights available"))
		return xList

	# Sensor List Generator
	########################################
	def sensorListGenerator(self, filter="", valuesDict=None, typeId="", targetId=0):
		# Used in actions and device configuration windows that need a list of sensor devices.
		if self.decideMyLog("EditSetup"): self.indiLOG.log(20,"Starting sensorListGenerator.\n  filter: {}\n  valuesDict: {}\n  typeId: {}\n  targetId: {}".format(filter, valuesDict, typeId, targetId))

		xList = list()
		addAtEnd = []
		if self.hubNumberSelected == "":
			hubNumbers = self.ipAddresses
		else:
			hubNumbers = {self.hubNumberSelected:True}



		for hubNumber in hubNumbers:
			# Iterate over our sensors, and return a sorted list in Indigo's format
			#   The "lambda" keyword in Python creates an inline function. Here it returns the device name.
			for sensorId, sensorDetails in self.hueConfigDict[hubNumber]['sensors'].items():
				if filter == "":
					# If no filter exists, list all devices.
					xList.append([sensorId, sensorDetails['name']])

				elif filter == "hueMotionSensor" and sensorDetails['type'] == "ZLLPresence":
					xList.append([sensorId, sensorDetails['name']])

				elif filter == "hueMotionTemperatureSensor" and sensorDetails['type'] == "ZLLTemperature":
					# The sensor name on the bridge is going to be generic.  Find the "parent"
					# motion sensor name by extracting the MAC address from the uniqueid value
					# and searching for other sensors with the same MAC address in the uniqueid.
					uniqueId = sensorDetails['uniqueid'].split("-")[0]
					#self.indiLOG.log(20,"uniqueId:{}".format(uniqueId) )
					for key, value in self.hueConfigDict[hubNumber]['sensors'].items():
						if value.get('uniqueid', False) and value.get('type', False):
							#self.indiLOG.log(20,"testing uniqueId:{}, type:{}".format(value['uniqueid'],  value['type'] ) )
							if uniqueId in value['uniqueid'] and value['type'] == "ZLLPresence":
								xList.append([sensorId, value['name']])

				elif filter == "hueMotionLightSensor" and sensorDetails['type'] == "ZLLLightLevel":
					# The sensor name on the bridge is going to be generic.  Find the "parent"
					# motion sensor name by extracting the MAC address from the uniqueid value
					# and searching for other sensors with the same MAC address in the uniqueid.
					uniqueId = sensorDetails['uniqueid'].split("-")[0]
					for key, value in self.hueConfigDict[hubNumber]['sensors'].items():
						if value.get('uniqueid', False) and value.get('type', False):
							if uniqueId in value['uniqueid'] and value['type'] == "ZLLPresence":
								xList.append([sensorId, value['name']])

				elif filter == "hueDimmerSwitch" and sensorDetails['type'] == "ZLLSwitch" and sensorDetails['modelid'] in kSwitchDeviceIDs and sensorDetails['modelid'] in kmapSensordevTypeToModelId['hueDimmerSwitch']:
					xList.append([sensorId, "{}".format(sensorDetails['name'])])

				elif filter == "hueRotaryWallRing" and sensorDetails['type'] == "ZLLRelativeRotary" and sensorDetails['modelid'] in kSwitchDeviceIDs and sensorDetails['modelid'] in kmapSensordevTypeToModelId['hueRotaryWallRing']:
					xList.append([sensorId, "{}".format(sensorDetails['name'])])

				elif filter == "hueRotaryWallSwitches" and sensorDetails['type'] == "ZLLSwitch" and sensorDetails['modelid'] in kSwitchDeviceIDs and sensorDetails['modelid'] in kmapSensordevTypeToModelId['hueRotaryWallSwitches']:
					xList.append([sensorId, "{}".format(sensorDetails['name'])])

				elif filter == "hueSmartButton" and sensorDetails['type'] == "ZLLSwitch" and sensorDetails['modelid'] in kSwitchDeviceIDs and sensorDetails['modelid'] in kmapSensordevTypeToModelId['hueSmartButton']:
					xList.append([sensorId, "{}".format(sensorDetails['name'])])

				elif filter == "hueWallSwitchModule" and sensorDetails['type'] == "ZLLSwitch" and sensorDetails['modelid'] in kSwitchDeviceIDs and sensorDetails['modelid'] in kmapSensordevTypeToModelId['hueWallSwitchModule']:
					xList.append([sensorId, "{}".format(sensorDetails['name'])])

				elif filter == "hueTapSwitch" and sensorDetails['type'] == "ZGPSwitch" and sensorDetails['modelid'] in kSwitchDeviceIDs and sensorDetails['modelid'] in kmapSensordevTypeToModelId['hueTapSwitch']:
					xList.append([sensorId, "{}".format(sensorDetails['name'])])
				# This also shows Niko switches...

				elif filter == "runLessWireSwitch" and sensorDetails['type'] == "ZGPSwitch" and sensorDetails['modelid'] in kSwitchDeviceIDs and sensorDetails['modelid'] in kmapSensordevTypeToModelId['runLessWireSwitch']:
					xList.append([sensorId, "{}".format(sensorDetails['name'])])


				elif filter.find('anySensor') > -1 and sensorDetails['type'] in kSupportedSensorTypes:
					xList.append([sensorId, "{}".format(sensorDetails['name'])])
					addAtEnd = ['*', 'all sensors, use * for new name']

				elif filter.find('oneSensor') > -1 and sensorDetails['type'] in kSupportedSensorTypes:
					xList.append([sensorId, "{}".format(sensorDetails['name'])])

		if addAtEnd != []:
			xList.append(addAtEnd)
		xList = sorted(xList, key = lambda x: x[1])
		if self.decideMyLog("EditSetup"): self.indiLOG.log(20,"sensorListGenerator: Return sensor list is {}".format(xList) )

		return xList

	# Light List Generator
	########################################
	def lightsListGenerator(self, filter="", valuesDict=None, typeId="", targetId=0):
		# Used in actions and device configuration windows that need a list of sensor devices.
		if self.decideMyLog("EditSetup"): self.indiLOG.log(20,"Starting lightsListGenerator.\n  filter: {}\n  valuesDict: {}\n  typeId: {}\n  targetId: {}".format(filter, valuesDict, typeId, targetId))

		xList = list()
		if self.hubNumberSelected == "":
			hubNumbers = self.ipAddresses
		else:
			hubNumbers = {self.hubNumberSelected:True}
		addAtEnd = []
		for hubNumber in hubNumbers:
			# Iterate over our sensors, and return a sorted list in Indigo's format
			#   The "lambda" keyword in Python creates an inline function. Here it returns the device name.
			for bulbId, lightDetails in self.hueConfigDict[hubNumber]['lights'].items():
				if filter.find('oneLight') > -1:
					xList.append([bulbId, "{}".format(lightDetails['name'])])
				if filter.find('anyLight') > -1:
					xList.append([bulbId, "{}".format(lightDetails['name'])])
					addAtEnd = ['*', 'all lights, use * for new name']

		if addAtEnd != []:
			xList.append(addAtEnd)
		xList = sorted(xList, key = lambda x: x[1])
		# Debug
		if self.decideMyLog("EditSetup"): self.indiLOG.log(20,"lightsListGenerator: Return lights list is {}".format(xList) )

		return xList



	# confirm hub number selection
	########################################
	def confirmGWNumber(self, valuesDict, dummy1="", dummy2=""):
		if self.decideMyLog("EditSetup"): self.indiLOG.log(20,"Starting confirmGWNumber.\n  filter: {}".format(valuesDict) )
		self.hubNumberSelected = valuesDict['hubNumber']
		valuesDict['confirmHubNumberText'] = 'Bridge selected, continue with selections'
		valuesDict['confirmHubNumberTextVisible'] = True
		return valuesDict




	########################################
	########################################
	########################################
	##### move device between bridges  #####
	########################################
	########################################
	########################################


	# confirm hub number selection for move of device between hubs
	########################################
	def confirmGWNumbers(self, valuesDict, dummy1="", dummy2=""):

		self.hubNumberSelectedFrom = valuesDict['hubNumberFrom']
		self.hubNumberSelectedTo = valuesDict['hubNumberTo']
		if self.hubNumberSelectedTo == self.hubNumberSelectedFrom:
			valuesDict['MSG'] = 'must select 2 different bridges'
			self.indiLOG.log(30,"Move DEV.. must select 2 different bridges from >{}< and to >{}< are the same ".format(self.hubNumberSelectedTo, self.hubNumberSelectedTo))
			return valuesDict
		valuesDict['MSG'] = 'Bridge selected, continue with selections'
		#if self.decideMyLog("EditSetup"): self.indiLOG.log(20,"Move DEV.. bridges selected: from:{} to {}".format(self.hubNumberSelectedFrom, self.hubNumberSelectedTo))
		return valuesDict



	########################################
	def sensLightGeneratorForMove(self, filter="", valuesDict=None, typeId="", targetId=0):
		# Used in actions and device configuration windows that need a list of sensor devices.
		#if self.decideMyLog("EditSetup"): self.indiLOG.log(20,"Move DEV..  starting lightsListGeneratorForMove.\n  filter: {}\n  valuesDict: {}\n  typeId: {}\n  targetId: {}".format(filter, valuesDict, typeId, targetId))

		xList = list()
		if self.hubNumberSelectedFrom == "":
			return [["0","please select FROM bridge first"]]
		if self.hubNumberSelectedTo == "":
			return [["0","please select TO bridge first"]]
	
		fromTo, sensorOrLight = filter.split("-") 

		for dev in indigo.devices.iter(self.pluginId):
			hubN = str(dev.pluginProps.get("hubNumber","")) 
			if ( ( fromTo == "from" and hubN == self.hubNumberSelectedFrom ) or 
				 ( fromTo == "to"   and hubN == self.hubNumberSelectedTo   )  ):
				if  sensorOrLight in dev.pluginProps: 
					xList.append([dev.id, "{}/{}".format(dev.name, dev.deviceTypeId)])

		xList = sorted(xList, key = lambda x: x[1])
		# Debug
		#if self.decideMyLog("EditSetup"): self.indiLOG.log(20,"Move DEV..  lightsListGeneratorForMove: Return light list is {}".format(xList) )

		return xList



	# now execute the move
	########################################
	def executeMoveLightToNewBridge(self, valuesDict, dummy1="", dummy2=""):
			return self.executeMoveToNewBridge(valuesDict, "bulbId")
	########################################
	def executeMoveSensorToNewBridge(self, valuesDict, dummy1="", dummy2=""):
			return self.executeMoveToNewBridge(valuesDict, "sensorId")

	# now execute the move
	########################################
	def executeMoveToNewBridge(self, valuesDict, devType):
		try:
			if self.decideMyLog("EditSetup"): self.indiLOG.log(20,"Move DEV..  Starting ExecuteMoveToNewBridge: {}".format(valuesDict) )
			if self.hubNumberSelectedFrom == "":
				valuesDict["MSG"] = "ERROR: select FROM bridge"
				self.indiLOG.log(30,"Move DEV..  ERROR:  bridge FROM is not selected" )
				return valuesDict
			if self.hubNumberSelectedTo == "":
				valuesDict["MSG"] = "ERROR: select TO bridge"
				self.indiLOG.log(30,"Move DEV..  ERROR:  TO bridge TO is not selected" )
				return valuesDict
			fromID = devType+"From"
			toID = devType+"To"
			theIDTo = int(valuesDict[toID])
			theIdFrom = int(valuesDict[fromID])

			try: devFrom = indigo.devices[theIdFrom]
			except:
				valuesDict["MSG"] = "ERROR: FROM dev not in indigo"
				if self.decideMyLog("EditSetup"): self.indiLOG.log(20,"Move DEV..  FROM dev does not exist in indigo >{}<".format(self.hubNumberSelectedFrom, theIdFrom ) )
				return valuesDict
			try: devTo = indigo.devices[theIDTo]
			except:
				valuesDict["MSG"] = "ERROR: TO dev not in indigo"
				if self.decideMyLog("EditSetup"): self.indiLOG.log(20,"Move DEV..  To dev does not exist in indigo >{}<".format(self.hubNumberSelectedTo, theIDTo ) )
				return valuesDict

			propsFrom = devFrom.pluginProps
			propsTo = devTo.pluginProps

			if devFrom.deviceTypeId != devTo.deviceTypeId:
				self.indiLOG.log(30,"Move DEV..  from >{}<  to  >{}<  have differnt devType ids: {} != {}".format(devFrom.name, devTo.name,  devFrom.deviceTypeId , devTo.deviceTypeId) )
				valuesDict["MSG"] = "ERROR: differnt dev types"
				return valuesDict

			self.indiLOG.log(20,"Move DEV:{}  to  {}".format(devFrom.name, devTo.name ) )
			for state in devFrom.states:
				if state not in devTo.states:
					self.indiLOG.log(20,"Move  state>{}< not in >TODEV< , skipping".format(state) )
					continue
				self.indiLOG.log(20,"Move DEV: moving state: {} value >{}< overwriting state value: >{}<".format( state, devFrom.states[state], devTo.states[state]) )
				devTo.updateStateOnServer(state, devFrom.states[state])

			for prop in propsFrom:
				self.indiLOG.log(20,"Move DEV:  moving prop: {} value >{}< overwriting old prop ".format(prop, propsFrom[prop]) )
				propsTo[prop] = propsFrom[prop]		
			del self.deviceList[devFrom.id]

			devTo.replacePluginPropsOnServer(propsTo)
			devTo.name += "-new"
			devTo.replaceOnServer()

			devFromName = devFrom.name
			devFromType = devFrom.deviceTypeId
			indigo.device.delete(devFrom)

			self.indiLOG.log(20,"Move DEV..  Bridge/Dev/type: {}/{}/{} has properties from newly moved hue device, new indigo dev:{}/{}/{} is deleted".format(self.hubNumberSelectedTo, devTo.name, devTo.deviceTypeId, self.hubNumberSelectedFrom, devFromName, devFromType ) )
			valuesDict["MSG"] = "device moved"
			self.lastTimeForAll  = 10 # force a refresh read from hue hubs and sync w indigo
			self.lastTimeForCheck = 10
		except Exception:
			self.indiLOG.log(30,"", exc_info=True)

		return valuesDict





	########################################
	# Device Update Methods
	########################################

	# Update Device State
	########################################
	def updateDeviceState(self, device, state, value=None, decimalPlaces=None, uiValue=None, uiImage=None, calledFrom=""):
		# Change the device state or states on the server
		#   if it's different than the current state.
		try:
			# Note that the uiImage value, if passed, should be a valid
			# Indigo State Image Select Enumeration value as defined at
			# http://wiki.indigodomo.com/doku.php?id=indigo_7_documentation:device_class.
			logChanges = (self.pluginPrefs['logAnyChanges'] == "yes") or self.trackSpecificDevice == device.id or (self.pluginPrefs['logAnyChanges'] == "leaveToDevice" and device.pluginProps.get('logChanges', True))
			if self.trackSpecificDevice == device.id:	sendLog = 20
			else: 										sendLog = self.sendDeviceUpdatesTo

			# First determine if we've been sent a key/value list or a device object.
			if state.__class__ == list:
				## self.indiLOG.log(20,"updateDeviceState into list update {}".format(dev.name) )			# Create a temporary key/value list to be used for device updating.
				tempKeyValList = []
				# Loop through the key/value items in the list.
				for statesDict in state:
					# Make sure the minimum required dictionary items exist.
					if "key" not in statesDict:
						self.doErrorLog("updateDeviceState: One of the key/value dicts passed in a multi-state update request is missing the \"key\" item. Unable to update any states for the \"{}\" device. State update:{}.".format(device.name, statesDict))
						return

					if  "value" not in statesDict:
						self.doErrorLog("updateDeviceState: One of the key/value dicts passed in a multi-state update request is missing the \"value\" item. Unable to update any states for the \"{}\" device. State update:{}.".format(device.name, statesDict))
						return

					sKey = statesDict['key']

					# Get any optional dictionary items that may have been passed.

					# First, if the state doesn't even exist on the device, force a reload
					#   of the device configuration to try to add the new state.
					if sKey not in device.states:
						if self.decideMyLog("UpdateIndigoDevices"): self.indiLOG.log(20,"The \"{}\" device doesn't have the \"{}\" state.  Updating device.".format(device.name , sKey))
						device.stateListOrDisplayStateIdChanged()
						continue

					# Now update the state if the new value (rounded if needed) is different.
					if statesDict['value'] == device.states.get(sKey, None):
						continue
					try:
						if self.decideMyLog("UpdateIndigoDevices"): self.indiLOG.log(10,"updateDeviceState: Updating device \"{}\" state: {}. Old value = {}. New value = {}".format(device.name, sKey, device.states.get(sKey, ""), statesDict["value"]))
					except Exception:
						self.indiLOG.log(30,"updateDeviceState: Updating device \"{}\" state: Unable to display state".format( device.name), exc_info=True)

					# Update the device UI icon if one was specified.
					uiImage = statesDict.get('uiImage', None)
					if uiImage is not None:
						device.updateStateImageOnServer(uiImage)
						# Delete the uiImage dictionary item as its not a valid key name for Indigo device updates.
						del statesDict['uiImage']

					# Add the statesDict dictionary to the temporary key/value list to be updated in the device.
					tempKeyValList.append(statesDict)

				# End loop through state key/value list.
				# Update all the states that have changed on the device at one time.
				device.updateStatesOnServer(tempKeyValList)

			# If state wasn't a list, treat it like a string and just update 1 device state.
			else:
				# Make sure the newValue variable wasn't left blank when passed to this method.
				if value is None:
					self.doErrorLog("updateDeviceState: A None value was passed as the new \"{}\" state for the \"{}\" device. The state value was not changed. Please report this error to the plugin developer. calledFrom:{}".format(state, device.name, calledFrom))
					return

				# First, if the state doesn't even exist on the device, force a reload
				#   of the device configuration to try to add the new state.
				if device.states.get(state, None) is None:
					return 
					if self.decideMyLog("UpdateIndigoDevices"): self.indiLOG.log(10,"The {} device doesn't have the \"{}\" state.  Updating device.".format(device.name , state))
					device.stateListOrDisplayStateIdChanged()

				# Set the initial UI Value to the same raw value in newValue.
				if uiValue is None:
					uiValue = "{}".format(value)


				# Now update the state if the new value (rounded if needed) is different.
				if (value != device.states.get(state, None)):
					try:
						if logChanges or self.decideMyLog("UpdateIndigoDevices"): self.indiLOG.log(sendLog,"updateDeviceState: Updating device \"{}\" state: \"{}\". Old value = {}. New value = {}".format(device.name , state, device.states.get(state, ""), value))
					except Exception:
						self.indiLOG.log(30,"updateDeviceState: Updating device \"{}\" state: Unable to display state".format( device.name), exc_info=True)

					# Actually update the device state now.
					device.updateStateOnServer(state, value, uiValue=uiValue)
					# Update the device UI icon if one was specified.
					if uiImage is not None:
						device.updateStateImageOnServer(uiImage)

			# End if state is a list or not.
		except Exception:
			self.logger.error("", exc_info=True)

		return 

	# execute the update of all states of each device
	########################################
	def excecStatesUpdate(self):
		temp = copy.deepcopy(self.updateList)
		self.updateList = dict()
		for devId in temp:
			indigo.devices[devId].updateStatesOnServer(temp[devId])
			#self.indiLOG.log(10," devid:{} chlist:{}".format(devId,self.updateList[devId] ))
		return 		
	# execute the update of all states of each device

	########################################
	def checkIfUpdateState(self, device, key, value, decimalPlaces=None, uiValue=None, uiImage=None, stateUpdateList=None):
		if key in device.states:
			if key == "batteryLevel":
				self.setlastBatteryReplaced(device, value)
			if device.states[key] != value:
				if stateUpdateList is not None: 
					stateUpdateList.append( {"key":key, "value":value, "uiValue":uiValue, "decimalPlaces":decimalPlaces, "uiImage":uiImage} )
					return stateUpdateList
				self.updateDeviceState(device, key, value, uiValue=uiValue, decimalPlaces=decimalPlaces, uiImage=uiImage)
		return stateUpdateList		

	# Update Device Properties
	########################################
	def updateDeviceProps(self, device, newProps):
		# Change the properties on the server only if there's actually been a change.
		if device.pluginProps != newProps:
			if self.decideMyLog("UpdateIndigoDevices"): self.indiLOG.log(10,"updateDeviceProps: Updating device {} properties.".format(device.name))
			device.replacePluginPropsOnServer(newProps)

		return 

	# Rebuild Device
	########################################
	def rebuildDevice(self, device, vd=None):
		if self.decideMyLog("UpdateIndigoDevices"): self.indiLOG.log(10,"Starting rebuildDevice.")

		if self.decideMyLog("UpdateIndigoDevices"): self.indiLOG.log(10,"Checking if the {} device needs to be rebuilt.".format(device.name))
		if self.decideMyLog("UpdateIndigoDevices"): self.indiLOG.log(10,"Device details before rebuild check:\n{}".format(device))

		props = device.pluginProps
		hubNumber = props.get('hubNumber', "0")
		if hubNumber == "-1":
			if vd is not None:
				hubNumber = vd.get('hubNumber', "-1")
				if hubNumber == "-1":
					self.indiLOG.log(20,"Device {} is new has no props yet, skipping rebuildDevice".format(device.name))
					return # this is at creation point, props not filled yet 
				else:
					props = copy.deepcopy(vd)

		if hubNumber not in self.ipAddresses or not self.isValidIP(self.ipAddresses[hubNumber]):
			self.doErrorLog("bridge number {} not registered in ip-addresses {}, please try to re-pair bridge in config ".format(hubNumber, self.ipAddresses), level=30)
			return 

		newProps = self.validateRGBWhiteOnOffetc(props, deviceTypeId=device.deviceTypeId, devId=device.id, devName=device.name)
	
		if newProps != device.pluginProps:
			if self.decideMyLog("UpdateIndigoDevices"): self.indiLOG.log(10,"Device properties have changed. New properties:\n{}".format(newProps))
			if self.decideMyLog("UpdateIndigoDevices"): self.indiLOG.log(10,"Replacing properties on server.")
			device.replacePluginPropsOnServer(newProps)

		if "created" not in device.states or len(device.states['created']) < 20:
			device.updateStateOnServer('created', datetime.datetime.now().strftime(u"%Y-%m-%d %H:%M:%S") )

		if self.decideMyLog("UpdateIndigoDevices"): self.indiLOG.log(10,"Telling server to reload state list and display state.")
		device.stateListOrDisplayStateIdChanged()

		if self.decideMyLog("UpdateIndigoDevices"): self.indiLOG.log(10,"rebuildDevice complete.")

		return 


	# Get ip number and hub id
	########################################
	def getIdsFromDevice(self, device):
		hubNumber = device.pluginProps.get('hubNumber', "0")
		if (hubNumber not in self.ipAddresses or 
			hubNumber not in self.hostIds or 
			hubNumber not in self.paired):
			self.doErrorLog("bridge#:{} not properly setup, please check config".format(hubNumber), level=30, force=False)
			return hubNumber, "","", False
		return hubNumber, self.ipAddresses[hubNumber], self.hostIds[hubNumber], self.paired[hubNumber]




	########################################
	# CHECK for missing  
	########################################

	# check for non existing devices on Hue bridge
	########################################
	def checkMissing(self):
		if self.decideMyLog("EditSetup"): self.debugLog("Starting checkMissing.")
		try:
			for deviceId in copy.deepcopy(self.deviceList):
				if  time.time() - self.missingOnHubs.get(deviceId,time.time() - self.printMissingOnHubeverySecs*4-10)	< self.printMissingOnHubeverySecs*4: continue# only check every 3 loop if already missing, do for new onse 
				device = indigo.devices[deviceId]
				pluginProps = device.pluginProps
				if "hubNumber" not in pluginProps:		continue
				hubNumber = pluginProps['hubNumber']
				if hubNumber not in self.hueConfigDict:	continue

				if self.deviceList[deviceId].get('typeId',-1) in kSensorTypeList: 
					if device.deviceTypeId in kSensorTypeList:
						if "sensors" in self.hueConfigDict[hubNumber]:
							if device.pluginProps['sensorId'] not in self.hueConfigDict[hubNumber]['sensors']:
								self.indiLOG.log(30,"checkMissing: set state to deleted, device not defined on bridge  dev>{:40s}< type:{}, devlisttype:{}".format(device.name, device.deviceTypeId, self.deviceList[deviceId]  ))
								device.updateStateOnServer('online', False)
								device.setErrorStateOnServer("deleted")
								self.missingOnHubs[deviceId] = time.time()

				elif self.deviceList[deviceId].get('typeId','') in kLightDeviceTypeIDs: 
					if device.deviceTypeId in kLightDeviceTypeIDs:
						if "lights" in self.hueConfigDict[hubNumber]:
							if device.pluginProps['bulbId'] not in self.hueConfigDict[hubNumber]['lights']:
								self.indiLOG.log(30,"checkMissing: set state to deleted, device not defined on bridge  dev>{:40s}< type:{}, devlisttype:{}".format(device.name, device.deviceTypeId, self.deviceList[deviceId]  ))
								device.updateStateOnServer('online', False)
								device.setErrorStateOnServer("deleted")
								self.missingOnHubs[deviceId] = time.time()

				elif self.deviceList[deviceId].get('typeId','') in kGroupDeviceTypeIDs: 
					if "groups" in self.hueConfigDict[hubNumber]:
						if pluginProps['groupId'] not in self.hueConfigDict[hubNumber]['groups']:
								self.indiLOG.log(30,"checkMissing: set state to deleted, device not defined on bridge  dev>{:40s}< type:{}, devlisttype:{}".format(device.name, device.deviceTypeId, self.deviceList[deviceId]  ))
								device.setErrorStateOnServer("deleted")
								self.missingOnHubs[deviceId] = time.time()



		except Exception:
			self.logger.error("", exc_info=True)
		return 
	########################################
	# CHECK for missing  END
	########################################





	########################################
	# Hue Communication Methods
	########################################

	# Get Bulb Status
	########################################
	def getBulbStatus(self, deviceId, verbose = False):
		# Get device status.

		device = indigo.devices[deviceId]

		if device.deviceTypeId == 'hueAttributeController':
			# this is not a physical bulb
			return 

		hubNumber, ipAddress, hostId, paired = self.getIdsFromDevice(device)
		if not paired: return 
		if verbose: self.indiLOG.log(20,"Get device status for {}".format(device.name))
		if self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(10,"Get device status for {}".format(device.name))
		# Proceed based on the device type.
		if device.deviceTypeId == "hueGroup":
			# This is a Hue Group device. Redirect the call to the group status update.
			self.getGroupStatus(deviceId)
			return
		else:
			# Get the bulbId from the device properties.
			bulbId = device.pluginProps.get('bulbId', False)
			# if the bulbId exists, get the device status.
			if int(bulbId) < 0: return 

			retCode, bulb, errorsDict =  self.commandToHub_HTTP( hubNumber, "lights/{}".format(bulbId))
			if not retCode:
				return

		### Parse Data
		#
		# Sanity check the returned data first.
		try:
			# If the bulb variable is a list, then there were processing errors.
			errorDict = bulb[0]
			self.doErrorLog("Error retrieving Hue bulb device status: >>{}<< for device :{}".format(errorDict['error']['description'], device.name))
			return
		except KeyError:
			errorDict = []
			# If there was a KeyError, then there were no processing errors.

		# Call the method to update the Indigo device with the Hue device info.
		self.hueConfigDict[hubNumber]['lights'][bulbId] = bulb
		if verbose: self.indiLOG.log(10,"commandToHub_HTTP {} return {}".format(device.name, bulb))
		self.parseOneHueLightData(bulb, device)

		return 

	# Get Group Status
	########################################
	def getGroupStatus(self, deviceId):
		# Get group status.

		device = indigo.devices[deviceId]
		hubNumber, ipAddress, hostId, paired = self.getIdsFromDevice(device)
		if not paired: return 
		# Get the groupId from the device properties.
		groupId = device.pluginProps.get('groupId', -1)


		if int(groupId) < 0: return 
		retCode, group, errorsDict =  self.commandToHub_HTTP( hubNumber, "groups/{}".format(groupId))
		if not retCode:
				return 
		'''
		### Parse Data
		#
		# Sanity check the returned data first.
		try:
			# If the group variable is a list, then there were processing errors.
			errorDict = group[0]
			self.doErrorLog("Error retrieving Hue groups device status: >>{}<< for device :{}".format(errorDict['error']['description'], device.name))
			return
		except KeyError:
			errorDict = []
			# If there was a KeyError, then there were no processing errors.

		# Call the method to update the Indigo device with the Hue group data.
		self.hueConfigDict[hubNumber]['groups'][groupId] = bulb
		self.parseOneHueGroupData(group, device)
		'''
		return 

	# Get Sensor Status
	########################################
	def getSensorStatus(self, deviceId):
		# Get sensor status.

		device = indigo.devices[deviceId]
		hubNumber, ipAddress, hostId, paired = self.getIdsFromDevice(device)
		if not paired: return 
		# Get the sensorId from the device properties.
		sensorId = device.pluginProps.get('sensorId', -1)
		# if the sensorId exists, get the sensor status.
		if int(sensorId) < 0: return
		retCode, sensor, errorsDict =  self.commandToHub_HTTP( hubNumber, "sensors/{}".format(sensorId))
		if not retCode:
			return


		### Parse Data
		#
		# Sanity check the returned data first.
		try:
			# If the sensor variable is a list, then there were processing errors.
			errorDict = sensor[0]
			self.doErrorLog("Error retrieving Hue sensor device status: >>{}<< for device :{}".format(errorDict['error']['description'], device.name))
			return
		except KeyError:
			errorDict = []
			# If there was a KeyError, then there were no processing errors.

		# Call the method to update the Indigo device with the Hue device info.
		self.hueConfigDict[hubNumber]['sensors'][sensorId] = sensor
		self.parseOneHueSensorData(sensor, device)

		return

	# Get Entire Hue bridge Config
	########################################
	def getHueConfig(self):
		# This method obtains the entire configuration object from the Hue bridge.  That
		#   object contains various Hue bridge settings along with every paired light,
		#   sensor device, group, scene, trigger rule, and schedule on the bridge.
		#   For this reason, this method should not be called frequently to avoid
		#   causing Hue bridge performance degredation.
		if self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(10,"Starting getHueConfig.")
		for hubNumber in self.ipAddresses:
			# 
			ipAddress, hostId, errorCode = self.getadresses(hubNumber)
			if errorCode >0: 
				self.indiLOG.log(30,"bridge#{} -bad ip# {} or hostId:{}, errCode:{}".format(hubNumber, ipAddress, hostId, errorCode))
				continue
			try:

				# Send the command and parse the response
				retCode, responseData, errorsDict =  self.commandToHub_HTTP( hubNumber, "")
				if not retCode: 
					self.indiLOG.log(30,"bridge#{} -ip:{}, hostId:{}; data returned >{}<, errors:{}".format(hubNumber, ipAddress, hostId, responseData, errorsDict ))
					continue

				# We should have a dictionary. If so, it's a Hue configuration response.
				if isinstance(responseData, dict):
					if self.decideMyLog("ReadFromBridge"): self.indiLOG.log(10,"Loaded entire Hue bridge configuration - {}".format(json.dumps(responseData,sort_keys=True, indent=2)))

					# Load the entire configuration into one big dictionary object.
					self.hueConfigDict[hubNumber] = responseData
					# Now separate out the component objects into various dictionaries to
					#   be used by other methods in the plugin.
					self.hueConfigDict[hubNumber]['lights'] 		= responseData.get('lights', dict())
					self.hueConfigDict[hubNumber]['groups'] 		= responseData.get('groups', dict())
					self.hueConfigDict[hubNumber]['resourcelinks'] 	= responseData.get('resourcelinks', dict())
					self.hueConfigDict[hubNumber]['sensors'] 		= responseData.get('sensors', dict())
					self.hueConfigDict[hubNumber]['config'] 		= responseData.get('config', dict())
					self.hueConfigDict[hubNumber]['users'] 			= self.hueConfigDict[hubNumber]['config'].get('whitelist', dict()) 
					self.hueConfigDict[hubNumber]['scenes'] 		= responseData.get('scenes', dict())
					self.hueConfigDict[hubNumber]['rules'] 			= responseData.get('rules', dict())
					self.hueConfigDict[hubNumber]['schedules'] 		= responseData.get('schedules', dict())


					# Make sure the plugin knows it's actually paired now.
					self.paired[hubNumber] = True
					self.notPairedMsg[hubNumber] = time.time() - 90
					self.checkIfnewDevices()


				elif isinstance(responseData, list):
					# Get the first item
					firstResponseItem = responseData[0]

					# Did we get an error?
					errorDict = firstResponseItem.get('error', None)
					if errorDict is not None:

						errorCode = errorDict.get('type', None)

						# Is this a link button not pressed error?
						if errorCode == 1:
							if self.checkForLastNotPairedMessage(hubNumber):
								self.doErrorLog("getHueConfig: Not paired with the Hue bridge. Press the middle button on the Hue bridge, then press the Pair Now button in the Hue Lights Configuration window (Plugins menu).")
						# Remember the error.
							self.paired[hubNumber] = False
	
						else:
							if self.checkForLastNotPairedMessage(hubNumber):
								self.doErrorLog("Error #{} from Hue bridge when getting the Hue bridge configuration. Description is \"{}\"." .format(errorCode, errorDict.get('description', "(no description")))
							self.paired[hubNumber] = False

			except Exception:
				self.indiLOG.log(30,"Unable to obtain the configuration from the Hue bridge.{}".format(hubNumber), exc_info=True)
		return



	# Update Groups List
	########################################
	def checkIfnewDevices(self):
		try:
			if not  self.pluginPrefs.get('autoCreatedNewDevices', False): return 

			valuesDict = dict()
			valuesDict["hueFolderName"] = ''
			updateDevices = {'lights':'createLights','sensors':'createSensors','groups':'createGroups'}
			for dType in updateDevices:
				valuesDict[updateDevices[dType]] = True
			self.autocreateNewDevices(valuesDict,"background")
				

		except Exception:
			self.indiLOG.log(30,"Unable to obtain the configuration from the Hue bridge.{}".format(hubNumber), exc_info=True)


	# Update Groups List
	########################################
	def updateGroupsList(self):
		self.updateTheTypeList("groups")
	# Update Groups List
	########################################
	def updateLightsList(self):
		self.updateTheTypeList("lights")

	########################################
	def updateSensorsList(self):
		self.updateTheTypeList("sensors")

	# Update the types  List
	########################################
	def updateTheTypeList(self, theType):
		if self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(10,"Starting update {} List.".format(theType))
		# 
		lastCount = dict()
		hubNumber = "undefined"
		try:
			for hubNumber in self.ipAddresses:
				# Sanity check for an IP address
				ipAddress, hostId, errorCode = self.getadresses(hubNumber)
				if errorCode >0: return

				# Remember the current number of Hue groups to see if new ones have been added.
				if hubNumber not in self.hueConfigDict:
					self.hueConfigDict[hubNumber] = {theType:{}}
				if theType not in self.hueConfigDict[hubNumber]:
					self.hueConfigDict[hubNumber][theType] = dict()

				lastCount[hubNumber] = len(self.hueConfigDict[hubNumber][theType])

				try:
					retCode, responseData, errorsDict =  self.commandToHub_HTTP( hubNumber, theType)
					if not retCode:
						if self.checkForLastNotPairedMessage(hubNumber):
							self.doErrorLog("Error #{} from Hue bridge#{} when loading available {}. Description is \"{}\".".format(errorCode, hubNumber, theType, errorDict.get('description', "(no description)")))
						self.paired[hubNumber] = False
						return 

					# We should have a dictionary. If so, it's a group list
					if isinstance(responseData, dict):
						if self.decideMyLog("ReadFromBridge"): self.indiLOG.log(10,"Loaded {} list - {}".format(theType, json.dumps(responseData, sort_keys=True, indent=2)) )
						self.hueConfigDict[hubNumber][theType] = responseData

						# See if there are more devices now than there were last time we checked.
						if len(self.hueConfigDict[hubNumber][theType]) > lastCount[hubNumber] and lastCount[hubNumber] is not 0:
							if self.pluginPrefs.get('autoCreatedNewDevices', False): 
								self.lastTimeForAll = 0 # trigger create missing devices 
						# Make sure the plugin knows it's actually paired now.
						self.paired[hubNumber] = True
						self.notPairedMsg[hubNumber] = time.time() - 90

					elif isinstance(responseData, list):
						# Get the first item
						firstResponseItem = responseData[0]

						# Did we get an error?
						errorDict = firstResponseItem.get('error', None)
						if errorDict is not None:

							errorCode = errorDict.get('type', None)

							# Is this a link button not pressed error?
							if errorCode == 1:
								if self.checkForLastNotPairedMessage(hubNumber):
									self.doErrorLog("update{}List: Not paired with the Hue bridge#{}. Press the middle button on the Hue bridge, then press the Pair Now button in the Hue Lights Configuration window (Plugins menu).".format(theType, hubNumber))
								self.paired[hubNumber] = False

							else:
								if self.checkForLastNotPairedMessage(hubNumber):
									self.doErrorLog("Error #{} from Hue bridge#{} when loading available {}. Description is \"{}\".".format(errorCode, hubNumber, theType, errorDict.get('description', "(no description)")))
								self.paired[hubNumber] = False

				except requests.exceptions.Timeout:
					self.doErrorLog("Failed to load {} list from the Hue bridge#{} at {} after {} seconds - check settings and retry.".format(theType, hubNumber, ipAddress, kTimeout))

				except requests.exceptions.ConnectionError:
					self.doErrorLog("Failed to connect to the Hue bridge#{} at {}. - Check that the bridge is connected, turned on and the network settings are correct.".format(hubNumber, ipAddress))
					return

				except Exception:
					self.indiLOG.log(40,"Unable to obtain list from the bridge# {}".format(hubNumber), exc_info=True)
		except Exception as e:
			if str(e).find('changed size') ==-1:# in case hub was added / removed in config, skip error message
				self.indiLOG.log(40,"Unable to obtain list from the bridge# {}".format(hubNumber), exc_info=True)
		return 


	# Parse All Hue Lights Data
	########################################
	def parseAllHueLightsData(self):

		# Iterate through all the Indigo devices and look for Hue light changes in the
		#   lights that changed, then update the Indigo device states and properties
		#   as needed.  This method does no actual Hue bridge communication.  It just updates
		#   Indigo devices with information already obtained through the use of the
		#   self.hueConfigDict.
		try:
			if self.decideMyLog("UpdateIndigoDevices"):
				for hubNumber in self.hueConfigDict:
					if "lights" not in self.hueConfigDict[hubNumber]: continue
					self.indiLOG.log(10,"parseAllHueLightsData: on Bridge#:{} There are {} lights on the Hue bridge.".format(hubNumber, len(self.hueConfigDict[hubNumber]['lights'] )))
			if self.decideMyLog("UpdateIndigoDevices"): self.indiLOG.log(10,"parseAllHueLightsData:  and Indigo devices controlling Hue devices:{}, \naccepted types:{}<<".format(self.deviceList, kLightDeviceTypeIDs))

			for deviceId in copy.deepcopy(self.deviceList):
				#self.indiLOG.log(10,"parseAllHueLightsData     deviceId:{},   deviceTypeId, hub#, id#:{}  ".format( deviceId, self.deviceList[deviceId]))
				if self.deviceList[deviceId].get('typeId','') not in kLightDeviceTypeIDs: continue
				device = indigo.devices[deviceId]
				pluginProps = device.pluginProps
				if device.deviceTypeId in kLightDeviceTypeIDs:
					if "hubNumber" not in pluginProps:
						if time.time() - self.lastReminderHubNumberNotPresent > 100: 
							self.indiLOG.log(30,"parseAllHueLightsData device>{}< id:{} not properly setup, please select bridge# in device edit".format(device.name, deviceId))
						self.lastReminderHubNumberNotPresent = time.time()
						continue

					hubNumber = pluginProps['hubNumber']
					if hubNumber not in self.hueConfigDict:
						if time.time() - self.lastReminderHubNumberNotPresent > 100: 
							self.indiLOG.log(30,"parseAllHueLightsData bridge#:{} not in hue Bridge data".format(hubNumber))
							self.lastReminderHubNumberNotPresent = time.time()
						continue
					if "lights" in self.hueConfigDict[hubNumber]:
						if device.pluginProps['bulbId'] in self.hueConfigDict[hubNumber]['lights']:
							self.parseOneHueLightData(self.hueConfigDict[hubNumber]['lights'][device.pluginProps['bulbId']], device, hubNumber, device.pluginProps['bulbId'] )
							
		except Exception:
			self.logger.error("", exc_info=True)

	# Parse One Hue Light Data
	########################################
	def parseOneHueLightData(self, bulb, device, hubNumber="", bulbId=""):
		## if if self.decideMyLog("UpdateIndigoDevices"): self.indiLOG.log(10,"Starting parseOneHueLightData.")

		# Take the bulb passed to this method, look up the data already obtained from the Hue bridge
		# and parse the bridge data for this bulb, making changes to the Indigo device as needed.
		deviceId = "no set"
		devName = "not set"
		hue = ""
		saturation = ""
		colorMode = ""
		colorTemp = ""
		try:
			logChanges = (self.pluginPrefs['logAnyChanges'] == "yes") or self.trackSpecificDevice == device.id or (self.pluginPrefs['logAnyChanges'] == "leaveToDevice" and device.pluginProps.get('logChanges', True))
			if self.trackSpecificDevice == device.id:	
				sendLog = 20
				self.indiLOG.log(sendLog, "Tracking:{}".format(bulb) )
			else: 	sendLog = self.sendDeviceUpdatesTo

			deviceId = device.id
			devName = device.name
			stateUpdateList = []
			decimalPlaces = 4


			#if device.id == 1144808261:   self.indiLOG.log(10,"parseOneHueLightData: {}, hubNumber:{}, bulbId:{},     hue dict:{} ".format(device.name, hubNumber, bulbId, bulb))
			# Separate out the specific Hue bulb data.
			# Data common to all device types...
			#   Value assignments.
			if "state" in bulb:
				if "bri" in bulb['state']:
					brightness 			= bulb['state'].get('bri', 0)
				else:
					brightness = -1 
				online 				= bulb['state'].get('reachable', False)
				if not online:
					if device.states['online']:
						device.updateStateOnServer('online', online)
					device.setErrorStateOnServer("disconnected")
					return 
					#self.indiLOG.log(20, " dev :{} not online , icon:{}".format(devName, icon))
				else:
					device.setErrorStateOnServer("")
				onState 			= bulb['state'].get('on', False)
				if device.onState != onState:
					if logChanges: self.indiLOG.log(sendLog, "Updated:  {:42s}  to {}".format(device.name, "on" if onState else "off"))
				if "{}".format(onState) == "True":
					stateUpdateList = self.checkIfUpdateState(device, 'onOffState', 'on', uiValue="on", stateUpdateList=stateUpdateList)
				elif "{}".format(onState) == "False":
					stateUpdateList = self.checkIfUpdateState(device, 'onOffState', 'off', uiValue="off", stateUpdateList=stateUpdateList)

				stateUpdateList = self.checkIfUpdateState(device, 'online', True,  stateUpdateList=stateUpdateList)
				stateUpdateList = self.checkIfUpdateState(device, 'effect', bulb['state'].get('effect', "none"), stateUpdateList=stateUpdateList)
				stateUpdateList = self.checkIfUpdateState(device, 'alertMode', bulb['state'].get('alert', ""), stateUpdateList=stateUpdateList)

			# Update the error state if needed.
			else:
				brightness			= 0
				onState 			=  False

			brightnessLevel 		= int(round(brightness * 100.0 / 255.0))
			if brightnessLevel == 0 and brightness > 0:
				brightnessLevel = 1


			nameOnBridge 			= bulb.get('name', "no name")
			modelId 				= bulb.get('modelid', "")
			manufacturerName 		= bulb.get('manufacturername', "")
			swVersion 				= bulb.get('swversion', "")
			dType 					= bulb.get('type', "")
			uniqueId 				= bulb.get('uniqueid', "")

			stateUpdateList = self.checkIfUpdateState(device, 'nameOnBridge', nameOnBridge, stateUpdateList=stateUpdateList )
			stateUpdateList = self.checkIfUpdateState(device, 'uniqueId', uniqueId, stateUpdateList=stateUpdateList)
			stateUpdateList = self.checkIfUpdateState(device, 'swVersion', swVersion, stateUpdateList=stateUpdateList)
			stateUpdateList = self.checkIfUpdateState(device, 'manufacturerName', manufacturerName, stateUpdateList=stateUpdateList)
			stateUpdateList = self.checkIfUpdateState(device, 'type', dType, stateUpdateList=stateUpdateList)
			stateUpdateList = self.checkIfUpdateState(device, 'modelId', modelId, stateUpdateList=stateUpdateList)


			#   Update Indigo states and properties common to all Hue devices.
			tempProps = device.pluginProps
			# -- All devices except for On/Off Only devices --
			if dType[0:len(kOnOffOnlyDeviceIDType)] != kOnOffOnlyDeviceIDType:
			#if modelId not in kOnOffOnlyDeviceIDs:
				#   Value manipulation.
				# If the "on" state is False, it doesn't matter what brightness the bridge
				#   is reporting, the effective brightness is zero.
				# Update the savedBrightness property to the current brightness level.
				if brightnessLevel != device.pluginProps.get('savedBrightness', -1):
					tempProps['savedBrightness'] = brightness

			# Update the Hue device name.
			if nameOnBridge != device.pluginProps.get('nameOnBridge', ""):
				tempProps['nameOnBridge'] = nameOnBridge
			# Update the modelId.
			if modelId != device.pluginProps.get('modelId', ""):
				tempProps['modelId'] = modelId
			# Update the manufacturer name.
			if manufacturerName != device.pluginProps.get('manufacturerName', ""):
				tempProps['manufacturerName'] = manufacturerName
			# Update the software version for the device on the Hue bridge.
			if swVersion != device.pluginProps.get('swVersion', ""):
				tempProps['swVersion'] = swVersion
			# Update the type as defined by Hue.
			if dType != device.pluginProps.get('type', ""):
				tempProps['type'] = dType
			# Update the unique ID (MAC address) of the Hue device.
			if uniqueId != device.pluginProps.get('uniqueId', ""):
				tempProps['uniqueId'] = uniqueId
			# If there were property changes, update the device.
			if tempProps != device.pluginProps:
				self.updateDeviceProps(device, tempProps)

			# Device-type-specific data...

			# -- "Extended color light" --
			if dType == kHueBulbDeviceIDType:
				if 'brightnessLevel' not in device.states:
					self.doErrorLog("Device \"{}\" does not have state \"brightnessLevel\"".format(device.name), level=30)
					return 
				#   Value assignment.  (Using the get() method to avoid KeyErrors).
				hue = bulb['state'].get('hue', 0)
				saturation = bulb['state'].get('sat', 0)
				colorX = bulb['state'].get('xy', [0.0,0.0])[0]
				colorY = bulb['state'].get('xy', [0.0,0.0])[1]
				colorRed = 255		# Initialize for later
				colorGreen = 255	# Initialize for later
				colorBlue = 255		# Initialize for later
				colorTemp = bulb['state'].get('ct', 0)
				colorMode = bulb['state'].get('colormode', "ct")

				#   Value manipulation.
				# Convert from HSB to RGB, scaling the hue and saturation values appropriately.
				if(hue == 0 and saturation == 0 and (colorX > 0 or colorY > 0)) or colorMode == "xy":
						colorX = max(0.00001, colorX)
						colorY = max(0.00001, colorY)
						xyY = xyYColor(colorX, colorY, brightness / 255.0)
						rgb = xyY.convert_to('rgb')
						# Let's also convert the xyY color to HSB so that related device states in Indigo are updated correctly.
						hsb = xyY.convert_to('hsv')
						hue = int(round(hsb.hsv_h * 182.0))
						saturation = int(round(hsb.hsv_s * 255.0))
				else:
						hsb = HSVColor(hue / 182.0416666668, saturation / 255.0, brightness / 255.0)
						rgb = hsb.convert_to('rgb')
				#hsb = HSVColor(hue / 182.0, saturation / 255.0, brightness / 255.0)
				#rgb = hsb.convert_to('rgb', rgb_type='wide_gamut_rgb')
				# RGB values will have a range of 0 to 255.
				colorRed = int(round(rgb.rgb_r))
				colorGreen = int(round(rgb.rgb_g))
				colorBlue = int(round(rgb.rgb_b))
				# Convert saturation from 0-255 scale to 0-100 scale.
				saturation = int(round(saturation * 100.0 / 255.0))
				# Convert hue from 0-65535 scale to 0-360 scale.

				# do a check for hue 
				self.normalizeHue(hue, device)
				# Must first test color temp value. If it's zero, the formula throws a divide by zero execption.
				if colorTemp > 0:
					# Converting from mireds to Kelvin.
					colorTemp = int(round(1000000.0/colorTemp))
				else:
					colorTemp = 0


				if str(onState) == "False":
					colorRed = 0
					colorGreen = 0
					colorBlue = 0
					brightnessLevel = 0
					decimalPlaces = 0


				# Update the Indigo device if the Hue device is on.
				if str(onState) in ['True', 'False']:
					# Update the brightness level if it's different.
						
					if device.states['brightnessLevel'] != brightnessLevel:
						if logChanges: self.indiLOG.log(sendLog, "Updated:  {:42s}  to {}".format(device.name, brightnessLevel))

					stateUpdateList = self.checkIfUpdateState(device , 'brightnessLevel', brightnessLevel, stateUpdateList=stateUpdateList )
					stateUpdateList = self.checkIfUpdateState(device , 'hue', hue, stateUpdateList=stateUpdateList )
					stateUpdateList = self.checkIfUpdateState(device , 'saturation', saturation, stateUpdateList=stateUpdateList )
					stateUpdateList = self.checkIfUpdateState(device , 'colorX', colorX, decimalPlaces=decimalPlaces, stateUpdateList=stateUpdateList )
					stateUpdateList = self.checkIfUpdateState(device , 'colorY', colorY, decimalPlaces=decimalPlaces, stateUpdateList=stateUpdateList )
					stateUpdateList = self.checkIfUpdateState(device , 'colorRed', colorRed, stateUpdateList=stateUpdateList )
					stateUpdateList = self.checkIfUpdateState(device , 'colorGreen', colorGreen, stateUpdateList=stateUpdateList )
					stateUpdateList = self.checkIfUpdateState(device , 'colorBlue', colorBlue, stateUpdateList=stateUpdateList )
					stateUpdateList = self.checkIfUpdateState(device , 'colorTemp', colorTemp, stateUpdateList=stateUpdateList )
					stateUpdateList = self.checkIfUpdateState(device , 'colorMode', colorMode, stateUpdateList=stateUpdateList )
					stateUpdateList = self.checkIfUpdateState(device , 'whiteLevel', 100 - saturation, uiValue="{}".format(int(100 - saturation)), stateUpdateList=stateUpdateList )
					stateUpdateList = self.checkIfUpdateState(device , 'whiteTemperature', colorTemp, uiValue="{}".format(int(colorTemp)), stateUpdateList=stateUpdateList )
					stateUpdateList = self.checkIfUpdateState(device , 'redLevel', int(round(colorRed * 100.0 / 255.0)), uiValue="{}".format(int(colorTemp)), stateUpdateList=stateUpdateList )
					stateUpdateList = self.checkIfUpdateState(device , 'greenLevel', int(round(colorGreen * 100.0 / 255.0)), uiValue="{}".format(int(round(colorGreen * 100.0 / 255.0))), stateUpdateList=stateUpdateList )
					stateUpdateList = self.checkIfUpdateState(device , 'blueLevel', int(round(colorBlue * 100.0 / 255.0)), uiValue="{}".format(int(round(colorBlue * 100.0 / 255.0))), stateUpdateList=stateUpdateList )

				else:
					# Unrecognized on state, but not important enough to mention in regular log.
					self.indiLOG.log(30,"Hue bulb unrecognized on state given by bridge: >{}<; not in 'True', 'False'".format(str(bulb['state']['on']) ))

				# Update any Hue Device Attribute Controller virtual dimmers associated with this bulb.
				for controlDeviceId in self.controlDeviceList:
					if controlDeviceId not in self.deviceList: continue 
					if controlDeviceId not in indigo.devices:
						if logChanges: self.indiLOG.log(sendLog, " control dev id:{} not in indigo device list:{}, \ntry to restart plugin".format(controlDeviceId, self.controlDeviceList))
					else:    
						controlDevice = indigo.devices[int(controlDeviceId)]
						attributeToControl = controlDevice.pluginProps.get('attributeToControl', None)
						if deviceId == int(controlDevice.pluginProps.get('bulbDeviceId', -1)): # KW changed None to -1 as int(None) does not work 
							# Device has attributes controlled by a Hue Device Attribute Controler.
							#	Update the controller device based on current bulb device states.
							#	But if the control destination device is off, update the value of the
							#	controller (virtual dimmer) to 0.
							if device.onState:
								# Destination Hue Bulb device is on, update Attribute Controller brightness.
								if attributeToControl == "hue":
									# Convert hue scale from 0-360 to 0-100.
									self.updateDeviceState(controlDevice, 'brightnessLevel', int(round(hue / 360.0 * 100.0)))
								elif attributeToControl == "saturation":
									self.updateDeviceState(controlDevice, 'brightnessLevel', saturation)
								elif attributeToControl == "colorRed":
									# Convert RGB scale from 0-255 to 0-100.
									self.updateDeviceState(controlDevice, 'brightnessLevel', int(round(colorRed * 100.0 / 255.0)))
								elif attributeToControl == "colorGreen":
									# Convert RGB scale from 0-255 to 0-100.
									self.updateDeviceState(controlDevice, 'brightnessLevel', int(round(colorGreen * 100.0 / 255.0)))
								elif attributeToControl == "colorBlue":
									# Convert RGB scale from 0-255 to 0-100.
									self.updateDeviceState(controlDevice, 'brightnessLevel', int(round(colorBlue * 100.0 / 255.0)))
								elif attributeToControl == "colorTemp":
									# Convert color temperature scale from 2000-6500 to 0-100.
									self.updateDeviceState(controlDevice, 'brightnessLevel', int(round((colorTemp - 2000.0) / 4500.0 * 100.0)))
							else:
								# Hue Device is off.  Set Attribute Controller device brightness level to 0.
								self.updateDeviceState(controlDevice, 'brightnessLevel', 0)

			# -- Ambiance -- "Color temperature light"
			elif dType == kAmbianceDeviceIDType:
				if 'brightnessLevel' not in device.states:
					self.doErrorLog("Device \"{}\" does not have state \"brightnessLevel\"".format(device.name), level=30)
					return 

				#   Value assignment.  (Using the get() method to avoid KeyErrors).
				colorTemp = bulb['state'].get('ct', 0)
				colorMode = bulb['state'].get('colormode', "ct")

				#   Value manipulation.
				# Must first test color temp value. If it's zero, the formula throws a divide by zero execption.
				if colorTemp > 0:
					# Converting from mireds to Kelvin.
					colorTemp = int(round(1000000.0/colorTemp))
				else:
					colorTemp = 0


				if str(onState) == "False":
					brightnessLevel = 0

				# Update the Indigo device if the Hue device is on.
				if str(onState) in ['True', 'False']:
					if device.states['brightnessLevel'] != brightnessLevel:
						if logChanges: self.indiLOG.log(sendLog, "Updated:  {:42s}  to {}".format(device.name, brightnessLevel))
					stateUpdateList = self.checkIfUpdateState(device , 'brightnessLevel', brightnessLevel, stateUpdateList=stateUpdateList )
					stateUpdateList = self.checkIfUpdateState(device , 'colorTemp', colorTemp, stateUpdateList=stateUpdateList )
					stateUpdateList = self.checkIfUpdateState(device , 'colorMode', colorMode, stateUpdateList=stateUpdateList )
					stateUpdateList = self.checkIfUpdateState(device , 'whiteLevel', brightnessLevel, uiValue="{}".format(int(brightnessLevel)), stateUpdateList=stateUpdateList )
					stateUpdateList = self.checkIfUpdateState(device , 'whiteTemperature', colorTemp, uiValue="{}".format(int(colorTemp)), stateUpdateList=stateUpdateList )

				else:
					# Unrecognized on state, but not important enough to mention in regular log.
					self.debugLog("Ambiance light unrecognized \"on\" state given by bridge: {}".format(bulb['state']['on']))

				# Update any Hue Device Attribute Controller virtual dimmers associated with this bulb.
				for controlDeviceId in self.controlDeviceList:
					controlDevice = indigo.devices[int(controlDeviceId)]
					attributeToControl = controlDevice.pluginProps.get('attributeToControl', None)
					if deviceId == int(controlDevice.pluginProps.get('bulbDeviceId', -1)):
						# Device has attributes controlled by a Hue Device Attribute Controler.
						#   Update the controller device based on current bulb device states.
						#   But if the control destination device is off, update the value of the
						#   controller (virtual dimmer) to 0.
						if device.onState:
							# Destination Ambiance light device is on, update Attribute Controller brightness.
							if attributeToControl == "colorTemp":
								# Convert color temperature scale from 2000-6500 to 0-100.
								self.updateDeviceState(controlDevice, 'brightnessLevel', int(round((colorTemp - 2000.0) / 4500.0 * 100.0)))
						else:
							# Hue Device is off.  Set Attribute Controller device brightness level to 0.
							self.updateDeviceState(controlDevice, 'brightnessLevel', 0)

			# -- Light Strips --Extended color light
			elif dType == kLightStripsDeviceIDType:
				if 'brightnessLevel' not in device.states:
					self.doErrorLog("Device \"{}\" does not have state \"brightnessLevel\"".format(device.name), level=30)
					return 
				# Handle values common for "Color light" and "Extended color light" strips.
				if dType in ['Color light', 'Extended color light']:
					hue = bulb['state'].get('hue', 0)
					saturation = bulb['state'].get('sat', 0)
					colorX = bulb['state'].get('xy', [0.0,0.0])[0]
					colorY = bulb['state'].get('xy', [0.0,0.0])[1]
					colorMode = bulb['state'].get('colormode', "xy")
					#   Value manipulation.
					# Newer Hue bridge firmware doesn't report hue and saturation values for the original LightStrips, so
					#   if HSB values are zero but xyY values are not, use the xyY values to convert to RGB, otherwise use
					#   the HSB values.
					if hue == 0 and saturation == 0 and (colorX > 0 or colorY > 0):
						colorX = max(0.00001, colorX)
						colorY = max(0.00001, colorY)
						xyY = xyYColor(colorX, colorY, brightness / 255.0)
						rgb = xyY.convert_to('rgb')
						# Let's also convert the xyY color to HSB so that related device states in Indigo are updated correctly.
						hsb = xyY.convert_to('hsv')
						hue = int(round(hsb.hsv_h * 182.0))
						saturation = int(round(hsb.hsv_s * 255.0))
					else:
						hsb = HSVColor(hue / 182.0, saturation / 255.0, brightness / 255.0)
						rgb = hsb.convert_to('rgb')
					# RGB values will have a range of 0 to 255.
					colorRed = int(round(rgb.rgb_r))
					colorGreen = int(round(rgb.rgb_g))
					colorBlue = int(round(rgb.rgb_b))
					# Convert saturation from 0-255 scale to 0-100 scale.
					saturation = int(round(saturation * 100.0 / 255.0))
					# Convert hue from 0-65535 scale to 0-360 scale.
					self.normalizeHue(hue, device)
				# Handle color temperature values for "Extended color light" type devices.
				if dType in ['Extended color light', 'Color temperature light']:
					colorTemp = bulb['state'].get('ct', 0)
					# Must first test color temp value. If it's zero, the formula throws a divide by zero exception.
					if colorTemp > 0:
						# Converting from mireds to Kelvin.
						colorTemp = int(round(1000000.0/colorTemp))
					else:
						colorTemp = 0
					# Set the colorMode.
					colorMode = bulb['state'].get('colormode', "ct")


				if str(onState) == "False":
					colorRed = 0
					colorGreen = 0
					colorBlue = 0
					brightnessLevel = 0
					decimalPlaces = 0

				# Update the Indigo device if the Hue device is on.
				if str(onState) in ['True', 'False']:

					if device.states['brightnessLevel'] != brightnessLevel:
						if logChanges: self.indiLOG.log(sendLog, "Updated:  {:42s}  to {}".format(device.name, brightnessLevel))
						stateUpdateList = self.checkIfUpdateState(device , 'brightnessLevel', brightnessLevel, stateUpdateList=stateUpdateList )

					if dType in ['Color light', 'Extended color light']:
						# We test to see if each device state actually exists with Light Strips because
						#   a state may not exist in the device (despite the light type).
						#
						stateUpdateList = self.checkIfUpdateState(device , 'hue', hue, stateUpdateList=stateUpdateList )
						stateUpdateList = self.checkIfUpdateState(device , 'saturation', saturation, stateUpdateList=stateUpdateList )
						stateUpdateList = self.checkIfUpdateState(device , 'colorX', colorX, decimalPlaces=decimalPlaces, stateUpdateList=stateUpdateList )
						stateUpdateList = self.checkIfUpdateState(device , 'colorY', colorY, decimalPlaces=decimalPlaces, stateUpdateList=stateUpdateList )
						stateUpdateList = self.checkIfUpdateState(device , 'colorRed', colorRed, stateUpdateList=stateUpdateList )
						stateUpdateList = self.checkIfUpdateState(device , 'colorGreen', colorGreen, stateUpdateList=stateUpdateList )
						stateUpdateList = self.checkIfUpdateState(device , 'colorBlue', colorBlue, stateUpdateList=stateUpdateList )

					if dType in ['Extended color light', 'Color temperature light']:
						stateUpdateList = self.checkIfUpdateState(device , 'colorTemp', colorTemp, stateUpdateList=stateUpdateList )

					if dType in ['Color light', 'Extended color light', 'Color temperature light']:
						stateUpdateList = self.checkIfUpdateState(device , 'colorMode', colorMode, stateUpdateList=stateUpdateList )

					### Update inherited states for Indigo 7+ devices.
					# Only for devices capabile of color temperature...
					if dType in ['Extended color light', 'Color temperature light']:
						# White Level (negative saturation, 0-100).
						stateUpdateList = self.checkIfUpdateState(device , 'whiteLevel', 100 - saturation, uiValue="{}".format(int(100 - saturation)), stateUpdateList=stateUpdateList )
						# White Temperature (0-100).
						stateUpdateList = self.checkIfUpdateState(device , 'whiteTemperature', colorTemp, uiValue="{}".format(int(colorTemp)), stateUpdateList=stateUpdateList )

					if dType in ['Color light', 'Extended color light']:
						stateUpdateList = self.checkIfUpdateState(device , 'redLevel', int(round(colorRed * 100.0 / 255.0)), uiValue="{}".format(int(round(colorRed * 100.0 / 255.0))), stateUpdateList=stateUpdateList )
						stateUpdateList = self.checkIfUpdateState(device , 'greenLevel', int(round(colorGreen * 100.0 / 255.0)), uiValue="{}".format(int(round(colorGreen * 100.0 / 255.0))), stateUpdateList=stateUpdateList )
						stateUpdateList = self.checkIfUpdateState(device , 'blueLevel', int(round(colorBlue * 100.0 / 255.0)), uiValue="{}".format(int(round(colorBlue * 100.0 / 255.0))), stateUpdateList=stateUpdateList )

				else:
					# Unrecognized on state, but not important enough to mention in regular log.
					self.debugLog("LightStrip unrecognized on state given by bridge: {}".format(bulb['state']['on']))


				# Update any Hue Device Attribute Controller virtual dimmers associated with this bulb.
				for controlDeviceId in self.controlDeviceList:
					controlDevice = indigo.devices[int(controlDeviceId)]
					attributeToControl = controlDevice.pluginProps.get('attributeToControl', None)
					if deviceId == int(controlDevice.pluginProps.get('bulbDeviceId', -1)):
						# Device has attributes controlled by a Hue Device Attribute Controler.
						#   Update the controller device based on current bulb device states.
						#   But if the control destination device is off, update the value of the
						#   controller (virtual dimmer) to 0.
						if device.onState:
							# Destination Hue Bulb device is on, update Attribute Controller brightness.
							if attributeToControl == "hue":
								# Convert hue scale from 0-360 to 0-100.
								self.updateDeviceState(controlDevice, 'brightnessLevel', int(round(hue / 360.0 * 100.0)))
							elif attributeToControl == "saturation":
								self.updateDeviceState(controlDevice, 'brightnessLevel', saturation)
							elif attributeToControl == "colorRed":
								# Convert RGB scale from 0-255 to 0-100.
								self.updateDeviceState(controlDevice, 'brightnessLevel', int(round(colorRed * 100.0 / 255.0)))
							elif attributeToControl == "colorGreen":
								# Convert RGB scale from 0-255 to 0-100.
								self.updateDeviceState(controlDevice, 'brightnessLevel', int(round(colorGreen * 100.0 / 255.0)))
							elif attributeToControl == "colorBlue":
								# Convert RGB scale from 0-255 to 0-100.
								self.updateDeviceState(controlDevice, 'brightnessLevel', int(round(colorBlue * 100.0 / 255.0)))
							elif attributeToControl == "colorTemp" and dType in ['Extended color light', 'Color temperature light']:
								# Convert color temperature scale from 2000-6500 to 0-100.
								self.updateDeviceState(controlDevice, 'brightnessLevel', int(round((colorTemp - 2000.0) / 4500.0 * 100.0)))
						else:
							# Hue Device is off.  Set Attribute Controller device brightness level to 0.
							self.updateDeviceState(controlDevice, 'brightnessLevel', 0)

			# -- LivingColors --
			elif dType == kLivingColorsDeviceIDType:
				if 'brightnessLevel' not in device.states:
					self.doErrorLog("Device \"{}\" does not have state \"brightnessLevel\"".format(device.name), level=30)
					return 
				#   Value assignment.
				saturation = bulb['state'].get('sat', "0")
				hue = bulb['state'].get('hue', "0")
				colorX = bulb['state'].get('xy', [0,0])[0]
				colorY = bulb['state'].get('xy', [0,0])[1]
				colorRed = 255		# Initialize for later
				colorGreen = 255	# Initialize for later
				colorBlue = 255		# Initialize for later
				colorMode = bulb['state'].get('colormode', "xy")

				#   Value manipulation.
				# Convert from HSB to RGB, scaling the hue and saturation values appropriately.
				hsb = HSVColor(hue / 182.0, saturation / 255.0, brightness / 255.0)
				rgb = hsb.convert_to('rgb', rgb_type='wide_gamut_rgb')
				colorRed = int(round(rgb.rgb_r))
				colorGreen = int(round(rgb.rgb_g))
				colorBlue = int(round(rgb.rgb_b))
				# Convert saturation from 0-255 scale to 0-100 scale.
				saturation = int(round(saturation * 100.0 / 255.0))
				# Convert hue from 0-65535 scale to 0-360 scale.

				self.normalizeHue(hue, device)

				if str(onState) == "False":
					colorRed = 0
					colorGreen = 0
					colorBlue = 0
					brightnessLevel = 0
					decimalPlaces = 0


				# Update the Indigo device if the Hue device is on.
				if str(onState) in ['True', 'False']:
					if device.states['brightnessLevel'] != brightnessLevel:
						if logChanges: self.indiLOG.log(sendLog, "Updated:  {:42s}  to {}".format(device.name, brightnessLevel))
					stateUpdateList = self.checkIfUpdateState(device , 'brightnessLevel', brightnessLevel, stateUpdateList=stateUpdateList )
					stateUpdateList = self.checkIfUpdateState(device , 'hue', hue, stateUpdateList=stateUpdateList )
					stateUpdateList = self.checkIfUpdateState(device , 'saturation', saturation, stateUpdateList=stateUpdateList )
					stateUpdateList = self.checkIfUpdateState(device , 'colorX', colorX, decimalPlaces=decimalPlaces, stateUpdateList=stateUpdateList )
					stateUpdateList = self.checkIfUpdateState(device , 'colorY', colorY, decimalPlaces=decimalPlaces, stateUpdateList=stateUpdateList )
					stateUpdateList = self.checkIfUpdateState(device , 'colorRed', colorRed, stateUpdateList=stateUpdateList )
					stateUpdateList = self.checkIfUpdateState(device , 'colorGreen', colorGreen, stateUpdateList=stateUpdateList )
					stateUpdateList = self.checkIfUpdateState(device , 'colorBlue', colorBlue, stateUpdateList=stateUpdateList )
					stateUpdateList = self.checkIfUpdateState(device , 'colorMode', colorMode, stateUpdateList=stateUpdateList )

					stateUpdateList = self.checkIfUpdateState(device , 'redLevel', int(round(colorRed * 100.0 / 255.0)), uiValue="{}".format(int(round(colorRed * 100.0 / 255.0))), stateUpdateList=stateUpdateList )
					stateUpdateList = self.checkIfUpdateState(device , 'greenLevel', int(round(colorGreen * 100.0 / 255.0)), uiValue="{}".format(int(round(colorGreen * 100.0 / 255.0))), stateUpdateList=stateUpdateList )
					stateUpdateList = self.checkIfUpdateState(device , 'blueLevel', int(round(colorBlue * 100.0 / 255.0)), uiValue="{}".format(int(round(colorBlue * 100.0 / 255.0))), stateUpdateList=stateUpdateList )

				else:
					# Unrecognized on state, but not important enough to mention in regular log.
					self.debugLog("LivingColors unrecognized on state given by bridge: {}".format(bulb['state']['on']))

				# Update any Hue Device Attribute Controller virtual dimmers associated with this bulb.
				for controlDeviceId in self.controlDeviceList:
					controlDevice = indigo.devices[int(controlDeviceId)]
					attributeToControl = controlDevice.pluginProps.get('attributeToControl', None)
					if deviceId == int(controlDevice.pluginProps.get('bulbDeviceId', -1)):
						# Device has attributes controlled by a Hue Device Attribute Controler.
						#   Update the controller device based on current bulb device states.
						#   But if the control destination device is off, update the value of the
						#   controller (virtual dimmer) to 0.
						if device.onState:
							# Destination Hue Bulb device is on, update Attribute Controller brightness.
							if attributeToControl == "hue":
								# Convert hue scale from 0-360 to 0-100.
								self.updateDeviceState(controlDevice, 'brightnessLevel', int(round(hue * 100. / 360.0)))
							elif attributeToControl == "saturation":
								self.updateDeviceState(controlDevice, 'brightnessLevel', saturation)
							elif attributeToControl == "colorRed":
								# Convert RGB scale from 0-255 to 0-100.
								self.updateDeviceState(controlDevice, 'brightnessLevel', int(round(colorRed * 100.0 / 255.0)))
							elif attributeToControl == "colorGreen":
								# Convert RGB scale from 0-255 to 0-100.
								self.updateDeviceState(controlDevice, 'brightnessLevel', int(round(colorGreen * 100.0 / 255.0)))
							elif attributeToControl == "colorBlue":
								# Convert RGB scale from 0-255 to 0-100.
								self.updateDeviceState(controlDevice, 'brightnessLevel', int(round(colorBlue * 100.0 / 255.0)))
						else:
							# Hue Device is off.  Set Attribute Controller device brightness level to 0.
							self.updateDeviceState(controlDevice, 'brightnessLevel', 0)

			# -- LivingWhites --
			elif dType == kLivingWhitesDeviceIDType:
				if 'brightnessLevel' not in device.states:
					self.doErrorLog("Device \"{}\" does not have state \"brightnessLevel\"".format(device.name), level=30)
					return 
				# Update the Indigo device if the Hue device is on.
				# Update the Indigo device if the Hue device is on.
				if str(onState) == "True":
					# Update the brightness level if it's different.
					if device.states['brightnessLevel'] != brightnessLevel:
						# Log the update.
						if logChanges: self.indiLOG.log(sendLog, "Updated:  {:42s}  to {}, on".format(device.name, brightnessLevel))
						stateUpdateList = self.checkIfUpdateState(device , 'brightnessLevel', brightnessLevel, stateUpdateList=stateUpdateList )
				elif str(onState) == "False":
					# Hue device is off. Set brightness to zero.
					if device.states['brightnessLevel'] != 0:
						# Log the update.
						if logChanges: self.indiLOG.log(sendLog, "Updated:  {:42s}  to {}, off".format(device.name, brightnessLevel))
						stateUpdateList = self.checkIfUpdateState(device , 'brightnessLevel', brightnessLevel, stateUpdateList=stateUpdateList )
				else:
					# Unrecognized on state, but not important enough to mention in regular log.
					self.debugLog(u"LivingWhites unrecognized on state given by bridge: {}".format(bulb['state']['on']))

			# There won't any Hue Device Attribute Controller virtual dimmers associated with this bulb,
				# so we won't bother checking them.

			# -- On/Off Only Device --
			elif dType[0:len(kOnOffOnlyDeviceIDType)] == kOnOffOnlyDeviceIDType:
				pass
				# all updates done at beginning
				# There won't be any Hue Device Attribute Controller virtual dimmers associated with this device,
				# so we won't bother checking..

			else:
				# Unrecognized model ID.
				if not self.unsupportedDeviceWarned:
					self.doErrorLog("The \"{}\" device has an unrecognized model ID:{}.  Hue Lights plugin does not support this device.".format( device.name,  bulb.get('modelid', "")))
					self.unsupportedDeviceWarned = True
			# End of model ID matching if/then test.


			self.updateDeviceState(device, stateUpdateList, calledFrom="parseOneHueLightsData")

		except Exception:
			self.logger.error("for devId:{}; devName:{}".format(deviceId, devName), exc_info=True)

		return


	# Parse All Hue Groups Data
	########################################
	def parseAllHueGroupsData(self):
		if self.decideMyLog("UpdateIndigoDevices"): self.indiLOG.log(10,"Starting parseAllHueGroupsData.")

		# Iterate through all the Indigo devices and look for Hue group changes in the
		#   groups  that changed, then update the Indigo device states and properties
		#   as needed.  This method does no actual Hue bridge communication.  It just updates
		#   Indigo devices with information already obtained through the use of the
		#   self.updateGroupsList.

		# Start going through all the devices in the self.deviceList and update any Indigo
		#   devices that are controlling the Hue group devices.
		try:
			for deviceId in copy.deepcopy(self.deviceList):
				if self.deviceList[deviceId].get('typeId',-1) not in kGroupDeviceTypeIDs: continue
				device = indigo.devices[deviceId]
				pluginProps = device.pluginProps
				if device.deviceTypeId in kGroupDeviceTypeIDs:
					if "hubNumber" not in pluginProps:
						self.indiLOG.log(30,"parseAllHueGroupsData device>{}< not properly setup, please select bridge# in device edit".format(device.name))
						continue
					hubNumber = pluginProps['hubNumber']
					if hubNumber not in self.hueConfigDict:
						if time.time() - self.lastReminderHubNumberNotPresent > 200: 
							self.indiLOG.log(30,"parseAllHueGroupsData bridge#:{} not in hue Bridge data".format(hubNumber))
							self.lastReminderHubNumberNotPresent = time.time()
						continue
					if "groups" in self.hueConfigDict[hubNumber]:
						if pluginProps['groupId'] in self.hueConfigDict[hubNumber]['groups']:
							self.parseOneHueGroupData(self.hueConfigDict[hubNumber]['groups'][pluginProps['groupId']], device)
							
		except Exception:
			self.logger.error("", exc_info=True)

	# Parse One Hue Group Data
	########################################
	def parseOneHueGroupData(self, group, device):

		# Take the groupId and device passed to this method, look up the data already obtained from the Hue bridge
		# and parse the bridge data for this group, making changes to the Indigo device as needed.

		# Take the groupId and device passed to this method, look up the data already obtained from the Hue bridge
		# and parse the bridge data for this group, making changes to the Indigo device as needed.
		try:
			logChanges = (self.pluginPrefs['logAnyChanges'] == "yes") or self.trackSpecificDevice == device.id or (self.pluginPrefs['logAnyChanges'] == "leaveToDevice" and device.pluginProps.get('logChanges', True))
			if self.decideMyLog("UpdateIndigoDevices"): self.indiLOG.log(10,"Starting parseOneHueGroupData.")
			if self.trackSpecificDevice == device.id:	
				sendLog = 20
				self.indiLOG.log(sendLog, "Hue Groups tracking:{}".format(group) ) 
			else: 	sendLog = self.sendDeviceUpdatesTo

			deviceId = device.id
			decimalPlaces = 4
			stateUpdateList = []
			# Separate out the specific Hue group data.
			stateUpdateList = self.checkIfUpdateState(device, 'lightIds', ",".join(group.get('lights', "")), stateUpdateList=stateUpdateList )
			stateUpdateList = self.checkIfUpdateState(device, 'sensorIds', ",".join(group.get('sensors', "")), stateUpdateList=stateUpdateList )
			nameOnBridge = group.get('name', "")
			groupType = group.get('type', "")
			groupClass = group.get('class', "")
			stateUpdateList = self.checkIfUpdateState(device, 'groupClass', groupClass, stateUpdateList=stateUpdateList )
			if "action" not in group:
				self.indiLOG.log(20, "no action key in dev:{}, group:{}".format(device.id, group))
				return 
			brightness = group['action'].get('bri', 0)
			onState = group['action'].get('on', False)
			allOn = group['state'].get('all_on', False)
			anyOn = group['state'].get('any_on', False)
			# Use a generic yellow hue as default if there isn't a hue.
			hue = group['action'].get('hue', 10920)
			saturation = group['action'].get('sat', 0)
			# Use a neutral colorX and Y value as default if one isn't there.
			colorX = group['action'].get('xy', [0.5128, 0.4147])[0]
			colorY = group['action'].get('xy', [0.5128, 0.4147])[1]
			colorRed = 255		# Initialize for later
			colorGreen = 255	# Initialize for later
			colorBlue = 255		# Initialize for later
			# Assign a generic 2800 K (357 mired) color temperature if one doesn't exist.
			colorTemp = group['action'].get('ct', 357)
			# Use "ct" as the color mode if one wasn't specified.
			colorMode = group['action'].get('colormode', "ct")
			# groupMemberIDs is populated a few lines down.
			groupMemberIDs = ""

			stateUpdateList = self.checkIfUpdateState(device, 'nameOnBridge', nameOnBridge, stateUpdateList=stateUpdateList )
			stateUpdateList = self.checkIfUpdateState(device, 'type', groupType, stateUpdateList=stateUpdateList )
			stateUpdateList = self.checkIfUpdateState(device, 'alertMode', group['action'].get('alert', ""), stateUpdateList=stateUpdateList )
			stateUpdateList = self.checkIfUpdateState(device, 'effect', group['action'].get('effect', ""), stateUpdateList=stateUpdateList )


			i = 0		# To count members in group.
			for tempMemberID in group['lights']:
				if i > 0:
					groupMemberIDs = "{}, {}".format(groupMemberIDs, tempMemberID)
				else:
					groupMemberIDs = tempMemberID
				i += 1
			# Clear the "i" variable.
			del i

			#   Value manipulation.
			# Convert brightness from 0-255 range to 0-100 range.
			brightnessLevel = int(round(brightness * 100.0 / 255.0))
			# Compensate for incorrect rounding to zero if original brightness is not zero.
			if brightnessLevel == 0 and brightness > 0:
				brightnessLevel = 1

			# Convert from HSB to RGB, scaling the hue and saturation values appropriately.
			hsb = HSVColor(hue / 182.0, saturation / 255.0, brightness / 255.0)
			rgb = hsb.convert_to('rgb', rgb_type='wide_gamut_rgb')
			colorRed = int(round(rgb.rgb_r))
			colorGreen = int(round(rgb.rgb_g))
			colorBlue = int(round(rgb.rgb_b))
			# Convert saturation from 0-255 scale to 0-100 scale.
			saturation = int(round(saturation * 100.0 / 255.0))
			# Convert hue from 0-65535 scale to 0-360 scale.
			hue = self.normalizeHue(hue, device)
			# Must first test color temp value. If it's zero, the formula throws a divide by zero execption.
			if colorTemp > 0:
				# Converting from mireds to Kelvin.
				colorTemp = int(round(1000000.0/colorTemp))
			else:
				colorTemp = 0

			#   Update Indigo states and properties common to all Hue devices.
			tempProps = device.pluginProps
			# Update the Hue group name.
			if nameOnBridge != tempProps.get('nameOnBridge', False):
				tempProps['nameOnBridge'] = nameOnBridge
				self.updateDeviceProps(device, tempProps)
			# Update the group type.
			if groupType != tempProps.get('type', False):
				tempProps['type'] = groupType
				self.updateDeviceProps(device, tempProps)
			# Update the group class.
			if groupClass != tempProps.get('groupClass', False):
				tempProps['groupClass'] = groupClass
				self.updateDeviceProps(device, tempProps)
			# Update the allOn state of the Hue group.
			stateUpdateList = self.checkIfUpdateState(device, 'allOn', allOn, stateUpdateList=stateUpdateList )
			# Update the anyOn state.
			stateUpdateList = self.checkIfUpdateState(device, 'anyOn', anyOn, stateUpdateList=stateUpdateList )
			# Update the group member IDs.
			stateUpdateList = self.checkIfUpdateState(device, 'groupMemberIDs', groupMemberIDs, stateUpdateList=stateUpdateList )

			if str(onState) == "False":
				colorRed = 0
				colorGreen = 0
				colorBlue = 0
				brightnessLevel = 0
				decimalPlaces = 0

			# Update the Indigo device if the Hue device is on.
			if str(onState) in ['True', 'False']:
				# Update the brightness level if it's different.
					
				if device.states['brightnessLevel'] != brightnessLevel:
					if logChanges: self.indiLOG.log(sendLog, "Updated:  {:42s}  to {}".format(device.name, brightnessLevel))

				stateUpdateList = self.checkIfUpdateState(device , 'brightnessLevel', brightnessLevel, stateUpdateList=stateUpdateList )
				stateUpdateList = self.checkIfUpdateState(device , 'hue', hue, stateUpdateList=stateUpdateList )
				stateUpdateList = self.checkIfUpdateState(device , 'saturation', saturation, stateUpdateList=stateUpdateList )
				stateUpdateList = self.checkIfUpdateState(device , 'colorX', colorX, decimalPlaces=decimalPlaces, stateUpdateList=stateUpdateList )
				stateUpdateList = self.checkIfUpdateState(device , 'colorY', colorY, decimalPlaces=decimalPlaces, stateUpdateList=stateUpdateList )
				stateUpdateList = self.checkIfUpdateState(device , 'colorRed', colorRed, stateUpdateList=stateUpdateList )
				stateUpdateList = self.checkIfUpdateState(device , 'colorGreen', colorGreen, stateUpdateList=stateUpdateList )
				stateUpdateList = self.checkIfUpdateState(device , 'colorBlue', colorBlue, stateUpdateList=stateUpdateList )
				stateUpdateList = self.checkIfUpdateState(device , 'colorTemp', colorTemp, stateUpdateList=stateUpdateList )
				stateUpdateList = self.checkIfUpdateState(device , 'colorMode', colorMode, stateUpdateList=stateUpdateList )

				stateUpdateList = self.checkIfUpdateState(device , 'whiteLevel', 100 - saturation, uiValue="{}".format(int(100 - saturation)), stateUpdateList=stateUpdateList )
				stateUpdateList = self.checkIfUpdateState(device , 'whiteTemperature', colorTemp, uiValue="{}".format(int(colorTemp)), stateUpdateList=stateUpdateList )
				stateUpdateList = self.checkIfUpdateState(device , 'redLevel', int(round(colorRed * 100.0 / 255.0)), uiValue="{}".format(int(round(colorRed * 100.0 / 255.0))), stateUpdateList=stateUpdateList )
				stateUpdateList = self.checkIfUpdateState(device , 'greenLevel', int(round(colorGreen * 100.0 / 255.0)), uiValue="{}".format(int(round(colorGreen * 100.0 / 255.0))), stateUpdateList=stateUpdateList )
				stateUpdateList = self.checkIfUpdateState(device , 'blueLevel', int(round(colorBlue * 100.0 / 255.0)), uiValue="{}".format(int(round(colorBlue * 100.0 / 255.0))), stateUpdateList=stateUpdateList )

			else:
				# Unrecognized on state, but not important enough to mention in regular log.
				self.debugLog("Hue group unrecognized on state given by bridge: {}".format(group['action']['on']))

			# Update any Hue Device Attribute Controller virtual dimmers associated with this group.
			for controlDeviceId in self.controlDeviceList:
				controlDevice = indigo.devices[int(controlDeviceId)]
				attributeToControl = controlDevice.pluginProps.get('attributeToControl', None)
				if deviceId == int(controlDevice.pluginProps.get('bulbDeviceId', -1)):
					# Device has attributes controlled by a Hue Device Attribute Controler.
					#   Update the controller device based on current group device states.
					#   But if the control destination device is off, update the value of the
					#   controller (virtual dimmer) to 0.
					if device.onState:
						# Destination Hue Group device is on, update Attribute Controller brightness.
						if attributeToControl == "hue":
							# Convert hue scale from 0-360 to 0-100.
							self.updateDeviceState(controlDevice, 'brightnessLevel', int(round(hue / 360.0 * 100.0)))
						elif attributeToControl == "saturation":
							self.updateDeviceState(controlDevice, 'brightnessLevel', saturation)
						elif attributeToControl == "colorRed":
							# Convert RGB scale from 0-255 to 0-100.
							self.updateDeviceState(controlDevice, 'brightnessLevel', int(round(colorRed * 100.0 / 255.0)))
						elif attributeToControl == "colorGreen":
							# Convert RGB scale from 0-255 to 0-100.
							self.updateDeviceState(controlDevice, 'brightnessLevel', int(round(colorGreen * 100.0 / 255.0)))
						elif attributeToControl == "colorBlue":
							# Convert RGB scale from 0-255 to 0-100.
							self.updateDeviceState(controlDevice, 'brightnessLevel', int(round(colorBlue * 100.0 / 255.0)))
						elif attributeToControl == "colorTemp":
							# Convert color temperature scale from 2000-6500 to 0-100.
							self.updateDeviceState(controlDevice, 'brightnessLevel', int(round((colorTemp - 2000.0) / 4500.0 * 100.0)))
					else:
						# Indigo Device is off.  Set Attribute Controller device brightness level to 0.
						self.updateDeviceState(controlDevice, 'brightnessLevel', 0)
					# End if device onState is True.
				# End if this device is an the current attribute controller device.
			# End loop through attribute controller device list.
			self.updateDeviceState(device, stateUpdateList)
		except Exception:
			self.logger.error("", exc_info=True)


	# Parse All Hue Sensors Data
	########################################
	def parseAllHueSensorsData(self):
		if self.decideMyLog("UpdateIndigoDevices"): self.debugLog("Starting parseAllHueSensorsData.")

		# Itterate through all the Indigo devices and look for Hue sensor changes in the
		#   sensors that changed, then update the Indigo device states and properties
		#   as needed.  This method does no actual Hue bridge communication.  It just updates
		#   Indigo devices with information already obtained through the use of the

		# Start going through all the devices in the self.deviceList and update any Indigo
		#   devices that are controlling the Hue sensors devices.
		try:
			for deviceId in copy.deepcopy(self.deviceList):
				if self.deviceList[deviceId].get('typeId',-1) not in kSensorTypeList: continue
				device = indigo.devices[deviceId]
				#self.indiLOG.log(20,"parseAllHueSensorsData  dev>{}< type:{}, devlisttype:{}".format(device.name, device.deviceTypeId, self.deviceList[deviceId]  ))
				if device.deviceTypeId in kSensorTypeList:
					hubNumber = device.pluginProps['hubNumber']
					if hubNumber not in self.hueConfigDict:
						if time.time() - self.lastReminderHubNumberNotPresent > 200: 
							self.indiLOG.log(30,"parseAllHueSensorsData hubNumber:{} / dev>{}< not in dict".format(hubNumber, device.name))
							self.lastReminderHubNumberNotPresent = time.time()
						continue
					if "sensors" in self.hueConfigDict[hubNumber]:
						if device.pluginProps['sensorId'] in self.hueConfigDict[hubNumber]['sensors'] :
							self.parseOneHueSensorData(self.hueConfigDict[hubNumber]['sensors'][device.pluginProps['sensorId']], device)
		except Exception:
			self.logger.error("", exc_info=True)
		return 

	# Parse One Hue theDict Data
	########################################
	def parseOneHueSensorData(self, sensor, device):
		#self.indiLOG.log(20,"Starting parseOneHueSensorData. device:{:25s}".format(device.name))
		sensorValue = ""
		try:
			logChanges = (self.pluginPrefs['logAnyChanges'] == "yes") or self.trackSpecificDevice == device.id or (self.pluginPrefs['logAnyChanges'] == "leaveToDevice" and device.pluginProps.get('logChanges', True))
			if self.trackSpecificDevice == device.id:	
				sendLog = 20
				self.indiLOG.log(sendLog, "Hue Sensors tracking:{}".format(sensor) ) 
			else: 	
				sendLog = self.sendDeviceUpdatesTo


			stateUpdateList = []


			#if device.id == 75886730: self.indiLOG.log(20,"parseOneHueSensorData  dev>{}< type:{}, sensor:{}".format(device.name, device.deviceTypeId, sensor ))

			if "state" in sensor:
				try: 	lastUpdated = datetime.datetime.strptime(sensor['state'].get('lastupdated', ""),'%Y-%m-%dT%H:%M:%S').strftime('%Y-%m-%d %H:%M:%S')
				except:	lastUpdated = ""
			else:
				lastUpdated 	= ""

			if 'config' in sensor:
				enabledOnHub 	= sensor['config'].get('on', True)
				online 			= str(sensor['config'].get('reachable', "notSupported")) # if found it is 'True' or 'False', otherwise set to 'notSupported'
				if online == "notSupported" and enabledOnHub:
					device.setErrorStateOnServer("")
				else:
					if online not in ['True','notSupported']:
						if device.states['online']:
							device.updateStateOnServer('online', False)
						device.setErrorStateOnServer("disconnected")
						return
					elif online == "notSupported" and not enabledOnHub:
						if not device.states['online']:
							device.updateStateOnServer('online', False)
						device.setErrorStateOnServer("disabled")
						return
					else:
						device.setErrorStateOnServer("")
				stateUpdateList = self.checkIfUpdateState(device, 'online', 		True, stateUpdateList=stateUpdateList )
				stateUpdateList = self.checkIfUpdateState(device, 'ledEnabled', 	sensor['config'].get('ledindication', False), stateUpdateList=stateUpdateList )
				stateUpdateList = self.checkIfUpdateState(device, 'testMode', 		sensor['config'].get('usertest', False), stateUpdateList=stateUpdateList )
				stateUpdateList = self.checkIfUpdateState(device, 'alertMode', 		sensor['config'].get('alert', "none"), stateUpdateList=stateUpdateList )
				stateUpdateList = self.checkIfUpdateState(device, 'batteryLevel',	sensor['config'].get('battery', 0), stateUpdateList=stateUpdateList )

			else:
				enabledOnHub 	= False

			nameOnBridge 		= sensor.get('name', "")
			uniqueId 			= sensor.get('uniqueid', "")
			productId 			= sensor.get('productid', "")
			swVersion 			= sensor.get('swversion', "")
			manufacturerName 	= sensor.get('manufacturername', "")
			sensorType 			= sensor.get('type', "")
			modelId 			= sensor.get('modelid', "")
			stateUpdateList = self.checkIfUpdateState(device, 'nameOnBridge', 		nameOnBridge, stateUpdateList=stateUpdateList )
			stateUpdateList = self.checkIfUpdateState(device, 'uniqueId', 			uniqueId, stateUpdateList=stateUpdateList )
			stateUpdateList = self.checkIfUpdateState(device, 'swVersion', 			swVersion, stateUpdateList=stateUpdateList )
			stateUpdateList = self.checkIfUpdateState(device, 'manufacturerName', 	manufacturerName, stateUpdateList=stateUpdateList )
			stateUpdateList = self.checkIfUpdateState(device, 'type', 				sensorType, stateUpdateList=stateUpdateList )
			stateUpdateList = self.checkIfUpdateState(device, 'modelId', 			modelId, stateUpdateList=stateUpdateList )

			tempProps = device.pluginProps
			# Update the device properties.
			tempProps['nameOnBridge'] = nameOnBridge
			tempProps['uniqueId'] = uniqueId
			tempProps['productId'] = productId
			tempProps['manufacturerName'] = manufacturerName
			tempProps['swVersion'] = swVersion
			tempProps['type'] = sensorType
			tempProps['modelId'] = modelId
			tempProps['enabledOnHub'] = enabledOnHub


			changedTimeStamp = lastUpdated != device.states['lastUpdated']




			# -- Hue Motion Sensor (Motion) --
			if device.deviceTypeId == "hueMotionSensor":
				## self.debugLog("parseOneHueSensorData: Parsing Hue sensor ID %s (\"%s\")." % (device.pluginProps.get('sensorId', ""), sensor.get('name', "no name")))

				# Separate out the specific Hue sensor data.
				sensitivity = sensor['config'].get('sensitivity', 0)
				sensitivityMax = sensor['config'].get('sensitivitymax', 0)
				onStateBool = sensor['state'].get('presence', False)
				# Convert True/False onState to on/off values.  Note that the value can be None if the sensor is disabled on the bridge.
				if onStateBool:
					onState = "on"
					sensorIcon = indigo.kStateImageSel.MotionSensorTripped
				else:
					onState = "off"
					sensorIcon = indigo.kStateImageSel.MotionSensor


				# Update the states on the device.
				stateUpdateList = self.checkIfUpdateState(device, 'sensitivity', sensitivity, stateUpdateList=stateUpdateList )
				stateUpdateList = self.checkIfUpdateState(device, 'sensitivityMax', sensitivityMax, stateUpdateList=stateUpdateList )


				# Update the device on state.  Only update if the device is enabled on the bridge though.
				if enabledOnHub:
					# Log any change to the onState.
					if onStateBool != device.onState:
						if logChanges: self.indiLOG.log(sendLog, "Received: {:42s}  {}".format(device.name, onState))
					stateUpdateList = self.checkIfUpdateState(device, 'onOffState', onStateBool, uiValue=onState, uiImage=sensorIcon, stateUpdateList=stateUpdateList )
				# Update the error state if needed.
			# End if this is a Hue motion sensor.

			# -- Hue Motion Sensor (Temperature) --
			if device.deviceTypeId == "hueMotionTemperatureSensor":
				## self.debugLog("parseOneHueSensorData: Parsing Hue sensor ID %s (\"%s\")." % (device.pluginProps.get('sensorId', ""), sensor.get('name', "no name")))

				# Separate out the specific Hue sensor data.
				# Get the name of the sensor as it appears on the Hue bridge.
				temperatureRaw = sensor['state'].get('temperature', 0)


				# Get the calibration offset specified in the device settings.
				sensorOffset = device.pluginProps.get('sensorOffset', 0)
				try:
					sensorOffset = round(float(sensorOffset), 1)
				except Exception:
					# If there's any conversion error, just use a zero offset.
					sensorOffset = 0.0
				# Get the temperature scale specified in the device settings.
				temperatureScale = device.pluginProps.get('temperatureScale', "c")
				# Only perform temperature conversion calculations of the sensor is enabled on the bridge.
				if enabledOnHub:
					# Convert raw temperature reading to Celcius and apply the calibration
					# offset based on selected temperature scale.
					temperatureC = round(float(temperatureRaw / 100.0), 1)
					if temperatureScale == "c":
						temperatureC = temperatureC + sensorOffset
						temperatureF = round(float(temperatureC * 9.0 / 5.0 + 32.0 ), 1)
						temperatureC = round(temperatureC, 1)
					else:
						temperatureF = float((temperatureRaw / 100.0) * 9.0 / 5.0 + 32.0 + sensorOffset)
						temperatureC = round(float((temperatureF - 32.0) * 5.0 / 9.0), 1)
						temperatureF = round(temperatureF, 1)
					# Set the sensor value based on the device temperature scale prefs.
					if temperatureScale == "f":
						sensorValue = temperatureF
						sensorUiValue = "{} \xbaF".format(sensorValue) + ""
					else:
						sensorValue = temperatureC
						sensorUiValue = "{} \xbaC".format(sensorValue) + ""

				sensorIcon = indigo.kStateImageSel.TemperatureSensor
				sensorPrecision = 1

				# Update the states on the device.

				# Update the device sensorValue state.  Only update if the device is enabled on the bridge though.
				if enabledOnHub:
					# Log any change to the sensorValue.
					if sensorValue != device.sensorValue:
						if logChanges: self.indiLOG.log(sendLog, "Received: {:42s}  {}".format(device.name, sensorUiValue))
					stateUpdateList = self.checkIfUpdateState(device, 'temperatureC', temperatureC, decimalPlaces=sensorPrecision, stateUpdateList=stateUpdateList )
					stateUpdateList = self.checkIfUpdateState(device, 'temperatureF', temperatureF, decimalPlaces=sensorPrecision, stateUpdateList=stateUpdateList )
					stateUpdateList = self.checkIfUpdateState(device, 'sensorValue',  sensorValue, 	decimalPlaces=sensorPrecision, stateUpdateList=stateUpdateList,  uiValue=sensorUiValue, uiImage=sensorIcon )

			# -- Hue Motion Sensor (Luninance) --
			if device.deviceTypeId == "hueMotionLightSensor":
				## self.debugLog("parseOneHueSensorData: Parsing Hue sensor ID %s (\"%s\")." % (device.pluginProps.get('sensorId', ""), sensor.get('name', "no name")))

				# Separate out the specific Hue sensor data.
				# Get the name of the sensor as it appears on the Hue bridge.
				luminanceRaw = sensor['state'].get('lightlevel', 0)
				dark = sensor['state'].get('dark', True)
				# If a sensor is disabled on the bridge, the value will be None so we have to account for this.
				if dark is None:
					dark = True
				daylight = sensor['state'].get('daylight', False)
				# If a sensor is disabled on the bridge, the value will be None so we have to account for this.
				if daylight is None:
					daylight = False
				darkThreshold = sensor['config'].get('tholddark', 0)
				thresholdOffset = sensor['config'].get('tholdoffset', 0)


				# Only convert raw luminance values to lux if the sensor is enabled on the bridge.
				if enabledOnHub:
					# Convert raw luminance reading to lux.
					try:
						luminance = pow(10.0, (luminanceRaw - 1.0) / 10000.0)
						darkThreshold = pow(10.0, (darkThreshold - 1.0) / 10000.0)
						thresholdOffset = pow(10.0, (thresholdOffset - 1.0) / 10000.0)
					except TypeError:
						# In rare circumstances, the value returned from the Hue bridge for
						# luminanceRaw might not be a number.  Rather than throw a Python
						# error in the Indigo log, let's just ignore the error and set
						# the lux value and the thresholds to 0 for now.
						luminance = 0.0
						darkThreshold = 0.0
						thresholdOffset = 0.0

					# If the luminanceRaw value is 0, that means the light level is blow
					# detectable levels, which should be reported as a light level of 0 lux.
					if luminanceRaw == 0:
						luminance = 0.0

					# Determine to how many decimal places the sensor value should be
					# rounded based on how much luminance there is.
					if 0 < luminance < 10:
						sensorPrecision = 2
					elif 10 <= luminance < 100:
						sensorPrecision = 1
					else:
						sensorPrecision = 0
					# Now round and set the sensorValue.
					if sensorPrecision > 0:
						sensorValue = round(luminance, sensorPrecision)
					else:
						sensorValue = int(round(luminance, 0))
					sensorUiValue = "{} lux".format(sensorValue)

				# Now do the same for the darkThreshold and thresholdOffset values.
				if 0 < darkThreshold < 10:
					thresholdPrecision = 2
				elif 10 <= darkThreshold < 100:
					thresholdPrecision = 1
				else:
					thresholdPrecision = 0
				if thresholdPrecision > 0:
					darkThreshold = round(darkThreshold, thresholdPrecision)
				else:
					darkThreshold = int(round(darkThreshold, 0))

				if 0 < thresholdOffset < 10:
					offsetPrecision = 2
				elif 10 <= thresholdOffset < 100:
					offsetPrecision = 1
				else:
					offsetPrecision = 0
				# Now round and set the sensorValue.
				if offsetPrecision > 0:
					thresholdOffset = round(thresholdOffset, offsetPrecision)
				else:
					thresholdOffset = int(round(thresholdOffset, 0))

				# Set the sensor on state based on whether it's daylight or not.
				if daylight:
					sensorIcon = indigo.kStateImageSel.LightSensorOn
				else:
					sensorIcon = indigo.kStateImageSel.LightSensor

				if True:
					stateUpdateList = self.checkIfUpdateState(device, 'dark', 			dark, 			stateUpdateList=stateUpdateList )
					stateUpdateList = self.checkIfUpdateState(device, 'darkThreshold',	darkThreshold,	stateUpdateList=stateUpdateList )
					stateUpdateList = self.checkIfUpdateState(device, 'daylight', 		daylight, 		stateUpdateList=stateUpdateList )

				# Update the sensor value, but only if the sensor is enabled on the bridge.
				if enabledOnHub:
					# Log any change to the sensorValue.
					if sensorValue != device.sensorValue:
						if logChanges: self.indiLOG.log(sendLog, "Received: {:42s}  {}".format(device.name, sensorUiValue))
					stateUpdateList = self.checkIfUpdateState(device, 'luminance', 		luminance, 		stateUpdateList=stateUpdateList, decimalPlaces=sensorPrecision )
					stateUpdateList = self.checkIfUpdateState(device, 'luminanceRaw',	luminanceRaw,	stateUpdateList=stateUpdateList, decimalPlaces=sensorPrecision )
					stateUpdateList = self.checkIfUpdateState(device, 'sensorValue', 	sensorValue,  	stateUpdateList=stateUpdateList, decimalPlaces=sensorPrecision,	uiValue=sensorUiValue, uiImage=sensorIcon, )

			# -- Hue Dimmer Switch --
			if device.deviceTypeId in keventButtonSettings:
				shortcut = keventButtonSettings[device.deviceTypeId]
				#deviceMode = sensor['config'].get('devicemode', "") not used

				errorFound 		= 0
				lastButtonPressed 	= 0
				onStateBool 		= False
				buttonOn			= False
				buttonHold			= False
				buttonReleaseShort	= False
				buttonReleaseLong	= False
				buttonLongPress		= False
				buttonRelease 		= False
				buttonBeingHeld 	= False
				eventType 			= -1

				buttonEventID	= sensor['state'].get('buttonevent', 0)
				if buttonEventID is None:	buttonEventID = 0
				if buttonEventID == 0: 		errorFound = 1

				if errorFound == 0:
					try:
						ii = buttonEventID//shortcut['findbuttonNumbers']['//'] # for eg evtypeID = 3002 gives 3
						if ii not in shortcut['findbuttonNumbers']['buttonNumbers']:
							errorFound = 2
						else:		
							lastButtonPressed = shortcut['findbuttonNumbers']['buttonNumbers'][ii]
							if  lastButtonPressed == 0: 
								errorFound = 3
							else:
								kk = buttonEventID%shortcut['findEventType']['%']  # for eg evtypeID = 3002 gives 2
								if kk not in shortcut['findEventType']['evType']:
									errorFound = 4
								else:
									eventType = shortcut['findEventType']['evType'][kk]
					except Exception:
						errorFound = 5
						self.indiLOG.log(self.sendDeviceUpdatesTo, "{:42s} dType:{}, buttonEID: {},  eventType:{}, lastButtonPressed:{}, errorFound:{}".format(device.name, device.deviceTypeId, buttonEventID, eventType, lastButtonPressed, errorFound))
				
					 
				if errorFound == 0:
					if eventType == 0 and shortcut['eventTypesEnabled'][eventType]:
						# Update the last button pressed state variable.
						# Sometimes the Hue bridge doesn't detect button releases from the Dimmer Switch and
						#   will continue to show the most recent button event as the initial press event.
						#   If the lastUpdated value from the Hue bridge hasn't changed, then allow the button
						#   on state to revert back to OFF (False) as set above. But if the lastUpdated value
						#   from the Hue bridge is different, then this must be a new initial button press,
						#   so set the button on state to True.
						if changedTimeStamp:
							buttonOn = True
							# Log any change to the onState.
							if logChanges: self.indiLOG.log(sendLog, "Received: {:42s}  {}  {}".format(device.name, shortcut['buttontexts'][lastButtonPressed], shortcut['textSuffix'][eventType]))

					elif eventType == 1 and shortcut['eventTypesEnabled'][eventType]:
						buttonOn = True
						buttonHold = True
						# Don't write to the Indigo log unless this is the first time this status has been seen.
						if buttonHold != device.states[shortcut['stateNames'][lastButtonPressed]+shortcut['stateSuffix'][1]]:
							if logChanges: self.indiLOG.log(sendLog, "Received: {:42s}  {}  {}".format(device.name, shortcut['buttontexts'][lastButtonPressed],  shortcut['textSuffix'][eventType]))

					elif eventType == 2 and shortcut['eventTypesEnabled'][eventType]:
						buttonReleaseShort = True
						# We're checking to see if a button press event was missed since we can only check the
						#   Hue bridge every 2 seconds or so.  If the last button event was a button release
						#   but the current device state for the button shows it was never on, and the lastUpdated
						#   time on the Hue bridge is different than that in the Indigo device, then the button
						#   had to have been pressed at some point, so we'll set the button ON state to True.
						if changedTimeStamp:
							# Update the Indigo log about the received button event regardless of current on state.
							if logChanges: self.indiLOG.log(sendLog, "Received: {:42s}  {}  {}".format(device.name, shortcut['buttontexts'][lastButtonPressed],  shortcut['textSuffix'][eventType]))
							if not device.states[shortcut['stateNames'][lastButtonPressed]+shortcut['stateSuffix'][0]]:
								buttonOn = True
						# Conversely, if the Indigo device state for the button is currently set to True, but
						#   the lastUpdated time on the bridge is the same as on the Indigo device, that means
						#   we set it to True the last time around and now we need to set it back to False.
						#   so we'll just leave the button1On variable set to the initial False assignment above.

					elif eventType == 3 and shortcut['eventTypesEnabled'][eventType]:
						buttonReleaseLong = True
						if changedTimeStamp:
							# Update the Indigo log regardless of current button on state.
							if logChanges: self.indiLOG.log(sendLog, "Received: {:42s}  {}  {}".format(device.name, shortcut['buttontexts'][lastButtonPressed],  shortcut['textSuffix'][eventType]))
							if not device.states[shortcut['stateNames'][lastButtonPressed]+shortcut['stateSuffix'][0]]:
								buttonOn = True

					elif eventType == 4 and shortcut['eventTypesEnabled'][eventType]:
						buttonLongPress = True
						if changedTimeStamp:
							# Update the Indigo log regardless of current button on state.
							if logChanges: self.indiLOG.log(sendLog, "Received: {:42s}  {}  {}".format(device.name, shortcut['buttontexts'][lastButtonPressed],  shortcut['textSuffix'][eventType]))
							if not device.states[shortcut['stateNames'][lastButtonPressed]+shortcut['stateSuffix'][0]]:
								buttonOn = True


					elif eventType == 5 and shortcut['eventTypesEnabled'][eventType]:
						buttonOn = True
						# If the lastUpdated value is different, this is a new button press. Log it.
						if changedTimeStamp:
							if logChanges: self.indiLOG.log(sendLog, "Received: {:42s}  {} {}".format(device.name, shortcut['buttontexts'][lastButtonPressed],  shortcut['textSuffix'][eventType]))
						else:
							# Looks like the button is being held down.
							buttonHold = True
							buttonBeingHeld = True
							# If the Indigo device doesn't show that a button is already being held, report a button hold in the log.
							if buttonBeingHeld != device.states['buttonBeingHeld']:
								if logChanges: self.indiLOG.log(sendLog, "Received: {:42s}  {} {}".format(device.name, shortcut['buttontexts'][lastButtonPressed],  shortcut['textSuffix'][eventType]))

					elif eventType == 6 and shortcut['eventTypesEnabled'][eventType]:
						buttonRelease = True
						if changedTimeStamp:
							# Update the Indigo log about the received button event regardless of current on state.
							if logChanges: self.indiLOG.log(sendLog, "Received: {:42s}  {}  {}".format(device.name, shortcut['buttontexts'][lastButtonPressed],  shortcut['textSuffix'][eventType]))
							if not device.states['button1On']: buttonOn = True
						else:
							buttonRelease = False# reset at next cycle 

					# Update the states on the device.
					if shortcut['eventTypesEnabled'][0]:	stateUpdateList = self.checkIfUpdateState(device, shortcut['stateNames'][lastButtonPressed]+shortcut['stateSuffix'][0], buttonOn, 				stateUpdateList=stateUpdateList)
					if shortcut['eventTypesEnabled'][1]:	stateUpdateList = self.checkIfUpdateState(device, shortcut['stateNames'][lastButtonPressed]+shortcut['stateSuffix'][1], buttonHold, 			stateUpdateList=stateUpdateList)
					if shortcut['eventTypesEnabled'][2]:	stateUpdateList = self.checkIfUpdateState(device, shortcut['stateNames'][lastButtonPressed]+shortcut['stateSuffix'][2], buttonReleaseShort, 	stateUpdateList=stateUpdateList)
					if shortcut['eventTypesEnabled'][3]:	stateUpdateList = self.checkIfUpdateState(device, shortcut['stateNames'][lastButtonPressed]+shortcut['stateSuffix'][3], buttonReleaseLong, 		stateUpdateList=stateUpdateList)
					if shortcut['eventTypesEnabled'][4]:	stateUpdateList = self.checkIfUpdateState(device, shortcut['stateNames'][lastButtonPressed]+shortcut['stateSuffix'][4], buttonLongPress, 		stateUpdateList=stateUpdateList)
					if shortcut['eventTypesEnabled'][6]:	stateUpdateList = self.checkIfUpdateState(device, shortcut['stateNames'][lastButtonPressed]+shortcut['stateSuffix'][6], buttonRelease, 			stateUpdateList=stateUpdateList)

					if shortcut['eventTypesEnabled'][5]:	stateUpdateList = self.checkIfUpdateState(device, 											shortcut['stateSuffix'][5], buttonBeingHeld, 		stateUpdateList=stateUpdateList)
					if True:
															stateUpdateList = self.checkIfUpdateState(device, 'lastButtonPressed', 													lastButtonPressed, 		stateUpdateList=stateUpdateList)
															stateUpdateList = self.checkIfUpdateState(device, 'buttonEventID', 														buttonEventID,			stateUpdateList=stateUpdateList)
					if buttonOn:							stateUpdateList = self.checkIfUpdateState(device, 'onOffState', 														False,					stateUpdateList=stateUpdateList, uiValue="on",  uiImage=indigo.kStateImageSel.PowerOn )
					else:									stateUpdateList = self.checkIfUpdateState(device, 'onOffState', 														True,  					stateUpdateList=stateUpdateList, uiValue="off", uiImage=indigo.kStateImageSel.PowerOff )

				# End if this is a Switch sensor.



			# -- Hue Smart Button --
			if device.deviceTypeId == "hueRotaryWallRing":
				## self.debugLog("parseOneHueSensorData: Parsing Hue sensor ID %s (\"%s\")." % (device.pluginProps.get('sensorId', ""), sensor.get('name', "no name")))

				# Separate out the specific Hue sensor data.
				rotaryEventID = sensor['state'].get('rotaryevent', 1)
				if   rotaryEventID is None:	rotaryEventID = "unknown"

				expectedEventDuration = sensor['state'].get('expectedeventduration', 0)
				if expectedEventDuration is None: expectedEventDuration = 0

				expectedRotation = sensor['state'].get('expectedrotation', 0)
				if expectedRotation is None: expectedRotation = 0


				if changedTimeStamp:
					# Update the Indigo log regardless of current button on state.
					if logChanges: self.indiLOG.log(sendLog, "Received: {:42s}  rotationID:{}, duration:{}, rotation:{} ".format(device.name, rotaryEventID, expectedEventDuration, expectedRotation))
					onStateBool = True
				else:
					onStateBool = False

				# Update the states on the device.
				if True:
												stateUpdateList = self.checkIfUpdateState(device, 'rotaryEventID', 								rotaryEventID, 			stateUpdateList=stateUpdateList)
												stateUpdateList = self.checkIfUpdateState(device, 'expectedEventDuration', 						expectedEventDuration,	stateUpdateList=stateUpdateList)
												stateUpdateList = self.checkIfUpdateState(device, 'expectedRotation', 							expectedRotation, 		stateUpdateList=stateUpdateList)
				if onStateBool:					stateUpdateList = self.checkIfUpdateState(device, 'onOffState', 								True, 					stateUpdateList=stateUpdateList, uiValue="on", uiImage=indigo.kStateImageSel.PowerOn )
				else:							stateUpdateList = self.checkIfUpdateState(device, 'onOffState', 								False, 					stateUpdateList=stateUpdateList, uiValue="off", uiImage=indigo.kStateImageSel.PowerOff )

			# End if this is a Hue Smart Button sensor.

			if stateUpdateList != [] or changedTimeStamp:
				stateUpdateList.append( {"key":"lastUpdated", "value":lastUpdated} )
				self.updateDeviceState(device, stateUpdateList)

			self.updateDeviceProps(device, tempProps)
		except Exception:
			self.logger.error("", exc_info=True)
		return 

	# Turn Device On or Off
	########################################
	def doOnOff(self, device, onState, rampRate=-1, showLog=True):
		if self.decideMyLog("UpdateIndigoDevices"): self.indiLOG.log(10,"Starting doOnOff. onState: {}, rampRate: {}. Device: {}".format(onState, rampRate, device))
		# onState:		Boolean on state.  True = on. False = off.
		# rampRate:		Optional float from 0 to 540.0 (higher values will probably work too).
		try:
			hubNumber, ipAddress, hostId, paired = self.getIdsFromDevice(device)
			if not paired: return 

			logChanges = (self.pluginPrefs['logAnyChanges'] == "yes") or self.trackSpecificDevice == device.id or (self.pluginPrefs['logAnyChanges'] == "leaveToDevice" and device.pluginProps.get('logChanges', True))
			if self.trackSpecificDevice == device.id:	sendLog = 20
			else: 										sendLog = self.sendDeviceUpdatesTo

			# Skip ramp rate and brightness stuff for on/off only devices.
			if device.deviceTypeId != "hueOnOffDevice":
				# If a rampRate wasn't specified (default of -1 assigned), use the default.
				#   (rampRate should be a float expressing transition time in seconds. Precission
				#   is limited to one-tenth seconds).
				if rampRate == -1:
					try:
						# Check for a blank default ramp rate.
						rampRate = device.pluginProps.get('rate', "")
						if rampRate == "":
							rampRate = 5
						else:
							# For user-friendliness, the rampRate provided in the device
							#   properties (as entered by the user) is expressed in fractions
							#   of a second (0.5 = 0.5 seconds, 10 = 10 seconds, etc), so
							#   it must be converted to 10th seconds here.
							rampRate = int(round(float(device.pluginProps['rate']) * 10))
					except Exception:
						self.logger.error("Default ramp rate could not be obtained", exc_info=True)
						rampRate = 5
				else:
					# Convert the passed rampRate from seconds to 1/10th-seconds.
					rampRate = int(round(float(rampRate) * 10))

				# Get the current brightness. Range is 0-100.
				currentBrightness = int(device.states['brightnessLevel'])
				# Get the bulb's saved brightness (if it exists). Range is 1-255.
				savedBrightness = device.pluginProps.get('savedBrightness', 255)
				# If savedBrightness is not a number, try to make it into one.
				try:
					savedBrightness = int(savedBrightness)
				except ValueError:
					# It's not a string representation of a number, so just give it a number.
					savedBrightness = 255
				# Get the bulb's default brightness (if it exists). Range is 1-100.
				defaultBrightness = device.pluginProps.get('defaultBrightness', 0)
				# Make sure the defaultBrightness is valid.
				try:
					defaultBrightness = int(defaultBrightness)
				except ValueError:
					defaultBrightness = 0
				# If the bulb has a default brightness, use it instead of the saved brightness.
				#   (We're using the "savedBrightness" variable as the brightness goal here).
				if defaultBrightness > 0:
					# Convert default brightness from percentage to 1-255 range.
					savedBrightness = int(round(defaultBrightness * 255.0 / 100.0))
				# If the currentBrightness is less than 100% and is the same as the savedBrightness, go to 100%
				if currentBrightness < 100 and currentBrightness == int(round(savedBrightness * 100.0 / 255.0)):
					savedBrightness = 255

			# Sanity check for an IP address
			if ipAddress is None:
				self.doErrorLog("No IP address set for the Hue bridge. You can get this information from the My Settings page at http://www.meethue.com")
				return

			# Act based on device type.
			if device.deviceTypeId == "hueGroup":
				# Sanity check on group ID
				groupId = device.pluginProps.get('groupId', None)
				if groupId is None or groupId == 0:
					self.doErrorLog("No group ID selected for device \"{}\". Check settings for this device and select a Hue Group to control.".format(device.name))
					return
			else:
				# Sanity check on bulb ID
				bulbId = device.pluginProps.get('bulbId', None)
				if bulbId is None or bulbId == 0:
					self.doErrorLog("No bulb ID selected for device \"{}\". Check settings for this device and select a Hue Device to control.".format(device.name))
					return

			# If the requested onState is True (on), then use the
			#   saved brightness level (which was determined above).
			if onState:
				# Skip ramp rate and brightness stuff for on/off devices.
				if device.deviceTypeId == "hueOnOffDevice":
					# Create the JSON object, ignoring brightness level and ramp rate for on/off devices,
					# and send the command to the bridge.
					requestData = json.dumps({"on": onState})
				else:
					# If the bulb's saved brightness is zero or less (for some reason), use a default value of 100% on (255).
					if savedBrightness <= 0:
						savedBrightness = 255
					# Create the JSON object for other types of devices based on whether they allow ON transition times.
					if device.pluginProps.get('noOnRampRate', False):
						requestData = json.dumps({"bri": savedBrightness, "on": onState})
					else:
						requestData = json.dumps({"bri": savedBrightness, "on": onState, "transitiontime": rampRate})
				# Create the command based on whether this is a group or light device.
				#baseHttp = self.baseHTTPAddress(hubNumber)
				if device.deviceTypeId == "hueGroup":
					command = "http://{}/api/{}/groups/{}/action".format(ipAddress, self.hostIds[hubNumber], groupId)
				else:
					command = "http://{}/api/{}/lights/{}/state".format(ipAddress, self.hostIds[hubNumber], bulbId)
				if self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(10,"Sending URL request: {}".format(command))
				
				try:
					self.setBridgeBusy(hubNumber, calledfrom="doOnOff")
					r = requests.put(command, data=requestData, timeout=kTimeout, headers={'Connection':'close'})
					self.resetBridgeBusy(hubNumber)
				except requests.exceptions.Timeout:
					self.doErrorLog("Failed to connect to the Hue bridge at {} after {} seconds. - Check that the bridge is connected and turned on.".format(ipAddress, kTimeout))
					self.resetBridgeBusy(hubNumber)
					return
				except requests.exceptions.ConnectionError:
					self.doErrorLog("Failed to connect to the Hue bridge at {}. - Check that the bridge is connected and turned on.".format(ipAddress))
					self.resetBridgeBusy(hubNumber)
					return
				if self.decideMyLog("UpdateIndigoDevices"): self.indiLOG.log(10,"Got response - {}".format(r.content) )
				# Customize the log and device update based on whether this is an on/off device or not.
				if device.deviceTypeId == "hueOnOffDevice":
					# Send the log to the console if showing the log is enabled.
					if showLog:
						if logChanges: self.indiLOG.log(sendLog,"Sent Hue Lights  \"{}\" on".format(device.name))
					# Update the Indigo device.
					self.updateDeviceState(device, 'onOffState', True, uiValue='on')
				else:
					tempBrightness = int(round(savedBrightness * 100.0 / 255.0))
					# Compensate for rounding to zero.
					if tempBrightness == 0:
						tempBrightness = 1
					# Log the change (if enabled).
					if showLog:
						# Customize the log based on whether the device supports ON transition time or not.
						if device.pluginProps.get('noOnRampRate', False):
							if logChanges: self.indiLOG.log(sendLog,"Sent Hue Lights  \"{}\"  to {}.".format(device.name,tempBrightness ))
						else:
							if logChanges: self.indiLOG.log(sendLog,"Sent Hue Lights  \"{}\"  to {}, at ramp rate:{} sec".format( device.name, tempBrightness, rampRate / 10.0 ))
					# Update the Indigo device.
					self.updateDeviceState(device, 'brightnessLevel', tempBrightness)
			else:
				# Bulb is being turned off.
				# Create the JSON object based on what device type we're working with.
				if device.deviceTypeId == "hueOnOffDevice":
					requestData = json.dumps({"on": onState})
				else:
					# If the current brightness is lower than 6%, use a ramp rate of 0
					#   because dimming from that low of a brightness level to 0 isn't noticeable.
					if currentBrightness < 6:
						rampRate = 0
					# Create the JSON object for other types of devices based on whether they allow OFF transition times.
					if device.pluginProps.get('noOnRampRate', False):
						requestData = json.dumps({"on": onState})
					else:
						requestData = json.dumps({"on": onState, "transitiontime": rampRate})
				# Create the command based on whether this is a light or group device.
				if device.deviceTypeId == "hueGroup":
					command = "http://{}/api/{}/groups/{}/action".format(ipAddress, self.hostIds[hubNumber], groupId)
				else:
					command = "http://{}/api/{}/lights/{}/state".format(ipAddress, self.hostIds[hubNumber], bulbId)
				if self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(10,"Sending URL request: {} with data: {}".format(command, requestData))
				try:
					self.setBridgeBusy(hubNumber, calledfrom="doOnOff-2")
					r = requests.put(command, data=requestData, timeout=kTimeout, headers={'Connection':'close'})
					self.resetBridgeBusy(hubNumber)
				except requests.exceptions.Timeout:
					self.resetBridgeBusy(hubNumber)
					self.doErrorLog("Failed to connect to the Hue bridge at {} after {} seconds. - Check that the bridge is connected and turned on.".format(ipAddress, kTimeout))
					return
				except requests.exceptions.ConnectionError:
					self.resetBridgeBusy(hubNumber)
					self.doErrorLog("Failed to connect to the Hue bridge at {}. - Check that the bridge is connected and turned on.".format(ipAddress))
					return
				if self.decideMyLog("ReadFromBridge"): self.indiLOG.log(10,"Got response - {}".format(r.content) )
				# Customize the log and device update based on whether this is an on/off device or other device.
				if device.deviceTypeId == "hueOnOffDevice":
					# Log the change.
					if logChanges: self.indiLOG.log(sendLog,"Sent Hue Lights  \"{}\" off".format(device.name))
					# Update the Indigo device.
					self.updateDeviceState(device, 'onOffState', False, uiValue='off')
				else:
					# Log the change (if showing the log is enabled).
					#   Some devices may not support transition times when turning off. Check for that.
					if showLog:
						if device.pluginProps.get('noOnRampRate', False):
							if logChanges: self.indiLOG.log(sendLog,"Sent Hue Lights  \"{}\" off.".format( device.name))
						else:
							if logChanges: self.indiLOG.log(sendLog,"Sent Hue Lights  \"{}\" off. At ramp rate {} sec.".format( device.name, rampRate / 10.0))
					# Update the Indigo device.
					self.updateDeviceState(device, 'brightnessLevel', 0)
		except Exception:
			self.logger.error("", exc_info=True)

		return

	# Set Brightness
	########################################
	def doBrightness(self, device, brightness, rampRate=-1., showLog=True):
		if self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(10,"Starting doBrightness. brightness: {}, rampRate: {}, showLogs: {}. Device: {}".format(brightness, rampRate, showLog, device.name))
		# brightness:	Integer from 0 to 255.
		# rampRate:		Optional float from 0 to 540.0 (higher values will probably work too).
		# showLog:		Optional boolean. False = hide change from Indigo log.
		try:
			hubNumber, ipAddress, hostId, paired = self.getIdsFromDevice(device)
			if not paired: return 
			logChanges = (self.pluginPrefs['logAnyChanges'] == "yes") or self.trackSpecificDevice == device.id or (self.pluginPrefs['logAnyChanges'] == "leaveToDevice" and device.pluginProps.get('logChanges', True))
			if self.trackSpecificDevice == device.id:	sendLog = 20
			else: 										sendLog = self.sendDeviceUpdatesTo

			# Sanity check for an IP address
			if ipAddress is None:
				self.doErrorLog("No IP address set for the Hue bridge. You can get this information from the My Settings page at http://www.meethue.com")
				return

			# Skip ramp rate and brightness stuff for on/off only devices.
			if device.deviceTypeId != "hueOnOffDevice":
				# If a rampRate wasn't specified (default of -1 assigned), use the default.
				#   (rampRate should be a float expressing transition time in seconds. Precission
				#   is limited to one-tenth seconds.
				if rampRate == -1:
					try:
						# Check for a blank default ramp rate.
						rampRate = device.pluginProps.get('rate', "")
						if rampRate == "":
							rampRate = 5
						else:
							# For user-friendliness, the rampRate provided in the device
							#   properties (as entered by the user) is expressed in fractions
							#   of a second (0.5 = 0.5 seconds, 10 = 10 seconds, etc), so
							#   it must be converted to 10th seconds here.
							rampRate = int(round(float(device.pluginProps['rate']) * 10))
					except Exception:
						self.logger.error("Default ramp rate could not be obtained", exc_info=True)
						rampRate = 5
				else:
					rampRate = int(round(float(rampRate) * 10))

				# Get the current brightness level.
				currentBrightness = int(device.states.get('brightnessLevel', 100))

			# Act based on device type.
			if device.deviceTypeId == "hueGroup":
				# Sanity check on group ID
				groupId = device.pluginProps.get('groupId', None)
				if groupId is None or groupId == 0:
					self.doErrorLog("No group ID selected for device \"{}\". Check settings for this device and select a Hue Group to control.".format(device.name))
					return
			else:
				# Sanity check on bulb ID
				bulbId = device.pluginProps.get('bulbId', None)
				if bulbId is None or bulbId == 0:
					self.doErrorLog("No bulb ID selected for device \"{}\". Check settings for this device and select a Hue Device to control.".format(device.name))
					return

			# If requested brightness is greater than 0, proceed. Otherwise, turn off the bulb.
			if brightness > 0:
				# Skip ramp rate and brightness stuff for on/off only devices.
				if device.deviceTypeId == "hueOnOffDevice":
					requestData = json.dumps({"on": True})
				else:
					# Create the JSON based on if a ramp rate should be used or not and if the device is already on or not.
					if device.pluginProps.get('noOnRampRate', False) and currentBrightness == 0:
						requestData = json.dumps({"bri": int(brightness), "on": True})
					else:
						requestData = json.dumps({"bri": int(brightness), "on": True, "transitiontime": rampRate})
				# Create the command based on whether this is a light or group device.
				if device.deviceTypeId == "hueGroup":
					command = "http://{}/api/{}/groups/{}/action".format(ipAddress, self.hostIds[hubNumber], groupId)
				else:
					command = "http://{}/api/{}/lights/{}/state".format(ipAddress, self.hostIds[hubNumber], bulbId)
				if self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(10,"Sending URL request: {}, data:{}".format(command, requestData))
				try:
					self.setBridgeBusy(hubNumber, calledfrom="doBrightness")
					r = requests.put(command, data=requestData, timeout=kTimeout, headers={'Connection':'close'})
					self.resetBridgeBusy(hubNumber)
				except requests.exceptions.Timeout:
					self.resetBridgeBusy(hubNumber)
					self.doErrorLog("Failed to connect to the Hue bridge at {} after {} seconds. - Check that the bridge is connected and turned on.".format(ipAddress, kTimeout))
					# Don't display the error if it's been displayed already.
					return
				except requests.exceptions.ConnectionError:
					self.resetBridgeBusy(hubNumber)
					self.doErrorLog("Failed to connect to the Hue bridge at {}. - Check that the bridge is connected and turned on.".format(ipAddress))
					# Don't display the error if it's been displayed already.
					return
				if self.decideMyLog("ReadFromBridge"): self.indiLOG.log(10,"Got response - {}".format(r.content))
				# Log the change.
				tempBrightness = int(round(brightness * 100.0 / 255.0))
				# Compensate for rounding to zero.
				if tempBrightness == 0:
					tempBrightness = 1
				# Only log changes if we're supposed to.
				if showLog:
					if device.pluginProps.get('noOnRampRate', False) and currentBrightness == 0:
						if logChanges: self.indiLOG.log(sendLog,"Sent Hue Lights  \"{}\"  to {}.".format( device.name, tempBrightness))
					else:
						if logChanges: self.indiLOG.log(sendLog,"Sent Hue Lights  \"{}\"  to {}, at ramp rate:{} sec".format( device.name, tempBrightness, rampRate / 10.0 ))

				# Update the device brightness (which automatically changes on state).
				self.updateDeviceState(device, 'brightnessLevel', int(tempBrightness))
			else:
				# Skip ramp rate and brightness stuff for on/off only devices.
				if device.deviceTypeId == "hueOnOffDevice":
					# Create the JSON request.
					requestData = json.dumps({"on": False})
				else:
					# Requested brightness is 0 (off).
					# If the current brightness is lower than 6%, use a ramp rate of 0
					#   because dimming from that low of a brightness level to 0 isn't noticeable.
					if currentBrightness < 6:
						rampRate = 0
					# Create the JSON request.
					if device.pluginProps.get('noOnRampRate', False):
						requestData = json.dumps({"on": False})
					else:
						requestData = json.dumps({"transitiontime": rampRate, "on": False})
				# Create the command based on whether this is a light or group device.
				if device.deviceTypeId == "hueGroup":
					command = "http://{}/api/{}/groups/{}/action".format(ipAddress, self.hostIds[hubNumber], groupId)
				else:
					command = "http://{}/api/{}/lights/{}/state".format(ipAddress, self.hostIds[hubNumber], bulbId)
				if self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(10,"Sending URL request: {}, data:{}".format(command, requestData))
				try:
					self.setBridgeBusy(hubNumber, calledfrom="doBrightness-2")
					r = requests.put(command, data=requestData, timeout=kTimeout, headers={'Connection':'close'})
					self.resetBridgeBusy(hubNumber)
				except requests.exceptions.Timeout:
					self.doErrorLog("Failed to connect to the Hue bridge at {} after {} seconds. - Check that the bridge is connected and turned on.".format(ipAddress, kTimeout))
					self.resetBridgeBusy(hubNumber)
					return
				except requests.exceptions.ConnectionError:
					self.doErrorLog("Failed to connect to the Hue bridge at {}. - Check that the bridge is connected and turned on.".format(ipAddress))
					self.resetBridgeBusy(hubNumber)
					return
				if self.decideMyLog("ReadFromBridge"): self.indiLOG.log(10,"Got response - {}".format(r.content))
				# Log the change.
				if showLog:
					if device.pluginProps.get('noOnRampRate', False):
						if logChanges: self.indiLOG.log(sendLog,"Sent Hue Lights  \"{}\" off".format( device.name ))
					else:
						if logChanges: self.indiLOG.log(sendLog,"Sent Hue Lights  \"{}\" off, at ramp rate:{} sec".format( device.name, rampRate / 10.0 ))
				# Update the device brightness (which automatically changes on state).
				self.updateDeviceState(device, 'brightnessLevel', 0)
		except Exception:
			self.logger.error("", exc_info=True)

	# Set RGB Levels
	########################################
	def doRGB(self, device, red, green, blue, rampRate=-1., showLog=True):
		if self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(10,"Starting doRGB. RGB: {}, {}, {}. Device: {}".format(red, green, blue, device))
		# red:			Integer from 0 to 255.
		# green:		Integer from 0 to 255.
		# blue:			Integer from 0 to 255.
		# rampRate:		Optional float from 0 to 540.0 (higher values will probably work too).
		try:
			hubNumber, ipAddress, hostId, paired = self.getIdsFromDevice(device)
			if not paired: return 
			logChanges = (self.pluginPrefs['logAnyChanges'] == "yes") or self.trackSpecificDevice == device.id or (self.pluginPrefs['logAnyChanges'] == "leaveToDevice" and device.pluginProps.get('logChanges', True))
			if self.trackSpecificDevice == device.id:	sendLog = 20
			else: 										sendLog = self.sendDeviceUpdatesTo

			# Get the model ID of the device.
			modelId = device.pluginProps.get('modelId', "")

			# If a rampRate wasn't specified (default of -1 assigned), use the default.
			#   (rampRate should be a float expressing transition time in seconds. Precission
			#   is limited to one-tenth seconds.
			if rampRate == -1:
				try:
					# Check for a blank default ramp rate.
					rampRate = device.pluginProps.get('rate', "")
					if rampRate == "":
						rampRate = 5
					else:
						# For user-friendliness, the rampRate provided in the device
						#   properties (as entered by the user) is expressed in fractions
						#   of a second (0.5 = 0.5 seconds, 10 = 10 seconds, etc), so
						#   it must be converted to 10th seconds here.
						rampRate = int(round(float(device.pluginProps['rate']) * 10))
				except Exception:
					self.logger.error("Default ramp rate could not be obtained", exc_info=True)
					rampRate = 5
			else:
				rampRate = int(round(float(rampRate) * 10))

			# Get the current brightness.
			currentBrightness = int(device.states.get('brightnessLevel', 100))

			# Convert RGB to HSL (same as HSB)
			rgb = RGBColor(red, green, blue, rgb_type='wide_gamut_rgb')
			hsb = rgb.convert_to('hsv')
			# Convert hue, saturation, and brightness to Hue system compatible ranges
			hue = int(round(hsb.hsv_h * 182.0))
			saturation = int(round(hsb.hsv_s * 255.0))
			brightness = int(round(hsb.hsv_v * 255.0))

			# Sanity check for an IP address
			if ipAddress is None:
				self.doErrorLog("No IP address set for the Hue bridge. You can get this information from the My Settings page at http://www.meethue.com")
				return

			# Act based on device type.
			if device.deviceTypeId == "hueGroup":
				# Sanity check on group ID
				groupId = device.pluginProps.get('groupId', None)
				if groupId is None or groupId == 0:
					self.doErrorLog("No group ID selected for device \"{}\". Check settings for this device and select a Hue Group to control.".format(device.name))
					return
			else:
				# Sanity check on bulb ID
				bulbId = device.pluginProps.get('bulbId', None)
				if bulbId is None or bulbId == 0:
					self.doErrorLog("No bulb ID selected for device \"{}\". Check settings for this device and select a Hue Device to control.".format(device.name))
					return

			# Make sure the device is capable of rendering color.
			if not device.pluginProps.get('SupportsRGB', False):
				self.doErrorLog("Cannot set RGB values. The \"{}\" device does not support color.".format(device.name))
				return

			# Send to Hue (Create JSON request based on whether brightness is zero or not).
			if brightness > 0:
				# Determine if a transition time should be used at all.
				if device.pluginProps.get('noOnRampRate', False) and currentBrightness == 0:
					if device.deviceTypeId == "hueGroup":
						# The Hue bridge doesn't accept the colormode parameter, so don't send it if we're dealing with a group.
						requestData = json.dumps({"bri": brightness, "hue": hue, "sat": saturation, "on": True})
					else:
						requestData = json.dumps({"bri": brightness, "colormode": 'hs', "hue": hue, "sat": saturation, "on": True})
				else:
					if device.deviceTypeId == "hueGroup":
						# The Hue bridge doesn't accept the colormode parameter, so don't send it if we're dealing with a group.
						requestData = json.dumps({"bri": brightness, "hue": hue, "sat": saturation, "transitiontime": int(rampRate), "on": True})
					else:
						requestData = json.dumps({"bri": brightness, "colormode": 'hs', "hue": hue, "sat": saturation, "transitiontime": int(rampRate), "on": True})
			else:
				# If the current brightness is below 6%, set the ramp rate to 0.
				if currentBrightness < 6:
					rampRate = 0
				# Determine if a transition time should be used at all.
				if device.pluginProps.get('noOnRampRate', False):
					# We create a separate command for when brightness is 0 (or below) because if
					#   the "on" state in the request was True, the Hue light wouldn't turn off.
					#   We also explicitly state the X and Y values (equivalent to RGB of 1, 1, 1)
					#   because the xyy object contains invalid "NaN" values when all RGB values are 0.
					if device.deviceTypeId == "hueGroup":
						# The Hue bridge doesn't accept the colormode parameter, so don't send it if we're dealing with a group.
						requestData = json.dumps({"bri": 0, "hue": 0, "sat": 0, "on": False})
					else:
						requestData = json.dumps({"bri": 0, "colormode": 'hs', "hue": 0, "sat": 0, "on": False})
				else:
					if device.deviceTypeId == "hueGroup":
						# The Hue bridge doesn't accept the colormode parameter, so don't send it if we're dealing with a group.
						requestData = json.dumps({"bri": 0, "hue": 0, "sat": 0, "transitiontime": int(rampRate), "on": False})
					else:
						requestData = json.dumps({"bri": 0, "colormode": 'hs', "hue": 0, "sat": 0, "transitiontime": int(rampRate), "on": False})

			# Create the HTTP command and send it to the bridge.
			# Create the command based on whether this is a light or group device.
			if device.deviceTypeId == "hueGroup":
				command = "http://{}/api/{}/groups/{}/action".format(ipAddress, self.hostIds[hubNumber], groupId)
			else:
				command = "http://{}/api/{}/lights/{}/state".format(ipAddress, self.hostIds[hubNumber], bulbId)
			if self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(10,"Data: {}, URL: {}".format(requestData, command))
			try:
				self.setBridgeBusy(hubNumber, calledfrom="doRGB")
				r = requests.put(command, data=requestData, timeout=kTimeout, headers={'Connection':'close'})
				self.resetBridgeBusy(hubNumber)
			except requests.exceptions.Timeout:
				self.doErrorLog("Failed to connect to the Hue bridge at {} after {} seconds. - Check that the bridge is connected and turned on.".format(ipAddress, kTimeout))
				self.resetBridgeBusy(hubNumber)
				return
			except requests.exceptions.ConnectionError:
				self.doErrorLog("Failed to connect to the Hue bridge at {}. - Check that the bridge is connected and turned on.".format(ipAddress))
				self.resetBridgeBusy(hubNumber)
				return
			if self.decideMyLog("ReadFromBridge"): self.indiLOG.log(10,"Got response - {}".format(r.content))

			# Update on Indigo
			if brightness > 0:
				# Convert brightness to a percentage.
				brightness = int(round(brightness * 100.0 / 255.0))
				# Log the change (if enabled).
				if showLog:
					# Exclude mention of ramp rate if none was used.
					if device.pluginProps.get('noOnRampRate', False) and currentBrightness == 0:
						if logChanges: self.indiLOG.log(sendLog,"Sent Hue Lights  \"{}\"  to {}  with RGB values {},{},{}.".format( device.name, brightness, red , green, blue) )
					else:
						if logChanges: self.indiLOG.log(sendLog,"Sent Hue Lights  \"{}\"  to {}  with RGB values {},{},{}.  at ramp rate  {} sec.".format( device.name, brightness, red , green, blue, rampRate / 10.0 ))
				# Update the device state.
				self.updateDeviceState(device, 'brightnessLevel', brightness)
			else:
				# Log the change.
				if showLog:
					# Exclude mention of ramp rate if none was used.
					if device.pluginProps.get('noOnRampRate', False):
						if logChanges: self.indiLOG.log(sendLog,"Sent Hue Lights  \"{}\" off".format( device.name ))
					else:
						if logChanges: self.indiLOG.log(sendLog,"Sent Hue Lights  \"{}\" off, at ramp rate:{} sec".format( device.name, rampRate / 10.0 ))
				# Update the device state.
				self.updateDeviceState(device, 'brightnessLevel', 0)
			# Update the other device states.
			self.updateDeviceState(device, 'colorMode', "hs")
			self.updateDeviceState(device, 'hue', self.normalizeHue(hue, device))
			self.updateDeviceState(device, 'saturation', saturation)
			# We don't set the colorRed, colorGreen, and colorBlue states
			#   because Hue devices are not capable of the full RGB color
			#   gamut and when the Hue bridge updates the HSB values to reflect
			#   actual displayed light, the interpreted RGB values will not
			#   match the values entered by the user in the Action dialog.
		except Exception:
			self.logger.error("", exc_info=True)

	# Set Hue, Saturation and Brightness
	########################################
	def doHSB(self, device, hue, saturation, brightness, rampRate=-1., showLog=True):
		# hue:			Integer from 0 to 65535.
		# saturation:	Integer from 0 to 255.
		# brightness:	Integer from 0 to 255.
		# rampRate:		Optional float from 0 to 540.0 (higher values will probably work too).
		try:
			hubNumber, ipAddress, hostId, paired = self.getIdsFromDevice(device)
			if not paired: return 
			logChanges = (self.pluginPrefs['logAnyChanges'] == "yes") or self.trackSpecificDevice == device.id or (self.pluginPrefs['logAnyChanges'] == "leaveToDevice" and device.pluginProps.get('logChanges', True))
			if self.trackSpecificDevice == device.id:	sendLog = 20
			else: 										sendLog = self.sendDeviceUpdatesTo

			if self.decideMyLog("SendCommandsToBridge") or logChanges: self.indiLOG.log(sendLog,"Starting doHSB. device:{},  HSB: {}, {}, {}." .format(device.name,  hue, saturation, brightness))

			# If a rampRate wasn't specified (default of -1 assigned), use the default.
			#   (rampRate should be a float expressing transition time in seconds. Precission
			#   is limited to one-tenth seconds.
			if rampRate == -1:
				try:
					# Check for a blank default ramp rate.
					rampRate = device.pluginProps.get('rate', "")
					if rampRate == "":
						rampRate = 5
					else:
						# For user-friendliness, the rampRate provided in the device
						#   properties (as entered by the user) is expressed in fractions
						#   of a second (0.5 = 0.5 seconds, 10 = 10 seconds, etc), so
						#   it must be converted to 10th seconds here.
						rampRate = int(round(float(device.pluginProps['rate']) * 10))
				except Exception:
					self.logger.error("Default ramp rate could not be obtained", exc_info=True)
					rampRate = 5
			else:
				rampRate = int(round(float(rampRate) * 10.0))

			# Get the current brightness level.
			currentBrightness = int(device.states.get('brightnessLevel', 100))

			# Sanity check for an IP address
			if ipAddress is None:
				self.doErrorLog("No IP address set for the Hue bridge. You can get this information from the My Settings page at http://www.meethue.com")
				return

			# Act based on device type.
			if device.deviceTypeId == "hueGroup":
				# Sanity check on group ID
				groupId = device.pluginProps.get('groupId', None)
				if groupId is None or groupId == 0:
					self.doErrorLog("No group ID selected for device \"{}\". Check settings for this device and select a Hue Group to control.".format(device.name))
					return
			else:
				# Sanity check on bulb ID
				bulbId = device.pluginProps.get('bulbId', None)
				if bulbId is None or bulbId == 0:
					self.doErrorLog("No bulb ID selected for device \"{}\". Check settings for this device and select a Hue Device to control.".format(device.name))
					return

			# Make sure this device supports color.
			modelId = device.pluginProps.get('modelId', "")
			htype = device.pluginProps.get('type', "")
			if htype == kLivingWhitesDeviceIDType or htype[0:len(kOnOffOnlyDeviceIDType)] == kOnOffOnlyDeviceIDType:
				self.doErrorLog("Cannot set HSB values. The \"{}\" device does not support color.".format(device.name))
				return

			# If the current brightness is below 6% and the requested brightness is
			#   greater than 0, set the ramp rate to 0.
			if currentBrightness < 6 and brightness == 0:
				rampRate = 0

			# Send to Hue (Create JSON request based on whether brightness is zero or not).
			if brightness > 0:
				# Exclude transition times if needed.
				if device.pluginProps.get('noOnRampRate', False) and currentBrightness == 0:
					if device.deviceTypeId == "hueGroup":
						# The Hue bridge doesn't accept the colormode parameter, so don't send it if we're dealing with a group.
						requestData = json.dumps({"bri":brightness, "hue":hue, "sat":saturation, "on":True})
					else:
						requestData = json.dumps({"bri":brightness, "colormode": 'hs', "hue":hue, "sat":saturation, "on":True})
				else:
					if device.deviceTypeId == "hueGroup":
						# The Hue bridge doesn't accept the colormode parameter, so don't send it if we're dealing with a group.
						requestData = json.dumps({"bri":brightness, "hue":hue, "sat":saturation, "on":True, "transitiontime":rampRate})
					else:
						requestData = json.dumps({"bri":brightness, "colormode": 'hs', "hue":hue, "sat":saturation, "on":True, "transitiontime":rampRate})
			else:
				# Exclude transition times if needed.
				if device.pluginProps.get('noOnRampRate', False):
					if device.deviceTypeId == "hueGroup":
						# The Hue bridge doesn't accept the colormode parameter, so don't send it if we're dealing with a group.
						requestData = json.dumps({"bri":brightness, "hue":hue, "sat":saturation, "on":False})
					else:
						requestData = json.dumps({"bri":brightness, "colormode": 'hs', "hue":hue, "sat":saturation, "on":False})
				else:
					if device.deviceTypeId == "hueGroup":
						# The Hue bridge doesn't accept the colormode parameter, so don't send it if we're dealing with a group.
						requestData = json.dumps({"bri":brightness, "hue":hue, "sat":saturation, "on":False, "transitiontime":rampRate})
					else:
						requestData = json.dumps({"bri":brightness, "colormode": 'hs', "hue":hue, "sat":saturation, "on":False, "transitiontime":rampRate})
			# Create the command based on whether this is a light or group device.
			if device.deviceTypeId == "hueGroup":
				command = "http://{}/api/{}/groups/{}/action".format(ipAddress, self.hostIds[hubNumber], groupId)
			else:
				command = "http://{}/api/{}/lights/{}/state".format(ipAddress, self.hostIds[hubNumber], bulbId)
			if self.decideMyLog("SendCommandsToBridge") or logChanges: self.indiLOG.log(10,"SEND is {}, {}".format(command, requestData) )
			try:
				self.setBridgeBusy(hubNumber, calledfrom="doHSB")
				r = requests.put(command, data=requestData, timeout=kTimeout, headers={'Connection':'close'})
				self.resetBridgeBusy(hubNumber)
			except requests.exceptions.Timeout:
				self.doErrorLog("Failed to connect to the Hue bridge at {} after {} seconds. - Check that the bridge is connected and turned on.".format(ipAddress, kTimeout))
				self.resetBridgeBusy(hubNumber)
				return
			except requests.exceptions.ConnectionError:
				self.doErrorLog("Failed to connect to the Hue bridge at {}. - Check that the bridge is connected and turned on.".format(ipAddress))
				self.resetBridgeBusy(hubNumber)
				return
			if self.decideMyLog("ReadFromBridge") or logChanges: self.indiLOG.log(sendLog,"Got response - {}".format(r.content))

			# Update on Indigo
			if int(round(brightness * 100.0 / 255.0)) > 0:
				# Log the change (if enabled).
				if showLog:
					# Exclude mention of ramp rate if none was used.
					if device.pluginProps.get('noOnRampRate', False) and currentBrightness == 0:
						if logChanges: self.indiLOG.log(sendLog,"Sent Hue Lights  \{}\"  to {} with hue {}, saturation {}%.".format(device.name, int(round(brightness * 100.0 / 255.0)), int(round(hue / 182.0)), int(round(saturation * 100.0 / 255.0)) ))
					else:
						if logChanges: self.indiLOG.log(sendLog,"Sent Hue Lights  \"{}\"  to {} with hue {},  saturation {}%. % at ramp rate {}sec.".format(device.name, int(round(brightness * 100.0 / 255.0)), int(round(hue / 182.0)), int(round(saturation * 100.0 / 255.0)), rampRate / 10.0 ))
				# Change the Indigo device.
				self.updateDeviceState(device, 'brightnessLevel', int(round(brightness * 100.0 / 255.0)))
			else:
				# Log the change.
				if showLog:
					# Exclude mention of ramp rate if none was used.
					if device.pluginProps.get('noOnRampRate', False):
						if logChanges: self.indiLOG.log(sendLog,"Sent Hue Lights  \"{}\" off.".format(device.name))
					else:
						if logChanges: self.indiLOG.log(sendLog,"Sent Hue Lights  \"{}\" off at ramp rate {} sec.".format(device.name, rampRate / 10.0))
				# Change the Indigo device.
				self.updateDeviceState(device, 'brightnessLevel', 0)
			# Update the other device states.
			self.updateDeviceState(device, 'colorMode', "hs")

			self.updateDeviceState(device, 'hue', self.normalizeHue(hue, device))
			self.updateDeviceState(device, 'saturation', int(saturation * 100.0 / 255.0))
		except Exception:
			self.logger.error("", exc_info=True)

	# Set CIE 1939 xyY Values
	########################################
	def doXYY(self, device, colorX, colorY, brightness, rampRate=-1, showLog=True):
		if self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(10,"Starting doXYY. xyY: {}, {}, {}. Device: {}".format(colorX, colorY, brightness, device))
		# colorX:		Integer from 0 to 1.0.
		# colorY:		Integer from 0 to 1.0.
		# brightness:	Integer from 0 to 255.
		# rampRate:		Optional float from 0 to 540.0 (higher values will probably work too).
		try:
			hubNumber, ipAddress, hostId, paired = self.getIdsFromDevice(device)
			if not paired: return 
			logChanges = (self.pluginPrefs['logAnyChanges'] == "yes") or self.trackSpecificDevice == device.id or (self.pluginPrefs['logAnyChanges'] == "leaveToDevice" and device.pluginProps.get('logChanges', True))
			if self.trackSpecificDevice == device.id:	sendLog = 20
			else: 										sendLog = self.sendDeviceUpdatesTo

			# If a rampRate wasn't specified (default of -1 assigned), use the default.
			#   (rampRate should be a float expressing transition time in seconds. Precission
			#   is limited to one-tenth seconds.
			if rampRate == -1:
				try:
					# Check for a blank default ramp rate.
					rampRate = device.pluginProps.get('rate', "")
					if rampRate == "":
						rampRate = 5
					else:
						# For user-friendliness, the rampRate provided in the device
						#   properties (as entered by the user) is expressed in fractions
						#   of a second (0.5 = 0.5 seconds, 10 = 10 seconds, etc), so
						#   it must be converted to 10th seconds here.
						rampRate = int(round(float(device.pluginProps['rate']) * 10))
				except Exception:
					self.logger.error("Default ramp rate could not be obtained", exc_info=True)
					rampRate = 5
			else:
				rampRate = int(round(float(rampRate) * 10.0))

			# Get the current brightness level.
			currentBrightness = int(device.states.get('brightnessLevel', 100))

			# Sanity check for an IP address
			if ipAddress is None:
				self.doErrorLog("No IP address set for the Hue bridge. You can get this information from the My Settings page at http://www.meethue.com")
				return

			# Act based on device type.
			if device.deviceTypeId == "hueGroup":
				# Sanity check on group ID
				groupId = device.pluginProps.get('groupId', None)
				if groupId is None or groupId == 0:
					self.doErrorLog("No group ID selected for device \"{}\". Check settings for this device and select a Hue Group to control." .format(device.name))
					return
			else:
				# Sanity check on bulb ID
				bulbId = device.pluginProps.get('bulbId', None)
				if bulbId is None or bulbId == 0:
					self.doErrorLog("No bulb ID selected for device \"{}\". Check settings for this device and select a Hue Device to control.".format(device.name))
					return

			# Make sure this device supports color.
			modelId = device.pluginProps.get('modelId', "")
			htype = device.pluginProps.get('type', "")
			if htype == kLivingWhitesDeviceIDType or htype[0:len(kOnOffOnlyDeviceIDType)] == kOnOffOnlyDeviceIDType:
				self.doErrorLog("Cannot set xyY values. The \"{}\" device does not support color.".format(device.name))
				return

			# Make sure the X and Y values are sane.
			if colorX < 0.0 or colorX > 1.0:
				self.doErrorLog("The specified X chromatisety value \"{}\" for the \"{}\" device is outside the acceptable range of 0.0 to 1.0.".format(colorX, device.name))
				return
			if colorY < 0.0 or colorY > 1.0:
				self.doErrorLog("The specified Y chromatisety value \"{}\" for the \"{}\" device is outside the acceptable range of 0.0 to 1.0.".format(colorX, device.name))
				return

			# If the current brightness is below 6% and the requested brightness is
			#   greater than 0, set the ramp rate to 0.
			if currentBrightness < 6 and brightness == 0:
				rampRate = 0

			# Send to Hue (Create JSON request based on whether brightness is zero or not).
			if brightness > 0:
				# Exclude transition time if needed.
				if device.pluginProps.get('noOnRampRate', False) and currentBrightness == 0:
					if device.deviceTypeId == "hueGroup":
						# The Hue bridge doesn't accept the colormode parameter, so don't send it if we're dealing with a group.
						requestData = json.dumps({"bri":brightness, "xy":[colorX, colorY], "on":True})
					else:
						requestData = json.dumps({"bri":brightness, "colormode": 'xy', "xy":[colorX, colorY], "on":True})
				else:
					if device.deviceTypeId == "hueGroup":
						# The Hue bridge doesn't accept the colormode parameter, so don't send it if we're dealing with a group.
						requestData = json.dumps({"bri":brightness, "xy":[colorX, colorY], "on":True, "transitiontime":rampRate})
					else:
						requestData = json.dumps({"bri":brightness, "colormode": 'xy', "xy":[colorX, colorY], "on":True, "transitiontime":rampRate})
			else:
				if device.deviceTypeId == "hueGroup":
					# The Hue bridge doesn't accept the colormode parameter, so don't send it if we're dealing with a group.
					requestData = json.dumps({"bri":brightness, "xy":[colorX, colorY], "on":False, "transitiontime":rampRate})
				else:
					requestData = json.dumps({"bri":brightness, "colormode": 'xy', "xy":[colorX, colorY], "on":False, "transitiontime":rampRate})

			# Create the command based on whether this is a light or group device.
			if device.deviceTypeId == "hueGroup":
				command = "http://{}/api/{}/groups/{}/action".format(ipAddress, self.hostIds[hubNumber], groupId)
			else:
				command = "http://{}/api/{}/lights/{}/state".format(ipAddress, self.hostIds[hubNumber], bulbId)
			try:
				if self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(10,"SEND is {}, {}".format(command, requestData) )
				self.setBridgeBusy(hubNumber, calledfrom="doXYY")
				r = requests.put(command, data=requestData, timeout=kTimeout, headers={'Connection':'close'})
				self.resetBridgeBusy(hubNumber)
			except requests.exceptions.Timeout:
				self.doErrorLog("Failed to connect to the Hue bridge at {} after {} seconds. - Check that the bridge is connected and turned on.".format(ipAddress, kTimeout))
				self.resetBridgeBusy(hubNumber)
				return
			except requests.exceptions.ConnectionError:
				self.doErrorLog("Failed to connect to the Hue bridge at {}. - Check that the bridge is connected and turned on.".format(ipAddress))
				self.resetBridgeBusy(hubNumber)
				return
			if self.decideMyLog("ReadFromBridge"): self.indiLOG.log(10,"Got response - {}".format(r.content) )

			# Update on Indigo
			if int(round(brightness * 100.0 / 255.0)) > 0:
				# Log the change (if enabled).
				if showLog:
					# Exclude mention of ramp rate if none was used.
					if device.pluginProps.get('noOnRampRate', False) and currentBrightness == 0:
						if logChanges: self.indiLOG.log(sendLog,"Sent Hue Lights  \"{}\"  to {} with x/y chromatisety values of {}/{}.".format( device.name,int(round(brightness * 100.0 / 255.0)), round(colorX, 4), round(colorY, 4)  ))
					else:
						if logChanges: self.indiLOG.log(sendLog,"Sent Hue Lights  \"{}\"  to {} with x/y chromatisety values of {}/{}.  at ramp rate  {} sec.".format( device.name, int(round(brightness * 100.0 / 255.0)), round(colorX, 4), round(colorY, 4), rampRate / 10.0 ))
				# Change the Indigo device.
				self.updateDeviceState(device, 'brightnessLevel', int(round(brightness * 100.0 / 255.0)))
			else:
				# Log the change.
				if showLog:
					# Exclude mention of ramp rate if none was used.
					if device.pluginProps.get('noOnRampRate', False):
						if logChanges: self.indiLOG.log(sendLog,"Sent Hue Lights  \"{}\" off,".format( device.name ))
					else:
						if logChanges: self.indiLOG.log(sendLog,"Sent Hue Lights  \"{}\" off, at ramp rate:{} sec".format( device.name, rampRate / 10.0 ))
				# Change the Indigo device.
				self.updateDeviceState(device, 'brightnessLevel', 0)
			# Update the other device states.
			self.updateDeviceState(device, 'colorMode', "xy")
			self.updateDeviceState(device, 'colorX', round(colorX, 4))
			self.updateDeviceState(device, 'colorY', round(colorY, 4))
		except Exception:
			self.logger.error("", exc_info=True)

	# Set Color Temperature
	########################################
	def doColorTemperature(self, device, temperature, brightness, rampRate=-1, showLog=True):
		if self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(10,"Starting doColorTemperature. temperature: {}, brightness: {}. Device: {}".format(temperature, brightness, device))
		# temperature:	Integer from 2000 to 6500.
		# brightness:	Integer from 0 to 255.
		# rampRate:		Optional float from 0 to 540.0 (higher values will probably work too).
		try:
			hubNumber, ipAddress, hostId, paired = self.getIdsFromDevice(device)
			if not paired: return 
			logChanges = (self.pluginPrefs['logAnyChanges'] == "yes") or self.trackSpecificDevice == device.id or (self.pluginPrefs['logAnyChanges'] == "leaveToDevice" and device.pluginProps.get('logChanges', True))
			if self.trackSpecificDevice == device.id:	sendLog = 20
			else: 										sendLog = self.sendDeviceUpdatesTo

			# If a rampRate wasn't specified (default of -1 assigned), use the default.
			#   (rampRate should be a float expressing transition time in seconds. Precission
			#   is limited to one-tenth seconds.
			if rampRate == -1:
				try:
					# Check for a blank default ramp rate.
					rampRate = device.pluginProps.get('rate', "")
					if rampRate == "":
						rampRate = 5
					else:
						# For user-friendliness, the rampRate provided in the device
						#   properties (as entered by the user) is expressed in fractions
						#   of a second (0.5 = 0.5 seconds, 10 = 10 seconds, etc), so
						#   it must be converted to 10th seconds here.
						rampRate = int(round(float(device.pluginProps['rate']) * 10))
				except Exception:
					self.logger.error("Default ramp rate could not be obtained", exc_info=True)
					rampRate = 5
			else:
				rampRate = int(round(float(rampRate) * 10))

			# Make sure the color temperature value is sane.
			if temperature < 2000 or temperature > 6500:
				self.doErrorLog("Invalid color temperature value of {}. Color temperatures must be between 2000 and 6500 K.".format(temperature))
				return

			# Get the current brightness level.
			currentBrightness = int(device.states.get('brightnessLevel', 100))

			# Save the submitted color temperature into another variable.
			colorTemp = temperature

			# Convert temperature from K to mireds.
			#   Use the ceil and add 3 to help compensate for Hue behavior that "rounds up" to
			#   the next highest compatible mired value for the device.
			temperature = int(3 + ceil(1000000.0 / temperature))

			# Sanity check for an IP address
			if ipAddress is None:
				self.doErrorLog("No IP address set for the Hue bridge. You can get this information from the My Settings page at http://www.meethue.com")
				return

			# Act based on device type.
			if device.deviceTypeId == "hueGroup":
				# Sanity check on group ID
				groupId = device.pluginProps.get('groupId', None)
				if groupId is None or groupId == 0:
					self.doErrorLog("No group ID selected for device \"{}\". Check settings for this device and select a Hue Group to control.".format(device.name))
					return
			else:
				# Sanity check on bulb ID
				bulbId = device.pluginProps.get('bulbId', None)
				if bulbId is None or bulbId == 0:
					self.doErrorLog("No bulb ID selected for device \"{}\". Check settings for this device and select a Hue Device to control.".format(device.name))
					return

			# Make sure this device supports color.
			modelId = device.pluginProps.get('modelId', "")
			htype = device.pluginProps.get('type', "")
			if htype == kLivingWhitesDeviceIDType or htype[0:len(kOnOffOnlyDeviceIDType)] == kOnOffOnlyDeviceIDType:
				self.doErrorLog("Cannot set Color Temperature values. The \"{}\" device does not support variable color temperature.".format(device.name))
				return

			# If the current brightness is below 6% and the requested
			#   brightness is 0, set the ramp rate to 0.
			if currentBrightness < 6 and brightness == 0:
				rampRate = 0

			# Send to Hue (Create JSON request based on whether brightness is zero or not).
			if brightness > 0:
				# Exclude transition time if needed.
				if device.pluginProps.get('noOnRampRate', False) and currentBrightness == 0:
					if device.deviceTypeId == "hueGroup":
						# The Hue bridge doesn't accept the colormode parameter, so don't send it if we're dealing with a group.
						requestData = json.dumps({"bri": brightness, "ct": temperature, "on": True})
					else:
						requestData = json.dumps({"bri": brightness, "colormode": 'ct', "ct": temperature, "on": True})
				else:
					if device.deviceTypeId == "hueGroup":
						# The Hue bridge doesn't accept the colormode parameter, so don't send it if we're dealing with a group.
						requestData = json.dumps({"bri": brightness, "ct": temperature, "on": True, "transitiontime": int(rampRate)})
					else:
						requestData = json.dumps({"bri": brightness, "colormode": 'ct', "ct": temperature, "on": True, "transitiontime": int(rampRate)})
			else:
				# Exclude transition time if needed.
				if device.pluginProps.get('noOnRampRate', False):
					if device.deviceTypeId == "hueGroup":
						requestData = json.dumps({"bri": brightness, "ct": temperature, "on": False})
					else:
						requestData = json.dumps({"bri": brightness, "colormode": 'ct', "ct": temperature, "on": False})
				else:
					if device.deviceTypeId == "hueGroup":
						requestData = json.dumps({"bri": brightness, "ct": temperature, "on": False, "transitiontime": int(rampRate)})
					else:
						requestData = json.dumps({"bri": brightness, "colormode": 'ct', "ct": temperature, "on": False, "transitiontime": int(rampRate)})

			# Create the command based on whether this is a light or group device.
			if device.deviceTypeId == "hueGroup":
				command = "http://{}/api/{}/groups/{}/action".format(ipAddress, self.hostIds[hubNumber], groupId)
			else:
				command = "http://{}/api/{}/lights/{}/state".format(ipAddress, self.hostIds[hubNumber], bulbId)
			if self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(10,"SEND is {}, {}".format(command, requestData) )
			try:
				self.setBridgeBusy(hubNumber, calledfrom="doColorTemperature")
				r = requests.put(command, data=requestData, timeout=kTimeout, headers={'Connection':'close'})
				self.resetBridgeBusy(hubNumber)
			except requests.exceptions.Timeout:
				self.doErrorLog("Failed to connect to the Hue bridge at {} after {} seconds. - Check that the bridge is connected and turned on.".format(ipAddress, kTimeout))
				self.resetBridgeBusy(hubNumber)
				return
			except requests.exceptions.ConnectionError:
				self.doErrorLog("Failed to connect to the Hue bridge at {}. - Check that the bridge is connected and turned on.".format(ipAddress))
				self.resetBridgeBusy(hubNumber)
				return
			if self.decideMyLog("ReadFromBridge"): self.indiLOG.log(10,"Got response - {}".format(r.content) )

			# Update on Indigo
			if brightness > 0:
				# Log the change.
				tempBrightness = int(round(brightness * 100.0 / 255.0))
				# Compensate for rounding errors where it rounds down even though brightness is > 0.
				if tempBrightness == 0 and brightness > 0:
					tempBrightness = 1
				# Use originally submitted color temperature in the log version (if logging is enabled).
				if showLog:
					# Exclude mention of ramp rate if none was used.
					if device.pluginProps.get('noOnRampRate', False) and currentBrightness == 0:
						if logChanges: self.indiLOG.log(sendLog,"Sent Hue Lights  \"{}\"  to {} using color temperature  {}K".format( device.name, tempBrightness, colorTemp ))
					else:
						if logChanges: self.indiLOG.log(sendLog,"Sent Hue Lights  \"{}\"  to {} using color temperature  {}K.  at ramp rate  {} sec.".format( device.name, tempBrightness, colorTemp, rampRate / 10.0))
				self.updateDeviceState(device, 'brightnessLevel', int(round(brightness * 100.0 / 255.0)))
			else:
				# Log the change.
				if showLog:
					# Exclude mention of ramp rate if none was used.
					if device.pluginProps.get('noOnRampRate', False):
						if logChanges: self.indiLOG.log(sendLog,"Sent Hue Lights  \"{}\" off".format( device.name))
					else:
						if logChanges: self.indiLOG.log(sendLog,"Sent Hue Lights  \"{}\" off, at ramp rate:{} sec".format( device.name,  rampRate / 10.0 ))
				self.updateDeviceState(device, 'brightnessLevel', 0)
			# Update the color mode state.
			self.updateDeviceState(device, 'colorMode', "ct")
			# Update the color temperature state (it's in mireds now, convert to Kelvin).
			self.updateDeviceState(device, 'colorTemp', colorTemp)
		except Exception:
			self.logger.error("", exc_info=True)

	# Start Alert (Blinking)
	########################################
	def doAlert(self, device, alertType="lselect", showLog=True):
		if self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(10,"Starting doAlert. alert: {}. Device: {}".format(alertType, device))
		# alertType:	Optional string.  String options are:
		#					lselect		: Long alert (default if nothing specified)
		#					select		: Short alert
		#					none		: Stop any running alerts
		try:
			hubNumber, ipAddress, hostId, paired = self.getIdsFromDevice(device)
			if not paired: return 
			logChanges = (self.pluginPrefs['logAnyChanges'] == "yes") or self.trackSpecificDevice == device.id or (self.pluginPrefs['logAnyChanges'] == "leaveToDevice" and device.pluginProps.get('logChanges', True))
			if self.trackSpecificDevice == device.id:	sendLog = 20
			else: 										sendLog = self.sendDeviceUpdatesTo

			# Sanity check for an IP address
			if ipAddress is None:
				self.doErrorLog("No IP address set for the Hue bridge. You can get this information from the My Settings page at http://www.meethue.com")
				return

			# Act based on device type.
			if device.deviceTypeId == "hueGroup":
				# Sanity check on group ID
				groupId = device.pluginProps.get('groupId', None)
				if groupId is None or groupId == 0:
					self.doErrorLog("No group ID selected for device \"{}\". Check settings for this device and select a Hue Group to control.".format(device.name))
					return
			elif device.deviceTypeId == 'hueAttributeController' or device.deviceTypeId in kMotionSensorTypeIDs or device.deviceTypeId in kTemperatureSensorTypeIDs or device.deviceTypeId in kLightSensorTypeIDs or device.deviceTypeId in kSwitchTypeIDs:
				# Attribute controllers and sensor devices don't support alert actions. Print the error in the Indigo log.
				self.doErrorLog("The \"{}\" device does not support Alert actions. Select a different Hue device.".format(device.name))
				return
			else:
				# Sanity check on bulb ID
				bulbId = device.pluginProps.get('bulbId', None)
				if bulbId is None or bulbId == 0:
					self.doErrorLog("No bulb ID selected for device \"{}\". Check settings for this device and select a Hue Device to control.".format(device.name))
					return

			requestData = json.dumps({"alert": alertType})
			# Create the command based on whether this is a light or group device.
			if device.deviceTypeId == "hueGroup":
				command = "http://{}/api/{}/groups/{}/action".format(ipAddress, self.hostIds[hubNumber], groupId)
			else:
				command = "http://{}/api/{}/lights/{}/state".format(ipAddress, self.hostIds[hubNumber], bulbId)
			try:
				if self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(10,"SEND is {}, {}".format(command, requestData) )
				self.setBridgeBusy(hubNumber, calledfrom="doAlert")
				r = requests.put(command, data=requestData, timeout=kTimeout, headers={'Connection':'close'})
				self.resetBridgeBusy(hubNumber)
			except requests.exceptions.Timeout:
				self.doErrorLog("Failed to connect to the Hue bridge at {} after {} seconds. - Check that the bridge is connected and turned on.".format(ipAddress, kTimeout))
				self.resetBridgeBusy(hubNumber)
				return
			except requests.exceptions.ConnectionError:
				self.doErrorLog("Failed to connect to the Hue bridge at {}. - Check that the bridge is connected and turned on.".format(ipAddress))
				self.resetBridgeBusy(hubNumber)
				return
			if self.decideMyLog("ReadFromBridge"): self.indiLOG.log(10,"Got response - {}".format(r.content) )

			# Log the change (if enabled).
			if showLog:
				if alertType == "select":
					if logChanges: self.indiLOG.log(sendLog,"Sent Hue Lights  \"{}\" start short alert blink.".format(device.name))
				elif alertType == "lselect":
					if logChanges: self.indiLOG.log(sendLog,"Sent Hue Lights  \"{}\" start long alert blink.".format(device.name))
				elif alertType == "none":
					if logChanges: self.indiLOG.log(sendLog,"Sent Hue Lights  \"{}\" stop alert blink.")
			# Update the device state.
			self.updateDeviceState(device, 'alertMode', alertType)
		except Exception:
			self.logger.error("", exc_info=True)

	# Set Effect Status
	########################################
	def doEffect(self, device, effect, showLog=True):
		if self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(10,"Starting doEffect. effect: {}. Device: {}".format(effect, device))
		# effect:		String specifying the effect to use.  Hue supported effects are:
		#					none		: Stop any current effect
		#					colorloop	: Cycle through all hues at current brightness/saturation.
		#				Other effects may be supported by Hue with future firmware updates.
		try:
			hubNumber, ipAddress, hostId, paired = self.getIdsFromDevice(device)
			if not paired: return 
			logChanges = (self.pluginPrefs['logAnyChanges'] == "yes") or self.trackSpecificDevice == device.id or (self.pluginPrefs['logAnyChanges'] == "leaveToDevice" and device.pluginProps.get('logChanges', True))
			if self.trackSpecificDevice == device.id:	sendLog = 20
			else: 										sendLog = self.sendDeviceUpdatesTo


			# Sanity check for an IP address
			if ipAddress is None:
				self.doErrorLog("No IP address set for the Hue bridge. You can get this information from the My Settings page at http://www.meethue.com")
				return False

			# Act based on device type.
			if device.deviceTypeId == "hueGroup":
				# Sanity check on group ID
				groupId = device.pluginProps.get('groupId', None)
				if groupId is None or groupId == 0:
					self.doErrorLog("No group ID selected for device \"{}\". Check settings for this device and select a Hue Group to control.".format(device.name))
					return
			else:
				# Sanity check on bulb ID
				bulbId = device.pluginProps.get('bulbId', None)
				if bulbId is None or bulbId == 0:
					self.doErrorLog("No bulb ID selected for device \"{}\". Check settings for this device and select a Hue Device to control.".format(device.name))
					return

			# Submit to Hue
			requestData = json.dumps({"effect": effect})
			if self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(10,"data to be send:{}".format(requestData) )
			# Create the command based on whether this is a light or group device.
			if device.deviceTypeId == "hueGroup":
				command = "http://{}/api/{}/groups/{}/action".format(ipAddress, self.hostIds[hubNumber], groupId)
			else:
				command = "http://{}/api/{}/lights/{}/state".format(ipAddress, self.hostIds[hubNumber], bulbId)
			if self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(10,"URL: " + command)
			try:
				self.setBridgeBusy(hubNumber, calledfrom="doEffect")
				r = requests.put(command, data=requestData, timeout=kTimeout, headers={'Connection':'close'})
				self.resetBridgeBusy(hubNumber)
			except requests.exceptions.Timeout:
				self.doErrorLog("Failed to connect to the Hue bridge at {} after {} seconds. - Check that the bridge is connected and turned on." .format(ipAddress, kTimeout))
				self.resetBridgeBusy(hubNumber)
				return
			except requests.exceptions.ConnectionError:
				self.doErrorLog("Failed to connect to the Hue bridge at {}. - Check that the bridge is connected and turned on.".format(ipAddress))
				self.resetBridgeBusy(hubNumber)
				return
			if str(r.content).find("success") == -1: self.logger.error("set effect failure: - {}".format(r.content) )
			elif self.decideMyLog("ReadFromBridge"): self.indiLOG.log(10,"Got response - {}".format(r.content) )
			# Log the change (if enabled).
			if showLog:
				if logChanges: self.indiLOG.log(sendLog,"Sent Hue Lights  \"{}\" set effect to \"{}\"".format(device.name, effect))
			# Update the device state.
			self.updateDeviceState(device, 'effect', effect)
		except Exception:
			self.logger.error("", exc_info=True)

	# Recall a Hue Scene
	########################################
	def doScene(self, groupId="0", sceneId="", hubNumber = "0", showLog=True):
		if self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(10,"Starting doScene. groupId: {}, sceneId: {}.".format(groupId, sceneId))
		# groupId:		String. Group ID (numeral) on Hue bridge on which to apply the scene.
		# sceneId:		String. Scene ID on Hue bridge of scene to be applied to the group.

		# The Hue bridge behavior is to apply the scene to all members of the group that are
		#   also members of the scene.  If a group is selected that has no lights that are
		#   also part of the scene, nothing will happen when the scene is activated.  The
		#   build-in Hue group 0 is the set of all Hue lights, so if the scene is applied
		#   to group 0, all lights that are part of the scene will be affected.

		# Sanity check for an IP address
		try:
			ipAddress = self.ipAddresses[hubNumber]
			if ipAddress is None:
				self.doErrorLog("No IP address set for the Hue bridge. You can get this information from the My Settings page at http://www.meethue.com")
				return

			# Make sure a scene ID was sent.
			if sceneId == "":
				self.doErrorLog("No scene selected. Check settings for this action and select a scene to recall.")
				return
			else:
				# Let's get more scene information.
				sceneName = self.hueConfigDict[hubNumber]['scenes'][sceneId]['name']
				sceneOwner = self.hueConfigDict[hubNumber]['scenes'][sceneId]['owner']
				if sceneOwner in self.hueConfigDict[hubNumber]['users'] :
					userName = self.hueConfigDict[hubNumber]['users'][sceneOwner]['name'].replace("#", " app on ")
				else:
					userName = " (a removed scene creator)"

			# If the group isn't the default group ID 0, get more group info.
			if groupId != "0":
				groupName = self.hueConfigDict[hubNumber]['groups'][groupId]['name']
			else:
				groupName = "all hue lights"


			# Create the JSON object and send the command to the bridge.
			requestData = json.dumps({"scene": sceneId})
			# Create the command.
			command = "http://{}/api/{}/groups/{}/action".format(ipAddress, self.hostIds[hubNumber], groupId)
			if self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(10,"Sending URL request: {}".format(command) )

			try:
				self.setBridgeBusy(hubNumber, calledfrom="doScene")
				r = requests.put(command, data=requestData, timeout=kTimeout, headers={'Connection':'close'})
				self.resetBridgeBusy(hubNumber)

			except requests.exceptions.Timeout:
				self.doErrorLog("Failed to connect to the Hue bridge at {} after {} seconds. - Check that the bridge is connected and turned on.".format(ipAddress, kTimeout))
				self.resetBridgeBusy(hubNumber)
				return

			except requests.exceptions.ConnectionError:
				self.doErrorLog("Failed to connect to the Hue bridge at {}. - Check that the bridge is connected and turned on.".format(ipAddress))
				self.resetBridgeBusy(hubNumber)
				return

			if self.decideMyLog("ReadFromBridge"): self.indiLOG.log(10,"Got response - {}".format(r.content) )
			# Show the log (if enabled).
			if showLog:
				self.indiLOG.log(20,"\"{}\" scene from \"{}\" recalled for \"{}\"".format(sceneName, userName, groupName ))

		except Exception:
			self.logger.error("", exc_info=True)


	# Update Light, Group, Scene and Sensor Lists
	########################################
	def updateAllHueLists(self):
		# This function is generally only used as a callback method for the
		#    Plugins -> Hue Lights -> Reload Hue bridge Config menu item, but can
		#    be used to force a reload of everything from the Hue bridge.

	   # Do we have a unique Hue username (a.k.a. key or host ID)?
		try:
			if self.hostIds == {"0":""}:
				self.hostIds = {"0": self.hostId}

			for hubNumber in  self.hostIds:
				hueUsername = self.hostIds[hubNumber]
				if hueUsername is None :
					self.indiLOG.log(30,"Plugin does not seem to be paired with the Hue bridge:{}".format(hubNumber))

			# Get the entire Hue bridge configuration and report the results.

			# Sanity check for an IP address
			## old if only one hub, expaned to option of having multiple hubs
			oldVersionipAddress = self.pluginPrefs.get('address', None)
			tempIP= json.loads(self.pluginPrefs.get('addresses', '{"0":""}'))


			if tempIP == {'0':''} and oldVersionipAddress is not None:
				tempIP['0'] = oldVersionipAddress

			try:
				for hubNumber in copy.copy(tempIP):
					if hubNumber not in khubNumbersAvailable: continue
					if tempIP[hubNumber] is None:
						self.doErrorLog("No IP address set for the Hue bridge. You can get this information from the My Settings page at http://www.meethue.com.".format(tempIP))
						del tempIP[hubNumber]
						continue

					if not self.isValidIP(tempIP[hubNumber]):
						self.doErrorLog("IP address\"{}\" set for the Hue bridge is not valid, please set in config,".format(tempIP))
						del tempIP[hubNumber]
						continue

			except Exception:
				self.logger.error("", exc_info=True)
			self.ipAddresses = copy.copy(tempIP)
			self.pluginPrefs['addresses'] = json.dumps(self.ipAddresses)


			for hubNumber in copy.copy(self.hostIds):
				if hubNumber not in self.ipAddresses:
					del self.hostIds[hubNumber]
					self.pluginPrefs['hostIds'] = json.dumps(self.hostIds)

			# Get the entire configuration from the Hue bridge.
			self.getHueConfig()
			if self.pluginState == "init": 
				self.printHueData({'sortBy':'', 'whatToPrint':'shortBridgeInfo'},"")
		except Exception:
			self.logger.error("", exc_info=True)
				
		return




	########################################
	# Action Handling Methods
	########################################

	# Start (or Stop if already) Brightening
	########################################
	def startStopBrightening(self, action, device):
		try:		
			# Catch if no device was passed in the action call.
			if device is None:
				self.doErrorLog("No device was selected for the \"{}\" action. Please edit the action and select a Hue Light device.".format(action.name))
				return
			# Catch if the device is an on/off only device.
			if not  device.pluginProps.get('isDimmerDevice', False):
					self.doErrorLog("startStopBrightening \"{}\" is not a dimmable device".format(device.name))
					return

			if self.decideMyLog("Init"): self.indiLOG.log(10,"startStopBrightening: device: {}, action:\n{}".format(device.name, action))
			# Make sure the device is in the deviceList.
			if device.id in self.deviceList:

				# First, remove from the dimmingList if it's there.
				if device.id in self.dimmingList:
					# Log the event to Indigo log.
					self.indiLOG.log(20,"Sent Hue Lights  \"{}\" stop dimming".format(device.name))
					# Remove from list.
					self.dimmingList.remove(device.id)

				# Now remove from brighteningList if it's in the list and add if not.
				if device.id in self.brighteningList:
					# Log the event to Indigo log.
					self.indiLOG.log(20,"Sent Hue Lights  \"{}\" stop brightening".format(device.name))
					# Remove from list.
					self.brighteningList.remove(device.id)
					# Get the bulb status
					self.getBulbStatus(device.id)
					# Log the new brightnss.
					self.indiLOG.log(20,"Sent Hue Lights  \"{}\" status request (received: {})".format( device.name, device.states['brightnessLevel']))
				else:
					# Only begin brightening if current brightness is less than 100%.
					if device.states['brightnessLevel'] < 100:
						# Log the event in Indigo log.
						self.indiLOG.log(20,"Sent Hue Lights  \"{}\" start brightening".format(device.name))
						# Add to list.
						self.brighteningList.append(device.id)
		except Exception:
			self.logger.error("", exc_info=True)

		return

	# Start (or Stop if already) Dimming
	########################################
	def startStopDimming(self, action, device):
		# Catch if no device was passed in the action call.
		try:
			if device is None:
				self.doErrorLog("No device was selected for the \"{}\" action. Please edit the action and select a Hue Light device.".format(action.name))
				return
			# Catch if the device is an on/off only device.
			if not  device.pluginProps.get('isDimmerDevice', False):
					self.doErrorLog("startStopDimming \"{}\" is not a dimmable device".format(device.name))
					return

			if self.decideMyLog("Init"): self.indiLOG.log(10,"startStopDimming: device: {}, action:\n{}".format(device.name, action))
			# Make sure the device is in the deviceList.
			if device.id in self.deviceList:
				# First, remove from brighteningList if it's there.
				if device.id in self.brighteningList:
					# Log the event to Indigo log.
					self.indiLOG.log(20,"Sent Hue Lights  \"{}\" stop brightening".format(device.name))
					# Remove from list.
					self.brighteningList.remove(device.id)

				# Now remove from dimmingList if it's in the list and add if not.
				if device.id in self.dimmingList:
					# Log the event to Indigo log.
					self.indiLOG.log(20,"Sent Hue Lights  \"{}\" stop dimming".format(device.name))
					# Remove from list.
					self.dimmingList.remove(device.id)
					# Get the bulb status
					self.getBulbStatus(device.id)
					# Log the new brightnss.
					self.indiLOG.log(20,"Sent Hue Lights  \"{}\" status request (received: {})".format(device.name, device.states['brightnessLevel']))
				else:
					# Only begin dimming if current brightness is greater than 0%.
					if device.states['brightnessLevel'] > 0:
						# Log the event in Indigo log.
						self.indiLOG.log(20,"Sent Hue Lights  \"{}\" start dimming".format(device.name))
						# Add to list.
						self.dimmingList.append(device.id)
		except Exception:
			self.logger.error("", exc_info=True)

		return

	# Stop Brightening and Dimming
	########################################
	def stopBrighteningAndDimming(self, action, device):
		# Catch if no device was passed in the action call.
		try:
			if device is None:
				self.doErrorLog("No device was selected for the \"{}\" action. Please edit the action and select a Hue Light device.".format(action))
				return
			# Catch if the device is an on/off only device.
			if not device.pluginProps.get('isDimmerDevice', False):
					self.doErrorLog("stopBrighteningAndDimming \"{}\" is not a dimmable device".format(device.name))
					return

			if self.decideMyLog("Init"): self.indiLOG.log(10,"stopBrighteningAndDimming: device: {}, action:\n{}".format(device.name, action))
			# Make sure the device is in the deviceList.
			if device.id in self.deviceList:
				# First, remove from brighteningList if it's there.
				if device.id in self.brighteningList:
					# Log the event to Indigo log.
					self.indiLOG.log(20,"Sent Hue Lights  \"{}\" stop brightening".format(device.name))
					# Remove from list.
					self.brighteningList.remove(device.id)

				# Now remove from dimmingList if it's in the list.
				if device.id in self.dimmingList:
					# Log the event to Indigo log.
					self.indiLOG.log(20,"Sent Hue Lights  \"{}\" stop dimming".format(device.name))
					# Remove from list.
					self.dimmingList.remove(device.id)
					# Get the bulb status
					self.getBulbStatus(device.id)
					# Log the new brightness.
					self.indiLOG.log(20,"Sent Hue Lights  \"{}\" status request (received: {})".format(device.name, device.states['brightnessLevel']))
		except Exception:
			self.logger.error("", exc_info=True)

		return

	# Set Brightness
	########################################
	def setBrightness(self, action, device):
		if self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(10,"setBrightness: device:\"{}\", action:\n{}".format(device.name, action))
		try:
			# Act based on device type.
			if device.deviceTypeId == "hueGroup":
				# Sanity check on group ID
				groupId = device.pluginProps.get('groupId', None)
				if groupId is None or groupId == 0:
					self.doErrorLog("No group ID selected for device \"{}\". Check settings for this device and select a Hue Group to control.".format(device.name))
					return
			else:
				# Sanity check on bulb ID
				bulbId = device.pluginProps.get('bulbId', None)
				if bulbId is None or bulbId == 0:
					self.doErrorLog("No bulb ID selected for device \"{}\". Check settings for this device and select a Hue Device to control.".format(device.name))
					return

			if not device.pluginProps.get('isDimmerDevice', False):
					self.doErrorLog("setBrightness \"{}\" is not a dimmable device".format(device.name))
					return

			brightnessSource = action.props.get('brightnessSource', False)
			brightness = action.props.get('brightness', False)
			brightnessVarId = action.props.get('brightnessVariable', False)
			brightnessDevId = action.props.get('brightnessDevice', False)
			useRateVariable = action.props.get('useRateVariable', False)
			rate = action.props.get('rate', False)
			rateVarId = action.props.get('rateVariable', False)


			# Validate the action properties.
			if not brightnessSource:
				# The dimmer level source wasn't specified. Try to figure out
				#   the intended source based on passed data in the action call.
				if brightness.__class__ != bool:
					brightnessSource = "custom"
				elif brightnessVarId:
					brightnessSource = "variable"
				elif brightnessDevId:
					brightnessSource = "dimmer"
				else:
					self.doErrorLog("No brightness source information was provided.")
					return None

			if brightnessSource == "custom":
				if not brightness and brightness.__class__ != int:
					self.doErrorLog("No brightness level was specified.")
					return None
				else:
					try:
						brightness = int(brightness)
						if brightness < 0 or brightness > 100:
							self.doErrorLog("Brightness level {} is outside the acceptable range of 0 to 100.".format(brightness))
							return None
					except ValueError:
						self.doErrorLog("Brightness level \"{}\" is invalid. Brightness values can only contain numbers.".format(brightness))
						return None
				if self.decideMyLog("Init"): self.indiLOG.log(10,"Brightness (source: custom): {}, class: {}".format(brightness, brightness.__class__))

			elif brightnessSource == "variable":
				if not brightnessVarId:
					self.doErrorLog("No variable containing the brightness level was specified.")
					return None
				else:
					try:
						brightnessVar = indigo.variables[int(brightnessVarId)]
						# Embedding float method inside int method allows for fractional
						#   data but just drops everything after the decimal.
						brightness = int(float(brightnessVar.value))
						if brightness < 0 or brightness > 100:
							self.doErrorLog("Brightness level {} found in variable \"{}\" is outside the acceptable range of 0 to 100.".format(brightness, brightnessVar.name))
							return None
					except ValueError:
						self.doErrorLog("Brightness level \"{}\" found in variable \"{}\" is invalid. Brightness values can only contain numbers.".format(brightnessVar.value, brightnessVar.name))
						return None
					except IndexError:
						self.doErrorLog("The specified variable (ID:{}) does not exist in the Indigo database.".format(brightnessVarId))
						return None
				if self.decideMyLog("Init"): self.indiLOG.log(10,"Brightness (source: variable):{} , class:{} ".format(brightnessVarId, brightness.__class__))

			elif brightnessSource == "dimmer":
				if not brightnessDevId:
					self.doErrorLog("No dimmer was specified as the brightness level source.")
					return None
				else:
					# See if the submitted value is a device ID or a device name.
					try:
						brightnessDevId = int(brightnessDevId)
						# Value is a device ID number.
					except ValueError:
						try:
							brightnessDevId = indigo.devices[brightnessDevId].name
							# Value is a device name.
						except KeyError:
							self.doErrorLog("No device with the name \"{}\" could be found in the Indigo database.".format(brightnessDevId))
							return None
					try:
						brightnessDev = indigo.devices[brightnessDevId]
						brightness = int(brightnessDev.states.get('brightnessLevel', None))
						if brightness is None:
							# Looks like this isn't a dimmer after all.
							self.doErrorLog("Device \"{}\" does not appear to be a dimmer. Only dimmers can be used as brightness sources.".format(brightnessDev.name))
							return None
						elif brightness < 0 or brightness > 100:
							self.doErrorLog("Brightness level {} of device \"{}\" is outside the acceptable range of 0 to 100.".format(brightness, brightnessDev.name))
							return None
					except ValueError:
						self.doErrorLog("The device \"{}\" does not have a brightness level. Please ensure that the device is a dimmer.".format(brightnessDev.name))
						return None
					except KeyError:
						self.doErrorLog("The specified device (ID:{}) does not exist in the Indigo database.".format(brightnessDevId))
						return None
				if self.decideMyLog("Init"): self.indiLOG.log(10,"Brightness (source: other dimmer): {}, class: {}".format(brightness, brightness.__class__))

			else:
				self.doErrorLog("Unrecognized brightness source \"{}\". Valid brightness sources are \"custom\", \"variable\", and \"dimmer\".".format(brightnessSource))
				return None

			if not useRateVariable:
				if not rate and rate.__class__ == bool:
					self.doErrorLog("No ramp rate was specified.")
					return None
				else:
					try:
						rate = float(rate)
						if rate < 0 or rate > 540:
							self.doErrorLog("Ramp rate value \"{}\" is outside the acceptible range of 0 to 540.".format(rate))
							return None
					except ValueError:
						self.doErrorLog("Ramp rate value \"{}\" is an invalid value. Ramp rate values can only contain numbers.".format(rate))
						return None
				if self.decideMyLog("Init"): self.indiLOG.log(10,"Rate: {}" .format(rate))

			else:
				if not rateVarId:
					self.doErrorLog("No variable containing the ramp rate time was specified.")
					return None
				else:
					try:
						# Make sure rate is set to ""
						rate = ""
						rateVar = indigo.variables[int(rateVarId)]
						rate = float(rateVar.value)
						if rate < 0 or rate > 540:
							self.doErrorLog("Ramp rate value \"{}\" found in variable \"{}\" is outside the acceptible range of 0 to 540.".format(rate, rateVar.name))
							return None
					except ValueError:
						self.doErrorLog("Ramp rate value \"{}\" found in variable \"{}\" is an invalid value. Ramp rate values can only contain numbers.".format(rate, rateVar.name))
						return None
					except IndexError:
						self.doErrorLog("The specified variable (ID:{}) does not exist in the Indigo database.".format(brightnessVarId))
				if self.decideMyLog("Init"): self.indiLOG.log(10,"Rate: {}".format(rate))

			# Save the new brightness level into the device properties.
			if brightness > 0:
				# On/Off devices have no savedBrightness, so don't try to change it.
				if device.deviceTypeId != "hueOnOffDevice":
					tempProps = device.pluginProps
					tempProps['savedBrightness'] = brightness
					self.updateDeviceProps(device, tempProps)

			# Send the command.
			self.doBrightness(device, int(round(brightness * 255.0 / 100.0)), rate)
		except Exception:
			self.logger.error("", exc_info=True)

	# Set RGB Level Action
	########################################
	def setRGB(self, action, device):
		if self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(10,"setRGB: device:\"{}\", action:\n{}".format(device.name, action))
		try:
			red = action.props.get('red', 0)
			green = action.props.get('green', 0)
			blue = action.props.get('blue', 0)
			useRateVariable = action.props.get('useRateVariable', False)
			rampRate = action.props.get('rate', -1)
			rateVarId = action.props.get('rateVariable', False)

			# Act based on device type.
			if device.deviceTypeId == "hueGroup":
				# Sanity check on group ID
				groupId = device.pluginProps.get('groupId', None)
				if groupId is None or groupId == 0:
					self.doErrorLog("No group ID selected for device \"{}\". Check settings for this device and select a Hue Group to control.".format(device.name))
					return
			else:
				# Sanity check on bulb ID
				bulbId = device.pluginProps.get('bulbId', None)
				if bulbId is None or bulbId == 0:
					self.doErrorLog("No bulb ID selected for device \"{}\". Check settings for this device and select a Hue Device to control.".format(device.name))
					return
			if not device.pluginProps.get('isDimmerDevice', False):
					self.doErrorLog("setRGB \"{}\" is not a dimmable device".format(device.name))
					return

			try:
				red = int(red)
			except ValueError:
				self.doErrorLog("Red color value specified for \"{}\" is invalid.".format(device.name))
				return

			try:
				green = int(green)
			except ValueError:
				self.doErrorLog("Green color value specified for \"{}\" is invalid.".format(device.name))
				return

			try:
				blue = int(blue)
			except ValueError:
				self.doErrorLog("Blue color value specified for \"{}\" is invalid.".format(device.name))
				return

			if not useRateVariable:
				# Not using variable, so they've specificed a ramp rate.
				if rampRate == "" or rampRate == -1:
					# No ramp rate was specificed. Use the device's default rate, or 0.5.
					rampRate = device.pluginProps.get('rate', 0.5)
					# Devices can have an empty string for the default ramp rate.
					#   Catch this and use a default rate of 0.5 seconds if empty.
					if rampRate == "":
						rampRate = 0.5

				try:
					rampRate = float(rampRate)
					if rampRate < 0 or rampRate > 540:
						self.doErrorLog("Ramp rate value {}\" is outside the acceptible range of 0 to 540.".format(rampRate))
						return None
				except ValueError:
					self.doErrorLog("Ramp rate value \"{}\" is an invalid value. Ramp rate values can only contain numbers.".format(rampRate))
					return None
				if self.decideMyLog("Init"): self.indiLOG.log(10,"Rate: {}".format(rampRate))

			else:
				# We're using a ramp rate variable.
				if not rateVarId:
					# No ramp rate variable was specified.
					self.doErrorLog("No variable containing the ramp rate time was specified.")
					return
				else:
					# A ramp rate variable was specified.
					try:
						rateVar = indigo.variables[int(rateVarId)]
						rampRate = rateVar.value
						rampRate = float(rampRate)
						if rampRate < 0 or rampRate > 540:
							self.doErrorLog("Ramp rate value \"{}\" found in variable \"{}\" is outside the acceptible range of 0 to 540.".format(rampRate, rateVar.name ))
							return
					except ValueError:
						self.doErrorLog("Ramp rate value \"{}\" found in variable \"{}\" is an invalid value. Ramp rate values can only contain numbers.".format(rampRate, rateVar.name ))
						return
					except IndexError:
						self.doErrorLog("The specified variable (ID:{}) does not exist in the Indigo database.".format(rateVarId ))
						return
				if self.decideMyLog("Init"): self.indiLOG.log(10,"Rate: {}".format(rampRate))

			# Determine the brightness based on the highest RGB value (to save in device props).
			brightness = red
			if blue > brightness:
				brightness = blue
			elif green > brightness:
				brightness = green

			# Save the new brightness level into the device properties.
			if brightness > 0:
				tempProps = device.pluginProps
				tempProps['savedBrightness'] = brightness
				self.updateDeviceProps(device, tempProps)

			# Send the command.
			self.doRGB(device, red, green, blue, rampRate)
		except Exception:
			self.logger.error("", exc_info=True)

	# Set HSB Action
	########################################
	def setHSB(self, action, device):
		if self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(10,"setHSB: device:\"{}\", action:\n{}".format(device.name, action))
		try:
			# Act based on device type.
			if device.deviceTypeId == "hueGroup":
				# Sanity check on group ID
				groupId = device.pluginProps.get('groupId', None)
				if groupId is None or groupId == 0:
					self.doErrorLog("No group ID selected for device \"{}\". Check settings for this device and select a Hue Group to control.".format(device.name))
					return
			else:
				# Sanity check on bulb ID
				bulbId = device.pluginProps.get('bulbId', None)
				if bulbId is None or bulbId == 0:
					self.doErrorLog("No bulb ID selected for device \"{}\". Check settings for this device and select a Hue Device to control.".format(device.name))
					return
			if not device.pluginProps.get('isDimmerDevice', False):
					self.doErrorLog("setHSB \"{}\" is not a dimmable device".format(device.name))
					return

			hue = action.props.get('hue', 0)
			saturation = action.props.get('saturation', 0)
			brightnessSource = action.props.get('brightnessSource', "custom")
			brightness = action.props.get('brightness', False)
			brightnessVariable = action.props.get('brightnessVariable', False)
			brightnessDevice = action.props.get('brightnessDevice', False)
			useRateVariable = action.props.get('useRateVariable', False)
			rampRate = action.props.get('rate', -1)
			rateVarId = action.props.get('rateVariable', False)


			try:
				hue = float(hue)
			except ValueError:
				# The float() cast above might fail if the user didn't enter a number:
				self.doErrorLog("Set Hue, Saturation, Brightness for device \"{}\" -- invalid hue value (must range 0-360)".format(device.name))
				return

			try:
				saturation = int(saturation)
			except ValueError:
				# The int() cast above might fail if the user didn't enter a number:
				self.doErrorLog("Set Hue, Saturation, Brightness for device \"{}\" -- invalid saturation value (must range 0-100)".format(device.name))
				return

			if brightnessSource == "custom":
				# Using an entered brightness value.
				if brightness:
					try:
						brightness = int(brightness)
					except ValueError:
						self.doErrorLog("Invalid brightness value \"{}\" specified for device \"{}\". Value must be in the range 0-100.".format(brightness, device.name))
						return

					# Make sure the brightness specified in the variable is sane.
					if brightness < 0 or brightness > 100:
						self.doErrorLog("Brightness value \"{}\" for device \"{}\" is outside the acceptible range of 0 to 100.".format(brightness, device.name))
						return
				else:
					brightness = device.states['brightnessLevel']
			elif brightnessSource == "variable":
				if brightnessVariable:
					# Action properties are passed as strings. Variable and device IDs are integers
					# so we need to convert the variable ID passed in brightnessVariable to an integer.
					brightnessVariable = int(brightnessVariable)
					try:
						brightness = int(indigo.variables[brightnessVariable].value)
					except ValueError:
						self.doErrorLog("Brightness value \"{}\" specified in variable \"{}\" for device \"{}\" is invalid.".format(indigo.variables[brightnessVariable].value , indigo.variables[brightnessVariable].name, device.name))
						return
					except IndexError:
						self.doErrorLog("The brightness source variable (ID:{}) does not exist in the Indigo database.".format(brightnessVariable))
						return

					# Make sure the brightness specified in the variable is sane.
					if brightness < 0 or brightness > 100:
						self.doErrorLog("Brightness value \"{}\" specified in variable \"{}\" is outside the acceptible range of 0 to 100.".format(brightness , indigo.variables[brightnessVariable].name))
						return
				else:
					brightness = device.states['brightnessLevel']
			elif brightnessSource == "dimmer":
				if brightnessDevice:
					# Action properties are passed as strings. Variable and device IDs are integers
					# so we need to convert the device ID passed in brightnessDevice to an integer.
					brightnessDevice = int(brightnessDevice)
					try:
						brightness = int(indigo.devices[brightnessDevice].states['brightnessLevel'])
					except ValueError:
						self.doErrorLog("The brightness \"{}\" of the selected source device \"{}\" is invalid.".format(indigo.devices[brightnessDevice].states['brightnessLevel']  , indigo.devices[brightnessDevice].name ))
						return
					except IndexError:
						self.doErrorLog("The brightness source device (ID:{}) does not exist in the Indigo database.".format(brightnessDevice))
						return
				else:
					brightness = device.states['brightnessLevel']

			if not useRateVariable:
				# Not using variable, so they've specified a ramp rate.
				if rampRate == "" or rampRate == -1:
					# No ramp rate was specificed. Use the device's default rate, or 0.5.
					rampRate = device.pluginProps.get('rate', 0.5)
					# Devices can have an empty string for the default ramp rate.
					#   Catch this and use a default rate of 0.5 seconds if empty.
					if rampRate == "":
						rampRate = 0.5

				try:
					rampRate = float(rampRate)
					if rampRate < 0 or rampRate > 540:
						self.doErrorLog("Ramp rate value {}\" is outside the acceptable range of 0 to 540.".format(rampRate))
						return None
				except ValueError:
					self.doErrorLog("Ramp rate value \"{}\" is an invalid value. Ramp rate values can only contain numbers.".format(rampRate))
					return None
				if self.decideMyLog("Init"): self.indiLOG.log(10,"Rate: {}".format(rampRate))

			else:
				# We're using a ramp rate variable.
				if not rateVarId:
					# No ramp rate variable was specified.
					self.doErrorLog("No variable containing the ramp rate time was specified.")
					return
				else:
					# A ramp rate variable was specified.
					try:
						rateVar = indigo.variables[int(rateVarId)]
						rampRate = rateVar.value
						rampRate = float(rampRate)
						if rampRate < 0 or rampRate > 540:
							self.doErrorLog("Ramp rate value \"{}\" found in variable \"{}\" is outside the acceptable range of 0 to 540.".format(rampRate, rateVar.name ))
							return
					except ValueError:
						self.doErrorLog("Ramp rate value \"{}\" found in variable \"{}\" is an invalid value. Ramp rate values can only contain numbers.".format(rampRate, rateVar.name ))
						return
					except IndexError:
						self.doErrorLog("The specified variable (ID:{}) does not exist in the Indigo database.".format(rateVarId))
						return
				if self.decideMyLog("Init"): self.indiLOG.log(10,"Rate: {}".format(rampRate))

			# Scale these values to match Hue
			brightness = int(ceil(brightness * 255.0 / 100.0))
			saturation = int(ceil(saturation * 255.0 / 100.0))
			hue = int(round(hue * 182.0))

			# Save the new brightness level into the device properties.
			if brightness > 0:
				tempProps = device.pluginProps
				tempProps['savedBrightness'] = brightness
				self.updateDeviceProps(device, tempProps)

			# Send the command.
			self.doHSB(device, hue, saturation, brightness, rampRate)
		except Exception:
			self.logger.error("", exc_info=True)

	# Set xyY Action
	########################################
	def setXYY(self, action, device):
		if self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(10,"setXYY called. device:\"{}\", action:\n{}".format(device.name, action))
		try:
			# Act based on device type.
			if device.deviceTypeId == "hueGroup":
				# Sanity check on group ID
				groupId = device.pluginProps.get('groupId', None)
				if groupId is None or groupId == 0:
					self.doErrorLog("No group ID selected for device \"{}\". Check settings for this device and select a Hue Group to control.".format(device.name))
					return
			else:
				# Sanity check on bulb ID
				bulbId = device.pluginProps.get('bulbId', None)
				if bulbId is None or bulbId == 0:
					self.doErrorLog("No bulb ID selected for device \"{}\". Check settings for this device and select a Hue Device to control.".format(device.name))
					return

			if not device.pluginProps.get('isDimmerDevice', False):
					self.doErrorLog("setXYY \"{}\" is not a dimmable device".format(device.name))
					return

			colorX = action.props.get('xyy_x', 0.0)
			colorY = action.props.get('xyy_y', 0.0)
			brightness = action.props.get('xyy_Y', 0)
			useRateVariable = action.props.get('useRateVariable', False)
			rampRate = action.props.get('rate', -1)
			rateVarId = action.props.get('rateVariable', False)


			try:
				colorX = float(colorX)
			except ValueError:
				# The float() cast above might fail if the user didn't enter a number:
				self.doErrorLog("Set chromatisety x, y, and Y values for the device \"{}\" -- invalid x value (must be in the range of 0.0-1.0)".format(device.name))
				return

			try:
				colorY = float(colorY)
			except ValueError:
				# The float() cast above might fail if the user didn't enter a number:
				self.doErrorLog("Set chromatisety x, y, and Y values for the device \"{}\" -- invalid y value (must be in the range of 0.0-1.0)".format(device.name))
				return

			try:
				brightness = float(brightness)
			except ValueError:
				# The float() cast above might fail if the user didn't enter a number:
				self.doErrorLog("Set chromatisety x, y, and Y values for the device \"{}\" -- invalid Y value of \"{}\" (must be in the range of 0.0-1.0)".format(device.name, brightness))
				return

			if not useRateVariable:
				# Not using variable, so they've specified a ramp rate.
				if rampRate == "" or rampRate == -1:
					# No ramp rate was specified. Use the device's default rate, or 0.5.
					rampRate = device.pluginProps.get('rate', 0.5)
					# Devices can have an empty string for the default ramp rate.
					#   Catch this and use a default rate of 0.5 seconds if empty.
					if rampRate == "":
						rampRate = 0.5

				try:
					rampRate = float(rampRate)
					if rampRate < 0 or rampRate > 540:
						self.doErrorLog("Ramp rate value {}\" is outside the acceptable range of 0 to 540.".format(rampRate))
						return None
				except ValueError:
					self.doErrorLog("Ramp rate value \"{}\" is an invalid value. Ramp rate values can only contain numbers.".format(rampRate))
					return None
				if self.decideMyLog("Init"): self.indiLOG.log(10,"Rate: {}".format(rampRate))

			else:
				# We're using a ramp rate variable.
				if not rateVarId:
					# No ramp rate variable was specified.
					self.doErrorLog("No variable containing the ramp rate time was specified.")
					return
				else:
					# A ramp rate variable was specified.
					try:
						rateVar = indigo.variables[int(rateVarId)]
						rampRate = rateVar.value
						rampRate = float(rampRate)
						if rampRate < 0 or rampRate > 540:
							self.doErrorLog("Ramp rate value \"{}\" found in variable \"{}\" is outside the acceptable range of 0 to 540.".format(rampRate, rateVar.name ))
							return
					except ValueError:
						self.doErrorLog("Ramp rate value \"{}\" found in variable \"{}\" is an invalid value. Ramp rate values can only contain numbers.".format(rampRate, rateVar.name ))
						return
					except IndexError:
						self.doErrorLog("The specified variable (ID:{}) does not exist in the Indigo database.".format(rateVarId))
						return
				if self.decideMyLog("Init"): self.indiLOG.log(10,"Rate: {}".format(rampRate))

			# Scale the brightness values to match Hue system requirements.
			brightness = int(ceil(brightness * 255.0))

			# Save the new brightness level into the device properties.
			if brightness > 0:
				tempProps = device.pluginProps
				tempProps['savedBrightness'] = brightness
				self.updateDeviceProps(device, tempProps)

			# Send the command.
			self.doXYY(device, colorX, colorY, brightness, rampRate)
		except Exception:
			self.logger.error("", exc_info=True)

	# Set Color Temperature Action
	########################################
	def setColorTemperature(self, action, device):
		if self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(10,"setColorTemperature: device:\"{}\", action:\n{}".format(device.name, action))
		try:
			if not device.pluginProps.get('isDimmerDevice', False):
					self.doErrorLog("setXYY \"{}\" is not a dimmable device".format(device.name))
					return
			bulbId = device.pluginProps.get('bulbId', None)
			groupId = device.pluginProps.get('groupId', None)
			# Act based on device type.
			if device.deviceTypeId == "hueGroup":
				# Sanity check on group ID
				if groupId is None or groupId == 0:
					self.doErrorLog("No group ID selected for device \"{}\". Check settings for this device and select a Hue Group to control.".format(device.name))
					return
			else:
				# Sanity check on bulb ID
				if bulbId is None or bulbId == 0:
					self.doErrorLog("No bulb ID selected for device \"{}\". Check settings for this device and select a Hue Device to control.".format(device.name))
					return


			# Get the Hue "color recipe" selection. Use "custom" if not specified.
			#   (The use of the property name "preset" pre-dates the implementation
			#   of the Save and Recall Preset functions within the plugin.  The
			#   term "preset" was originally used in the Hue app distributed by
			#   Phillips, who've since decided to call them "recipes."  Now it's
			#   just confusing).
			preset = action.props.get('preset', "custom")
			temperatureSource = action.props.get('temperatureSource', "custom")
			temperature = action.props.get('temperature', 2800)
			temperatureVariable = action.props.get('temperatureVariable', False)
			brightnessSource = action.props.get('brightnessSource', "custom")
			brightness = action.props.get('brightness', False)
			brightnessVariable = action.props.get('brightnessVariable', False)
			brightnessDevice = action.props.get('brightnessDevice', False)
			useRateVariable = action.props.get('useRateVariable', False)
			rampRate = action.props.get('rate', -1)
			rateVarId = action.props.get('rateVariable', False)


			if preset == "custom":
				# Using a custom color recipe (temperature/brightness combination).
				if temperatureSource == "custom":
					try:
						temperature = int(temperature)
					except ValueError:
						# The int() cast above might fail if the user didn't enter a number:
						self.doErrorLog("Invalid color temperature specified for device \"{}\".  Value must be in the range 2000 to 6500.".format(device.name))
						return
				elif temperatureSource == "variable":
					if temperatureVariable:
						# Action properties are passed as strings. Variable and device IDs are integers
						# so we need to convert the variable ID passed in brightnessVariable to an integer.
						temperatureVariable = int(temperatureVariable)
						try:
							temperature = int(indigo.variables[temperatureVariable].value)
						except ValueError:
							self.doErrorLog("Invalid color temperature value \{}\" found in source variable \"{}\" for device \"{}\".".format(indigo.variables[temperatureVariable].value, indigo.variables[temperatureVariable].name , device.name))
							return

						# Make sure the color temperature specified in the variable is sane.
						if temperature < 2000 or temperature > 6500:
							self.doErrorLog("Color temperature value \"{}\" found in source variable \"{}\" for device \"{}\" is outside the acceptable range of 2000 to 6500." .format(temperature, indigo.variables[temperatureVariable].name , device.name))
							return
					else:
						temperature = device.states['colorTemp']

				if brightnessSource == "custom":
					# Using an entered brightness value.
					if brightness:
						try:
							brightness = int(brightness)
						except ValueError:
							self.doErrorLog("Invalid brightness value \"{}\" specified for device \"{}\". Value must be in the range 0-100.".format(brightness, device.name))
							return

						# Make sure the brightness specified in the variable is sane.
						if brightness < 0 or brightness > 100:
							self.doErrorLog("Brightness value \"{}\" for device \"{}\" is outside the acceptable range of 0 to 100.".format(brightness, device.name))
							return
					else:
						brightness = device.states['brightnessLevel']
				elif brightnessSource == "variable":
					if brightnessVariable:
						# Action properties are passed as strings. Variable and device IDs are integers
						# so we need to convert the variable ID passed in brightnessVariable to an integer.
						brightnessVariable = int(brightnessVariable)
						try:
							brightness = int(indigo.variables[brightnessVariable].value)
						except ValueError:
							self.doErrorLog("Brightness value \"{}\" specified in variable \"{}\" for device \"{}\" is invalid.".format(indigo.variables[brightnessVariable].value, indigo.variables[brightnessVariable].name , device.name))
							return
						except IndexError:
							self.doErrorLog("The brightness source variable (ID{}) does not exist in the Indigo database.".format(brightnessVariable))
							return

						# Make sure the brightness specified in the variable is sane.
						if brightness < 0 or brightness > 100:
							self.doErrorLog("Brightness value \"{}\" specified in variable \"{}\" is outside the acceptable range of 0 to 100.".format(brightnessVariable, indigo.variables[brightnessVariable].name))
							return
					else:
						brightness = device.states['brightnessLevel']
				elif brightnessSource == "dimmer":
					if brightnessDevice:
						# Action properties are passed as strings. Variable and device IDs are integers
						# so we need to convert the device ID passed in brightnessDevice to an integer.
						brightnessDevice = int(brightnessDevice)
						try:
							brightness = int(indigo.devices[brightnessDevice].states['brightnessLevel'])
						except ValueError:
							self.doErrorLog("The brightness \"{}\" of the selected source device \"{}\" is invalid.".format(indigo.devices[brightnessDevice].states['brightnessLevel'], indigo.devices[brightnessDevice].name ))
							return
						except IndexError:
							self.doErrorLog("The brightness source device (ID:{}) does not exist in the Indigo database.".format(brightnessDevice))
							return
					else:
						brightness = device.states['brightnessLevel']

				# Scale the brightness value for use with Hue.
				brightness = int(round(brightness * 255.0 / 100.0))

			if not useRateVariable:
				# Not using variable, so they've specified a ramp rate.
				if rampRate == "" or rampRate == -1:
					# No ramp rate was specified. Use the device's default rate, or 0.5.
					rampRate = device.pluginProps.get('rate', 0.5)
					# Devices can have an empty string for the default ramp rate.
					#   Catch this and use a default rate of 0.5 seconds if empty.
					if rampRate == "":
						rampRate = 0.5

				try:
					rampRate = float(rampRate)
					if rampRate < 0 or rampRate > 540:
						self.doErrorLog("Ramp rate value {}\" is outside the acceptable range of 0 to 540.".format(rampRate))
						return None
				except ValueError:
					self.doErrorLog("Ramp rate value \"{}\" is an invalid value. Ramp rate values can only contain numbers.".format(rampRate))
					return None
				if self.decideMyLog("Init"): self.indiLOG.log(10,"Rate: {}".format(rampRate))

			else:
				# We're using a ramp rate variable.
				if not rateVarId:
					# No ramp rate variable was specified.
					self.doErrorLog("No variable containing the ramp rate time was specified.")
					return
				else:
					# A ramp rate variable was specified.
					try:
						rateVar = indigo.variables[int(rateVarId)]
						rampRate = rateVar.value
						rampRate = float(rampRate)
						if rampRate < 0 or rampRate > 540:
							self.doErrorLog("Ramp rate value \"{}\" found in variable \"{}\" is outside the acceptable range of 0 to 540.".format(rampRate, rateVar.name ))
							return
					except ValueError:
						self.doErrorLog("Ramp rate value \"{}\" found in variable \"{}\" is an invalid value. Ramp rate values can only contain numbers.".format(rampRate, rateVar.name ))
						return
					except IndexError:
						self.doErrorLog("The specified variable (ID:{}) does not exist in the Indigo database.".format(rateVarId))
						return
				if self.decideMyLog("Init"): self.indiLOG.log(10,"Rate: {}".format(rampRate))

			# Configure presets
			if preset == "concentrate":
				brightness = 219
				temperature = 4292
			elif preset == "relax":
				brightness = 144
				temperature = 2132
			elif preset == "energize":
				brightness = 203
				temperature = 6410
			elif preset == "reading":
				brightness = 240
				temperature = 2890

			# Save the new brightness level into the device properties.
			if brightness > 0:
				tempProps = device.pluginProps
				tempProps['savedBrightness'] = brightness
				self.updateDeviceProps(device, tempProps)

			# Send the command.
			self.doColorTemperature(device, temperature, brightness, rampRate)
		except Exception:
			self.logger.error("", exc_info=True)

	# Set Single Alert Action
	########################################
	def alertOnce(self, action, device):
		if self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(10,"alertOnce: device:\"{}\", action:\n{}".format(device.name, action))
		try:
			# Act based on device type.
			if device.deviceTypeId == "hueGroup":
				# Sanity check on group ID
				groupId = device.pluginProps.get('groupId', None)
				if groupId is None or groupId == 0:
					self.doErrorLog("No group ID selected for device \"{}\". Check settings for this device and select a Hue Group to control.".format(device.name))
					return
			elif device.deviceTypeId == 'hueAttributeController' or device.deviceTypeId in kMotionSensorTypeIDs or device.deviceTypeId in kTemperatureSensorTypeIDs or device.deviceTypeId in kLightSensorTypeIDs or device.deviceTypeId in kSwitchTypeIDs:
				# Attribute controllers and sensor devices don't support alert actions. Print the error in the Indigo log.
				self.doErrorLog("The \"{}\" device does not support Alert actions. Select a different Hue device.".format(device.name))
				return
			else:
				# Sanity check on bulb ID
				bulbId = device.pluginProps.get('bulbId', None)
				if bulbId is None or bulbId == 0:
					self.doErrorLog("No bulb ID selected for device \"{}\". Check settings for this device and select a Hue Device to control.".format(device.name))
					return

			self.doAlert(device, "select")
		except Exception:
			self.logger.error("", exc_info=True)

	# Set Long Alert Action
	########################################
	def longAlert(self, action, device):
		if self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(10,"longAlert: device:\"{}\", action:\n{}".format(device.name, action))
		try:
			# Act based on device type.
			if device.deviceTypeId == "hueGroup":
				# Sanity check on group ID
				groupId = device.pluginProps.get('groupId', None)
				if groupId is None or groupId == 0:
					self.doErrorLog("No group ID selected for device \"{}\". Check settings for this device and select a Hue Group to control.".format(device.name))
					return
			elif device.deviceTypeId == 'hueAttributeController' or device.deviceTypeId in kMotionSensorTypeIDs or device.deviceTypeId in kTemperatureSensorTypeIDs or device.deviceTypeId in kLightSensorTypeIDs or device.deviceTypeId in kSwitchTypeIDs:
				# Attribute controllers and sensor devices don't support alert actions. Print the error in the Indigo log.
				self.doErrorLog("The \"{}\" device does not support Alert actions. Select a different Hue device.".format(device.name))
				return
			else:
				# Sanity check on bulb ID
				bulbId = device.pluginProps.get('bulbId', None)
				if bulbId is None or bulbId == 0:
					self.doErrorLog("No bulb ID selected for device \"{}\". Check settings for this device and select a Hue Device to control.".format(device.name))
					return

			self.doAlert(device, "lselect")
		except Exception:
			self.logger.error("", exc_info=True)

	# Stop Alert Action
	########################################
	def stopAlert(self, action, device):
		if self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(10,"stopAlert: device:\"{}\", action:\n{}".format(device.name, action))
		try:
			# Act based on device type.
			if device.deviceTypeId == "hueGroup":
				# Sanity check on group ID
				groupId = device.pluginProps.get('groupId', None)
				if groupId is None or groupId == 0:
					self.doErrorLog("No group ID selected for device \"{}\". Check settings for this device and select a Hue Group to control.".format(device.name))
					return
			elif device.deviceTypeId == 'hueAttributeController' or device.deviceTypeId in kMotionSensorTypeIDs or device.deviceTypeId in kTemperatureSensorTypeIDs or device.deviceTypeId in kLightSensorTypeIDs or device.deviceTypeId in kSwitchTypeIDs:
				# Attribute controllers and sensor devices don't support alert actions. Print the error in the Indigo log.
				self.doErrorLog("The \"{}\" device does not support Alert actions so there is no alert to cancel.  Select a different Hue device.".format(device.name))
				return
			else:
				# Sanity check on bulb ID
				bulbId = device.pluginProps.get('bulbId', None)
				if bulbId is None or bulbId == 0:
					self.doErrorLog("No bulb ID selected for device \"{}\". Check settings for this device and select a Hue Device to control.".format(device.name))
					return

			self.doAlert(device, "none")
		except Exception:
			self.logger.error("", exc_info=True)

	# Set Effect Action
	########################################
	def effect(self, action, device):
		if self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(10,"effect: device:\"{}\", action:\n{}".format(device.name, action))
		try:
			# Act based on device type.
			if device.deviceTypeId == "hueGroup":
				# Sanity check on group ID
				groupId = device.pluginProps.get('groupId', None)
				if groupId is None or groupId == 0:
					self.doErrorLog("No group ID selected for device \"{}\". Check settings for this device and select a Hue Group to control.".format(device.name))
					return
			elif device.deviceTypeId == 'hueAttributeController' or device.deviceTypeId in kMotionSensorTypeIDs or device.deviceTypeId in kTemperatureSensorTypeIDs or device.deviceTypeId in kLightSensorTypeIDs or device.deviceTypeId in kSwitchTypeIDs:
				# Attribute controllers and sensor devices don't support effects actions. Print the error in the Indigo log.
				self.doErrorLog("The \"{}\" device does not support Effects actions. Select a different Hue device.".format(device.name))
				return
			else:
				# Sanity check on bulb ID
				bulbId = device.pluginProps.get('bulbId', None)
				if bulbId is None or bulbId == 0:
					self.doErrorLog("No bulb ID selected for device \"{}\". Check settings for this device and select a Hue Device to control.".format(device.name))
					return

			effect = action.props.get('effect', "")
			if effect == "manual":
				effect = action.props.get('effectManual',"")

			if len(effect) < 4:
				self.doErrorLog("No effect specified.")
				return False

			else:
				self.doEffect(device, effect)
		except Exception:
			self.logger.error("", exc_info=True)

	# Save Preset Action
	########################################
	def savePreset(self, action, device):
		if True or self.decideMyLog("EditSetup"): self.indiLOG.log(10,"Starting savePreset. action values:\n{}\nDevice/Type ID:\n{}".format(action, device) + "\n")
		errorsDict = indigo.Dict()
		errorsDict['showAlertText'] = ""
		actionType = "action"

		try:
			# Work with both Menu and Action actions.
			try:
				device = indigo.devices[int(action.get('deviceId', 0))]
				actionType = "menu"
			except AttributeError:
				# This is an action, not a menu call.
				pass

			# Check if the target is a light or group.
			if device.deviceTypeId in kGroupDeviceTypeIDs:
				bulbId = device.pluginProps.get('groupId', "")
			elif device.deviceTypeId in kLightDeviceTypeIDs:
				bulbId = device.pluginProps.get('bulbId', "")
			else:
				bulbId = ""

			# Sanity check on bulb ID
			if bulbId == "":
				self.doErrorLog("No compatible Hue device selected for \"{}\". Check settings and select a Hue light or group to control.".format(device.name))
				return (False, action, errorsDict)

			# Get the presetId.
			if actionType == "menu":
				presetId = action.get('presetId', False)
			else:
				presetId = action.props.get('presetId', False)

			if not presetId:
				self.doErrorLog("No Preset specified.")
				return (False, action, errorsDict)
			else:
				# Convert to integer.
				presetId = int(presetId)
				# Subtract 1 because key values are 0-based.
				presetId -= 1

			# Get the Ramp Rate.
			if actionType == "menu":
				rampRate = action.get('rate', "")
				# Validate Ramp Rate.
				if len(rampRate) > 0:
					try:
						rampRate = float(rampRate)
						if (rampRate < 0) or (rampRate > 540):
							errorsDict['rate'] = "Ramp Rate must be a number between 0 and 540 seconds and can be in increments of 0.1 seconds."
							errorsDict['showAlertText'] += errorsDict['rate']
							return (False, action, errorsDict)
					except ValueError:
						errorsDict['rate'] = "Ramp Rate must be a number between 0 and 540 seconds and can be in increments of 0.1 seconds."
						errorsDict['showAlertText'] += errorsDict['rate']
						return (False, action, errorsDict)
					except Exception as e:
						errorsDict['rate'] = "Invalid Ramp Rate value: {}  @line#:{})".format(e,sys.exc_info()[2].tb_lineno)
						errorsDict['showAlertText'] += errorsDict['rate']
						return (False, action, errorsDict)
			else:
				rampRate = action.props.get('rate', "")

			# If there was no Ramp Rate specified, use -1.
			if rampRate == "":
				rampRate = -1

			# Get the plugin prefs and populate them into a local array.
			presets = list()
			for num in range(0,len(self.pluginPrefs['presets'])):
				tempPresetName = self.pluginPrefs['presets'][num][0]
				tempPresetData = self.pluginPrefs['presets'][num][1]
				try:
					# Prior to version 1.2.4, the Ramp Rate index did not exist.
					tempPresetRate = self.pluginPrefs['presets'][num][2]
				except IndexError:
					tempPresetRate = -1
				presets.append(list((tempPresetName, tempPresetData, tempPresetRate)))

			# Update the new array with the submitted values.
			if actionType == "menu":
				presetName = action.get('presetName', False)
				# Return an error if the presetName is too long.
				if len(presetName) > 50:
					errorsDict['presetName'] = "The Preset Name is too long. Please choose a name that is 50 or fewer characters long."
					errorsDict['showAlertText'] += errorsDict['presetName']
					return (False, action, errorsDict)

			else:
				presetName = action.props.get('presetName', False)

			if not presetName:
				presetName = ""

			# If the submitted name is not blank, change the name in the prefs.
			if presetName != "":
				# (Index 0 = preset name).
				presets[presetId][0] = presetName
			else:
				# Submitted presetName is blank. Use the current presetName for logging.
				presetName = presets[presetId][0]

			# Create the states list dict.
			for key, value in device.states.items():
				# (Index 1 = preset data).
				presets[presetId][1][key] = value

			# Add the Ramp Rate to the Preset.
			if rampRate != -1:	# May still be a string if passed by embedded script call.
				try:
					rampRate = float(rampRate)
					if (rampRate < 0) or (rampRate > 540):
						self.doErrorLog("Ramp Rate must be a number between 0 and 540 seconds and can be in increments of 0.1 seconds. Value \"{}\" ignored.".format(rampRate))
						rampRate = -1
				except ValueError:
					self.doErrorLog("Ramp Rate must be a number between 0 and 540 seconds and can be in increments of 0.1 seconds. Value \"{}\" ignored.".format(rampRate))
					rampRate = -1
				except Exception:
					self.indiLOG.log(40,"Invalid Ramp Rate value \"{}\"".format(rampRate), exc_info=True)
					rampRate = -1
			else:
				# No Ramp Rate submitted. Use -1 to indicate this.
				rampRate = -1
			# (Index 2 = ramp rate).
			presets[presetId][2] = rampRate

			# Save the device's states to the preset.
			self.pluginPrefs['presets'] = presets

			# Log the action.
			if rampRate == -1:
				self.indiLOG.log(20,"\"{}\" states saved to Preset {} ({})".format(device.name , presetId + 1, presetName))
			else:
				self.indiLOG.log(20,"\"{}\" states saved to Preset {} ({}) with ramp rate {} sec.".format(device.name , presetId + 1, presetName, rampRate))

			# Return a tuple if this is a menu item action.
			if actionType == "menu":
				return (True, action)
		except Exception:
			self.logger.error("", exc_info=True)
		return (False, action, errorsDict)


	# Recall Preset Action
	########################################
	def recallPreset(self, action0, device):
		testdebug = False
		if testdebug or self.decideMyLog("EditSetup"): self.indiLOG.log(10,"Starting recallPreset. action values:\n{}\n\n\nDevice/Type ID:>>{}<<\n".format(action0, device))
		errorsDict = indigo.Dict()
		errorsDict['showAlertText'] = ""
		actionType = "action"
		# Work with both Menu and Action actions.

		try:
			device = indigo.devices[int(action0.get('deviceId', 0))]
			actionType = "menu"
			action = action0
			if str(action.get('deviceId', 0)) == "0": 
				errorsDict['showAlertText'] = '"all" devices currently not supported'
				self.indiLOG.log(30,"recallPreset,\"all\" devices currently not supported: \n{}".format(str(action)))
				return (False, action, errorsDict)

		except AttributeError:
			action = action0.props
			# This is an action, not a menu call.

		# Check if the target is a light or group.
		if device.deviceTypeId in kGroupDeviceTypeIDs:
			bulbId = device.pluginProps.get('groupId', "")
		elif device.deviceTypeId in kLightDeviceTypeIDs:
			bulbId = device.pluginProps.get('bulbId', "")
		else:
			bulbId = ""

		# Sanity check on bulb ID
		if bulbId == "":
			self.doErrorLog("No compatible Hue device selected for \"{}\". Check settings and select a Hue light or group to control.".format(device.name))
			errorsDict['showAlertText'] = "error, see log"
			return (False, action, errorsDict)

		# Get the presetId.
		presetId = action.get('presetId', False)

		if not presetId:
			self.doErrorLog("No Preset specified.")
			errorsDict['showAlertText'] = "error, see log"
			return (False, action, errorsDict)
		else:
			# Convert to integer.
			presetId = int(presetId)
			# Subtract 1 because key values are 0-based.
			presetId -= 1

		# Get the Ramp Rate.
		rampRate = action.get('rate', "")
		if actionType == "menu":
			# Validate Ramp Rate.
			if len(rampRate) > 0:
				try:
					rampRate = float(rampRate)
					# Round the number to the nearest 10th.
					rampRate = round(rampRate, 1)
					if (rampRate < 0) or (rampRate > 540):
						errorsDict['rate'] = "Ramp Rate must be a number between 0 and 540 seconds and can be in increments of 0.1 seconds."
						errorsDict['showAlertText'] += errorsDict['rate']
						return (False, action, errorsDict)
				except ValueError:
					errorsDict['rate'] = "Ramp Rate must be a number between 0 and 540 seconds and can be in increments of 0.1 seconds."
					errorsDict['showAlertText'] += errorsDict['rate']
					return (False, action, errorsDict)
				except Exception as e:
					errorsDict['rate'] = "Invalid Ramp Rate value: {}  @line#:{})".format(e,sys.exc_info()[2].tb_lineno)
					errorsDict['showAlertText'] += errorsDict['rate']
					return (False, action, errorsDict)

		# If there is no Ramp Rate specified, use -1.
		if rampRate == "":
			rampRate = -1

		htype = device.pluginProps.get('type', False)
		if device.deviceTypeId in kLightDeviceTypeIDs:
			# Get the modelId from the device.
			if not htype:
				self.doErrorLog("The \"{}\" device is not a Hue device. Please select a Hue device for this action.".format(device.name))
				errorsDict['showAlertText'] = "error, see log"
				return (False, action, errorsDict)

			elif htype not in kCompatibleDeviceIDType:
				self.doErrorLog("The \"{}\" device is not a compatible Hue device. Please select a compatible Hue device.".format(device.name))
				errorsDict['showAlertText'] = "error, see log"
				return (False, action, errorsDict)

		elif device.deviceTypeId not in kLightDeviceTypeIDs and device.deviceTypeId not in kGroupDeviceTypeIDs:
			self.doErrorLog("The \"{}\" device is not a compatible Hue device. Please select a compatible Hue device.".format(device.name))
			errorsDict['showAlertText'] = "error, see log"
			return (False, action, errorsDict)

		# Sanity check on preset ID.
		try:
			preset = self.pluginPrefs['presets'][presetId]
		except Exception:
			self.indiLOG.log(40,"Preset number {} couldn't be recalled.".format( presetId + 1), exc_info=True)
			errorsDict['showAlertText'] = "error, see log"
			return (False, action, errorsDict)

		# Get the data from the preset in the plugin prefs.
		presetName = preset[0]
		presetData = preset[1]
		try:
			# Prior to version 1.2.4, this key did not exist in the presets.
			presetRate = self.pluginPrefs['presets'][presetId][2]
			# Round the saved preset ramp rate to the nearest 10th.
			presetRate = round(presetRate, 1)
		except Exception:
			# Key probably doesn't exist. Proceed as if no rate was saved.
			presetRate = -1
			pass

		# If there was no Ramp Rate override specified in the recall action,
		#   use the one saved in the Preset (if any).
		if rampRate == -1:
			rampRate = presetRate

		# If the presetData has no data, return an error as this Preset is empty.
		if len(presetData) < 1:
			# Return an error if the Preset is empty (since there's nothing to display).
			if actionType == "menu":
				errorsDict['presetId'] = "This Preset is empty. Please select a Preset that contains data (the number will have an asterisk (*) next to it)."
				errorsDict['showAlertText'] += errorsDict['presetId']
				return (False, action, errorsDict)
			else:
				self.doErrorLog("Preset  ({}) is empty. The \"{}\" device was not changed.".format(presetId + 1, device.name))
				return (False, action, errorsDict)

		# Get the brightness level (which is common to all devices).
		brightnessLevel = presetData.get('brightnessLevel', 100)
		# Convert the brightnessLevel to 0-255 range for use in the light
		#   changing method calls.
		brightness = int(round(brightnessLevel * 255.0 / 100.0))

		if testdebug: self.indiLOG.log(20,"\"{}\"  (general) set to brightness {}  at {} ramprate".format(device.name, brightness, rampRate) )

		# Act based on the capabilities of the target device.
		if device.supportsColor:
			if device.supportsWhiteTemperature and device.supportsRGB:
				# This device supports both color temperature and full color.
				colorMode = presetData.get('colorMode', "ct")
				if testdebug: self.indiLOG.log(20,"\"{}\"  (colormode:{}) set to brightness {}  at {} ramprate".format(device.name, colorMode, brightness, rampRate) )

				if colorMode == "ct":
					# Get the color temperature state (use 2800 as default).
					colorTemp = presetData.get('colorTemp', 2800)

					# Make the change to the light.
					self.doColorTemperature(device, colorTemp, brightness, rampRate)

				elif colorMode == "hs":
					# Get the hue (use 0 as the default).
					hue = presetData.get('hue', 0)
					# Convert the hue from 0-360 range to 0-65535 range.
					hue = int(round(hue * 182.0))
					# Get the saturation (use 100 as the default).
					saturation = presetData.get('saturation', 100)
					# Convert from 0-100 range to 0-255 range.
					saturation = int(round(saturation * 255.0 / 100.0))

					# Make the light change.
					self.doHSB(device, hue, saturation, brightness, rampRate)

				elif colorMode == "xy":
					# Get the x and y values (using 0.35 as default for both).
					colorX = presetData.get('colorX', 0.35)
					colorY = presetData.get('colorY', 0.35)

					# Make the light change.
					self.doXYY(device, colorX, colorY, brightness, rampRate)

			elif device.supportsWhiteTemperature and not device.supportsRGB:
				# This device only supports color temperature.
				colorMode = presetData.get('colorMode', "ct")

				if colorMode == "ct":
					# Get the color temperature state (use 2800 as default).
					colorTemp = presetData.get('colorTemp', 2800)

					# Make the change to the light.
					self.doColorTemperature(device, colorTemp, brightness, rampRate)

			elif device.supportsRGB and not device.supportsWhiteTemperature:
				# This device only supports full color and not color temperature.
				colorMode = presetData.get('colorMode', "hs")

				if colorMode == "ct":
					# The target device doesn't support color temperature.
					#   Use an alternate color rendering method such as xy.
					colorMode = "xy"

				if colorMode == "hs":
					# Get the hue (use 0 as the default).
					hue = presetData.get('hue', 0)
					# Convert the hue from 0-360 range to 0-65535 range.
					hue = int(round(hue * 182.0))
					# Get the saturation (use 100 as the default).
					saturation = presetData.get('saturation', 100)
					# Convert from 0-100 range to 0-255 range.
					saturation = int(round(saturation * 255.0 / 100.0))

					# Make the light change.
					self.doHSB(device, hue, saturation, brightness, rampRate)

				elif colorMode == "xy":
					# Get the x and y values (using 0.35 as default for both).
					colorX = presetData.get('colorX', 0.35)
					colorY = presetData.get('colorY', 0.35)

					# Make the light change.
					self.doXYY(device, colorX, colorY, brightness, rampRate)

		else:
			if testdebug: self.indiLOG.log(20,"\"{}\"  (else) set to brightness {}  at {} ramprate".format(device.name, brightness, rampRate) )
			# This device doesn't support color.  Just set the brightness.
			self.doBrightness(device, brightness, rampRate)

		# Log the action.
		if rampRate == -1:
			self.indiLOG.log(20,"\"{}\" compatible states set to Preset {} ({})".format(device.name, presetId + 1, presetName) )
		else:
			self.indiLOG.log(20,"\"{}\" compatible states set to Preset {} ({}) at ramp rate {} sec.".format(device.name, presetId + 1, presetName, rampRate) )

		# Return a tuple if this is a menu item action.
		if actionType == "menu":
			return (True, action)


	# Recall Hue Scene Action
	########################################
	def recallScene(self, action, device):
		errorsDict = indigo.Dict()
		errorsDict['showAlertText'] = ""
		# Work with both Menu and Action actions.
		try:
			actionDict = action.props
			# If this succeeds, no need to do anything.
		except AttributeError:
			# If there is an attribute error, this is a Plugins menu call.
			actionDict = action
		if self.decideMyLog("SendCommandsToBridge"): self.indiLOG.log(10,"Starting recallScene. action values:\n{}\nDevice/Type ID:\n{}\n".format(actionDict, device))

		# Get the sceneId.
		sceneId = actionDict.get('sceneId', False)
		hubNumber = actionDict.get('hubNumber', "0")

		if not sceneId:
			self.doErrorLog("No Scene specified.")
			return (False, action)

		# Get the groupId.
		groupId = actionDict.get('groupId', False)

		if not groupId:
			# No group ID specified.  Assume it should be 0 (apply scene to all devices).
			groupId = 0

		# Recall the scene.
		self.doScene(groupId, sceneId, hubNumber)

		return (True, action)

	# print to logfile info from hub 
	########################################
  # Bulb List Generator
	########################################
	def printsListGenerator(self, filter="", valuesDict=None, typeId="", targetId=0):
		# Used in actions that need a list of Hue bridge devices.
		#if self.decideMyLog("EditSetup"): self.indiLOG.log(20,"Starting printsListGenerator.\n  filter: {}\n  valuesDict: {}\n  typeId: {}\n  targetId: {}".format(filter, str(valuesDict), typeId, targetId))
		xList = list()

		for hubNumber in sorted(self.ipAddresses, key=self.ipAddresses.get):
			if filter in self.hueConfigDict[hubNumber]:
				for ID in self.hueConfigDict[hubNumber][filter]:
					xList.append([ID+"-"+hubNumber, hubNumber+"-"+ID+"-"+self.hueConfigDict[hubNumber][filter][ID]['name']])
		#if filter.lower().find("scene") >-1: self.indiLOG.log(20,"printsListGenerator:  xList={}".format(xList))
		return sorted(xList, key=lambda tup: tup[1])

	####----------------- initiate  findHueBridges run   ---------
	def updateBridges(self, valuesDict):
		# initiate  findHueBridges run 
		self.findHueBridgesNowForce = time.time()
		return valuesDict


	####----------------- use bonjour to find local hue bridges , store in self.bridgesAvailable, to be used in config setup  ---------
	def findHueBridges(self):# , startTime):
		self.indiLOG.log(10,"findHueBridges:  process starting")
		self.findHueBridgesDict['status'] = "running"
		bridgesAvailableOld = dict()
		self.bridgesAvailable = dict()
		self.timeWhenNewBridgeRunFinished = 0
		normalwaitBetweentriesFindBridges = 300
		first = True
		self.findHueBridgesAreBeingupdated = "updating"

		while True:
			if self.decideMyLog("FindHueBridge"): self.indiLOG.log(10,"findHueBridges:  next try")
			self.findHueBridgesNow = time.time() + normalwaitBetweentriesFindBridges
			lastFindBridges = time.time()
			try:
				if self.pluginState == "stop" or self.findHueBridgesDict['status'] == "stop": 
					self.indiLOG.log(30,"findHueBridges: stopping process due to stop request")
					return  

				self.findHueBridgesAreBeingupdated = "updating"
				# first scan, get bonjour devices 
				# returns lines like: 14:53:34.464  Add        3   4 local.               _hue._tcp.           Philips Hue - A30D45
				cmd =  "/usr/bin/dns-sd -B _hue._tcp local. & sleep 1; /bin/kill $!"
				ret, err = self.readPopen(cmd)
				if self.decideMyLog("FindHueBridge"): self.indiLOG.log(10,"findHueBridges:  (1) cmd:{}, ret={}".format(cmd, ret))
				lines = ret.split("\n")
				huesFound = dict()
				bridgeIds = dict()
				ipAddress = dict()
				count = 0
				for line in lines:
					if self.searchForStringinFindHueBridge in line:
						ll = line.split() #   ll[-1] == A30D45
						huesFound[count] = {"cmd":'"'+self.searchForStringinFindHueBridge+' - '+ ll[-1]+'"',"name":"none"} 
						ipAddress[count] = "none"
						bridgeIds[count] = "none"
						count += 1

				if self.decideMyLog("FindHueBridge"): self.indiLOG.log(10,"findHueBridges:  (2) huesFound={}".format( huesFound))
				# second scan get  names 
				# returns a line like: 14:55:09.260  Philips\032Hue\032-\032A8A63E._hue._tcp.local. can be reached at Bridge-2-201-d2.local.:443 (interface 4)
				for cc in range(count):
					if self.findHueBridgesDict['status'] == "stop": return 
					if self.pluginState == "stop": return 
					cmd = "/usr/bin/dns-sd  -L "+huesFound[cc]['cmd']+' _hue._tcp & sleep 1; /bin/kill $!'
					ret, err = self.readPopen(cmd)
					if self.decideMyLog("FindHueBridge"): self.indiLOG.log(10,"findHueBridges:  (2)-{} cmd:{}, ret={}".format(cc, cmd, ret))
					if " can be reached at " in ret:
						name = ret.split(" can be reached at ")[1].split(":")[0]
						huesFound[cc]['name'] = name # == Bridge-2-201-d2.local.

						if "bridgeid=" in ret:
							bridgeIds[cc] = ret.split("bridgeid=")[1].split(" ")[0].upper()
						
				if self.decideMyLog("FindHueBridge"): self.indiLOG.log(10,"findHueBridges:  (4) huesFound={}".format( bridgeIds))

				# third scan:
				# returns line like: 14:56:22.568  Add 40000002  4 Bridge-2-201-d2.local.                 192.168.1.201                                120
				for cc in range(count):
					if self.findHueBridgesDict['status'] == "stop": return 
					if self.pluginState == "stop": return 
					if len(bridgeIds) <= cc: continue
					if huesFound[cc]['name'] == "none": continue
					if bridgeIds[cc] == "none": continue

					cmd =  "/usr/bin/dns-sd -G v4 " + huesFound[cc]['name'] +" & sleep 1; /bin/kill $!"
					ret, err = self.readPopen(cmd)
					if self.decideMyLog("FindHueBridge"): self.indiLOG.log(10,"findHueBridges:  (3)-{} cmd:{}, ret={}".format(cc, cmd, ret))
					if huesFound[cc]['name'] in ret:
						ipAddress[cc] = ret.split(huesFound[cc]['name'])[1].lstrip(" ").split(" ")[0] # == 192.168.1.201 

				for cc in range(count):
					if bridgeIds[cc] != "none" and ipAddress[cc] != "none":
						self.bridgesAvailable[bridgeIds[cc]] =  {"ipAddress":ipAddress[cc],"hubNumber":"", "linked": False}


				## now wait for next round, using delay to update dicts 
				self.timeWhenNewBridgeRunFinished = time.time()
				self.findHueBridgesAreBeingupdated = "updated"
				for ii in range(normalwaitBetweentriesFindBridges):
					if self.findHueBridgesDict['status'] == "stop": return 
					if self.pluginState == "stop": return

					hubNumbers = []
					for hubNumber in self.ipAddresses:
						if hubNumber in self.hueConfigDict:
							hubNumbers.append(hubNumber)
							if "config" in self.hueConfigDict[hubNumber]:
								if "bridgeid" in self.hueConfigDict[hubNumber]['config']:
									bridgeId = self.hueConfigDict[hubNumber]['config']['bridgeid']
									if bridgeId in self.bridgesAvailable:
										self.bridgesAvailable[bridgeId]['hubNumber'] = hubNumber
										self.bridgesAvailable[bridgeId]['linked'] = True
									else:
										pass
										# self.bridgesAvailable[bridgeId] = {"ipAddress":"","hubNumber":"", "linked": False}
			
					for bridgeId in self.bridgesAvailable:
						if bridgeId not in bridgesAvailableOld:
							if not first:
								self.indiLOG.log(30,"!!!! \nfindHueBridges: new bridge found:{}\n!!!!".format(self.bridgesAvailable[bridgeId]))
								self.lastTimeForAll = 0
					bridgesAvailableOld = copy.deepcopy(self.bridgesAvailable)

					first = False
					if time.time() - lastFindBridges >  normalwaitBetweentriesFindBridges:
						break 
					if time.time() - self.findHueBridgesNowForce < 10:
						break 

					#end of loop wait 1 secs each for shutdown commend intercept 
					try:
						self.sleep(1)
					except:
						break
			except Exception:
				self.logger.error("", exc_info=True)
				try:
					self.sleep(1)
				except: pass
		return 


	# print  Preset Menu Action to log 
	########################################
	def displayPreset(self, valuesDict, typeId):
		if self.decideMyLog("EditSetup"): self.indiLOG.log(20,"Starting displayPreset. action values:\n{}\nType ID:{}\n".format(valuesDict, typeId) )
		errorsDict = indigo.Dict()
		errorsDict['showAlertText'] = ""

		# Get the presetId.
		presetId = valuesDict.get('presetId', False)

		if not presetId:
			errorsDict['presetId'] = "No Preset is selected."
			errorsDict['showAlertText'] += errorsDict['presetId']
			return (False, valuesDict, errorsDict)

		else:
			# Convert to integer.
			presetId = int(presetId)
			# Subtract 1 because key values are 0-based.
			presetId -= 1

		# Get the data from the preset in the plugin prefs.
		presetName = self.pluginPrefs['presets'][presetId][0]
		presetData = self.pluginPrefs['presets'][presetId][1]
		try:
			# Prior to version 1.2.4, this key did not exist in the presets.
			presetRate = self.pluginPrefs['presets'][presetId][2]
			# Round the saved preset ramp rate to the nearest 10th.
			presetRate = round(presetRate, 1)
		except Exception:
			# Key probably doesn't exist. Proceed as if no rate was saved.
			presetRate = -1
			pass

		# Return an error if the Preset is empty (since there's nothing to display).
		if len(presetData) < 1:
			errorsDict['presetId'] = "This Preset is empty. Please select a Preset that contains data (the number will have an asterisk (*) next to it)."
			errorsDict['showAlertText'] += errorsDict['presetId']
			return (False, valuesDict, errorsDict)

		# Display the Preset data in the Indigo log.
		logRampRate = "{} sec".format(presetRate)
		if presetRate == -1:
			logRampRate = "(none specified)"
		self.indiLOG.log(20,"Displaying Preset {} ({}) stored data:\nRamp Rate: {} {}\n".format(presetId + 1, presetName, logRampRate, presetData))

		# Return a tuple to dismiss the menu item dialog.
		return (True, valuesDict)



	# print device info etc to indigolog
	########################################
	def startTrackSpecificDevice(self, valuesDict, menuItem):

		self.trackSpecificDevice = 0
		try:
			if valuesDict['whatToPrint'] not in ["lights","sensors"]: 
				self.indiLOG.log(10,"TrackSpecificDevice not dev type selected")
				return
			whatToPrint = valuesDict['whatToPrint'] 
			if	 whatToPrint== "lights":	idType = "bulbId"
			elif whatToPrint == "sensors":	idType = "sensorId"
			hubNumber = valuesDict['hubNumber']
			ID  = valuesDict[idType]
			for deviceId in copy.deepcopy(self.deviceList):
				if "hubNumber" not in self.deviceList[deviceId]: 		continue
				if self.deviceList[deviceId]['hubNumber'] != hubNumber: continue
				if idType not in self.deviceList[deviceId]: 			continue
				if self.deviceList[deviceId][idType] != ID: 			continue
				device = indigo.devices[deviceId]
				self.indiLOG.log(20,"startTrackSpecificDevice: Bridge:{}, id:{}, type:{}, bridgeName:{}, devId:{}, IndigoName:{}.".format(hubNumber, self.deviceList[deviceId][idType], whatToPrint, self.hueConfigDict[hubNumber][whatToPrint][ID]['name'], deviceId, device.name))
				self.trackSpecificDevice = deviceId
				return 
			self.indiLOG.log(30,"startTrackSpecificDevice: Bridge:{}, id:{}, type:{} not found ".format(hubNumber, self.deviceList[deviceId][idType], whatToPrint))

		except	Exception:
			self.logger.error("", exc_info=True)

	# print device info etc to indigolog
	########################################
	def stopTrackSpecificDevice(self, valuesDict, menuItem):
		self.indiLOG.log(20,"stopTrackSpecificDevice")
		self.trackSpecificDevice = 0
		return 
	# print config etc
	########################################
	def printHueData(self, valuesDict, menuItem):
		if self.decideMyLog("EditSetup"): self.indiLOG.log(20,"Starting printHueData. menuItem:{}, {} ".format(menuItem, str(valuesDict)))
 
		try:
			indigoList = dict()
			sortBy = valuesDict['sortBy']

			if valuesDict['whatToPrint'] == "shortBridgeInfo":
				self.indiLOG.log(20,"bridge lights groups scenes users resources Active/rules schedules Physicl/sensors ZigBChanl hostIds / user names ------------------- ip Numbers ---- BridgeIds-------")
				#self.indiLOG.log(20,"Max       /{:2}    /{:2}    /{:2}                   /{:2}       /{:2}     /{:2}     ".format(kmaxHueItems["lights"], kmaxHueItems["groups"], kmaxHueItems["scenes"], kmaxHueItems["rules"], kmaxHueItems["schedules"], kmaxHueItems["sensors"] ))
				hublist = []
				for hubNumber in self.ipAddresses:
					hublist.append(hubNumber)

				for hubNumber in sorted(hublist):
					if hubNumber in self.hueConfigDict:
						activeRules = 0
						physicalSensors = 0
						if "lights" in self.hueConfigDict[hubNumber]:
							for ii in self.hueConfigDict[hubNumber]['rules']:
								if not self.hueConfigDict[hubNumber]['rules'][ii].get('recycle',False):
									activeRules +=1
							for ii in self.hueConfigDict[hubNumber]['sensors']:
								if self.hueConfigDict[hubNumber]['sensors'][ii].get('type','').find("CLIPGenericStatus") ==-1:
									physicalSensors +=1

							self.indiLOG.log(20,"#{:5s} {:6d} {:6d} {:6d} {:5d} {:9d}  {:5d}/{:<5d} {:9d} {:7d}/{:<7d} {:9} {:20s} {:15s} {:16}".format(
								hubNumber,
								len(self.hueConfigDict[hubNumber]['lights'] ), 
								len(self.hueConfigDict[hubNumber]['groups'] ), 
								len(self.hueConfigDict[hubNumber]['users'] ), 
								len(self.hueConfigDict[hubNumber]['scenes'] ), 
								len(self.hueConfigDict[hubNumber]['resourcelinks'] ), 
								activeRules, 
								len(self.hueConfigDict[hubNumber]['rules'] ), 
								len(self.hueConfigDict[hubNumber]['schedules'] ), 
								physicalSensors, 
								len(self.hueConfigDict[hubNumber]['sensors'] ), 
								self.hueConfigDict[hubNumber]['config']['zigbeechannel'],
								self.hostIds[hubNumber],self.ipAddresses[hubNumber], 
							self.hueConfigDict[hubNumber]['config']['bridgeid']) 
							)
						else:
							self.indiLOG.log(30,"#{:5s}; ipNumber:{} --- not properly setup, no data received from bridge, try to re-pair".format(hubNumber, self.ipAddresses[hubNumber]))
							self.indiLOG.log(30,"        pluginPrefs IP#s: {},   ..hostIDs:   {}".format(self.pluginPrefs.get('addresses','empty'), self.pluginPrefs.get('hostIds','empty') ))
							self.indiLOG.log(30,"        self.ipNumbers:   {}    self.hostIds:{}, paired:{}".format(self.ipAddresses, self.hostIds, self.paired  ))
							
					else:
						self.indiLOG.log(30,"#{:5s}; ipNumber:{} --- bridge not setup, not paired or bridge is not connected".format(hubNumber, self.ipAddresses[hubNumber]))
						self.indiLOG.log(30,"        pluginPrefs IP#s: {},   ..hostIDs:   {}".format(self.pluginPrefs.get('addresses','empty'), self.pluginPrefs.get('hostIds','empty')))
						self.indiLOG.log(30,"        self.ipNumbers:   {}    self.hostIds:{}, paired:{}".format(self.ipAddresses, self.hostIds, self.paired  ))


			elif  valuesDict['whatToPrint'] == "config":
				outs = ['\n======================= print Hue Config =====================']
				for hubNumber in sorted(self.ipAddresses):
					if valuesDict['whatToPrint'] not in self.hueConfigDict[hubNumber]: continue
					activeRules = 0
					deletedRules = 0
					physicalSensors = 0
					for ii in self.hueConfigDict[hubNumber]['rules']:
						if not self.hueConfigDict[hubNumber]['rules'][ii].get('recycle',False):
							activeRules +=1
						if self.hueConfigDict[hubNumber]['rules'][ii].get('status','').find("resourcedeleted") >-1:
							deletedRules +=1
					for ii in self.hueConfigDict[hubNumber]['sensors']:
						if self.hueConfigDict[hubNumber]['sensors'][ii].get('type','').find("CLIPGenericStatus") ==-1:
							physicalSensors +=1

					theDict = self.hueConfigDict[hubNumber][valuesDict['whatToPrint']]
					outs.append("===== Bridge#:    {:1}                ipNumber:  {:<15}      mac:        {}".format(hubNumber, self.ipAddresses[hubNumber], theDict['mac']))
					outs.append(" zigbee channel: {:2}                swversion: {:<15}      apiversion: {}".format(theDict['zigbeechannel'], theDict['swversion'], theDict['apiversion']))
					outs.append(" bridgeid:       {:15}  modelid:   {:<15}      paired:     {}  ".format(theDict['bridgeid'], theDict['modelid'], self.paired[hubNumber]))

					#outs.append(" swupdates available: ")
					#for tt in theDict['config']['swupdate2']['devicetypes']:
					#	xx = str(theDict['config']['swupdate2']['devicetypes'][tt]).replace('[','').replace(']','').replace("u'",'').replace("'",'')
					#	outs.append("    {}: {}".format(tt, xx))


					for xx in kmaxHueItems:
						if xx not in ['rules','sensors']:
							outs.append(" # of {:27s} {:3d}/{:}".format(xx, len(self.hueConfigDict[hubNumber][xx]), kmaxHueItems[xx]))
					outs.append(" # of sensors(all/phys)           {:3d}/{:}      maxPhysical:{:}".format(len(self.hueConfigDict[hubNumber]['sensors']), physicalSensors, kmaxHueItems['sensors']))
					outs.append(" # of rules(all/Active/deleted)   {:3d}/{:}/{:}    maxActive:{:}".format(len(self.hueConfigDict[hubNumber]['rules']), activeRules, deletedRules, kmaxHueItems['rules']))

					IDlist = self.makeSortedIDList(theDict['whitelist'], 'last use date')

								  #123456789 123456789 123456789 123456789  123456789 123456789 123456789 
					outs.append("registered users (Whitelist), go to https://account.meethue.com/ to manage/ remove users ")
					outs.append("ID--------------------------------------- name------------------------- create date---------- last use date-------- ")
					for ID in IDlist:
						temp = theDict['whitelist'][ID]
						out  = 										 '{:41s} '.format(ID)
						out += self.printColumns(temp,				 '{:30s}',	'name') 
						out += self.printColumns(temp,				 '{:22s}',	'create date') 
						out += self.printColumns(temp,				 '{:22s}',	'last use date') 
						outs.append(out)
					outs.append("")
				outs.append("---- bridges detected on network:")
				for bridgeId in self.bridgesAvailable:
					outs.append("bridgeId: {}, ipAddress:{},  used in plugin:{}, BridgeNumber:{}".format(bridgeId, self.bridgesAvailable[bridgeId]['ipAddress'], self.bridgesAvailable[bridgeId]['linked'], self.bridgesAvailable[bridgeId]['hubNumber']))

				self.indiLOG.log(20,"\n".join(outs)+"\n")


			elif valuesDict['whatToPrint'].find("configJson") > -1:
				for hubNumber in self.ipAddresses:
					if hubNumber not in self.hueConfigDict: continue
					if "config" not in self.hueConfigDict[hubNumber]: continue
					self.indiLOG.log(20,"printHueData --- complete config bridge#: {}   json=\n{} ".format(hubNumber, json.dumps(self.hueConfigDict[hubNumber]['config'], indent=2, sort_keys=True)))


			elif valuesDict['whatToPrint'].find("configDict") > -1:
				for hubNumber in self.ipAddresses:
					if hubNumber not in self.hueConfigDict: continue
					if "config" not in self.hueConfigDict[hubNumber]: continue
					self.indiLOG.log(20,"printHueData --- complete Hue bridge info #{}   json=\n{} ".format(hubNumber, json.dumps(self.hueConfigDict[hubNumber], indent=2, sort_keys=True)))




			elif valuesDict['whatToPrint'] == "lights":
				hueIdToIndigoName, indigoNameToHueId = self.getIndigoDevDict("bulbId")

				outs = ['\n======================= print Hue Lights =====================']
				for hubNumber in sorted(self.ipAddresses):
					if valuesDict['whatToPrint'] not in self.hueConfigDict[hubNumber]: continue
					theDict = self.hueConfigDict[hubNumber][valuesDict['whatToPrint']]
					outs.append("==  Bridge:{}, ipNumber:{}, hostId:{}, paired:{}, #of lights:{}, sorted by:{}".format(hubNumber, self.ipAddresses[hubNumber],self.hostIds[hubNumber], self.paired[hubNumber], len(theDict), sortBy))
								 #123 12345678901 12345678901234567890123456 12345678901234567890123456789 12345678901234567890123456789 1234567890123456789012345 12345678901234567890123456789 12345678901 1234567890123456789012345 123456789 12345 
					outs.append(" ID ONoff Reach modelId--------- type--------------------- uniqueid------------------ SNumber Name------------------------------- ProductId-------------------- manufacturername------------- ProductName------------------ Group indigoDevName-----")

					if   sortBy in ['type','name','modelid']: 	IDlist = self.makeSortedIDList(theDict, sortBy)
					else:										IDlist = sorted(theDict, key=lambda key: int(key))

					for IDi in IDlist:
						ID = str(IDi)
						temp = theDict[ID]
						try: 
							device = indigo.devices[hueIdToIndigoName[hubNumber][ID]]
							serialNumber = device.pluginProps.get("serialNumber","")
						except:
							serialNumber = ""
						out  = 										 '{:>3s} '.format(ID)
						if "state" in temp:
							out += self.printColumns(temp['state'],	 '  {:<4}',	'reachable') 
							out += self.printColumns(temp['state'],	 '  {:<4}',	'on') 
						else:
							out += 									 ' {:12s}'.format(' ')
						out += self.printColumns(temp,				 '{:17s}',	'modelid') 
						out += self.printColumns(temp,				 '{:26s}',	'type') 
						out += self.printColumns(temp,				 '{:27s}',	'uniqueid') 
						out += "{:8s}".format(serialNumber) 
						out += self.printColumns(temp,				 '{:36s}',	'name') 
						out += self.printColumns(temp,				 '{:30s}',	'productid') 
						out += self.printColumns(temp,				 '{:30s}',	'manufacturername') 
						out += self.printColumns(temp,				 '{:30s}',	'productname') 
						out += self.getMemberOfGroup(hubNumber, IDi, valuesDict['whatToPrint'])
						out += self.printColumns(hueIdToIndigoName[hubNumber], '{:20s}',	ID) 
						outs.append(out)
				self.indiLOG.log(20,"\n".join(outs))

			elif valuesDict['whatToPrint'] == "sensors":
				hueIdToIndigoName, indigoNameToHueId = self.getIndigoDevDict("sensorId")

				outs = ['\n======================= print Hue Sensors =====================']
				for hubNumber in sorted(self.ipAddresses):
					if valuesDict['whatToPrint'] not in self.hueConfigDict[hubNumber]: continue
					theDict = self.hueConfigDict[hubNumber][valuesDict['whatToPrint']]
					physicalSensors = 0
					for ii in theDict:
						if theDict[ii].get('type','').find("CLIPGenericStatus") ==-1:
							physicalSensors +=1

					outs.append( "==   Bridge:{}, ipNumber:{}, hostId:{}, paired:{}, #of phys:{}/Sensors:{}, sorted by:{}".format(hubNumber, self.ipAddresses[hubNumber],self.hostIds[hubNumber], self.paired[hubNumber], physicalSensors, len(theDict), sortBy))
							#1234 12345678901     12345678901234567890123456789 12345678901234567890123456789 12345678901234567890123456789 1234567890123456789     123456 123456 123456 1234567890123456789    1234567890 
					outs.append(" ID ONoff Reach Status lastupdated-------- modelid----------------------- type--------------- SNumber Name------------------------- productname------------------  manufacturername------------- Group Indigo Device")
				
					if   sortBy in ['type','name','modelid']: 	IDlist = self.makeSortedIDList(theDict, sortBy)
					else:										IDlist = sorted(theDict, key=lambda key: int(key))

					for IDi in IDlist:
						try: 
							device = indigo.devices[hueIdToIndigoName[hubNumber][ID]]
							serialNumber = device.pluginProps.get("serialNumber","")
						except:
							serialNumber = ""
						ID = str(IDi)
						temp = theDict[ID]
						out  = 										 '{:>3s} '.format(ID)
						if "config" in temp: 
							out += self.printColumns(temp['config'], '  {:<4}', 'on') 
							out += self.printColumns(temp['config'], '  {:<4}', 'reachable') 
						else:								  out += '{:<12}'.format(" ")
						if "state" in temp: 
							out += self.printColumns(temp['state'],  '   {:<4}', 'status') 
							out += self.printColumns(temp['state'],  '{:21s}',	'lastupdated') 
						else:								  out += '{:24s}'.format(" ")
						out += self.printColumns(temp,				 '{:31s}',	'modelid') 
						out += self.printColumns(temp,				 '{:20s}',	'type') 
						out += "{:8s}".format(serialNumber) 
						out += self.printColumns(temp,				 '{:30s}',	'name') 
						out += self.printColumns(temp,				 '{:31s}',	'productname') 
						out += self.printColumns(temp,				 '{:30s}',	'manufacturername') 
						out += self.getMemberOfGroup(hubNumber, IDi, valuesDict['whatToPrint'])
						out += self.printColumns(hueIdToIndigoName[hubNumber], '{:20s}', ID) 
						outs.append(out)
				self.indiLOG.log(20,"\n".join(outs)+"\n")

 
			elif valuesDict['whatToPrint'] == "groups":
				hueIdToIndigoName, indigoNameToHueId = self.getIndigoDevDict("groupId")
				outs = ['\n======================= print Hue Groups =====================']
				for hubNumber in sorted(self.ipAddresses):
					if valuesDict['whatToPrint'] not in self.hueConfigDict[hubNumber]: continue
					theDict = self.hueConfigDict[hubNumber][valuesDict['whatToPrint']]
					outs.append("==  Bridge: {}, ipNumber: {}, hostId: {}, #of Groups: {}, paired: {}, sortedby: {}".format(hubNumber, self.ipAddresses[hubNumber],self.hostIds[hubNumber], len(theDict), self.paired[hubNumber], sortBy))
								 #123 123456789 123456789 123456789 123456789 1 123456789 12345678901234567890123456789 12345678901234567890123456789 1234567890123456789012345
					outs.append(" ID Name------------------------- Name------- Lights---------------------------- IndigoDevName------ ")

					if   sortBy in ['type','name']: 	IDlist = self.makeSortedIDList(theDict, sortBy)
					else:							IDlist = sorted(theDict, key=lambda key: int(key))

					for IDi in IDlist:
						ID = str(IDi)
						temp = theDict[ID]
						out  = 										 '{:>3s} '.format(ID)
						out += self.printColumns(temp,				 '{:30s}',	'name') 
						out += self.printColumns(temp,				 '{:12s}',	'type') 
						if "lights" in temp:
							out += "{:35s}".format(",".join(sorted(temp['lights'])))
						out += self.printColumns(hueIdToIndigoName[hubNumber],		 '{:<20}',	ID) 
						outs.append(out)
				self.indiLOG.log(20,"\n".join(outs)+"\n")


			elif valuesDict['whatToPrint'] == "scenes":
				outs = ['\n======================= print Hue Scenes =====================']
				for hubNumber in sorted(self.ipAddresses):
					if valuesDict['whatToPrint'] not in self.hueConfigDict[hubNumber]: continue
					theDict = self.hueConfigDict[hubNumber][valuesDict['whatToPrint']]
					outs.append("== Bridge: {}, ipNumber: {}, hostId: {}, #of Scenes: {}, paired: {}, sortedby: {}".format(hubNumber, self.ipAddresses[hubNumber],self.hostIds[hubNumber], len(theDict), self.paired[hubNumber], sortBy))
								  #123456789 1234 123456789 123456789  123456789 123456789 1234 1234567890123456789 123456789 
					outs.append("ID------------- Group Type---------- Lights---------------------------- Name------------------------- ")

					if   sortBy in['name']:	IDlist = self.makeSortedIDList(theDict, sortBy)
					else:					IDlist = sorted(theDict, key=lambda key: key)

					for ID in IDlist:
						temp = theDict[ID]
						out  = 										 '{:15s} '.format(ID)
						out += self.printColumns(temp,				 '{:6s}',	'group') 
						out += self.printColumns(temp,				 '{:15s}',	'type') 
						if "lights" in temp:
							out += "{:35s}".format(",".join(sorted(temp['lights'])))
						out += self.printColumns(temp,				 '{:30s}',	'name') 
						outs.append(out)
				self.indiLOG.log(20,"\n".join(outs)+"\n")


			elif valuesDict['whatToPrint'] == "resourcelinks":
				outs = ['\n======================= print Hue resourcelinks =====================']
				for hubNumber in sorted(self.ipAddresses):
					if valuesDict['whatToPrint'] not in self.hueConfigDict[hubNumber]: continue
					theDict = self.hueConfigDict[hubNumber][valuesDict['whatToPrint']]
					outs.append("== Bridge: {}, ipNumber: {}, hostId: {}, #of Scenes: {}, paired: {}, sortedby: {}".format(hubNumber, self.ipAddresses[hubNumber],self.hostIds[hubNumber], len(theDict), self.paired[hubNumber], sortBy))
								 #123456789 1 123456789 123456789  123456789 12345 123456789 123456789 123456789 
					outs.append("ID--------- Name-------------------------- Type- Links- description------------------ ")

					if   sortBy in['name']:	IDlist = self.makeSortedIDList(theDict, sortBy)
					else:					IDlist = sorted(theDict, key=lambda key: int(key))

					for ID in IDlist:
						temp = theDict[ID]
						out  = 										 '{:12s} '.format(ID)
						out += self.printColumns(temp,				 '{:30s}',	'name') 
						out += self.printColumns(temp,				 '{:6s}',	'type') 
						out += '{:>4d}   '.format(len(temp['links'])) 
						out += self.printColumns(temp,				 '{:30s}',	'description') 
						outs.append(out)
				self.indiLOG.log(20,"\n".join(outs)+"\n")


			elif valuesDict['whatToPrint'] == "rules":
				outs = ['\n======================= print Hue Rules =====================']
				for hubNumber in sorted(self.ipAddresses):
					if valuesDict['whatToPrint'] not in self.hueConfigDict[hubNumber]: continue
					theDict = self.hueConfigDict[hubNumber][valuesDict['whatToPrint']]
					outs.append("== Bridge: {}, ipNumber: {}, hostId: {}, #of Scenes: {}, paired: {}, sortedby: {}".format(hubNumber, self.ipAddresses[hubNumber],self.hostIds[hubNumber], len(theDict), self.paired[hubNumber], sortBy))
								  #   123456789 123456789 123456789 1234 123456789 123456789 1234567890  123456789 1 123456789 
					outs.append("ID- Name------------------------------ Status--------- recycle last triggered----    <Actions>          <Conditions>")

					if   sortBy in['name']:	IDlist = self.makeSortedIDList(theDict, sortBy)
					else:					IDlist = sorted(theDict, key=lambda key: int(key))

					for ID in IDlist:
						temp = theDict[ID]
						out  = 										 '{:>3s} '.format(ID)
						out += self.printColumns(temp,				 '{:35s}',	'name') 
						out += self.printColumns(temp,				 '{:16s}',	'status') 
						out += self.printColumns(temp,				 '  {:<5} ',	'recycle') 
						out += self.printColumns(temp,				 '{:22s}',	'lasttriggered') 
						out += self.printColumns(temp,				 '<{:}> ',		'actions') 
						out += self.printColumns(temp,				 ' <{:}> ',		'conditions') 
						outs.append(out)
				self.indiLOG.log(20,"\n".join(outs)+"\n")


			elif valuesDict['whatToPrint'] == "schedules":
				outs = ['\n======================= print Hue Schedules =====================']
				for hubNumber in sorted(self.ipAddresses):
					if valuesDict['whatToPrint'] not in self.hueConfigDict[hubNumber]: continue
					theDict = self.hueConfigDict[hubNumber][valuesDict['whatToPrint']]
					outs.append("== Bridge: {}, ipNumber: {}, hostId: {}, #of Scenes: {}, paired: {}, sortedby: {}".format(hubNumber, self.ipAddresses[hubNumber],self.hostIds[hubNumber], len(theDict), self.paired[hubNumber], sortBy))
								  #   123456789 123456789 123456789 123456789 123456789 1234567890123456789 123456789 
					outs.append("ID- Name------------------------- Status--- starttime ------- ")

					if   sortBy in['name']:	IDlist = self.makeSortedIDList(theDict, sortBy)
					else:					IDlist = sorted(theDict, key=lambda key: int(key))

					for ID in IDlist:
						temp = theDict[ID]
						out  = 										 '{:>3s} '.format(ID)
						out += self.printColumns(temp,				 '{:30s}',	'name') 
						out += self.printColumns(temp,				 '{:10s}',	'status') 
						out += self.printColumns(temp,				 '{:22s}',	'starttime') 
						outs.append(out)
				self.indiLOG.log(20,"\n".join(outs)+"\n")


			elif valuesDict['whatToPrint'] == "NoHudevice":
				out = ""
				out += "\n======================= print Hue {} =====================".format(valuesDict['whatToPrint'])
				anyorphan = 0
				tests = [['bulbId','lights'],['groupId','groups'],['sensorId','sensors']]
				for tt in tests:
					hueIdToIndigoName, indigoNameToHueId = self.getIndigoDevDict(tt[0])
					for hubNumber in self.hueConfigDict:
						if "config" not in self.hueConfigDict[hubNumber]: continue
						# go through all indigop devices 
						for indigoName in indigoNameToHueId[hubNumber]:
							hueIdToFind = indigoNameToHueId[hubNumber][indigoName]
							if tt[1] not in self.hueConfigDict[hubNumber]:
								anyorphan += 1
								out += "\n orphan indigo {:7s} device: == {:47s} ==   ID:{:3} does not exist on bridge: {} - {}".format(tt[1], indigoName, hueIdToFind, hubNumber, self.ipAddresses[hubNumber])
							elif  hueIdToFind not in self.hueConfigDict[hubNumber][tt[1]]:
								anyorphan += 1
								out += "\n orphan indigo {:7s} device: == {:47s} ==   ID:{:3} does not exist on bridge: {} - {}".format(tt[1], indigoName, hueIdToFind, hubNumber, self.ipAddresses[hubNumber])

				for deviceId in copy.deepcopy(self.deviceList):
					device = indigo.devices[deviceId]
					if device.deviceTypeId in kSensorTypeList:
						hubNumber = device.pluginProps['hubNumber']
						if hubNumber not in self.hueConfigDict:
							anyorphan += 1
							out += "\nIndigo device :{:45s}  has no corresponding device on Hue Bridge# {:}".format(device.name, hubNumber )
				out += "\n======================= print Hue {} END =================".format(valuesDict['whatToPrint'])

				if anyorphan > 0 or menuItem == "printHueDataMenu":
					self.indiLOG.log(20,out)
					self.checkMissing()
				elif menuItem == "printHueDataMenu":
					out = ""
					out += "\n======================= print Hue {} =====================".format(valuesDict['whatToPrint'])
					out += "\n     no Indigo devices found that have no corrsponding Hue device "
					out += "\n======================= print Hue {} END =================".format(valuesDict['whatToPrint'])
					self.indiLOG.log(20,out)


			elif valuesDict['whatToPrint'] == "NoIndigoDevice":
				out = ""
				out += "\n======================= print Hue {} =====================".format(valuesDict['whatToPrint'])
				anyorphan = 0
				HIT =  self.getIndigoHIT([['bulbId','lights'],['groupId','groups'],['sensorId','sensors']])
				#self.indiLOG.log(20,"HIT: {}".format(HIT))
				for hubNumber in self.hueConfigDict:
					if "config" not in self.hueConfigDict[hubNumber]: continue
					#self.indiLOG.log(20,"H:{}".format(hubNumber))
					for idX, hType in [['bulbId','lights'],['groupId','groups'],['sensorId','sensors']]:
						#self.indiLOG.log(20,"idX:{} hType:{}".format(idX, hType))
						if hType not in self.hueConfigDict[hubNumber]: continue
						for ID in self.hueConfigDict[hubNumber][hType]:
							test = hType+"-"+hubNumber+"-"+ID
							#self.indiLOG.log(20,test)
							if test in HIT: continue
							if menuItem == "OnlySupportedDevices":  
								if (
										self.hueConfigDict[hubNumber][hType][ID].get('type',"xxx") not in kSupportedSensorTypes and 
										self.hueConfigDict[hubNumber][hType][ID].get('type',"xxx") not in kmapHueTypeToIndigoDevType and
										self.hueConfigDict[hubNumber][hType][ID].get('type',"xxx") not in kmapHueTypeToIndigoDevType 
									):
										continue
							if hType == "sensors" and self.hueConfigDict[hubNumber][hType][ID].get('type',"xxx") not in kSupportedSensorTypes: 
								addText = "--- Plugin does not support THIS Hue device type"
							else: addText = "====  missing in Indigo:  use menu \"Add New Devices on Hue Bridge to Indigo...\" or create manually"
							theName = self.hueConfigDict[hubNumber][hType][ID].get('name',"")
							out += "\nNo corresponding indigo dev for   Bridge#:{:}   type:{:7s},   ID:{:3}   {:32} {:}".format(hubNumber, hType, ID, theName, addText)
							anyorphan +=1
				out += "\n======================= print Hue {} END =================".format(valuesDict['whatToPrint'])

				if anyorphan > 0 or menuItem == "printHueDataMenu":
					self.indiLOG.log(20,out)
				elif menuItem == "printHueDataMenu":
					out = ""
					out += "\n======================= print Hue {} =====================".format(valuesDict['whatToPrint'])
					out += "\n     no Hue devices found that have no corrsponding Indigo device "
					out += "\n======================= print Hue {} END =================".format(valuesDict['whatToPrint'])
					self.indiLOG.log(20,out)




			elif valuesDict['whatToPrint'].find("mappingOfNames") >-1:
				out = ""
				out += "\n======================== mapping of light devtypes     ====================="
				#		  1234567890123456789012345 1234567890123456789012345 1234567890123456789012345678901234567890012345678901234567890
				out += "\n------hue dev type------- -----indigo devType------ --------------------indigo dev type Name---------------------"
				for hdevType in  kmapHueTypeToIndigoDevType:
					idevTypes = kmapHueTypeToIndigoDevType[hdevType]
					for idevType in  idevTypes:
						out+= "\n{:25s} {:25s} {:60s}".format(hdevType, idevType,kmapIndigodevTypeToIndigofulldevType[idevType])
				out += "\n======================= mapping of light devtypes END ====================="
				self.indiLOG.log(20,out)




			elif valuesDict['whatToPrint'].find("lightsDict") >-1:
				tag = valuesDict['whatToPrint'].split('Dict')[0]
				for hubNumber in  self.hueConfigDict:
					out = "printHueData ---hub:{}, {} \n".format(hubNumber,tag)
					for ID in self.hueConfigDict[hubNumber][tag]:
						out+= "{}: {} \n".format( ID, self.hueConfigDict[hubNumber][tag][ID])
					self.indiLOG.log(20,out)

			elif valuesDict['whatToPrint'].find("sensorsDict") >-1:
				tag = valuesDict['whatToPrint'].split('Dict')[0]
				for hubNumber in  self.hueConfigDict:
					out = "printHueData ---hub:{}, {} \n".format(hubNumber,tag)
					for ID in self.hueConfigDict[hubNumber][tag]:
						out+= "{}: {} \n".format( ID, self.hueConfigDict[hubNumber][tag][ID])
					self.indiLOG.log(20,out)

			elif valuesDict['whatToPrint'].find("pluginPrefs") >-1:
					self.indiLOG.log(20, "plugin preferences:\n{}".format(self.pluginPrefs) )

			elif valuesDict['whatToPrint'].find("specific") >-1:
				whatToPrint = valuesDict['whatToPrint'].lower().split("specific")[1]
				xxx =  valuesDict[whatToPrint].split("-")
				if len(xxx) >1: 
					hubNumber = xxx[-1]
					ID = "-".join(xxx[:-1])
					#self.indiLOG.log(30,"printHueData --- xxx {}, hub:{}, ID:{}".format(xxx, hubNumber, ID))
				else:
					self.indiLOG.log(30,"printHueData --- split (-) error, not enough data >{}<, try other selection".format(valuesDict))
					return valuesDict
					
				if whatToPrint not in self.hueConfigDict[hubNumber]:
					self.indiLOG.log(30,"ERROR printHueData --- bad input ".format(valuesDict))
					return valuesDict

				if	 whatToPrint == "lights":	idType = "bulbId"
				elif whatToPrint == "groups":	idType = "groupId"
				elif whatToPrint == "sensors":	idType = "sensorId"
				elif whatToPrint == "scenes":	idType = "sceneId"
				else: idType = ""
				self.indiLOG.log(20,"printHueData --- {}: Bridge:{}, {}={}: Hue-Dict\n{} ".format(whatToPrint, hubNumber, idType, ID, json.dumps(self.hueConfigDict[hubNumber][whatToPrint][ID], indent=2, sort_keys=True)))
				if idType !="":
					devFound = False
					for devId in self.deviceList:
						try:
							dev = indigo.devices[devId]
							props = dev.pluginProps
							if props['hubNumber'] == hubNumber and idType in props and props[idType] == ID:
								self.indiLOG.log(20,"printHueData --- {}, indigo props:\n{} ".format(dev.name, dev.pluginProps))
								self.indiLOG.log(20,"printHueData --- {}, indigo states:\n{} ".format(dev.name, dev.states))
								devFound = True
								break
						except	Exception:
							self.logger.error("", exc_info=True)
					if not devFound: 
								self.indiLOG.log(20,"printHueData --- *****  has not indigo device assigned *****")
		except	Exception:
			self.logger.error("", exc_info=True)

		return valuesDict


	# format columns 
	########################################
	def printColumns(self, theDict, formatString, itemToPrint ):
		if itemToPrint in theDict:	return formatString.format(theDict[itemToPrint])
		else:						return formatString.format(" ")

	# nake a sorted list for the key 
	########################################
	def makeSortedIDList(self, theDict, sortBy):
		IDlist = []
		zz = []
		for ID in theDict:
			if sortBy in theDict[ID]:
				zz.append( theDict[ID][sortBy] +";"+ID)
			else:
				zz.append( " " +";"+ID)

		for xx in sorted(zz):
			IDlist.append(xx.split(";")[1])

		return IDlist


	# nake a list of group members 
	########################################
	def getMemberOfGroup(self, hubNumber, thisDev, thisType):

		out = ""
		theDict = self.hueConfigDict[hubNumber]['groups'] 
		IDlist = sorted(theDict, key=lambda key: int(key))
		for IDi in IDlist:
			ID = str(IDi)
			temp = theDict[ID]
			if thisType in temp:
				if thisDev in temp[thisType]:
					out += "{},".format(ID)
			else: pass
		return "{:6s}".format(out.strip(",")) 


	# nake a dict of hue indigo devices {id:indigoName} for specific dev types 
	########################################
	def getIndigoDevDict(self, typeName):
		hueIdToIndigoName = dict()
		indigoNameToHueId = dict()
		for hubNumber in self.ipAddresses:
			hueIdToIndigoName[hubNumber] = dict()
			indigoNameToHueId[hubNumber] = dict()
		for dev in indigo.devices.iter(self.pluginId):
			props = dev.pluginProps
			if typeName in props:
				hubNumber = props.get('hubNumber','0')
				if hubNumber in hueIdToIndigoName:
					hueIdToIndigoName[hubNumber][dev.pluginProps[typeName]] = dev.name
					indigoNameToHueId[hubNumber][dev.name] = dev.pluginProps[typeName]
		return hueIdToIndigoName, indigoNameToHueId

	# nake a list of hue indigo devices 
	########################################
	def getIndigoHIT(self, IdType):
		xList =[]
		for dev in indigo.devices.iter(self.pluginId):
			props = dev.pluginProps
			H = props.get('hubNumber','0')
			for idX, hType in IdType:
				if idX in props:
					T = hType
					I = props.get(idX,'')
					xList.append(T+"-"+H+"-"+I)

		return xList


####-----------------	 ---------
	def completePath(self,inPath):
		if len(inPath) == 0: return ""
		if inPath == " ":	 return ""
		if inPath[-1] != "/": inPath +="/"
		return inPath

####-----------------	 ---------
	# Toggle Debug Logging Menu Action
	########################################
	def setDebugAreas(self, valuesDict, item=""):
		self.getDebugLevels( useMe={"debugall": not self.pluginPrefs['debugall']} )
		self.pluginPrefs['debugall'] = not self.pluginPrefs.get('debugall',False)
		return 

####-------------------------------------------------------------------------####
	def getDebugLevels(self, useMe=dict()):
		try:
			self.debugLevel	= []
			if useMe == dict():
				for d in _debugAreas:
					if self.pluginPrefs.get('debug'+d, False): self.debugLevel.append(d)
				self.showLoginTest = self.pluginPrefs.get("showLoginTest", True)
			else:
				for d in _debugAreas:
					if useMe.get('debug'+d, False): self.debugLevel.append(d)
				self.showLoginTest = useMe.get("showLoginTest", True)

			self.indiLOG.log(20,"debug areas:{}".format(self.debugLevel))
		except Exception:
			self.indiLOG.log(50,"Error in startup of plugin, plugin prefs are wrong", exc_info=True)
		return
####-----------------	 ---------
	def decideMyLog(self, msgArea):
		try:
			if msgArea	 == "all" or "all" in self.debugLevel:	 return True
			if msgArea	 == ""	  and "all" not in self.debugLevel: return False
			if msgArea in self.debugLevel:							 return True
			return False
		except	Exception:
			self.logger.error("", exc_info=True)
		return False

####----------------- print to log as error only if different from last error message ---------
	def doErrorLog(self, errorText, level=40, force=False):
		if errorText != self.lastErrorMessage or force:
			self.indiLOG.log(level, errorText)
			self.lastErrorMessage = errorText
		return errorText


	########################################
	def checkForLastNotPairedMessage(self, hubNumber):
		#self.indiLOG.log(20,"checkForLastNotPairedMessage, hubnumber, notPairedMsg:{}, {}, paired:{}".format(hubNumber, self.notPairedMsg, self.paired))
		if hubNumber not in self.notPairedMsg:
			#self.indiLOG.log(20,"checkForLastNotPairedMessage, hubnumber not in notPairedMsg:{}, {}".format(hubNumber, self.notPairedMsg))
			self.notPairedMsg[hubNumber]  = time.time() - 99

		ret = time.time() - self.notPairedMsg[hubNumber] > 100
		if ret:
			self.notPairedMsg[hubNumber]  = time.time()
		return ret 

####-----------------	 ---------
	def normalizeHue(self, hueIn, device):
		# hue should be <=0 Hue <65535 --  to catch anythig close, set number a little lower for logging.
		if hueIn >= 65536 or hueIn < 0:
			self.indiLOG.log(10,"device:{:35} has hue:{} > 65500, called from:{} @line:{}".format(device.name, hueIn, inspect.stack()[1][3],inspect.stack()[1][2] ))
		return 	max(0,min(360,(int(round(hueIn / 182.0416666668)))))

####-----------------	 ---------
	def isValidIP(self, ip0):
		try:
			if ip0 == "localhost": 						return True

			ipx = ip0.split(".")
			if len(ipx) != 4:								return False
			if ipx[0] == "0":								return False

			else:
				for ip in ipx:
					try:
						if int(ip) < 0 or  int(ip) > 255: 	return False
					except:
															return False
			if True:										return True

		except:
			pass
		if True:											return False


	# get ip numbers etc
	########################################
	def getadresses(self, hubNumber):
			ipAddress = self.ipAddresses[hubNumber]
			if ipAddress is None:
				self.doErrorLog("No IP address set for the Hue bridge. You can get this information from the My Settings page at http://www.meethue.com.")
				return 0,0,1
			if not self.isValidIP(ipAddress):
				self.doErrorLog("No IP address set for the Hue bridge. You can get this information from the My Settings page at http://www.meethue.com.")
				return 0,0,1
			if hubNumber not in self.hostIds:
				return 0,0,2
			return ipAddress, self.hostIds[hubNumber], 0

####-------------------------------------------------------------------------####
	def readPopen(self, cmd):
		try:
			ret, err = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
			return ret.decode('utf_8'), err.decode('utf_8')
		except Exception as e:
			if str(e).find("None") == -1: self.logger.error("", exc_info=True)


####-------------------------------------------------------------------------####
	def openEncoding(self, ff, readOrWrite):

		if sys.version_info[0]  > 2:
			return open( ff, readOrWrite, encoding="utf-8")
		else:
			return codecs.open( ff ,readOrWrite, "utf-8")


	########################################
	def baseHTTPAddress(self, hubNumber):
		if hubNumber in self.ipAddresses:
			return "http://{}/api/{}".format(self.ipAddresses[hubNumber], self.hostIds[hubNumber])
		else:
			return "http://{}/api/{}".format(self.ipAddresses['0'], self.hostIds['0'])



####-------------------------------------------------------------------------####
	def setlastBatteryReplaced(self, device, batL):
		try:	
			if "lastBatteryReplaced"  not in device.states: return 
			if "batteryLevel"  not in device.states: return 

			# remember the last datetime when batlevel was 100%
			if len(device.states["lastBatteryReplaced"]) < 5:
				self.updateDeviceState(device, "lastBatteryReplaced",	datetime.datetime.now().strftime(_defaultDateStampFormat))
				return 

			if  batL == 100:
				if len(str(device.states["batteryLevel"])) < 1:# empty 
					self.updateDeviceState(device, "lastBatteryReplaced",	datetime.datetime.now().strftime(_defaultDateStampFormat))

				elif device.states["batteryLevel"] < batL: # update if new 100%
					self.updateDeviceState(device, "lastBatteryReplaced",	datetime.datetime.now().strftime(_defaultDateStampFormat))
		except Exception as e:
			if str(e).find("None") == -1: self.logger.error("", exc_info=True)



####--------------------------- Start ---------------------------------------####

	# manage connects to bridge, make sure that  only one connection at a time is active
	########################################
	def setBridgeBusy(self, hubNumber, calledfrom=""):
		try:
			if hubNumber not in self.bridgeBusy: # init
				self.bridgeBusy[hubNumber] = time.time()
				return 


			if self.bridgeBusy[hubNumber]  == 0. : # nothing curretly active, set timer and return 
				self.bridgeBusy[hubNumber] = time.time()
				return 


			mxDelay = time.time() - self.bridgeBusy[hubNumber]
			if mxDelay > 5: #  something is active, check if too long:
					self.indiLOG.log(30, "set Bridge# {:} busy,  last action active for:{:.1f} secs, cancelling wait, too long..;  pgm request connection:{:}, delay timers:{:}".format(hubNumber, mxDelay, calledfrom, self.bridgeBusy ))
					self.indiLOG.log(30, "                       !! bridge gets polled too often causing forced delays;  please reduce polling of bridge to a lower frequency in config !!")
					self.bridgeBusy[hubNumber] = time.time()
					return 


			startDelay = time.time()  # now wait until previous process is finished
			for ii in range(50):
				self.sleep(0.1) 

				if time.time() - startDelay  > 4.5: # wait max 4.5 secs, then 
					self.indiLOG.log(30, "set Bridge#:{:} delay: cancel wait- too long, total delay={:.2f}; continue with connection pgm request connection:{}".format(hubNumber, time.time() - startDelay, calledfrom ))
					break 

				if self.bridgeBusy[hubNumber] == 0.:  # ==0 was reset by previous pgm, write to plugin.log only
					if ii > 2: self.indiLOG.log(10, "set Bridge#:{:} delay: not busy anymore, total delay={:.2f}; continue with connection pgm request connection:{}".format(hubNumber, time.time() - startDelay, calledfrom ))
					break

				#if ii > 10: self.indiLOG.log(20,  "set Bridge#:{:} busy,  Nth delay:{} now delayed by:{:.3f}, pgm request connection:{}".format(hubNumber, ii, time.time() - startDelay, calledfrom ))



			self.bridgeBusy["max delay"] = max(self.bridgeBusy["max delay"] ,  time.time() - startDelay)  # remember largest delay

			if self.bridgeBusy["max delay"]  > 3.5:  #  waiting to log and rest max 
				self.indiLOG.log(30, "set Bridge::{} Busy,       !! bridge gets polled too often causing forced delays, max={:.1f} secs;  please reduce polling of bridge to a lower frequency in config !!".format(hubNumber, self.bridgeBusy["max delay"] ))
				self.bridgeBusy["max delay"] = 0.


			self.bridgeBusy[hubNumber] = time.time()
		except Exception:
			self.indiLOG.log(30,"", exc_info=True)
		return 
	
	# reset bridge busy from above
	########################################
	def resetBridgeBusy(self, hubNumber):
		try:
			self.bridgeBusy[hubNumber] = 0.
		except:
			pass
		return 		
####----------------------------- END ------------------------------------####
	



##################################################################################################################
####-----------------  valiable formatter for different log levels ---------
# call with:
# formatter = LevelFormatter(fmt='<default log format>', level_fmts={logging.INFO: '<format string for info>'})
# handler.setFormatter(formatter)
class LevelFormatter(logging.Formatter):
####-------------------------------------------------------------------------####
	def __init__(self, fmt=None, datefmt=None, level_fmts=dict(), level_date=dict()):
		formt = None
		self._level_formatters = dict()
		self._level_date_format = dict()
		for level, formt in level_fmts.items():
			# Could optionally support level names too
			self._level_formatters[level] = logging.Formatter(fmt=formt, datefmt=level_date[level])
		# self._fmt will be the default format
		super(LevelFormatter, self).__init__(fmt=formt, datefmt=datefmt)

####-------------------------------------------------------------------------####
	def format(self, record):
		if record.levelno in self._level_formatters:
			return self._level_formatters[record.levelno].format(record)

		return super(LevelFormatter, self).format(record)



