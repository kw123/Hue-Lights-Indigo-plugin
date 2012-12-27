#! /usr/bin/env python
# -*- coding: utf-8 -*-
####################
# Based on the "Hue.indigoPlugin" (Hue Lighting Control) plugin originally
#   developed by Alistair Galbraith (alistairg on GitHub,
#   https://github.com/alistairg ).
#
#   His comment:
#   "This is UNSUPPORTED, AS-IS, open source code - do with it as you wish. Don't
#   blame me if it breaks! :)"
#
# The code base was fored on GitHub and mostly rewritten by Nathan Sheldon
#   (nathan@nathansheldon.com)
#   http://www.nathansheldon.com/files/Hue-Lights-Plugin.php
#   All modificiations are open source.
#
#	Version 0.9.5
#
#	History:	0.9.5 (27-Dec-2012)
#				* Fixed bug that would cause the Hue light not to turn off
#				  if using RGB mode when Red, Green, and Blue were all zero.
#				--
#				0.9.4 (27-Nov-2012)
#				* Fixed bug that would return an error if no default ramp
#				  rate were enered for a Hue bulb device.
#				* Added more debug logging.
#				* Changed how logging is done to be more consistant with
#				  other Indigo device update events. A log entry now appears
#				  after the physical device has changed (as was always the
#				  case) but now it appears before the Indigo device state
#				  is updated.
#				* Increased delay between status update requests to about
#				  8 seconds to decrease number of requests per minute
#				  sent to the Hue hub.
#				--
#				0,9.3 (18-Nov-2012)
#				* Fixed typo (bug) that caused the plugin to crash when the
#				  Hue hub was unreachable within the timeout period.
#				* Worked around a colormath bug that would throw a
#				  ZeroDivisionError if the "y" component was zero.
#				* Added checks in bulb status gathering to prevent unnecessary
#				  Indigo device status updates. Added logging for any device
#				  brightness updates detected.
#				* Added more exception handling for HTTP requests to hub.
#				* Slightly tweaked status request timing.
#				--
#				0.9.2 (17-Nov-2012)
#				* Corrected error in actionControlDimmerRelay that prevented
#				  setBrightness call from working.
#				--
#				0.9.1 (16-Nov-2012)
#				* Tweaked brightening and dimming timing for Start Brightening
#				  and Start Dimming actions so the rate was about the same speed
#				  as SmartLabs SwithcLinc Dimmers and LampLinc Dimmers.
#				* Removed code that immediately changes the RGB color states for
#				  the Indigo device as the values entered by the user are not
#				  actual displayed values. Actual values will be updated by the
#				  getBulbStatus method later.
#				* Added the "Set Brightness with Ramp Rate" action and associated
#				  plugin.py code. Renamed multiple methods for easier redability
#				  and for easier plugin scripting within Indigo.  Reorganized
#				  order in which methods appear in the source code for a more
#				  logical layout.
#				--
#				0.9 (13-Nov-2012)
#				* Initial Nathan Sheldon forked beta release.
#				* This version removes the use of the "ColorPy" library from
#				  Alistair's version and replaces it with the "colormath"
#				  library as it includes the ability to specify a target
#				  illumination source during color conversion, thus presenting
#				  a closer RGB to xyY conversion (and vice-versa).
#				* Most of Alistair's original code was rewritten to remain
#				  consistent with coding convensions in my other plugins, but
#				  some of his code is still in here.
#
################################################################################

import os
import sys
import uuid
import hashlib
import requests
import socket
from colormath.color_objects import RGBColor, xyYColor, XYZColor
import simplejson as json
from math import ceil, floor

# Default timeout
kTimeout = 4		# seconds


################################################################################
class Plugin(indigo.PluginBase):
	########################################
	# Loading and Starting Methods
	########################################
	
	# Load Plugin
	########################################
	def __init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs):
		indigo.PluginBase.__init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs)
		self.debug = pluginPrefs.get('showDebugInfo', False)
		self.debugLog(u"Initializing Plugin.")
		self.deviceList = []		# list of device IDs to monitor
		self.brighteningList = []	# list of device IDs being brightened
		self.dimmingList = []		# list of device IDs being dimmed
		self.paired = False			# if paired with Hue hub or not
		self.lightsDict = dict()	# Hue bulb ID: Name dict.
		self.ipAddress = ""			# Hue hub IP address
	
	# Unload Plugin
	########################################
	def __del__(self):
		indigo.PluginBase.__del__(self)
		
	# Startup
	########################################
	def startup(self):
		self.debugLog(u"Startup called")

		# Do we have a site ID?
		siteId = self.pluginPrefs.get('hostId', None)
		if siteId is None:
			siteId = str(uuid.uuid1())
			siteId = hashlib.md5(siteId).hexdigest().lower()
			self.debugLog(u"Host ID is %s" % siteId)
			self.pluginPrefs['hostId'] = siteId
		
		# Load lights list
		self.updateLightsList()
		
	# Start Devices
	########################################
	def deviceStartComm(self, device):
		self.debugLog(u"Starting device: " + device.name)
		# Update the device list and the device states.
		if device.id not in self.deviceList:
			self.debugLog(u"Device definition:\n" + str(device))
			self.deviceList.append(device.id)
			# Get the bulb's status.
			self.getBulbStatus(device.id)

	# Stop Devices
	########################################
	def deviceStopComm(self, device):
		self.debugLog(u"Stopping device: " + device.name)
		if device.id in self.deviceList:
			self.deviceList.remove(device.id)
			
	# Shutdown
	########################################
	def shutdown(self):
		self.debugLog(u"Plugin shutdown called")
	
	
	########################################
	# Standard Plugin Methods
	########################################
	
	# New Device Created
	########################################
	def deviceCreated(self, dev):
		self.debugLog(u"Created device of type \"%s\"" % dev.deviceTypeId)
	
	# Run a Concurrent Thread for Status Updates
	########################################
	def runConcurrentThread(self):
		self.debugLog(u"runConcurrentThread called.")
		#
		# Continuously loop through all Hue lighting devices to see if the
		#   status has changed.
		#
		try:
			while True:
				## Brightening Devices ##
				i = 0
				# Loop 20 times (about 0.4 sec per loop, 8 sec total).
				while i < 20:
					# Go through the devices waiting to be brightened.
					for brightenDeviceId in self.brighteningList:
						# Make sure the device is in the deviceList.
						if brightenDeviceId in self.deviceList:
							# Increase the brightness level by 10 percent.
							brightenDevice = indigo.devices[brightenDeviceId]
							brightness = brightenDevice.states['brightnessLevel']
							self.debugLog(u"Brightness: " + str(brightness))
							brightness += 12
							self.debugLog(u"Updated to: " + str(brightness))
							if brightness >= 100:
								brightness = 100
								# Log the event to Indigo log.
								indigo.server.log(u"\"" + brightenDevice.name + "\" stop brightening")
								self.brighteningList.remove(brightenDeviceId)
								# Get the bulb status
								self.getBulbStatus(brightenDeviceId)
								# Log the new brightnss.
								indigo.server.log(u"\"" + brightenDevice.name + "\" status request (received: 100)")
							# Convert percent-based brightness to 255-based brightness.
							brightness = int(round(brightness / 100.0 * 255.0))
							# Set brightness to new value, with 0.5 sec ramp rate and no logging.
							self.doBrightness(brightenDevice, brightness, 0.5, False)
							
					# Go through the devices waiting to be dimmed.
					for dimDeviceId in self.dimmingList:
						# Make sure the device is in the deviceList.
						if dimDeviceId in self.deviceList:
							# Decrease the brightness level by 10 percent.
							dimDevice = indigo.devices[dimDeviceId]
							brightness = dimDevice.states['brightnessLevel']
							brightness -= 12
							if brightness <= 0:
								brightness = 0
								# Log the event to Indigo log.
								indigo.server.log(u"\"" + dimDevice.name + "\" stop dimming")
								self.dimmingList.remove(dimDeviceId)
								# Get the bulb status
								self.getBulbStatus(dimDeviceId)
								# Log the new brightnss.
								indigo.server.log(u"\"" + dimDevice.name + "\" status request (received: 0)")
							# Convert percent-based brightness to 255-based brightness.
							brightness = int(round(brightness / 100.0 * 255.0))
							# Set brightness to new value, with 0.5 sec ramp rate and no logging.
							self.doBrightness(dimDevice, brightness, 0.5, False)
							
					# Wait for 0.45 seconds before loop repeats.
					self.sleep(0.40)
					# Increment loop counter.
					i += 1
					
				# Now the the brightening/dimming loop has finished, get device states.
				# Cycle through each device.
				for deviceId in self.deviceList:
					# Get the bulb's status.
					self.getBulbStatus(deviceId)
					# Wait just a bit to avoid hub rate limiting.
					self.sleep(0.2)
							
		except self.StopThread:
			self.debugLog(u"runConcurrentThread stopped.")
			pass
		
		self.debugLog(u"runConcurrentThread exiting.")
	
	# Validate Device Configuration
	########################################
	def validateDeviceConfigUi(self, valuesDict, typeId, deviceId):
		self.debugLog(u"validateDeviceConfigUi called.")
		errorsDict = indigo.Dict()
		errorsDict['showAlertText'] = ""
		isError = False
		# Make sure a bulb was selected.
		if valuesDict.get('bulbId', "") == "":
			isError = True
			errorsDict['bulbId'] = u"Please select a Hue bulb to control."
			errorsDict['showAlertText'] += errorsDict['bulbId']
			return (False, valuesDict, errorsDict)
			
		# Make sure the bulb ID isn't used by another device.
		for otherDeviceId in self.deviceList:
			if otherDeviceId != deviceId:
				otherDevice = indigo.devices[otherDeviceId]
				if valuesDict['bulbId'] == otherDevice.pluginProps.get('bulbId', 0):
					otherDevice = indigo.devices[otherDeviceId]
					isError = True
					errorsDict['bulbId'] = u"This Hue bulb is already being controlled by the \"" + otherDevice.name + "\" Indigo device. Choose a different Hue bulb to control."
					errorsDict['showAlertText'] += errorsDict['bulbId'] + "\n\n"
					
		# Validate the default ramp rate (transition time) is reasonable.
		if valuesDict.get('rate', "") != "":
			try:
				rampRate = float(valuesDict['rate'])
				if rampRate < 0 or rampRate > 540:
					isError = True
					errorsDict['rate'] = u"The Ramp Rate must be a number between 0 and 540 in increments of 0.1 seconds."
					errorsDict['showAlertText'] += errorsDict['rate'] + "\n\n"
			except ValueError:
				isError = True
				errorsDict['rate'] = u"The Ramp Rate must be a number between 0 and 540 in increments of 0.1 seconds."
				errorsDict['showAlertText'] += errorsDict['rate'] + "\n\n"
			except Execption, e:
				isError = True
				errorsDict['rate'] = u"The Ramp Rate must be a number between 0 and 540 in increments of 0.1 seconds. Error: " + str(e)
				errorsDict['showAlertText'] += errorsDict['rate'] + "\n\n"
				
		# Show errors if there are any.
		if isError:
			errorsDict['showAlertText'] = errorsDict['showAlertText'].strip()
			return (False, valuesDict, errorsDict)

		else:
			# Define the device's address to appear in Indigo.
			device = indigo.devices[deviceId]
			valuesDict['address'] = self.pluginPrefs.get('address', "") + " (ID " + str(valuesDict['bulbId']) + ")"
			return (True, valuesDict)
			
	# Validate Action Configuration.
	########################################
	def validateActionConfigUi(self, valuesDict, typeId, deviceId):
		device = indigo.devices[deviceId]
		self.debugLog(u"Validating action config for type: " + typeId + u", device: " + device.name)
		self.debugLog(u"Values:\n" + str(valuesDict))
		isError = False
		errorsDict = indigo.Dict()
		errorsDict['showAlertText'] = ""
		descString = u""
		
		### SET BRIGHTNESS WITH RAMP RATE ###
		if typeId == "setBrightness":
			brightnessSource = valuesDict.get('brightnessSource', False)
			brightness = valuesDict.get('brightness', False)
			brightnessVarId = valuesDict.get('brightnessVariable', False)
			brightnessDevId = valuesDict.get('brightnessDevice', False)
			useRateVariable = valuesDict.get('useRateVariable', False)
			rate = valuesDict.get('rate', False)
			rateVarId = valuesDict.get('rateVariable', False)
			
			if not brightnessSource:
				isError = True
				errorsDict['brightnessSource'] = u"Please specify a Brightness Source."
				errorsDict['showAlertText'] += errorsDict['brightnessSource'] + "\n\n"
			elif brightnessSource == "custom":
				if not brightness:
					isError = True
					errorsDict['brightness'] = u"Please specify a brightness level."
					errorsDict['showAlertText'] += errorsDict['brightness'] + "\n\n"
				else:
					try:
						brightness = int(brightness)
						if brightness < 0 or brightness > 100:
							isError = True
							errorsDict['brightness'] = u"Brightness levels must be a number between 0 and 100."
							errorsDict['showAlertText'] += errorsDict['brightness'] + "\n\n"
					except ValueError:
						isError = True
						errorsDict['brightness'] = u"Brightness levels must be a number between 0 and 100."
						errorsDict['showAlertText'] += errorsDict['brightness'] + "\n\n"
				descString += u"set brightness of \"" + device.name + "\" to " + str(brightness) + "%"
			elif brightnessSource == "variable":
				if not brightnessVarId:
					isError = True
					errorsDict['brightnessVariable'] = u"Please specify a variable to use for brightness level."
					errorsDict['showAlertText'] += errorsDict['brightnessVariable'] + "\n\n"
				else:
					try:
						brightnessVar = indigo.variables[int(brightnessVarId)]
						descString += u"set brightness of \"" + device.name + "\" to value in variable \"" + brightnessVar.name + "\""
					except IndexError:
						isError = True
						errorsDict['brightnessVariable'] = u"The specified variable does not exist in the Indigo database. Please choose a different variable."
						errorsDict['showAlertText'] += errorsDict['brightnessVariable'] + "\n\n"
			elif brightnessSource == "dimmer":
				if not brightnessDevId:
					isError = True
					errorsDict['brightnessDevice'] = u"Please specify a dimmer device to use as the source for brightness level."
					errorsDict['showAlertText'] += errorsDict['brightnessDevice'] + "\n\n"
				else:
					try:
						brightnessDev = indigo.devices[int(brightnessDevId)]
						descString += u"set brightness of \"" + device.name + "\" to current brightness of \"" + brightnessDev.name + "\""
					except IndexError:
						isError = True
						errorsDict['brightnessDevice'] = u"The specified device does not exist in the Indigo database. Please choose a different device."
						errorsDict['showAlertText'] += errorsDict['brightnessDevice'] + "\n\n"
					if brightnessDev.id == device.id:
						isError = True
						errorsDict['brightnessDevice'] = u"You cannot select the same dimmer as the one for which you're setting the brightness."
						errorsDict['showAlertText'] += errorsDict['brightnessDevice'] + "\n\n"
			
			if not useRateVariable:
				if not rate and rate.__class__ != bool:
					isError = True
					errorsDict['rate'] = u"Please enter a Ramp Rate."
					errorsDict['showAlertText'] += errorsDict['rate'] + "\n\n"
				else:
					try:
						rate = round(float(rate), 1)
						if rate < 0 or rate > 540:
							isError = True
							errorsDict['rate'] = u"Ramp Rate times must be between 0 and 540 seconds."
							errorsDict['showAlertText'] += errorsDict['rate'] + "\n\n"
					except ValueError:
						isError = True
						errorsDict['rate'] = u"Ramp Rates must be between 0 and 540 seconds and cannot contain non-numeric characters."
						errorsDict['showAlertText'] += errorsDict['rate'] + "\n\n"
				descString += u" using ramp rate " + str(rate) + " sec"
			else:
				if not rateVarId:
					isError = True
					errorsDict['rateVariable'] = u"Please select a variable to use for the ramp rate."
					errorsDict['showAlertText'] += errorsDict['rateVariable'] + "\n\n"
				else:
					try:
						rateVar = indigo.variables[int(rateVarId)]
						descString += u" using ramp rate in variable \"" + rateVar.name + "\""
					except IndexError:
						isError = True
						errorsDict['rateVariable'] = u"The specified variable does not exist in the Indigo database. Please choose a different variable."
						errorsDict['showAlertText'] += errorsDict['rateVariable'] + "\n\n"
		
		### SET RGB LEVELS ###
		if typeId == "setRGB":
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
			rampRate = valuesDict.get('rate', "")
			
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
			except Exception, e:
				isError = True
				errorsDict['red'] = "Invalid Red value: " + str(e)
				errorsDict['showAlertText'] += errorsDict['red'] + "\n\n"
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
			except Exception, e:
				isError = True
				errorsDict['green'] = "Invalid Green value: " + str(e)
				errorsDict['showAlertText'] += errorsDict['green'] + "\n\n"
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
			except Exception, e:
				isError = True
				errorsDict['blue'] = "Invalid Blue value: " + str(e)
				errorsDict['showAlertText'] += errorsDict['blue'] + "\n\n"
			# Validate Ramp Rate.
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
				except Exception, e:
					isError = True
					errorsDict['rate'] = "Invalid Ramp Rate value: " + str(e)
					errorsDict['showAlertText'] += errorsDict['rate'] + "\n\n"
			if not isError:
				descString += u"set hue bulb RGB levels to " + str(red) + ", " + str(green) + ", " + str(blue)
				if len(valuesDict.get('rate', "")) > 0:
					descString += u" with ramp rate " + str(rampRate)
					
		### SET HSB ###
		elif typeId == "setHSB":
			# Check the RGB values.
			hue = valuesDict.get('hue', 0)
			if hue == "":
				hue = 0
				valuesDict['hue'] = hue
			saturation = valuesDict.get('saturation', 100)
			if saturation == "":
				saturation = 100
				valuesDict['saturation'] = saturation
			brightness = valuesDict.get('brightness', "")
			if brightness == "":
				brightness = device.states['brightnessLevel']
				valuesDict['brightness'] = brightness
			rampRate = valuesDict.get('rate', "")
			
			try:
				hue = int(hue)
				if (hue < 0) or (hue > 360):
					isError = True
					errorsDict['red'] = "Hue values must be a whole number between 0 and 360 degrees."
					errorsDict['showAlertText'] += errorsDict['hue'] + "\n\n"
			except ValueError:
				isError = True
				errorsDict['hue'] = "Hue values must be a whole number between 0 and 360 degrees."
				errorsDict['showAlertText'] += errorsDict['hue'] + "\n\n"
			except Exception, e:
				isError = True
				errorsDict['hue'] = "Invalid Hue value: " + str(e)
				errorsDict['showAlertText'] += errorsDict['hue'] + "\n\n"
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
			except Exception, e:
				isError = True
				errorsDict['saturation'] = "Invalid Green value: " + str(e)
				errorsDict['showAlertText'] += errorsDict['saturation'] + "\n\n"
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
			except Exception, e:
				isError = True
				errorsDict['brightness'] = "Invalid Brightness value: " + str(e)
				errorsDict['showAlertText'] += errorsDict['brightness'] + "\n\n"
			# Validate Ramp Rate.
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
				except Exception, e:
					isError = True
					errorsDict['rate'] = "Invalid Ramp Rate value: " + str(e)
					errorsDict['showAlertText'] += errorsDict['rate'] + "\n\n"
			if not isError:
				descString += u"set hue bulb hue, sturation, brightness to " + str(hue) + ", " + str(saturation) + ", " + str(brightness)
				if len(valuesDict.get('rate', "")) > 0:
					descString += u" with ramp rate " + str(rampRate)
					
		### SET COLOR TEMPERATURE ###
		elif typeId == "setCT":
			# Check the Color Temperature values.
			preset = valuesDict.get('preset', False)
			if preset == "":
				preset = "relax"
				valuesDict['preset'] = preset
			temperature = valuesDict.get('temperature', 2800)
			if temperature == "":
				temperature = 2800
				valuesDict['temperature'] = temperature
			brightness = valuesDict.get('brightness', "")
			if brightness == "":
				brightness = device.states['brightnessLevel']
				valuesDict['brightness'] = brightness
			rampRate = valuesDict.get('rate', "")
			
			# Validate that a Preset item or Custom was selected.
			if preset == False:
				isError = True
				errorsDict['preset'] = "Please select an item from the Preset menu."
				errorsDict['showAlertText'] += errorsDict['preset'] + "\n\n"
			elif preset == "custom":
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
				except Exception, e:
					isError = True
					errorsDict['temperature'] = "Invalid Color Temperature value: " + str(e)
					errorsDict['showAlertText'] += errorsDict['temperature'] + "\n\n"
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
				except Exception, e:
					isError = True
					errorsDict['brightness'] = "Invalid Brightness value: " + str(e)
					errorsDict['showAlertText'] += errorsDict['brightness'] + "\n\n"
			# Validate Ramp Rate.
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
				except Exception, e:
					isError = True
					errorsDict['rate'] = "Invalid Ramp Rate value: " + str(e)
					errorsDict['showAlertText'] += errorsDict['rate'] + "\n\n"
			if not isError:
				if preset != "custom":
					descString += u"set hue bulb color temperature to preset \"" + preset + "\""
				else:
					descString += u"set hue bulb color temperature to custom value " + str(temperature) + " K at " + str(brightness) + "% brightness"
				if len(valuesDict.get('rate', "")) > 0:
					descString += u" with ramp rate " + str(rampRate)
					
		valuesDict['description'] = descString
		if isError:
			errorsDict['showAlertText'] = errorsDict['showAlertText'].strip()
			return (False, valuesDict, errorsDict)
		
		return (True, valuesDict)
		
	# Did Device Communications Properties Change?
	########################################
	def didDeviceCommPropertyChange(self, origDev, newDev):
		# Automatically called by plugin host when device properties change.
		self.debugLog("didDeviceCommPropertyChange called.")
		# If this is a Hue bulb device, return True (which stops then starts
		#   Indigo communication.  That's not necessary if only the name or
		#   saved brightness changes.
		if origDev.deviceTypeId == "hueBulb":
			if origDev.pluginProps['bulbId'] != newDev.pluginProps['bulbId']:
				return True
			return False
		else:
			# This is some device type other than a Hue bulb, so do the
			#   default action of returning True if anything has changed.
			if origDev.pluginProps != newDev.pluginProps:
				return True
			return False
	
	# Plugin Configuration Dialog Closed
	########################################
	def closedPrefsConfigUi(self, valuesDict, userCancelled):
		self.debugLog(u"closedPrefsConfigUi called")
		if not userCancelled:
			self.debug = valuesDict.get(u"showDebugInfo", False)
			if self.debug:
				indigo.server.log(u"Debug logging enabled")
			else:
				indigo.server.log(u"Debug logging disabled")
	
	
	########################################
	# Plugin-Specific Device Methods
	########################################
	
	# Update Device State
	########################################
	def updateDeviceState(self, device, state, newValue):
		# Change the device state on the server
		#   if it's different than the current state.
		if (newValue != device.states[state]):
			try:
				self.debugLog(u"updateDeviceState: Updating device " + device.name + u" state: " + str(state) + u" = " + str(newValue))
			except Exception, e:
				self.debugLog(u"updateDeviceState: Updating device " + device.name + u" state: (Unable to display state due to error: " + str(e) + u")")
			# If this is a floating point number, specify the maximum
			#   number of digits to make visible in the state.  Everything
			#   in this plugin only needs 1 decimal place of precission.
			#   If this isn't a floating point value, don't specify a number
			#   of decimal places to display.
			if newValue.__class__.__name__ == 'float':
				device.updateStateOnServer(key=state, value=newValue, decimalPlaces=4)
			else:
				device.updateStateOnServer(key=state, value=newValue)
	
	# Update Device Properties
	########################################
	def updateDeviceProps(self, device, newProps):
		# Change the properties on the server only if there's actually been a change.
		if device.pluginProps != newProps:
			self.debugLog(u"updateDeviceProps: Updating device " + device.name + u" properties.")
			device.replacePluginPropsOnServer(newProps)
	
	
	########################################
	# Hue Communication Methods
	########################################
	
	# Get Bulb Status
	########################################
	def getBulbStatus(self, deviceId):
		device = indigo.devices[deviceId]
		### self.debugLog(u"Get bulb status for " + device.name)
		# Get the bulb ID from the device properties.
		bulbId = device.pluginProps.get('bulbId', False)
		# if the bulbId exists, get the device status.
		if bulbId:
			command = "http://%s/api/%s/lights/%s" % (self.ipAddress, self.pluginPrefs['hostId'], bulbId)
			### self.debugLog(u"Sending URL request: " + command)
			try:
				r = requests.get(command, timeout=kTimeout)
			except requests.exceptions.Timeout:
				indigo.server.log(u"Failed to connect to the Hue hub at %s after %i seconds. - Check that the hub is connected and turned on." % (self.ipAddress, kTimeout))
				return
			except requests.exceptions.ConnectionError:
				indigo.server.log(u"Failed to connect to the Hue hub at %s. - Check that the hub is connected and turned on." % (self.ipAddress))
				return
				
			### self.debugLog(u"Data from hub: " + r.content)
			# Convert the response to a Python object.
			try:
				bulb = json.loads(r.content)
			except Exception, e:
				indigo.server.log(u"Error retrieving Hue bulb status: " + str(e))
				return False
				
			# Update device states based on bulb object data.
			#   On/Off State (True/False).
			#   (It's not necessary to update the onOffState since, if brightness
			#     is greater than 0, onOffState is automatically set to On and if
			#     brightness is 0, onOffState is Off).
			#   Brightness Level (convert from 0-255 to 0-100).
			if bulb['state']['on'] == True:
				# Only update the brightness level if the bulb is actually on.
				if device.states['brightnessLevel'] != int(ceil(bulb['state']['bri']/255.0*100.0)):
					self.debugLog(u"Data from Hue hub:\n" + str(bulb))
					# Log the update.
					indigo.server.log(u"\"" + device.name + "\" updated to on at " + str(int(ceil(bulb['state']['bri']/255.0*100.0))))
					# Only update the brightness level if it's different.
					self.updateDeviceState(device, 'brightnessLevel', int(ceil(bulb['state']['bri']/255.0*100.0)))
				#   Hue Degrees (convert from 0-65535 to 0-360).
				self.updateDeviceState(device, 'hue', int(round(bulb['state']['hue']/182.0)))
				#   Saturation (convert from 0-255 to 0-100).
				self.updateDeviceState(device, 'saturation', int(ceil(bulb['state']['sat']/255.0*100)))
				#   CIE XY Cromaticity.
				self.updateDeviceState(device, 'colorX', bulb['state']['xy'][0])
				self.updateDeviceState(device, 'colorY', bulb['state']['xy'][1])
				#   Red, Green, and Blue Color.
				#     Convert from XY to RGB.
				if bulb['state']['xy'][1] == 0:
					# If the y component is zero, there's a bug in colormath that throws a
					#   ZeroDivisionError.  Work around this by setting the y component to
					#   something close to, but not quite zero.
					bulb['state']['xy'][1] = 0.00001
				xyy = xyYColor(bulb['state']['xy'][0], bulb['state']['xy'][1], bulb['state']['bri']/255.0, illuminant='a')
				rgb = xyy.convert_to('rgb', target_illuminant='a')
				#     Assign the 3 RGB values to device states. We multiply each RGB value
				#     by the brightness percentage because the above xyY conversion returns
				#     normalized RGB values (ignoring luminance in the conversion).
				self.updateDeviceState(device, 'colorRed', int(round(rgb.rgb_r * bulb['state']['bri'] / 255.0)))
				self.updateDeviceState(device, 'colorGreen', int(round(rgb.rgb_g * bulb['state']['bri'] / 255.0)))
				self.updateDeviceState(device, 'colorBlue', int(round(rgb.rgb_b * bulb['state']['bri'] / 255.0)))
				#   Color Temperature (convert from 154-500 mireds to 6494-2000 K).
				self.updateDeviceState(device, 'colorTemp', int(floor(1000000.0/bulb['state']['ct'])))
				#   Alert Status.
				self.updateDeviceState(device, 'alertMode', bulb['state']['alert'])
				#   Effect Status.
				self.updateDeviceState(device, 'effect', bulb['state']['effect'])
				#   Color Mode.
				self.updateDeviceState(device, 'colorMode', bulb['state']['colormode'])
			elif bulb['state']['on'] == False:
				# Bulb is off. Set brightness to zero.
				if device.states['brightnessLevel'] != 0:
					self.debugLog(u"Data from Hue hub:\n" + str(bulb))
					# Log the update.
					indigo.server.log(u"\"" + device.name + "\" updated to off")
					# Only if current brightness is not zero.
					self.updateDeviceState(device, 'brightnessLevel', 0)
				#   Hue Degrees (convert from 0-65535 to 0-360).
				self.updateDeviceState(device, 'hue', int(round(bulb['state']['hue']/182.0)))
				#   Saturation (convert from 0-255 to 0-100).
				self.updateDeviceState(device, 'saturation', int(ceil(bulb['state']['sat']/255.0*100)))
				#   CIE XY Cromaticity.
				self.updateDeviceState(device, 'colorX', bulb['state']['xy'][0])
				self.updateDeviceState(device, 'colorY', bulb['state']['xy'][1])
				#   Red, Green, and Blue Color.
				#     If the bulb is off, all RGB values should be 0.
				self.updateDeviceState(device, 'colorRed', 0)
				self.updateDeviceState(device, 'colorGreen', 0)
				self.updateDeviceState(device, 'colorBlue', 0)
				#   Color Temperature (convert from 154-500 mireds to 6494-2000 K).
				if bulb['state']['ct'] > 0:
					# This is to prevent divide by zero errors if the data returned is incomplete.
					self.updateDeviceState(device, 'colorTemp', int(floor(1000000.0/bulb['state']['ct'])))
				else:
					# Set the state to 0 if the value returned is 0.
					self.updateDeviceState(device, 'colorTemp', 0)
				#   Alert Status.
				self.updateDeviceState(device, 'alertMode', bulb['state']['alert'])
				#   Effect Status.
				self.updateDeviceState(device, 'effect', bulb['state']['effect'])
				#   Color Mode.
				self.updateDeviceState(device, 'colorMode', bulb['state']['colormode'])
			else:
				# Unrecognized on state, but not important enough to mention in regular log.
				self.debugLog(u"Hue bulb unrecognized on state given by hub: " + str(bulb['state']['on']))
				
			#   Save the raw bulb brightness number in the Indigo device's "savedBrightness"
			#     plugin property so that Indigo can properly represent bulb brightness when
			#     the bulb is turned on with a Turn On, Turn Off, or Toggle command.
			tempProps = device.pluginProps
			tempProps['savedBrightness'] = bulb['state']['bri']
			self.updateDeviceProps(device, tempProps)
			#   Online State.
			self.updateDeviceState(device, 'online', bulb['state']['reachable'])
			#   Bulb Name
			if bulb['name'] != device.pluginProps.get('nameOnHub', False):
				tempProps = device.pluginProps
				tempProps['nameOnHub'] = bulb['name']
				self.updateDeviceProps(device, tempProps)
	
	# Turn Bulb On or Off
	#   (not currently being used)
	########################################
	def doOnOff(self, device, onState, rampRate=-1):
		# If a rampRate wasn't specified (default of -1 assigned), use the default.
		#   (rampRate should be an integer expressing 10th of seconds, so
		#   5 = 0.5 seconds, 100 = 10 seconds, etc).
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
			except Exception, e:
				self.errorLog(u"Default ramp rate could not be obtained: " + str(e))
				rampRate = 5
		else:
			rampRate = int(round(float(rampRate) * 10))
		
		# Get the bulb's saved brightness (if it exists).
		savedBrightness = device.pluginProps.get('savedBrightness', 255)
		
		# Sanity check for an IP address
		self.ipAddress = self.pluginPrefs.get('address', None)
		if self.ipAddress is None:
			self.errorLog(u"No IP address set for the Hue hub. You can get this information from the My Settings page at http://www.meethue.com")
			return
		
		# Sanity check on bulb ID
		bulbId = device.pluginProps.get('bulbId', None)
		if bulbId is None or bulbId == 0:
			self.errorLog(u"No bulb ID selected for device \"%s\". Check settings for this bulb and select a Hue bulb to control." % (indigoDevice.name))
			return
		
		# If the requested onOffState is True (on), then return the
		#   brightness level to previously saved level.
		if onState == True:
			# If saved brightness is greater than 0, proceed. If not
			#   turn the bulb on to 100%.
			if savedBrightness > 0:
				# Create the JSON object and send the command to the hub.
				requestData = json.dumps({"on": onState, "transitiontime": rampRate})
				command = "http://%s/api/%s/lights/%s/state" % (self.ipAddress, self.pluginPrefs['hostId'], bulbId)
				self.debugLog("Sending URL request: " + command)
				try:
					r = requests.put(command, data=requestData, timeout=kTimeout)
				except requests.exceptions.Timeout:
					indigo.server.log(u"Failed to connect to the Hue hub at %s after %i seconds. - Check that the hub is connected and turned on." % (self.ipAddress, kTimeout))
					return
				except requests.exceptions.ConnectionError:
					indigo.server.log(u"Failed to connect to the Hue hub at %s. - Check that the hub is connected and turned on." % (self.ipAddress))
					return
				self.debugLog("Got response - %s" % r.content)
				# Log the change.
				indigo.server.log(u"\"" + device.name + "\" on to " + str(int(round(savedBrightness/255.0*100.0))) + " at ramp rate " + str(rampRate / 10.0) + " sec.")
				# Update the Indigo device.
				self.updateDeviceState(device, 'brightnessLevel', int(round(savedBrightness/255.0*100.0)))
			else:
				# Since the bulb can be "on" with 0 brightness, we'll need
				#   to also tell the bulb to go to 100% brightness.
				# Create the JSON object and send the command to the hub.
				requestData = json.dumps({"on": onState, "bri": 255, "transitiontime": rampRate})
				command = "http://%s/api/%s/lights/%s/state" % (self.ipAddress, self.pluginPrefs['hostId'], bulbId)
				self.debugLog("Sending URL request: " + command)
				try:
					r = requests.put(command, data=requestData, timeout=kTimeout)
				except requests.exceptions.Timeout:
					indigo.server.log(u"Failed to connect to the Hue hub at %s after %i seconds. - Check that the hub is connected and turned on." % (self.ipAddress, kTimeout))
					return
				except requests.exceptions.ConnectionError:
					indigo.server.log(u"Failed to connect to the Hue hub at %s. - Check that the hub is connected and turned on." % (self.ipAddress))
					return
				self.debugLog("Got response - %s" % r.content)
				# Log the change.
				indigo.server.log(u"\"" + device.name + "\" on to 100 at ramp rate " + str(rampRate / 10.0) + " sec.")
				# Update the Indigo device.
				self.updateDeviceState(device, 'brightnessLevel', 100)
		else:
			# Blub is being turned off.
			# Create the JSON object and send the command to the hub.
			requestData = json.dumps({"on": onState, "transitiontime": rampRate})
			command = "http://%s/api/%s/lights/%s/state" % (self.ipAddress, self.pluginPrefs['hostId'], bulbId)
			self.debugLog("Sending URL request: " + command)
			try:
				r = requests.put(command, data=requestData, timeout=kTimeout)
			except requests.exceptions.Timeout:
				indigo.server.log(u"Failed to connect to the Hue hub at %s after %i seconds. - Check that the hub is connected and turned on." % (self.ipAddress, kTimeout))
				return
			except requests.exceptions.ConnectionError:
				indigo.server.log(u"Failed to connect to the Hue hub at %s. - Check that the hub is connected and turned on." % (self.ipAddress))
				return
			self.debugLog("Got response - %s" % r.content)
			# Log the change.
			indigo.server.log(u"\"" + device.name + "\" off at ramp rate " + str(rampRate / 10) + " sec.")
			# Update the Indigo device.
			self.updateDeviceState(device, 'brightnessLevel', 0)
	
	# Set Bulb Brightness
	########################################
	def doBrightness(self, device, brightness, rampRate=-1, showLog=True):
		# NOTE that brightness is expected to be in the range of 0 to 255.
		
		# If a rampRate wasn't specified (default of -1 assigned), use the default.
		#   (rampRate should be an integer expressing 10th of seconds, so
		#   5 = 0.5 seconds, 100 = 10 seconds, etc).
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
			except Exception, e:
				self.errorLog(u"Default ramp rate could not be obtained: " + str(e))
				rampRate = 5
		else:
			rampRate = int(round(float(rampRate) * 10))

		# Sanity check for an IP address
		self.ipAddress = self.pluginPrefs.get('address', None)
		if self.ipAddress is None:
			self.errorLog(u"No IP address set for the Hue hub. You can get this information from the My Settings page at http://www.meethue.com")
			return
		
		# Sanity check on bulb ID
		bulbId = device.pluginProps.get('bulbId', None)
		if bulbId is None or bulbId == 0:
			self.errorLog(u"No bulb ID selected for device \"%s\". Check settings for this bulb and select a Hue bulb to control." % (device.name))
			return
		
		# If requested brightness is greater than 0, proceed. Otherwise, turn off the bulb.
		if brightness > 0:
			requestData = json.dumps({"bri": int(brightness), "on": True, "transitiontime": rampRate})
			command = "http://%s/api/%s/lights/%s/state" % (self.ipAddress, self.pluginPrefs['hostId'], bulbId)
			self.debugLog("Sending URL request: " + command)
			try:
				r = requests.put(command, data=requestData, timeout=kTimeout)
			except requests.exceptions.Timeout:
				indigo.server.log(u"Failed to connect to the Hue hub at %s after %i seconds. - Check that the hub is connected and turned on." % (self.ipAddress, kTimeout))
				return
			except requests.exceptions.ConnectionError:
				indigo.server.log(u"Failed to connect to the Hue hub at %s. - Check that the hub is connected and turned on." % (self.ipAddress))
				return
			self.debugLog("Got response - %s" % r.content)
			# Log the change.
			if showLog:
				indigo.server.log(message = u"\"" + device.name + "\" on to " + str(int(round(brightness/255.0*100.0))) + " at ramp rate " + str(rampRate / 10.0) + " sec.")
			# Update the device brightness (which automatically changes on state).
			self.updateDeviceState(device, 'brightnessLevel', int(round(brightness/255.0*100.0)))
		else:
			requestData = json.dumps({"on": False, "transitiontime": rampRate})
			command = "http://%s/api/%s/lights/%s/state" % (self.ipAddress, self.pluginPrefs['hostId'], bulbId)
			self.debugLog("Sending URL request: " + command)
			try:
				r = requests.put(command, data=requestData, timeout=kTimeout)
			except requests.exceptions.Timeout:
				indigo.server.log(u"Failed to connect to the Hue hub at %s after %i seconds. - Check that the hub is connected and turned on." % (self.ipAddress, kTimeout))
				return
			except requests.exceptions.ConnectionError:
				indigo.server.log(u"Failed to connect to the Hue hub at %s. - Check that the hub is connected and turned on." % (self.ipAddress))
				return
			self.debugLog("Got response - %s" % r.content)
			# Log the change.
			if showLog:
				indigo.server.log(u"\"" + device.name + "\" off at ramp rate " + str(rampRate / 10.0) + " sec.")
			# Update the device brightness (which automatically changes on state).
			self.updateDeviceState(device, 'brightnessLevel', 0)
	
	# Set RGB Levels
	########################################
	def doRGB(self, device, red, green, blue, rampRate=-1):
		# If a rampRate wasn't specified (default of -1 assigned), use the default.
		#   (rampRate should be an integer expressing 10th of seconds, so
		#   5 = 0.5 seconds, 100 = 10 seconds, etc).
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
			except Exception, e:
				self.errorLog(u"Default ramp rate could not be obtained: " + str(e))
				rampRate = 5
		else:
			rampRate = int(round(float(rampRate) * 10))
		
		# Sanity check for an IP address
		self.ipAddress = self.pluginPrefs.get('address', None)
		if self.ipAddress is None:
			self.errorLog(u"No IP address set for the Hue hub. You can get this information from the My Settings page at http://www.meethue.com")
			return
		
		# Sanity check on bulb ID
		bulbId = device.pluginProps.get('bulbId', None)
		if bulbId is None or bulbId == 0:
			self.errorLog(u"No bulb ID selected for device \"%s\". Check settings for this bulb and select a Hue bulb to control." % (device.name))
			return
		
		# Convert the linear RGB to xyY.
		rgb = RGBColor(red, green, blue)
		xyy = rgb.convert_to('xyy', target_illuminant='a')
		# target_illuminant "a" = incandescent
		# xyy.xyy_x is the x chromaticity.
		# xyy.xyy_y is the y chromaticity.
		# xyy.xyy_Y is the z chrimaticity (ignored).
		
		# Determine the brightness based on the highest RGB value.
		#   This is a crude method, but using the Y component from
		#   the conversion above results in brightness values lower
		#   than what the bulb is capable of.
		brightness = red
		if blue > brightness:
			brightness = blue
		elif green > brightness:
			brightness = green
		
		# Send to Hue (Create JSON request based on whether brightness is zero or not).
		if brightness > 0:
			requestData = json.dumps({"bri": brightness, "xy": [xyy.xyy_x, xyy.xyy_y], "transitiontime": int(rampRate), "on": True})
		else:
			# We create a separate command for when brightness is 0 (or below) because if
			#   the "on" state in the request was True, the Hue light wouldn't turn off.
			#   We also explicity state the X and Y values (equivilant to RGB of 1, 1, 1)
			#   because the xyy object contains invalid "NaN" values when all RGB values are 0.
			requestData = json.dumps({"bri": 0, "xy": [0.4473, 0.4073], "transitiontime": int(rampRate), "on": False})
		command = "http://%s/api/%s/lights/%s/state" % (self.ipAddress, self.pluginPrefs['hostId'], bulbId)
		self.debugLog(u"Data: " + str(requestData) + ", URL: " + command)
		try:
			r = requests.put(command, data=requestData, timeout=kTimeout)
		except requests.exceptions.Timeout:
			indigo.server.log(u"Failed to connect to the Hue hub at %s after %i seconds. - Check that the hub is connected and turned on." % (self.ipAddress, kTimeout))
			return
		except requests.exceptions.ConnectionError:
			indigo.server.log(u"Failed to connect to the Hue hub at %s. - Check that the hub is connected and turned on." % (self.ipAddress))
			return
		self.debugLog("Got response - %s" % r.content)
		
		# Update on Indigo
		if brightness > 0:
			# Convert brightness to a percentage.
			brightness = int(round(brightness / 255.0 * 100.0))
			# Log the change.
			indigo.server.log(u"\"" + device.name + "\" on to " + str(brightness) + " with RGB values " + str(red) + ", " + str(green) + " and " + str(blue) + " at ramp rate " + str(rampRate / 10.0) + " sec.")
			# Update the device state.
			self.updateDeviceState(device, 'brightnessLevel', brightness)
		else:
			# Log the change.
			indigo.server.log(u"\"" + device.name + "\" off at ramp rate " + str(rampRate / 10.0) + " sec.")
			# Update the device state.
			self.updateDeviceState(device, 'brightnessLevel', 0)
		# Update the other device states.
		self.updateDeviceState(device, 'colorMode', "xy")
		self.updateDeviceState(device, 'colorX', round(xyy.xyy_x, 4))
		self.updateDeviceState(device, 'colorY', round(xyy.xyy_y, 4))
		# We don't set the colorRed, colorGreen, and colorBlue states
		#   because the Hue bulb is not capable of the full RGB color
		#   gamut and when the Hue hub updates the xy values to reflect
		#   actual displayed light, the interpreted RGB values will not
		#   match the values entered by the user in the Action dialog.
		
	# Set Hue, Saturation and Brightness
	########################################
	def doHSB(self, device, hue, saturation, brightness, rampRate=-1):
		# If a rampRate wasn't specified (default of -1 assigned), use the default.
		#   (rampRate should be an integer expressing 10th of seconds, so
		#   5 = 0.5 seconds, 100 = 10 seconds, etc).
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
			except Exception, e:
				self.errorLog(u"Default ramp rate could not be obtained: " + str(e))
				rampRate = 5
		else:
			rampRate = int(round(float(rampRate) * 10))
		
		# Sanity check for an IP address
		self.ipAddress = self.pluginPrefs.get('address', None)
		if self.ipAddress is None:
			self.errorLog(u"No IP address set for the Hue hub. You can get this information from the My Settings page at http://www.meethue.com")
			return
		
		# Sanity check on bulb ID
		bulbId = device.pluginProps.get('bulbId', None)
		if bulbId is None or bulbId == 0:
			self.errorLog(u"No bulb ID selected for device \"%s\". Check settings for this bulb and select a Hue bulb to control." % (device.name))
			return
		
		# Submit to Hue
		requestData = json.dumps({"bri":brightness, "hue": hue, "sat": saturation, "on":True, "transitiontime": rampRate})
		command = "http://%s/api/%s/lights/%s/state" % (self.ipAddress, self.pluginPrefs['hostId'], bulbId)
		self.debugLog(u"Request is %s" % requestData)
		try:
			r = requests.put(command, data=requestData, timeout=kTimeout)
		except requests.exceptions.Timeout:
			indigo.server.log(u"Failed to connect to the Hue hub at %s after %i seconds. - Check that the hub is connected and turned on." % (self.ipAddress, kTimeout))
			return
		except requests.exceptions.ConnectionError:
			indigo.server.log(u"Failed to connect to the Hue hub at %s. - Check that the hub is connected and turned on." % (self.ipAddress))
			return
		self.debugLog("Got response - %s" % r.content)
		
		# Update on Indigo
		if int(ceil(brightness/255.0*100.0)) > 0:
			# Log the change.
			indigo.server.log(u"\"" + device.name + u"\" on to " + str(int(round(brightness / 255.0 * 100.0))) + u" with hue " + str(int(round(hue / 182.0))) + u"° saturation " + str(int(saturation / 255.0 * 100.0)) + u"% at ramp rate " + str(rampRate / 10.0) + u" sec.")
			# Change the Indigo device.
			self.updateDeviceState(device, 'brightnessLevel', int(round(brightness/255.0*100.0)))
		else:
			# Log the change.
			indigo.server.log(u"\"" + device.name + "\" off at ramp rate " + str(rampRate / 10.0) + " sec.")
			# Change the Indigo device.
			self.updateDeviceState(device, 'brightnessLevel', 0)
		# Update the other device states.
		self.updateDeviceState(device, 'colorMode', "hs")
		self.updateDeviceState(device, 'hue', hue)
		self.updateDeviceState(device, 'saturation', saturation)
		
	# Set Color Temperature
	########################################
	def doColorTemperature(self, device, temperature, brightness, rampRate=-1):
		# If a rampRate wasn't specified (default of -1 assigned), use the default.
		#   (rampRate should be an integer expressing 10th of seconds, so
		#   5 = 0.5 seconds, 100 = 10 seconds, etc).
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
			except Exception, e:
				self.errorLog(u"Default ramp rate could not be obtained: " + str(e))
				rampRate = 5
		else:
			rampRate = int(round(float(rampRate) * 10))
		
		# Convert temperature from K to mireds.
		temperature = int(floor(1000000.0 / temperature))
		
		# Sanity check for an IP address
		self.ipAddress = self.pluginPrefs.get('address', None)
		if self.ipAddress is None:
			self.errorLog(u"No IP address set for the Hue hub. You can get this information from the My Settings page at http://www.meethue.com")
			return
		
		# Sanity check on bulb ID
		bulbId = device.pluginProps.get('bulbId', None)
		if bulbId is None or bulbId == 0:
			self.errorLog(u"No bulb ID selected for device \"%s\". Check settings for this bulb and select a Hue bulb to control." % (device.name))
			return
		
		# Submit to Hue
		requestData = json.dumps({"bri":brightness, "ct": temperature, "on":True, "transitiontime": int(rampRate)})
		command = "http://%s/api/%s/lights/%s/state" % (self.ipAddress, self.pluginPrefs['hostId'], bulbId)
		self.debugLog(u"Request is %s" % requestData)
		try:
			r = requests.put(command, data=requestData, timeout=kTimeout)
		except requests.exceptions.Timeout:
			indigo.server.log(u"Failed to connect to the Hue hub at %s after %i seconds. - Check that the hub is connected and turned on." % (self.ipAddress, kTimeout))
			return
		except requests.exceptions.ConnectionError:
			indigo.server.log(u"Failed to connect to the Hue hub at %s. - Check that the hub is connected and turned on." % (self.ipAddress))
			return
		self.debugLog("Got response - %s" % r.content)
		
		# Update on Indigo
		if int(ceil(brightness/255.0*100.0)) > 0:
			# Log the change.
			indigo.server.log(u"\"" + device.name + "\" on to " + str(int(round(brightness / 255.0 * 100.0))) + " using color temperature " + str(int(floor(1000000.0 / temperature))) + " K at ramp rate " + str(rampRate / 10.0) + " sec.")
			self.updateDeviceState(device, 'brightnessLevel', int(round(brightness / 255.0 * 100.0)))
		else:
			# Log the change.
			indigo.server.log(u"\"" + device.name + "\" off at ramp rate " + str(rampRate / 10.0) + " sec.")
			self.updateDeviceState(device, 'brightnessLevel', 0)
		# Update the other device states as well.
		self.updateDeviceState(device, 'colorMode', "ct")
		self.updateDeviceState(device, 'colorTemp', temperature)
	
	# Start Alert (Blinking)
	########################################
	def doAlert(self, device, alertType="lselect"):
		
		# Sanity check for an IP address
		self.ipAddress = self.pluginPrefs.get('address', None)
		if self.ipAddress is None:
			self.errorLog(u"No IP address set for the Hue hub. You can get this information from the My Settings page at http://www.meethue.com")
			return
		
		# Sanity check on bulb ID
		bulbId = device.pluginProps.get('bulbId', None)
		if bulbId is None or bulbId == 0:
			self.errorLog(u"No bulb ID selected for device \"%s\". Check settings for this bulb and select a Hue bulb to control." % (device.name))
			return
		
		command = "http://%s/api/%s/lights/%s/state" % (self.ipAddress, self.pluginPrefs['hostId'], bulbId)
		requestData = json.dumps({"alert": alertType})
		try:
			r = requests.put(command, data=requestData, timeout=kTimeout)
		except requests.exceptions.Timeout:
			indigo.server.log(u"Failed to connect to the Hue hub at %s after %i seconds. - Check that the hub is connected and turned on." % (self.ipAddress, kTimeout))
			return
		except requests.exceptions.ConnectionError:
			indigo.server.log(u"Failed to connect to the Hue hub at %s. - Check that the hub is connected and turned on." % (self.ipAddress))
			return
		self.debugLog("Got response - %s" % r.content)
		
		# Log the change.
		if alertType == "select":
			indigo.server.log(u"\"" + device.name + "\" start short alert blink.")
		elif alertType == "lselect":
			indigo.server.log(u"\"" + device.name + "\" start long alert blink.")
		elif alertType == "none":
			indigo.server.log(u"\"" + device.name + "\" stop alert blink.")
		# Update the device state.
		self.updateDeviceState(device, 'alertMode', alertType)
			
	# Set Effect Status
	#   (not currently being used)
	########################################
	def doEffect(self, device, effect):
		# Sanity check for an IP address
		self.ipAddress = self.pluginPrefs.get('address', None)
		if self.ipAddress is None:
			self.errorLog(u"No IP address set for the Hue hub. You can get this information from the My Settings page at http://www.meethue.com")
			return
		
		# Sanity check on bulb ID
		bulbId = device.pluginProps.get('bulbId', None)
		if bulbId is None or bulbId == 0:
			self.errorLog(u"No bulb ID selected for device \"%s\". Check settings for this bulb and select a Hue bulb to control." % (device.name))
			return
		
		# Submit to Hue
		requestData = json.dumps({"effect": effect})
		indigo.server.log(u"Request is %s" % requestData)
		command = "http://%s/api/%s/lights/%s/state" % (self.ipAddress, self.pluginPrefs['hostId'], bulbId)
		indigo.server.log(u"URL: " + command)
		try:
			r = requests.put(command, data=requestData, timeout=kTimeout)
		except requests.exceptions.Timeout:
			indigo.server.log(u"Failed to connect to the Hue hub at %s after %i seconds. - Check that the hub is connected and turned on." % (self.ipAddress, kTimeout))
			return
		except requests.exceptions.ConnectionError:
			indigo.server.log(u"Failed to connect to the Hue hub at %s. - Check that the hub is connected and turned on." % (self.ipAddress))
			return
		indigo.server.log(u"Got response - %s" % r.content)
		
		# Log the change.
		indigo.server.log(u"\"" + device.name + "\" set effect \"" + effect + "\"")
		# Update the device state.
		self.updateDeviceState(device, 'effect', effect)
	
	# Update Lights List
	########################################
	def updateLightsList(self):
		# Sanity check for an IP address
		self.ipAddress = self.pluginPrefs.get('address', None)
		if self.ipAddress is None:
			self.errorLog(u"No IP address set for the Hue hub. You can get this information from the My Settings page at http://www.meethue.com")
			return
		
		# Force a timeout
		socket.setdefaulttimeout(kTimeout)
		
		try:
			# Parse the response
			command = "http://%s/api/%s/lights" % (self.ipAddress, self.pluginPrefs.get('hostId', "ERROR"))
			r = requests.get(command, timeout=kTimeout, timeout=kTimeout)
			lightsListResponseData = json.loads(r.content)
			self.debugLog(u"Got response %s" % lightsListResponseData)
			
			# We should have a dictionary. If so, it's a light list
			if isinstance(lightsListResponseData, dict):
				self.debugLog(u"Loaded lights list - %s" % (lightsListResponseData))
				self.lightsDict = lightsListResponseData
				indigo.server.log(u"Loaded %i bulb(s)" % len(self.lightsDict))
				
			elif isinstance(lightsListResponseData, list):
				# Get the first item
				firstResponseItem = lightsListResponseData[0]
				
				# Did we get an error?
				errorDict = firstResponseItem.get('error', None)
				if errorDict is not None:
					
					errorCode = errorDict.get('type', None)
					
					# Is this a link button not pressed error?
					if errorCode == 1:
						self.errorLog(u"Not paired with Hue. Press the middle button on the Hue hub, then press the Start/Finish button in the Plugin Settings (Plugins menu)")
						self.paired = False
						
					else:
						self.errorLog(u"Error #%i from Hue Hub when loading available bulbs. Description is \"%s\"" % (errorCode, errorDict.get('description', "(no description")))
						self.paired = False
					
				else:
					indigo.server.log(u"Unexpected response from Hue (%s) when loading available bulbs!" % (lightsListResponseData))
					
			else:
				indigo.server.log(u"Unexpected response from Hue (%s) when loading available bulbs!" % (lightsListResponseData))
			
		except requests.exceptions.Timeout:
			self.errorLog(u"Failed to load light list from the Hue hub at %s after %i seconds - check settings and retry." % (self.ipAddress, kTimeout))
			
		except requests.exceptions.ConnectionError:
			indigo.server.log(u"Failed to connect to the Hue hub at %s. - Check that the hub is connected and turned on." % (self.ipAddress))
			return
			
		except Exception, e:
			self.errorLog(u"Unable to obtain list of Hue lights from hub. " + str(e))
	
	
	########################################
	# Hue Hub Registration Methods
	########################################

	# Update Registration State
	########################################
	def updateRegistrationState(self):
		# Sanity check for an IP address
		self.ipAddress = self.pluginPrefs.get("address", None)
		if self.ipAddress is None:
			indigo.server.log(u"No IP address set for the Hue hub. You can get this information from the My Settings page at http://www.meethue.com", isError=True)
			pass
		
		# Configure timeout
		socket.setdefaulttimeout(kTimeout)
		
		# Request login state
		try:
			indigo.server.log(u"Checking with the Hue hub at %s for pairing state..." % (self.ipAddress))
			requestData = json.dumps({"username": self.pluginPrefs.get('hostId', None), "devicetype": "Indigo Hue Plugin"})
			self.debugLog(u"Request is %s" % requestData)
			command = "http://%s/api" % (self.ipAddress)
			r = requests.post(command, data=requestData, timeout=kTimeout)
			responseData = json.loads(r.content)
			self.debugLog(u"Got response %s" % responseData)

			# We should have a single response item
			if len(responseData) == 1:
				# Get the first item
				firstResponseItem = responseData[0]
				
				# Did we get an error?
				errorDict = firstResponseItem.get('error', None)
				if errorDict is not None:
					errorCode = errorDict.get('type', None)
					
					# Is this a link button not pressed error?
					if errorCode == 101:
						self.errorLog(u"Could not pair with Hue. Press the middle button on the Hue hub, then press the Retry Pairing button in Plugin Settings")
						self.paired = False
						
					else:
						self.errorLog(u"Error #%i from Hue Hub when checking pairing. Description is \"%s\"" % (errorCode, errorDict.get("description", "(No Description")))
						self.paired = False
					
				# Were we successful?
				successDict = firstResponseItem.get('success', None)
				if successDict is not None:
					indigo.server.log(u"Connected to Hue hub successfully.")
					self.paired = True
				
			else:
				self.errorLog(u"Invalid response from Hue. Check the IP address and try again.")
				
		except requests.exceptions.Timeout:
			self.errorLog(u"Failed to connect to Hue hub at %s after %i seconds - check the IP address and try again." % (self.ipAddress, kTimeout))
		except requests.exceptions.ConnectionError:
			indigo.server.log(u"Failed to connect to the Hue hub at %s. - Check that the hub is connected and turned on." % (self.ipAddress))
			return

	# Restart Pairing with Hue Hub
	########################################
	def restartPairing(self, valuesDict):
		if not self.paired:
			self.updateRegistrationState()
		else:
			self.errorLog(u"Already paired. No need to update registration")

	# Bulb List Generator
	########################################
	def bulbListGenerator(self, filter="", valuesDict=None, typeId="", targetId=0):
		returnBulbList = list()
		
		# Iterate over our bulbs, and return the available list in Indigo's format
		for bulbId, bulbDetails in self.lightsDict.items():
			returnBulbList.append([bulbId, bulbDetails["name"]])
			
		# Debug
		self.debugLog(u"Return bulb list is %s" % returnBulbList)
		
		return returnBulbList
	
	
	########################################
	# Indigo UI Control Methods
	########################################
	
	# Dimmer/Relay Control Actions
	########################################
	def actionControlDimmerRelay(self, action, device):
		try:
			self.debugLog("actionControlDimmerRelay called for device " + device.name + ". action: " + str(action) + "\n\ndevice: " + str(device))
		except Exception, e:
			self.debugLog("actionControlDimmerRelay called for device " + device.name + ". (Unable to display action or device data due to error: " + str(e) + ")")
		# Get the current brightness and on-state of the device.
		currentBrightness = device.states['brightnessLevel']
		currentOnState = device.states['onOffState']
		# Get key variables
		command = action.deviceAction
		bulbId = device.pluginProps.get('bulbId', None)
		hostId = self.pluginPrefs.get('hostId', None)
		self.ipAddress = self.pluginPrefs.get('address', None)
		self.debugLog("Command is %s, Bulb is %s" % (command, bulbId))
		
		##### TURN ON #####
		if command == indigo.kDeviceAction.TurnOn:
			try:
				self.debugLog("device on:\n%s" % action)
			except Exception, e:
				self.debugLog("device on: (Unable to display action data due to error: " + str(e) + ")")
			# Turn it on by setting the brightness to maximum.
			self.doBrightness(device, 255)
			
		##### TURN OFF #####
		elif command == indigo.kDeviceAction.TurnOff:
			try:
				self.debugLog("device off:\n%s" % action)
			except Exception, e:
				self.debugLog("device off: (Unable to display action data due to error: " + str(e) + ")")
			# Turn it off by setting the brightness to minimum.
			self.doBrightness(device, 0)

		##### TOGGLE #####
		elif command == indigo.kDeviceAction.Toggle:
			try:
				self.debugLog("device toggle:\n%s" % action)
			except Exception, e:
				self.debugLog("device toggle: (Unable to display action due to error: " + str(e) + ")")
			if currentOnState == True:
				# It's on. Turn it off by setting the brightness to minimum.
				self.doBrightness(device, 0)
			else:
				# It's off. Turn it on by setting the brightness to maximum.
				self.doBrightness(device, 255)
		
		##### SET BRIGHTNESS #####
		elif command == indigo.kDeviceAction.SetBrightness:
			try:
				self.debugLog("device set brightness:\n%s" % action)
			except Exception, e:
				self.debugLog("device set brightness: (Unable to display action data due to error: " + str(e) + ")")
			brightnessLevel = int(floor(action.actionValue / 100.0 * 255.0))
			# Save the new brightness level into the device properties.
			tempProps = device.pluginProps
			tempProps['savedBrightness'] = brightnessLevel
			self.updateDeviceProps(device, tempProps)
			# Set the new brightness level on the bulb.
			self.doBrightness(device, brightnessLevel)

		##### BRIGHTEN BY #####
		elif command == indigo.kDeviceAction.BrightenBy:
			try:
				self.debugLog("device increase brightness by:\n%s" % action)
			except Exception, e:
				self.debugLog("device increase brightness by: (Unable to display action data due to error: " + str(e) + ")")
			brightnessLevel = currentBrightness + action.actionValue
			if brightnessLevel > 100:
				brightnessLevel = 100
			# Save the new brightness level into the device properties.
			tempProps = device.pluginProps
			tempProps['savedBrightness'] = int(floor(brightnessLevel / 100.0 * 255.0))
			self.updateDeviceProps(device, tempProps)
			# Set the new brightness level on the bulb.
			self.doBrightness(device, int(floor(brightnessLevel / 100.0 * 255.0)))
			
		##### DIM BY #####
		elif command == indigo.kDeviceAction.DimBy:
			try:
				self.debugLog("device decrease brightness by:\n%s" % action)
			except Exception, e:
				self.debugLog("device decrease brightness by: (Unable to display action data due to error: " + str(e) + ")")
			brightnessLevel = currentBrightness - action.actionValue
			if brightnessLevel < 0:
				brightnessLevel = 0
			# Save the new brightness level into the device properties.
			tempProps = device.pluginProps
			tempProps['savedBrightness'] = int(floor(brightnessLevel / 100.0 * 255.0))
			self.updateDeviceProps(device, tempProps)
			# Set the new brightness level on the bulb.
			self.doBrightness(device, int(floor(brightnessLevel / 100.0 * 255.0)))
			
		##### REQUEST STATUS #####
		elif command == indigo.kDeviceAction.RequestStatus:
			try:
				self.debugLog("device request status:\n%s" % action)
			except Exception, e:
				self.debugLog("device request status: (Unable to display action data due to error: " + str(e) + ")")
			self.getBulbStatus(device.id)
			# Log the new brightnss.
			indigo.server.log(u"\"" + device.name + "\" status request (received: " + str(device.states['brightnessLevel']) + ")")

		#### CATCH ALL #####
		else:
			indigo.server.log(u"Unhandled Hue bulb command \"%s\"" % (command))
		pass
	
	
	########################################
	# Action Handling Methods
	########################################
	
	# Start/Stop Brightening
	########################################
	def startStopBrightening(self, action, device):
		self.debugLog(u"startStopBrightening: device: " + device.name + ", action:\n" + str(action))
		# Make sure the device is in the deviceList.
		if device.id in self.deviceList:
			
			# First, remove from the dimmingList if it's there.
			if device.id in self.dimmingList:
				# Log the event to Indigo log.
				indigo.server.log(u"\"" + device.name + "\" stop dimming")
				# Remove from list.
				self.dimmingList.remove(device.id)
				
			# Now remove from brighteningList if it's in the list and add if not.
			if device.id in self.brighteningList:
				# Log the event to Indigo log.
				indigo.server.log(u"\"" + device.name + "\" stop brightening")
				# Remove from list.
				self.brighteningList.remove(device.id)
				# Get the bulb status
				self.getBulbStatus(device.id)
				# Log the new brightnss.
				indigo.server.log(u"\"" + device.name + "\" status request (received: " + str(device.states['brightnessLevel']) + ")")
			else:
				# Only begin brightening if current brightness is less than 100%.
				if device.states['brightnessLevel'] < 100:
					# Log the event in Indigo log.
					indigo.server.log(u"\"" + device.name + "\" start brightening")
					# Add to list.
					self.brighteningList.append(device.id)
				
		return
		
	# Start/Stop Dimming
	########################################
	def startStopDimming(self, action, device):
		self.debugLog(u"startStopDimming: device: " + device.name + ", action:\n" + str(action))
		# Make sure the device is in the deviceList.
		if device.id in self.deviceList:
			# First, remove from brighteningList if it's there.
			if device.id in self.brighteningList:
				# Log the event to Indigo log.
				indigo.server.log(u"\"" + device.name + "\" stop brightening")
				# Remove from list.
				self.brighteningList.remove(device.id)
				
			# Now remove from dimmingList if it's in the list and add if not.
			if device.id in self.dimmingList:
				# Log the event to Indigo log.
				indigo.server.log(u"\"" + device.name + "\" stop dimming")
				# Remove from list.
				self.dimmingList.remove(device.id)
				# Get the bulb status
				self.getBulbStatus(device.id)
				# Log the new brightnss.
				indigo.server.log(u"\"" + device.name + "\" status request (received: " + str(device.states['brightnessLevel']) + ")")
			else:
				# Only begin dimming if current brightness is greater than 0%.
				if device.states['brightnessLevel'] > 0:
					# Log the event in Indigo log.
					indigo.server.log(u"\"" + device.name + "\" start dimming")
					# Add to list.
					self.dimmingList.append(device.id)

		return
	
	# Set Brightness
	########################################
	def setBrightness(self, action, device):
		self.debugLog(u"setBrightness: device: " + device.name + ", action:\n" + str(action))
		
		brightnessSource = action.props.get('brightnessSource', False)
		brightness = action.props.get('brightness', False)
		brightnessVarId = action.props.get('brightnessVariable', False)
		brightnessDevId = action.props.get('brightnessDevice', False)
		useRateVariable = action.props.get('useRateVariable', False)
		rate = action.props.get('rate', False)
		rateVarId = action.props.get('rateVariable', False)
		delay = action.props.get('delay', False)
		retries = action.props.get('retries', False)
		
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
				self.errorLog(u"No brightness source information was provided.")
				return None
		
		if brightnessSource == "custom":
			if brightness == False and brightness.__class__ != int:
				self.errorLog(u"No brightness level was specified.")
				return None
			else:
				try:
					brightness = int(brightness)
					if brightness < 0 or brightness > 100:
						self.errorLog(u"Brightness level " + str(brightness) + " is outside the acceptable range of 0 to 100.")
						return None
				except ValueError:
					self.errorLog(u"Brightness level \"" + str(brightness) + "\" is invalid. Brightness values can only contain numbers.")
					return None
			self.debugLog("Brightness (source: custom): " + str(brightness) + ", class: " + str(brightness.__class__))
		
		elif brightnessSource == "variable":
			if not brightnessVarId:
				self.errorLog(u"No variable containing the brightness level was specified.")
				return None
			else:
				try:
					brightnessVar = indigo.variables[int(brightnessVarId)]
					# Embedding float method inside int method allows for fractional
					#   data but just drops everything after the decimal.
					brightness = int(float(brightnessVar.value))
					if brightness < 0 or brightness > 100:
						self.errorLog(u"Brightness level " + str(brightness) + " found in variable \"" + brightnessVar.name + "\" is outside the acceptable range of 0 to 100.")
						return None
				except ValueError:
					self.errorLog(u"Brightness level \"" + str(brightnessVar.value) + "\" found in variable \"" + brightnessVar.name + "\" is invalid. Brightness values can only contain numbers.")
					return None
				except IndexError:
					self.errorLog(u"The specified variable (ID " + str(brightnessVarId) + ") does not exist in the Indigo database.")
					return None
			self.debugLog("Brightness (source: variable): " + str(brightness) + ", class: " + str(brightness.__class__))
		
		elif brightnessSource == "dimmer":
			if not brightnessDevId:
				self.errorLog(u"No dimmer was specified as the brightness level source.")
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
						self.errorLog(u"No device with the name \"" + str(brightnessDevId) + "\" could be found in the Indigo database.")
						return None
				try:
					brightnessDev = indigo.devices[brightnessDevId]
					brightness = int(brightnessDev.states.get('brightnessLevel', None))
					if brightness == None:
						# Looks like this isn't a dimmer after all.
						self.errorLog(u"Device \"" + brightnessDev.name + "\" does not appear to be a dimmer. Only dimmers can be used as brightness sources.")
						return None
					elif brightness < 0 or brightness > 100:
						self.errorLog(u"Brightness level " + str(brightness) + " of device \"" + brightnessDev.name + "\" is outside the acceptable range of 0 to 100.")
						return None
				except ValueError:
					self.errorLog(u"The device \"" + brightnessDev.name + "\" does not have a brightness level. Please ensure that the device is a dimmer.")
					return None
				except KeyError:
					self.errorLog(u"The specified device (ID " + str(brightnessDevId) + ") does not exist in the Indigo database.")
					return None
			self.debugLog("Brightness (source: other dimmer): " + str(brightness) + ", class: " + str(brightness.__class__))
		
		else:
			self.errorLog(u"Unrecognized brightness source \"" + str(brightnessSource) + u"\". Valid brightness sources are \"custom\", \"variable\", and \"dimmer\".")
			return None
		
		if not useRateVariable:
			if not rate and rate.__class__ == bool:
				self.errorLog(u"No ramp rate was specified.")
				return None
			else:
				try:
					rate = float(rate)
					if rate < 0 or rate > 540:
						self.errorLog(u"Ramp rate value " + str(rate) + " is outside the acceptible range of 0 to 540.")
						return None
				except ValueError:
					self.errorLog(u"Ramp rate value \"" + str(rate) + " is an invalid value. Ramp rate values can only contain numbers.")
					return None
			self.debugLog("Rate: " + str(rate))
		
		else:
			if not rateVarId:
				self.errorLog(u"No variable containing the ramp rate time was specified.")
				return None
			else:
				try:
					# Make sure rate is set to ""
					rate = ""
					rateVar = indigo.variables[int(rateVarId)]
					rate = float(rateVar.value)
					if rate < 0 or rate > 540:
						self.errorLog(u"Ramp rate value \"" + str(rate) + "\" found in variable \"" + rateVar.name + "\" is outside the acceptible range of 0 to 540.")
						return None
				except ValueError:
					self.errorLog(u"Ramp rate value \"" + str(rate) + "\" found in variable \"" + rateVar.name + "\" is an invalid value. Ramp rate values can only contain numbers.")
					return None
				except IndexError:
					self.errorLog(u"The specified variable (ID " + str(brightnessVarId) + ") does not exist in the Indigo database.")
			self.debugLog("Rate: " + str(rate))
		
		# Send the command.
		self.doBrightness(device, int(round(brightness / 100.0 * 255.0)), rate)
		
	# Set RGB Level Action
	########################################
	def setRGB(self, action, device):
		self.debugLog(u"setRGB: device: " + device.name + ", action:\n" + str(action))
		try:
			red = int(action.props.get('red', 0))
		except ValueError:
			self.errorLog(u"Red color value specified for \"" + device.name + u"\" is invalid.")
			return
			
		try:
			green = int(action.props.get('green', 0))
		except ValueError:
			self.errorLog(u"Green color value specified for \"" + device.name + u"\" is invalid.")
			return
			
		try:
			blue = int(action.props.get('blue', 0))
		except ValueError:
			self.errorLog(u"Blue color value specified for \"" + device.name + u"\" is invalid.")
			return
			
		try:
			rampRate = action.props.get('rate', -1)
			if rampRate != "":
				rampRate = float(rampRate)
			else:
				rampRate = device.pluginProps.get('rate', 0.5)
		except ValueError:
			self.errorLog(u"Ramp Rate value specified for \"" + device.name +u"\" is invalid.")
			return
			
		self.doRGB(device, red, green, blue, rampRate)
		
	# Set HSB Action
	########################################
	def setHSB(self, action, device):
		self.debugLog(u"setHSB: device: " + device.name + ", action:\n" + str(action))
		try:
			hue = float(action.props.get('hue', 0))
		except ValueError:
			# The float() cast above might fail if the user didn't enter a number:
			self.errorLog(u"Set Hue, Saturation, Brightness for device \"%s\" -- invalid hue value (must range 0-360)" % (device.name,))
			return
			
		try:
			saturation = int(action.props.get('saturation', 0))
		except ValueError:
			# The int() cast above might fail if the user didn't enter a number:
			self.errorLog(u"Set Hue, Saturation, Brightness for device \"%s\" -- invalid saturation value (must range 0-100)" % (device.name,))
			return
			
		try:
			brightness = int(action.props.get('brightness', 100))
		except ValueError:
			# The int() cast above might fail if the user didn't enter a number:
			self.errorLog(u"Set Hue, Saturation, Brightness for device \"%s\" -- invalid brightness percentage (must range 0-100)" % (device.name,))
			return
		
		try:
			rampRate = action.props.get('rate', -1)
			if rampRate != "":
				rampRate = float(rampRate)
			else:
				rampRate = device.pluginProps.get('rate', 0.5)
		except ValueError:
			self.errorLog(u"Ramp Rate value specified for \"" + device.name +u"\" is invalid.")
			return
			
		# Scale these values to match Hue
		brightness = int(round((float(brightness)/100.0) * 255.0))
		saturation = int(floor((float(saturation)/100.0) * 255.0))
		hue = int(floor(hue*182.0))
		
		self.doHSB(device, hue, saturation, brightness, rampRate)
		
	# Set Color Temperature Action
	########################################
	def setColorTemperature(self, action, device):
		self.debugLog(u"setColorTemperature: device: " + device.name + ", action:\n" + str(action))
		preset = action.props.get('preset', "relax")
		try:
			temperature = int(action.props.get('temperature', 2800))
		except ValueError:
			# The int() cast above might fail if the user didn't enter a number:
			self.errorLog(u"Set Color Temperature for device \"%s\" -- invalid color temperature (must range 2000-6500)" % (device.name,))
			return
		
		if preset == "custom":
			brightness = action.props.get('brightness', False)
			if brightness:
				try:
					brightness = int(brightness)
					brightness = int(ceil(brightness / 100.0 * 255.0))
				except ValueError:
					self.errorLog(u"Set Color Temperature for device \"%s\" -- invalid brightness (must be in the range 0-100)" % (device.name,))
			else:
				brightness = int(ceil(device.states['brightnessLevel'] / 100.0 * 255.0))
				
		try:
			rampRate = action.props.get('rate', -1)
			if rampRate != "":
				rampRate = float(rampRate)
			else:
				rampRate = device.pluginProps.get('rate', 0.5)
		except ValueError:
			self.errorLog(u"Ramp Rate value specified for \"" + device.name +u"\" is invalid.")
			return
			
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
			
		self.doColorTemperature(device, temperature, brightness, rampRate)
		
	# Set Single Alert Action
	########################################
	def alertOnce(self, action, device):
		self.debugLog(u"alertOnce: device: " + device.name + ", action:\n" + str(action))
		self.doAlert(device, "select")
		
	# Set Long Alert Action
	########################################
	def longAlert(self, action, device):
		self.debugLog(u"longAlert: device: " + device.name + ", action:\n" + str(action))
		self.doAlert(device, "lselect")
		
	# Stop Alert Action
	########################################
	def stopAlert(self, action, device):
		self.debugLog(u"stopAlert: device: " + device.name + ", action:\n" + str(action))
		self.doAlert(device, "none")
	
	# Set Effect (Test) Action
	########################################
	def effect(self, action, device):
		effect = action.props.get('effect', False)
		if not effect:
			self.errorLog(u"No effect text provided to try.")
			return
			
		self.doEffect(device, effect)
		
