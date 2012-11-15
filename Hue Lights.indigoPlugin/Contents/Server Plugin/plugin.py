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
#	Version 0.9
#
#	History:	0.9 (13-Nov-2012) (Version Number Reset)
#				* Initial Nathan Sheldon branch beta release.
#				* This version removes the use of ColorPy from Alistair's
#				  version and all attempts to faithfully reproduce
#				  true red, green and blue colors, were abandoned
#				  as the Hue is not capable of that high of a color
#				  gamut coverage.  RGB levels, if used, are now
#				  converted to HSB values using included libraries
#				  instead of xyY values using ColorPy libraries.
#
################################################################################

import os
import sys
import uuid
import hashlib
import requests
import socket
import colorsys
import simplejson as json
from math import ceil
from math import floor


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
		self.deviceList = []
		self.paired = False
		self.lightsDict = dict()
		self.ipAddress = ""
	
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
	# Overridden Plugin Methods
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
				self.sleep(5)
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
		if valuesDict.get('rampRate', "") != "":
			try:
				rampRate = float(valuesDict['rampRate'])
				if rampRate < 0 or rampRate > 540:
					isError = True
					errorsDict['rampRate'] = u"The Ramp Rate must be a number between 0 and 540 in increments of 0.1 seconds."
					errorsDict['showAlertText'] += errorsDict['rampRate'] + "\n\n"
			except ValueError:
				isError = True
				errorsDict['rampRate'] = u"The Ramp Rate must be a number between 0 and 540 in increments of 0.1 seconds."
				errorsDict['showAlertText'] += errorsDict['rampRate'] + "\n\n"
			except Execption, e:
				isError = True
				errorsDict['rampRate'] = u"The Ramp Rate must be a number between 0 and 540 in increments of 0.1 seconds. Error: " + str(e)
				errorsDict['showAlertText'] += errorsDict['rampRate'] + "\n\n"
				
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
		
		### SET RGB COLOR ###
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
			rampRate = valuesDict.get('rampRate', False)
			if rampRate == "":
				rampRate = False
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
			if rampRate:
				try:
					rampRate = float(rampRate)
					if (rampRate < 0) or (rampRate > 540):
						isError = True
						errorsDict['rampRate'] = "Ramp Rate must be a number between 0 and 540 seconds and can be in increments of 0.1 seconds."
						errorsDict['showAlertText'] += errorsDict['rampRate'] + "\n\n"
				except ValueError:
					isError = True
					errorsDict['rampRate'] = "Ramp Rate must be a number between 0 and 540 seconds and can be in increments of 0.1 seconds."
					errorsDict['showAlertText'] += errorsDict['rampRate'] + "\n\n"
				except Exception, e:
					isError = True
					errorsDict['rampRate'] = "Invalid Ramp Rate value: " + str(e)
					errorsDict['showAlertText'] += errorsDict['rampRate'] + "\n\n"
					
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
			rampRate = valuesDict.get('rampRate', False)
			if rampRate == "":
				rampRate = False
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
			if rampRate:
				try:
					rampRate = float(rampRate)
					if (rampRate < 0) or (rampRate > 540):
						isError = True
						errorsDict['rampRate'] = "Ramp Rate must be a number between 0 and 540 seconds and can be in increments of 0.1 seconds."
						errorsDict['showAlertText'] += errorsDict['rampRate'] + "\n\n"
				except ValueError:
					isError = True
					errorsDict['rampRate'] = "Ramp Rate must be a number between 0 and 540 seconds and can be in increments of 0.1 seconds."
					errorsDict['showAlertText'] += errorsDict['rampRate'] + "\n\n"
				except Exception, e:
					isError = True
					errorsDict['rampRate'] = "Invalid Ramp Rate value: " + str(e)
					errorsDict['showAlertText'] += errorsDict['rampRate'] + "\n\n"
					
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
			rampRate = valuesDict.get('rampRate', False)
			if rampRate == "":
				rampRate = False
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
			if rampRate:
				try:
					rampRate = float(rampRate)
					if (rampRate < 0) or (rampRate > 540):
						isError = True
						errorsDict['rampRate'] = "Ramp Rate must be a number between 0 and 540 seconds and can be in increments of 0.1 seconds."
						errorsDict['showAlertText'] += errorsDict['rampRate'] + "\n\n"
				except ValueError:
					isError = True
					errorsDict['rampRate'] = "Ramp Rate must be a number between 0 and 540 seconds and can be in increments of 0.1 seconds."
					errorsDict['showAlertText'] += errorsDict['rampRate'] + "\n\n"
				except Exception, e:
					isError = True
					errorsDict['rampRate'] = "Invalid Ramp Rate value: " + str(e)
					errorsDict['showAlertText'] += errorsDict['rampRate'] + "\n\n"
					
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
	# Plugin-Specific Methods
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
	
	# Get the status of a bulb.
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
			r = requests.get(command)
			### self.debugLog(u"Data from hub: " + r.content)
			# Convert the response to a Python object.
			try:
				bulb = json.loads(r.content)
			except Exception, e:
				self.errorLog(u"Error retrieving Hue bulb status: " + str(e))
				return False
				
			# Update device states based on bulb object data.
			#   On/Off State (True/False).
			#   (It's not necessary to update the onOffState since, if brightness
			#     is greater than 0, onOffState is automatically set to On and if
			#     brightness is 0, onOffState is Off).
			#   Brightness Level (convert from 0-255 to 0-100).
			if bulb['state']['on']:
				# Only update the brightness level if the bulb is actually on.
				self.updateDeviceState(device, 'brightnessLevel', int(ceil(bulb['state']['bri']/255.0*100.0)))
				#   Hue Degrees (convert from 0-65535 to 0-360).
				self.updateDeviceState(device, 'hue', int(round(bulb['state']['hue']/182.0)))
				#   Saturation (convert from 0-255 to 0-100).
				self.updateDeviceState(device, 'saturation', int(ceil(bulb['state']['sat']/255.0*100)))
				#   CIE XY Cromaticity.
				self.updateDeviceState(device, 'colorX', bulb['state']['xy'][0])
				self.updateDeviceState(device, 'colorY', bulb['state']['xy'][1])
				#   Red, Green, and Blue Color.
				#     Convert from HSB to linear RGB (real numbers from 0 to 1).
				rgb = colorsys.hsv_to_rgb((bulb['state']['hue']/182.04)/360.00, bulb['state']['sat']/255.00, bulb['state']['bri']/255.00)
				#     Assign the 3 RGB values to device states (after converting them to
				#     integers in the 0-255 range).
				self.updateDeviceState(device, 'colorRed', int(ceil(rgb[0]*255.00)))
				self.updateDeviceState(device, 'colorGreen', int(ceil(rgb[1]*255.00)))
				self.updateDeviceState(device, 'colorBlue', int(ceil(rgb[2]*255.00)))
				#   Color Temperature (convert from 154-500 mireds to 6494-2000 K).
				self.updateDeviceState(device, 'colorTemp', int(floor(1000000.0/bulb['state']['ct'])))
				#   Alert Status.
				self.updateDeviceState(device, 'alertMode', bulb['state']['alert'])
				#   Effect Status.
				self.updateDeviceState(device, 'effect', bulb['state']['effect'])
				#   Color Mode.
				self.updateDeviceState(device, 'colorMode', bulb['state']['colormode'])
			else:
				# Bulb is off. Set brightness to zero.
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
				self.updateDeviceState(device, 'colorTemp', int(floor(1000000.0/bulb['state']['ct'])))
				#   Alert Status.
				self.updateDeviceState(device, 'alertMode', bulb['state']['alert'])
				#   Effect Status.
				self.updateDeviceState(device, 'effect', bulb['state']['effect'])
				#   Color Mode.
				self.updateDeviceState(device, 'colorMode', bulb['state']['colormode'])
				
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
				
	# Set Bulb Brightness
	########################################
	def setBrightness(self, device, brightness, rampRate=-1):
		# If a rampRate wasn't specified (default of -1 assigned), use the default.
		#   (rampRate should be an integer expressing 10th of seconds, so
		#   5 = 0.5 seconds, 100 = 10 seconds, etc).
		if rampRate == -1:
			try:
				# For user-friendliness, the rampRate provided in the device
				#   properties (as entered by the user) is expressed in fractions
				#   of a second (0.5 = 0.5 seconds, 10 = 10 seconds, etc), so
				#   it must be converted to 10th seconds here.
				rampRate = int(round(float(device.pluginProps.get('rampRate', 0.5)) * 10))
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
			r = requests.put(command, data=requestData)
			self.debugLog("Got response - %s" % r.content)
			# Update the device brightness (which automatically changes on state).
			self.updateDeviceState(device, 'brightnessLevel', int(ceil(brightness/255.0*100.0)))
			# Log the change.
			indigo.server.log(message = u"\"" + device.name + "\" on to " + str(int(ceil(brightness/255.0*100.0))) + " at ramp rate " + str(rampRate / 10.0) + " sec.")
		else:
			requestData = json.dumps({"on": False, "transitiontime": rampRate})
			command = "http://%s/api/%s/lights/%s/state" % (self.ipAddress, self.pluginPrefs['hostId'], bulbId)
			self.debugLog("Sending URL request: " + command)
			r = requests.put(command, data=requestData)
			self.debugLog("Got response - %s" % r.content)
			# Update the device brightness (which automatically changes on state).
			self.updateDeviceState(device, 'brightnessLevel', 0)
			# Log the change.
			indigo.server.log(u"\"" + device.name + "\" off at ramp rate " + str(rampRate / 10.0) + " sec.")
			
	# Turn Bulb On or Off
	########################################
	def setOnOff(self, device, onState, rampRate=-1):
		# If a rampRate wasn't specified (default of -1 assigned), use the default.
		#   (rampRate should be an integer expressing 10th of seconds, so
		#   5 = 0.5 seconds, 100 = 10 seconds, etc).
		if rampRate == -1:
			try:
				# For user-friendliness, the rampRate provided in the device
				#   properties (as entered by the user) is expressed in fractions
				#   of a second (0.5 = 0.5 seconds, 10 = 10 seconds, etc), so
				#   it must be converted to 10th seconds here.
				rampRate = int(round(float(device.pluginProps.get('rampRate', 0.5)) * 10))
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
				r = requests.put(command, data=requestData)
				self.debugLog("Got response - %s" % r.content)
				# Update the Indigo device.
				self.updateDeviceState(device, 'brightnessLevel', int(ceil(savedBrightness/255.0*100.0)))
				# Log the change.
				indigo.server.log(u"\"" + device.name + "\" on to " + str(int(ceil(savedBrightness/255.0*100.0))) + " at ramp rate " + str(rampRate / 10.0) + " sec.")
			else:
				# Since the bulb can be "on" with 0 brightness, we'll need
				#   to also tell the bulb to go to 100% brightness.
				# Create the JSON object and send the command to the hub.
				requestData = json.dumps({"on": onState, "bri": 255, "transitiontime": rampRate})
				command = "http://%s/api/%s/lights/%s/state" % (self.ipAddress, self.pluginPrefs['hostId'], bulbId)
				self.debugLog("Sending URL request: " + command)
				r = requests.put(command, data=requestData)
				self.debugLog("Got response - %s" % r.content)
				# Update the Indigo device.
				self.updateDeviceState(device, 'brightnessLevel', 100)
				# Log the change.
				indigo.server.log(u"\"" + device.name + "\" on to 100 at ramp rate " + str(rampRate / 10.0) + " sec.")
		else:
			# Blub is being turned off.
			# Create the JSON object and send the command to the hub.
			requestData = json.dumps({"on": onState, "transitiontime": rampRate})
			command = "http://%s/api/%s/lights/%s/state" % (self.ipAddress, self.pluginPrefs['hostId'], bulbId)
			self.debugLog("Sending URL request: " + command)
			r = requests.put(command, data=requestData)
			self.debugLog("Got response - %s" % r.content)
			# Update the Indigo device.
			self.updateDeviceState(device, 'brightnessLevel', 0)
			# Log the change.
			indigo.server.log(u"\"" + device.name + "\" off at ramp rate " + str(rampRate / 10) + " sec.")
		
	# Set Color Temperature
	########################################
	def setTemperature(self, device, temperature, brightness, rampRate=-1):
		# If a rampRate wasn't specified (default of -1 assigned), use the default.
		#   (rampRate should be an integer expressing 10th of seconds, so
		#   5 = 0.5 seconds, 100 = 10 seconds, etc).
		if rampRate == -1:
			try:
				# For user-friendliness, the rampRate provided in the device
				#   properties (as entered by the user) is expressed in fractions
				#   of a second (0.5 = 0.5 seconds, 10 = 10 seconds, etc), so
				#   it must be converted to 10th seconds here.
				rampRate = int(round(float(device.pluginProps.get('rampRate', 0.5)) * 10))
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
		self.debugLog(u"Request is %s" % requestData)
		r = requests.put("http://%s/api/%s/lights/%s/state" % (self.ipAddress, self.pluginPrefs['hostId'], bulbId), data=requestData)
		self.debugLog("Got response - %s" % r.content)
		
		# Update on Indigo
		if int(ceil(brightness/255.0*100.0)) > 0:
			self.updateDeviceState(device, 'brightnessLevel', int(ceil(brightness / 255.0 * 100.0)))
			# Log the change.
			indigo.server.log(u"\"" + device.name + "\" on to " + str(int(ceil(brightness / 255.0 * 100.0))) + " using white point " + str(int(floor(1000000.0 / temperature))) + " K at ramp rate " + str(rampRate / 10.0) + " sec.")
		else:
			self.updateDeviceState(device, 'brightnessLevel', 0)
			# Log the change.
			indigo.server.log(u"\"" + device.name + "\" off at ramp rate " + str(rampRate / 10.0) + " sec.")
			
	# Set Hue, Saturation and Brightness
	########################################
	def setHSB(self, device, hue, saturation, brightness, rampRate=-1):
		# If a rampRate wasn't specified (default of -1 assigned), use the default.
		#   (rampRate should be an integer expressing 10th of seconds, so
		#   5 = 0.5 seconds, 100 = 10 seconds, etc).
		if rampRate == -1:
			try:
				# For user-friendliness, the rampRate provided in the device
				#   properties (as entered by the user) is expressed in fractions
				#   of a second (0.5 = 0.5 seconds, 10 = 10 seconds, etc), so
				#   it must be converted to 10th seconds here.
				rampRate = int(round(float(device.pluginProps.get('rampRate', 0.5)) * 10))
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
		self.debugLog(u"Request is %s" % requestData)
		r = requests.put("http://%s/api/%s/lights/%s/state" % (self.ipAddress, self.pluginPrefs['hostId'], bulbId), data=requestData)
		self.debugLog("Got response - %s" % r.content)
		
		# Update on Indigo
		# Log the change.
		if int(ceil(brightness/255.0*100.0)) > 0:
			self.updateDeviceState(device, 'brightnessLevel', int(ceil(brightness/255.0*100.0)))
			indigo.server.log(u"\"" + device.name + u"\" on to " + str(int(ceil(brightness / 255.0 * 100.0))) + u" with hue " + str(int(round(hue / 182.0))) + u"° saturation " + str(int(saturation / 255.0 * 100.0)) + u"% at ramp rate " + str(rampRate / 10.0) + u" sec.")
		else:
			self.updateDeviceState(device, 'brightnessLevel', 0)
			# Log the change.
			indigo.server.log(u"\"" + device.name + "\" off at ramp rate " + str(rampRate / 10.0) + " sec.")
			
	# Set RGB Levels
	########################################
	def setRGB(self, device, red, green, blue, rampRate=-1):
		# If a rampRate wasn't specified (default of -1 assigned), use the default.
		#   (rampRate should be an integer expressing 10th of seconds, so
		#   5 = 0.5 seconds, 100 = 10 seconds, etc).
		if rampRate == -1:
			try:
				# For user-friendliness, the rampRate provided in the device
				#   properties (as entered by the user) is expressed in fractions
				#   of a second (0.5 = 0.5 seconds, 10 = 10 seconds, etc), so
				#   it must be converted to 10th seconds here.
				rampRate = int(round(float(device.pluginProps.get('rampRate', 0.5)) * 10))
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
		
		# Convert the red, green, and blue integers into linear RGB values.
		red = red/255.00
		green = green/255.00
		blue = blue/255.00
		# Convert the linear RGB to HSB.
		hsb = colorsys.rgb_to_hsv(red, green, blue)
		
		# Send to Hue
		requestData = json.dumps({"bri": int(round(hsb[2]*255.0)), "hue": int(floor(hsb[0]*360.0*182.0)), "sat": int(ceil(hsb[1]*255.0)), "transitiontime": int(rampRate), "on": True})
		command = "http://%s/api/%s/lights/%s/state" % (self.ipAddress, self.pluginPrefs['hostId'], bulbId)
		self.debugLog(u"Data: " + str(requestData) + ", URL: " + command)
		r = requests.put(command, data=requestData)
		self.debugLog("Got response - %s" % r.content)
		
		# Update on Indigo
		if int(round(hsb[2]*100.0)) > 0:
			self.updateDeviceState(device, 'brightnessLevel', int(round(hsb[2]*100.0)))
			# Log the change.
			indigo.server.log(u"\"" + device.name + "\" on to " + str(int(round(hsb[2]*100.0))) + " with RGB values " + str(int(red * 255.0)) + ", " + str(int(green * 255.0)) + " and " + str(int(blue * 255.0)) + " at ramp rate " + str(rampRate / 10.0) + " sec.")
		else:
			self.updateDeviceState(device, 'brightnessLevel', 0)
			# Log the change.
			indigo.server.log(u"\"" + device.name + "\" off at ramp rate " + str(rampRate / 10.0) + " sec.")
			
	# Start Alert (Blinking)
	########################################
	def setAlert(self, device, alertType="lselect"):
		
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
		
		requestData = json.dumps({"alert": alertType})
		r = requests.put("http://%s/api/%s/lights/%s/state" % (self.ipAddress, self.pluginPrefs['hostId'], bulbId), data=requestData)
		self.debugLog("Got response - %s" % r.content)
		
		# Log the change.
		if alertType == "select":
			indigo.server.log(u"\"" + device.name + "\" start short alert blink.")
		elif alertType == "lselect":
			indigo.server.log(u"\"" + device.name + "\" start long alert blink.")
		elif alertType == "none":
			indigo.server.log(u"\"" + device.name + "\" stop alert blink.")
			
	# Set Effect Status
	# (This is experimental right now).
	########################################
	def setEffect(self, device, effect):
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
		r = requests.put(command, data=requestData)
		indigo.server.log(u"Got response - %s" % r.content)
		
		# Update on Indigo
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
		socket.setdefaulttimeout(3)
		
		try:
			# Parse the response
			r = requests.get("http://%s/api/%s/lights" % (self.ipAddress, self.pluginPrefs.get('hostId', "ERROR")), timeout=3)
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
			
		except requests.exceptions.Timeout, e:
			self.errorLog(u"Timeout loading light list from hue at %s - check settings and retry" % self.ipAddress)
			
		except Exception, e:
			self.errorLog(u"Unable to obtain list of Hue lights from hub. " + str(e))
			
			
	########################################
	# Registration Methods
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
		socket.setdefaulttimeout(5)
		
		# Request login state
		try:
			indigo.server.log(u"Checking with the Hue hub at %s for pairing state..." % (self.ipAddress))
			requestData = json.dumps({"username": self.pluginPrefs.get('hostId', None), "devicetype": "Indigo Hue Plugin"})
			self.debugLog(u"Request is %s" % requestData)
			r = requests.post("http://%s/api" % self.ipAddress, data=requestData, timeout=3)
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
			self.errorLog(u"Timeout connecting to Hue hub at %s - check the IP address and try again." % self.ipAddress)
			
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
	# Indigo UI Controls
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
			self.setBrightness(device, 255)
			
		##### TURN OFF #####
		elif command == indigo.kDeviceAction.TurnOff:
			try:
				self.debugLog("device off:\n%s" % action)
			except Exception, e:
				self.debugLog("device off: (Unable to display action data due to error: " + str(e) + ")")
			# Turn it off by setting the brightness to minimum.
			self.setBrightness(device, 0)

		##### TOGGLE #####
		elif command == indigo.kDeviceAction.Toggle:
			try:
				self.debugLog("device toggle:\n%s" % action)
			except Exception, e:
				self.debugLog("device toggle: (Unable to display action due to error: " + str(e) + ")")
			if currentOnState == True:
				# It's on. Turn it off by setting the brightness to minimum.
				self.setBrightness(device, 0)
			else:
				# It's off. Turn it on by setting the brightness to maximum.
				self.setBrightness(device, 255)
		
		##### SET BRIGHTNESS #####
		elif command == indigo.kDeviceAction.SetBrightness:
			try:
				self.debugLog("device set brightness:\n%s" % action)
			except Exception, e:
				self.debugLog("device set brightness: (Unable to display action data due to error: " + str(e) + ")")
			brightnessLevel = int(round(action.actionValue / 100.0 * 255.0))
			# Save the new brightness level into the device properties.
			tempProps = device.pluginProps
			tempProps['savedBrightness'] = brightnessLevel
			self.updateDeviceProps(device, tempProps)
			# Set the new brightness level on the bulb.
			self.setBrightness(device, brightnessLevel)

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
			tempProps['savedBrightness'] = int(round(brightnessLevel / 100.0 * 255.0))
			self.updateDeviceProps(device, tempProps)
			# Set the new brightness level on the bulb.
			self.setBrightness(device, int(round(brightnessLevel / 100.0 * 255.0)))
			
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
			tempProps['savedBrightness'] = int(round(brightnessLevel / 100.0 * 255.0))
			self.updateDeviceProps(device, tempProps)
			# Set the new brightness level on the bulb.
			self.setBrightness(device, int(round(brightnessLevel / 100.0 * 255.0)))
			
		##### REQUEST STATUS #####
		elif command == indigo.kDeviceAction.RequestStatus:
			try:
				self.debugLog("device request status:\n%s" % action)
			except Exception, e:
				self.debugLog("device request status: (Unable to display action data due to error: " + str(e) + ")")
			self.getBulbStatus(device)

		#### CATCH ALL #####
		else:
			indigo.server.log(u"Unhandled Hue bulb command \"%s\"" % (command))
		pass
		
	########################################
	# Custom Plugin Action callbacks (defined in Actions.xml)
	########################################
	
	# Set RGB Level Action
	########################################
	def setRGBAction(self, action, device):
		self.debugLog(u"setRGBAction: device: " + device.name + ", action:\n" + str(action))
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
			rampRate = action.props.get('rampRate', -1)
			if rampRate != "":
				rampRate = float(rampRate)
			else:
				rampRate = device.pluginProps.get('rampRate', 0.5)
		except ValueError:
			self.errorLog(u"Ramp Rate value specified for \"" + device.name +u"\" is invalid.")
			return
			
		self.setRGB(device, red, green, blue, rampRate)
		
	# Set HSB Action
	########################################
	def setHSBAction(self, action, device):
		self.debugLog(u"setHSBAction: device: " + device.name + ", action:\n" + str(action))
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
			rampRate = action.props.get('rampRate', -1)
			if rampRate != "":
				rampRate = float(rampRate)
			else:
				rampRate = device.pluginProps.get('rampRate', 0.5)
		except ValueError:
			self.errorLog(u"Ramp Rate value specified for \"" + device.name +u"\" is invalid.")
			return
			
		# Scale these values to match Hue
		brightness = int(round((float(brightness)/100.0) * 255.0))
		saturation = int(floor((float(saturation)/100.0) * 255.0))
		hue = int(floor(hue*182.0))
		
		self.setHSB(device, hue, saturation, brightness, rampRate)
		
	# Set Color Temperature Action
	########################################
	def setCTAction(self, action, device):
		self.debugLog(u"setCTAction: device: " + device.name + ", action:\n" + str(action))
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
			rampRate = action.props.get('rampRate', -1)
			if rampRate != "":
				rampRate = float(rampRate)
			else:
				rampRate = device.pluginProps.get('rampRate', 0.5)
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
			
		self.setTemperature(device, temperature, brightness, rampRate)
		
	# Set Single Alert Action
	########################################
	def alertOnce(self, action, device):
		self.debugLog(u"alertOnce: device: " + device.name + ", action:\n" + str(action))
		self.setAlert(device, "select")
		
	# Set Long Alert Action
	########################################
	def longAlert(self, action, device):
		self.debugLog(u"longAlert: device: " + device.name + ", action:\n" + str(action))
		self.setAlert(device, "lselect")
		
	# Stop Alert Action
	########################################
	def stopAlert(self, action, device):
		self.debugLog(u"stopAlert: device: " + device.name + ", action:\n" + str(action))
		self.setAlert(device, "none")
	
	# Set Effect (Test) Action
	########################################
	def effect(self, action, device):
		effect = action.props.get('effect', False)
		if not effect:
			self.errorLog(u"No effect text provided to try.")
			return
			
		self.setEffect(device, effect)
		
