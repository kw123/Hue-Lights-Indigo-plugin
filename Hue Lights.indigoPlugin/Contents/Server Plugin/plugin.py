#! /usr/bin/env python
# -*- coding: utf-8 -*-
####################
# Some code borrowed from the "Hue.indigoPlugin" (Hue Lighting Control) plugin
#   originally developed by Alistair Galbraith (alistairg on GitHub,
#   https://github.com/alistairg ).
#
#   His comment:
#   "This is UNSUPPORTED, AS-IS, open source code - do with it as you wish. Don't
#   blame me if it breaks! :)"
#
# His code base was forked on GitHub and mostly rewritten by Nathan Sheldon
#   (nathan@nathansheldon.com)
#   http://www.nathansheldon.com/files/Hue-Lights-Plugin.php
#   All modificiations are open source.
#
#	Version 1.3.4
#
#	History:	1.3.4
#				* Yet another attempt to fix the same bug found in 1.3.0.
#				--
#				1.3.3
#				* Another attempt to fix the same bug found in 1.3.0.
#				--
#				1.3.2
#				* Fixed a bug introduced in 1.3.1 that causes an error when
#				  no ramp rate is provided for Color Temperatur and other
#				  color change actions are initiated.
#				--
#				1.3.1
#				* Fixed a bug that could cause a plugin crash if a string
#				  was passed as the ramp rate in a Python script when
#				  executing any action that sets color.
#				--
#				1.3.0
#				* Added limited, experimental support for Hue groups.
#				  Support is limited to working with existing groups on
#				  the Hue hub. Hue groups are treated like other Hue
#				  devices.
#				* Minor error message corrections throughout the plugin.
#				--
#				1.2.11 (29-Apr-2014)
#				* Fixed a bug that would cause device edit dialogs to
#				  incorrectly report that the hub was not paired after
#				  the hub had been unreachable then became reachable again.
#				--
#				1.2.10 (23-Apr-2014)
#				* Fixed a bug that would cause the plugin to crash
#				  if a command was sent to the hub while the hub
#				  (or the plugin) was in an unstable state that
#				  resulted in an invalid pairing status.
#				* Updated the error reporting process so that major
#				  connection failure errors were actually reported as
#				  errors in the log rather than standard log entries.
#				* Updated the error reporting process so frequently
#				  displayed errors during a network or hub outage
#				  are reduced from once every 4 seconds to about once
#				  every minute.
#				--
#				1.2.9 (31-Mar-2014)
#				* Added support for the LivingColor Aura available
#				  in Europe (model ID LLC014).
#				* Updated Hue device types in Indigo device dialog
#				  to help clarify which device type to choose based
#				  on which Hue device you have.
#				--
#				1.2.8 (07-Feb-2014)
#				* Added support for the European version of the
#				  Bloom (model ID LLC011).
#				* Audited code to make sure all printable text is
#				  explicitly marked as Unicode text.
#				--
#				1.2.7 (10-Dec-2013)
#				* Added support for the Friends of Hue Disney
#				  StoryLight.
#				--
#				1.2.6 (21-Nov-2013)
#				* Added support for the Hue GU10 spot light.
#				* Increased number of Presets from 10 to 30.
#				--
#				1.2.5 (05-Nov-2013)
#				* Added support for the Hue "Downlight" BR30 bulb.
#				--
#				1.2.4 (10-Sep-2013)
#				* Added optional Ramp Rate to the Save Preset and Recall Preset
#				  actions and menu items.
#				* Fixed (hopefully) a bug that caused an ASCII translation error
#				  when editing an action for a device with non-ASCII characters
#				  in the name.
#				--
#				1.2.3 (04-Sep-2013... later that day.  :-) )
#				* Fixed a bug that caused a "typeId 'setBrightness'" error when
#				  attempting to create a Set Brightness with Ramp Rate action.
#				--
#				1.2.2 (04-Sep-2013)
#				* Increased the number of connection retries should a connection
#				  error be reported by the requests library.  Also disabled the
#				  HTTP "keep alive" connection pooling feature.
#				--
#				1.2.1 (02-Sep-2013)
#				* Fixed a bug that could cause the plugin to crash when using the
#				  Set Hue/Saturation/Brightness action from an external or embedded
#				  script then from an Indigo action.
#				* Added elipses to Plugins menu Preset items to conform to standard
#				  menu item naming convension when a dialog results from selecting
#				  a menu item.
#				--
#				1.2.0 (25-Aug-2013)
#				* Added Hue device settings Presets option that can save a device's
#				  current settings to be recalled (applied) later to any other
#				  compatible Hue device.
#				* Fixed a bug that would cause Hue devices to not turn off if the
#				  requested brightness level was 0 when using the Set RGB, Set HSB,
#				  Set Color Temperature, or Set xyY actions.
#				--
#				1.1.1 (20-Aug-2013)
#				* Added code to update device error states if a Hue device's online
#				  state changes to false, or there's some other kind of error.
#				* Corrected some UI labeling errors.
#				--
#				1.1.0 (18-Aug-2013)
#				* Added support for the following Friends of Hue devices:
#				     - LightStrips
#				     - LivingColors Bloom
#				* Added experimental support for LivingWhites devices.
#				* Fixed a bug that wouldn't turn off the Hue bulb as quickly if using
#				  the standard device Turn Off command as opposed to setting the
#				  brightness to 0 method.
#				* Updated the Set Red/Green/Blue function to better match
#				  Hue device capabilities.
#				* Added a Set xyY Chromaticity (Advanced) action that allows one to
#				  directly specify the x/y chromaticity and Y luminosity values for
#				  devices that can render color.
#				--
#				1.0.3 (09-Aug-2013)
#				* Fixed bug that caused the plugin to crash when using a LightStrip
#				  device.
#				--
#				1.0.2 (09-Aug-2013)
#				* Added ability to recognize new LightStrips and "wall washer" strips.
#				--
#				1.0.1 (30-Jul-2013)
#				* Added the indigoPluginUpdateChecker module (code by Travis CooK)
#				  to facilitate automatic plugin version checking.
#				--
#				1.0 (03-Jul-2013)
#				* Updated brightness status code to accurately reflect a 1
#				  percent brightness level (rather than rounding up to 2 percent).
#				* Added Default Brightness property for Hue Bulbs devices so
#				  their features are more consistent with other lighting devices
#				  in Indigo (such as SwitchLinc and LampLinc Dimmers).
#				* Changed "on", "off", and "toggle" action control functions so
#				  that sending an "on" command to a Hue Bulb from within Indigo
#				  returns the bulb to its previous brightness level, or its
#				  default brightness level (if set).
#				* Updated Brightness, HSB, and Color Temperature setting methods
#				  so that they properly save the brightness level specified in
#				  those actions to the Hue Bulb's device properties for recall
#				  should an "on" command be sent to it.
#				* Updated the bulb status gathering method so that if the bulb
#				  brightness changes outside of the Hue Lights plugin (or the hub
#				  updates the bulb brightness during a long transition time),
#				  Hue Lights does not save the new brightness to the bulb
#				  properties and thus causing an "on" command later to recall an
#				  incorrect previous brightness state.
#				* Changed the logging slightly to more closely match the log
#				  format of native INSTEON device changes.
#				--
#				0.10.2 (24-Jun-2013)
#				* Added more code to work better with LivingWhites bulbs.
#				--
#				0.10.1 (24-Jun-2013)
#				* Modified debugging code so it wouldn't throw errors when the
#				  plugin is installed on versions of Indigo Pro earlier than
#				  version 5.1.7.
#				* Added the LWB003 model ID to the list of recognized Hue models.
#				--
#				0.10.0 (12-Jun-2013)
#				* Added a Hue Bulb Attribute Controller virtual dimmer device
#				  which can be created to control a specific attribute (hue,
#				  saturation, RGB levels, or color temperature) of an existing
#				  Hue Lights bulb device.
#				* Added an "Effect" action which allows you to specify an effect
#				  to be turned on for a Hue bulb (requires latest firmware on
#				  the Hue hub. Currently, only the Color Loop effect is supported
#				  by the Hue hub and bulbs).
#				* Changed light control methods so that if the current light
#				  brightness is below 6% and the requested action is to turn off
#				  the bulb, set the ramp rate to 0 regardless of the default or
#				  specified ramp rate (transition time) because going from a
#				  brightness of 6% or lower to an off state with a dimming rate
#				  isn't noticeable.
#				--
#				0.9.11 (10-Apr-2013)
#				* Updated code to more elegantly handle non-Hue devices attached
#				  to the Hue hub.
#				--
#				0.9.10 (02-Apr-2013)
#				* Fixed a bug that would cause the plugin to crash if a
#				  registered bulb on the Hue hub had no "hue" attribute (which
#				  could happen when using "LivingWhites" plugin dimmers found in
#				  some European countries).
#				--
#				0.9.9 (24-Jan-2013)
#				* Attempted to make RGB-to-xyY conversions more accurate by
#				  changing the illuminant used by the colormath functions from
#				  type "a" to type "e".
#				--
#				0.9.8 (23-Jan-2013)
#				* Fixed a bug that would crash the plugin if no device was
#				  selected in a start/stopBrightening/Dimming action when the
#				  action was executed.
#				* Fixed a bug that would cause an error during device creation
#				  dialog validation for new Hue Light devices in Indigo 5.x.
#				--
#				0.9.7 (31-Dec-2012)
#				* Fixed a bug that updated the "hue" state of plugin devices
#				  with an invalid number when the setHSB action was used.
#				--
#				0.9.6 (31-Dec-2012)
#				* Fixed a divide by zero error in getBulbStatus that could
#				  happen if the Hue hub returns no value for a blub's color
#				  temperature.
#				--
#				0.9.5 (27-Dec-2012)
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
from colormath.color_objects import RGBColor, xyYColor, HSVColor
from math import ceil, floor
import simplejson as json
import indigoPluginUpdateChecker

# Default timeout.
kTimeout = 4		# seconds
# Default connection retries.
requests.defaults.defaults['max_retries'] = 3
# Turn off the HTTP connection "keep alive" feature.
requests.defaults.defaults['keep_alive'] = False

# List of compatible device IDs that may be associated with a Hue hub.
#
# LCT001	=	Hue bulb
# LCT002	=	Hue Downlight BR30 bulb
# LCT003	=	Hue Spot Light GU10 bulb
# LLC001	=	LivingColor light (generic)
# LLC006	=	" " "
# LLC007	=	" " "
# LLC011	=	Bloom (European?)
# LLC012	=	Bloom
# LLC013	=	Disney StoryLight
# LLC014	=	LivingColor Aura
# LST001	=	LED LightStrip
# LWB001	=	LivingWhites bulb
# LWB003	=	" " "
# LWL001	=	LivingWhites light socket
#   (compatible Hue bulb devices)
kHueBulbDeviceIDs = ['LCT001', 'LCT002', 'LCT003']
#   (compatible LivingColors devices)
kLivingColorsDeviceIDs = ['LLC001', 'LLC006', 'LLC007', 'LLC011', 'LLC012', 'LLC013', 'LLC014']
#   (compatible LightStrips devices)
kLightStripsDeviceIDs = ['LST001']
#   (compatible LivingWhites devices)
kLivingWhitesDeviceIDs = ['LWB001', 'LWB003', 'LWL001']
#   (all compatible devices)
kCompatibleDeviceIDs = kHueBulbDeviceIDs + kLivingColorsDeviceIDs + kLightStripsDeviceIDs + kLivingWhitesDeviceIDs


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
		self.controlDeviceList = []	# list of virtual dimmer device IDs that control bulb devices
		self.brighteningList = []	# list of device IDs being brightened
		self.dimmingList = []		# list of device IDs being dimmed
		self.paired = False			# if paired with Hue hub or not
		self.lastErrorMessage = ""	# last error message displayed in log
		self.lightsDict = dict()	# Hue device ID: Name dict.
		self.groupsDict = dict()	# Hue group ID: Name dict.
		self.ipAddress = ""			# Hue hub IP address
		self.unsupportedDeviceWarned = False	# Boolean. Was user warned this device isn't supported?
		# Load the update checker module.
		self.updater = indigoPluginUpdateChecker.updateChecker(self, 'http://www.nathansheldon.com/files/PluginVersions/Hue-Lights.html')
	
	# Unload Plugin
	########################################
	def __del__(self):
		indigo.PluginBase.__del__(self)
		
	# Startup
	########################################
	def startup(self):
		self.debugLog(u"Startup called")
		# Perform an initial version check.
		self.updater.checkVersionPoll()
		
		# Prior to version 1.2.0, the "presets" property did not exist in the plugin preferences.
		#   If that property does not exist, add it.
		# As of version 1.2.6, there are now 30 presets instead of 10.
		if not self.pluginPrefs.get('presets', False):
			self.debugLog(u"pluginPrefs lacks presets.  Adding.")
			# Add the empty presets list to the prefs.
			self.pluginPrefs['presets'] = list()
			# Start a new list of empty presets.
			presets = list()
			for aNumber in range(1,31):
				# Create a blank sub-list for storing preset name and preset states.
				preset = list()
				# Add the preset name.
				preset.append('Preset ' + str(aNumber))
				# Add the empty preset states Indigo dictionary
				preset.append(indigo.Dict())
				# Add the sub-list to the empty presets list.
				presets.append(preset)
			# Add the new list of empty presets to the prefs.
			self.pluginPrefs['presets'] = presets
			self.debugLog(u"pluginPrefs now contains 30 presets. Prefs are:\n" + str(self.pluginPrefs))
		# If presets exist, make sure there are 30 of them.
		else:
			presets = self.pluginPrefs.get('presets', "")
			presetCount = len(presets)
			self.debugLog(u"pluginPrefs contains " + str(presetCount) + u" presets.")
			if presetCount < 30:
				self.debugLog(u"... Adding " + str(30 - presetCount) + u" presets to bring total to 30.")
				for aNumber in range(presetCount + 1,31):
					# Add ever how many presets are needed to make a total of 30.
					# Create a blank sub-list for storing preset name and preset states.
					preset = list()
					# Add the preset name.
					preset.append('Preset ' + str(aNumber))
					# Add the empty preset states Indigo dictionary
					preset.append(indigo.Dict())
					# Add the sub-list to the empty presets list.
					presets.append(preset)
				# Add the new list of empty presets to the prefs.
				self.pluginPrefs['presets'] = presets
				self.debugLog(u"pluginPrefs now contains presets. Prefs are:\n" + str(self.pluginPrefs))

		# Do we have a site ID?
		siteId = self.pluginPrefs.get('hostId', None)
		if siteId is None:
			siteId = str(uuid.uuid1())
			siteId = hashlib.md5(siteId).hexdigest().lower()
			self.debugLog(u"Host ID is %s" % siteId)
			self.pluginPrefs['hostId'] = siteId
		
		# Load lights list
		self.updateLightsList()
		
		# Load groups list
		self.updateGroupsList()
		
	# Start Devices
	########################################
	def deviceStartComm(self, device):
		self.debugLog(u"Starting device: " + device.name)
		# Clear any device error states first.
		device.setErrorStateOnServer("")
		
		# Prior to version 1.1.0, the "modelId" property did not exist in lighting devices.
		#   If that property does not exist, force an update.
		if device.deviceTypeId != "hueAttributeController" and not device.pluginProps.get('modelId', False):
			newProps = device.pluginProps
			newProps['modelId'] = ""
			device.replacePluginPropsOnServer(newProps)
			
		# Update the device lists and the device states.
		# Hue Bulbs
		if device.deviceTypeId == "hueBulb":
			if device.id not in self.deviceList:
				try:
					self.debugLog(u"Hue Bulb device definition:\n" + str(device))
				except Exception, e:
					self.debugLog(u"Hue Bulb device definition cannot be displayed because: " + str(e))
				self.deviceList.append(device.id)
				# Get the bulb's status.
				self.getBulbStatus(device.id)
		# LightStrips
		elif device.deviceTypeId == "hueLightStrips":
			if device.id not in self.deviceList:
				try:
					self.debugLog(u"LightStrips device definition:\n" + str(device))
				except Exception, e:
					self.debugLog(u"LightStrips device definition cannot be displayed because: " + str(e))
				self.deviceList.append(device.id)
				# Get the device's status.
				self.getBulbStatus(device.id)
		# LivingColors Bloom
		elif device.deviceTypeId == "hueLivingColorsBloom":
			if device.id not in self.deviceList:
				try:
					self.debugLog(u"LivingColors Bloom device definition:\n" + str(device))
				except Exception, e:
					self.debugLog(u"LivingColors Bloom device definition cannot be displayed because: " + str(e))
				self.deviceList.append(device.id)
				# Get the device's status.
				self.getBulbStatus(device.id)
		# LivingWhites
		elif device.deviceTypeId == "hueLivingWhites":
			if device.id not in self.deviceList:
				try:
					self.debugLog(u"LivingWhites device definition:\n" + str(device))
				except Exception, e:
					self.debugLog(u"LovingWhites device definition cannot be displayed because: " + str(e))
				self.deviceList.append(device.id)
				# Get the device's status.
				self.getBulbStatus(device.id)
		# Hue Groups
		elif device.deviceTypeId == "hueGroup":
			if device.id not in self.deviceList:
				try:
					self.debugLog(u"Hue Group device definition:\n" + str(device))
				except Exception, e:
					self.debugLog(u"Hue Group device definition cannot be displayed because: " + str(e))
				self.deviceList.append(device.id)
				# Get the group's status.
				self.getGroupStatus(device.id)
		# Hue Device Attribute Controller
		elif device.deviceTypeId == "hueAttributeController":
			if device.id not in self.controlDeviceList:
				try:
					self.debugLog(u"Attribute Control device definition:\n" + str(device))
				except Exception, e:
					self.debugLog(u"Attribute Control device definition cannot be displayed because: " + str(e))
				self.controlDeviceList.append(device.id)
				
	# Stop Devices
	########################################
	def deviceStopComm(self, device):
		self.debugLog(u"Stopping device: " + device.name)
		if device.deviceTypeId == "hueBulb":
			if device.id in self.deviceList:
				self.deviceList.remove(device.id)
		elif device.deviceTypeId == "hueLightStrips":
			if device.id in self.deviceList:
				self.deviceList.remove(device.id)
		elif device.deviceTypeId == "hueLivingColorsBloom":
			if device.id in self.deviceList:
				self.deviceList.remove(device.id)
		elif device.deviceTypeId == "hueLivingWhites":
			if device.id in self.deviceList:
				self.deviceList.remove(device.id)
		elif device.deviceTypeId == "hueGroup":
			if device.id in self.deviceList:
				self.deviceList.remove(device.id)
		elif device.deviceTypeId == "hueAttributeController":
			if device.id in self.controlDeviceList:
				self.controlDeviceList.remove(device.id)
			
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

		j = 0	# Used to reset lastErrorMessage value every 8 loops.

		try:
			while True:
				# Check for newer plugin versions.
				self.updater.checkVersionPoll()
				
				## Brightening Devices ##
				i = 0	# Used to gage timing of brightening or dimming loops.
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
								indigo.server.log(u"\"" + brightenDevice.name + "\" stop brightening", 'Sent Hue Lights')
								self.brighteningList.remove(brightenDeviceId)
								# Get the bulb status (but only if paired with the hub).
								if self.paired == True:
									self.getBulbStatus(brightenDeviceId)
									# Log the new brightnss.
									indigo.server.log(u"\"" + brightenDevice.name + "\" status request (received: 100)", 'Sent Hue Lights')
								else:
									self.debugLog(u"Not currently paired with Hue hub. Status update skipped.")
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
								indigo.server.log(u"\"" + dimDevice.name + u"\" stop dimming", 'Sent Hue Lights')
								self.dimmingList.remove(dimDeviceId)
								# Get the bulb status (but only if we're paired with the hub).
								if self.paired == True:
									self.getBulbStatus(dimDeviceId)
									# Log the new brightnss.
									indigo.server.log(u"\"" + dimDevice.name + u"\" status request (received: 0)", 'Sent Hue Lights')
								else:
									self.debugLog(u"Not currently paired with Hue hub. Status update skipped.")
							# Convert percent-based brightness to 255-based brightness.
							brightness = int(round(brightness / 100.0 * 255.0))
							# Set brightness to new value, with 0.5 sec ramp rate and no logging.
							self.doBrightness(dimDevice, brightness, 0.5, False)
							
					# Wait for 0.4 seconds before loop repeats.
					self.sleep(0.4)
					# Increment loop counter.
					i += 1
					
				# If the error clearing loop counter has reached 8 (about 64 seconds
				#    have passed), then clear the lastErrorMessage and reset the loop.
				if j >= 8:
					self.lastErrorMessage = u""
					j = 0
				else:
					# Error clearing loop counter not yet complete, increment the value.
					j += 1
				
				# Now that the brightening/dimming loop has finished, get device states.
				# Cycle through each device.
				for deviceId in self.deviceList:
					# Get the device's status (but only if we're paired with the hub).
					if self.paired == True:
						self.getBulbStatus(deviceId)
					# Wait just a bit to avoid hub rate limiting.
					self.sleep(0.15)
					
		except self.StopThread:
			self.debugLog(u"runConcurrentThread stopped.")
			pass
		
		self.debugLog(u"runConcurrentThread exiting.")
	
	# Validate Device Configuration
	########################################
	def validateDeviceConfigUi(self, valuesDict, typeId, deviceId):
		self.debugLog(u"validateDeviceConfigUi called.\n  valuesDict: %s\n  typeId: %s\n  deviceId: %s" % (valuesDict, typeId, deviceId))
		errorsDict = indigo.Dict()
		errorsDict['showAlertText'] = ""
		isError = False
		
		# Make sure we're still paired with the Hue hub.
		if self.paired == False:
			isError = True
			errorsDict['bulbId'] = u"Not currently paired with the Hue hub. Close this window and use the Configure... option in the Plugins -> Hue Lights menu to pair Hue Lights with the Hue hub first."
			errorsDict['showAlertText'] += errorsDict['bulbId']
			return (False, valuesDict, errorsDict)
			
		# Check data based on which device config UI was returned.
		#  -- Hue Bulb --
		if typeId == "hueBulb":
			# Make sure a bulb was selected.
			if valuesDict.get('bulbId', "") == "":
				isError = True
				errorsDict['bulbId'] = u"Please select a Hue bulb to control."
				errorsDict['showAlertText'] += errorsDict['bulbId']
				return (False, valuesDict, errorsDict)
			
			bulbId = valuesDict['bulbId']
			
			# Make sure the device selected is a Hue device.
			#   Get the device info directly from the hub.
			command = "http://%s/api/%s/lights/%s" % (self.ipAddress, self.pluginPrefs['hostId'], bulbId)
			self.debugLog(u"Sending URL request: " + command)
			try:
				r = requests.get(command, timeout=kTimeout)
			except requests.exceptions.Timeout:
				errorText = u"Failed to connect to the Hue hub at %s after %i seconds. - Check that the hub is connected and turned on." % (self.ipAddress, kTimeout)
				# Don't display the error if it's been displayed already.
				if errorText != self.lastErrorMessage:
					self.errorLog(errorText)
					# Remember the error.
					self.lastErrorMessage = errorText
				return
			except requests.exceptions.ConnectionError:
				errorText = u"Failed to connect to the Hue hub at %s. - Check that the hub is connected and turned on." % (self.ipAddress)
				# Don't display the error if it's been displayed already.
				if errorText != self.lastErrorMessage:
					self.errorLog(errorText)
					# Remember the error.
					self.lastErrorMessage = errorText
				return
			self.debugLog(u"Data from hub: " + r.content)
			# Convert the response to a Python object.
			try:
				bulb = json.loads(r.content)
			except Exception, e:
				# There was an error in the returned data.
				indigo.server.log(u"Error retrieving Hue bulb data from hub.  Error reported: " + str(e))
				isError = True
				errorsDict['bulbId'] = u"Error retrieving Hue bulb data from hub. See Indigo log."
				errorsDict['showAlertText'] += errorsDict['bulbId']
				return (False, valuesDict, errorsDict)
			if bulb.get('modelid', "") not in kHueBulbDeviceIDs:
				isError = True
				errorsDict['bulbId'] = u"The selected device is not a Hue bulb. Plesea select a Hue bulb to control."
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
				
			# Validate the default brightness is reasonable.
			if valuesDict.get('defaultBrightness', "") != "":
				try:
					defaultBrightness = int(valuesDict['defaultBrightness'])
					if defaultBrightness < 1 or defaultBrightness > 100:
						isError = True
						errorsDict['defaultBrightness'] = u"The Default Brightness must be a number between 1 and 100."
						errorsDict['showAlertText'] += errorsDict['defaultBrightness'] + "\n\n"
				except ValueError:
					isError = True
					errorsDict['defaultBrightness'] = u"The Default Brightness must be a number between 1 and 100."
					errorsDict['showAlertText'] += errorsDict['defaultBrightness'] + "\n\n"
				except Exception, e:
					isError = True
					errorsDict['defaultBrightness'] = u"The Default Brightness must be a number between 1 and 100. Error: " + str(e)
					errorsDict['showAlertText'] += errorsDict['defaultBrightness'] + "\n\n"
					
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
				valuesDict['address'] = self.pluginPrefs.get('address', "") + " (ID " + str(valuesDict['bulbId']) + ")"
				return (True, valuesDict)
				
		#  -- LightStrips Device --
		elif typeId == "hueLightStrips":
			# Make sure a device was selected.
			if valuesDict.get('bulbId', "") == "":
				isError = True
				errorsDict['bulbId'] = u"Please select a LightStrips device to control."
				errorsDict['showAlertText'] += errorsDict['bulbId']
				return (False, valuesDict, errorsDict)
			
			bulbId = valuesDict['bulbId']
			
			# Make sure the device selected is a LightStrips device.
			#   Get the device info directly from the hub.
			command = "http://%s/api/%s/lights/%s" % (self.ipAddress, self.pluginPrefs['hostId'], bulbId)
			self.debugLog(u"Sending URL request: " + command)
			try:
				r = requests.get(command, timeout=kTimeout)
			except requests.exceptions.Timeout:
				errorText = u"Failed to connect to the Hue hub at %s after %i seconds. - Check that the hub is connected and turned on." % (self.ipAddress, kTimeout)
				# Don't display the error if it's been displayed already.
				if errorText != self.lastErrorMessage:
					self.errorLog(errorText)
					# Remember the error.
					self.lastErrorMessage = errorText
				return
			except requests.exceptions.ConnectionError:
				errorText = u"Failed to connect to the Hue hub at %s. - Check that the hub is connected and turned on." % (self.ipAddress)
				# Don't display the error if it's been displayed already.
				if errorText != self.lastErrorMessage:
					self.errorLog(errorText)
					# Remember the error.
					self.lastErrorMessage = errorText
				return
			self.debugLog(u"Data from hub: " + r.content)
			# Convert the response to a Python object.
			try:
				bulb = json.loads(r.content)
			except Exception, e:
				# There was an error in the returned data.
				indigo.server.log(u"Error retrieving LightStrips data from hub.  Error reported: " + str(e))
				isError = True
				errorsDict['bulbId'] = u"Error retrieving LightStrips data from hub. See Indigo log."
				errorsDict['showAlertText'] += errorsDict['bulbId']
				return (False, valuesDict, errorsDict)
			if bulb.get('modelid', "") not in kLightStripsDeviceIDs:
				isError = True
				errorsDict['bulbId'] = u"The selected device is not a LightStrips device. Plesea select a LightStrips device to control."
				errorsDict['showAlertText'] += errorsDict['bulbId']
				return (False, valuesDict, errorsDict)
				
			# Make sure the bulb ID isn't used by another device.
			for otherDeviceId in self.deviceList:
				if otherDeviceId != deviceId:
					otherDevice = indigo.devices[otherDeviceId]
					if valuesDict['bulbId'] == otherDevice.pluginProps.get('bulbId', 0):
						otherDevice = indigo.devices[otherDeviceId]
						isError = True
						errorsDict['bulbId'] = u"This LightStrips device is already being controlled by the \"" + otherDevice.name + "\" Indigo device. Choose a different device to control."
						errorsDict['showAlertText'] += errorsDict['bulbId'] + "\n\n"
				
			# Validate the default brightness is reasonable.
			if valuesDict.get('defaultBrightness', "") != "":
				try:
					defaultBrightness = int(valuesDict['defaultBrightness'])
					if defaultBrightness < 1 or defaultBrightness > 100:
						isError = True
						errorsDict['defaultBrightness'] = u"The Default Brightness must be a number between 1 and 100."
						errorsDict['showAlertText'] += errorsDict['defaultBrightness'] + "\n\n"
				except ValueError:
					isError = True
					errorsDict['defaultBrightness'] = u"The Default Brightness must be a number between 1 and 100."
					errorsDict['showAlertText'] += errorsDict['defaultBrightness'] + "\n\n"
				except Exception, e:
					isError = True
					errorsDict['defaultBrightness'] = u"The Default Brightness must be a number between 1 and 100. Error: " + str(e)
					errorsDict['showAlertText'] += errorsDict['defaultBrightness'] + "\n\n"
					
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
				valuesDict['address'] = self.pluginPrefs.get('address', "") + " (ID " + str(valuesDict['bulbId']) + ")"
				return (True, valuesDict)
				
		#  -- LivingColors Bloom Device --
		elif typeId == "hueLivingColorsBloom":
			# Make sure a device was selected.
			if valuesDict.get('bulbId', "") == "":
				isError = True
				errorsDict['bulbId'] = u"Please select a LivingColors Bloom device to control."
				errorsDict['showAlertText'] += errorsDict['bulbId']
				return (False, valuesDict, errorsDict)
			
			bulbId = valuesDict['bulbId']
			
			# Make sure the device selected is a LivingColors device.
			#   Get the device info directly from the hub.
			command = "http://%s/api/%s/lights/%s" % (self.ipAddress, self.pluginPrefs['hostId'], bulbId)
			self.debugLog(u"Sending URL request: " + command)
			try:
				r = requests.get(command, timeout=kTimeout)
			except requests.exceptions.Timeout:
				errorText = u"Failed to connect to the Hue hub at %s after %i seconds. - Check that the hub is connected and turned on." % (self.ipAddress, kTimeout)
				# Don't display the error if it's been displayed already.
				if errorText != self.lastErrorMessage:
					self.errorLog(errorText)
					# Remember the error.
					self.lastErrorMessage = errorText
				return
			except requests.exceptions.ConnectionError:
				errorText = u"Failed to connect to the Hue hub at %s. - Check that the hub is connected and turned on." % (self.ipAddress)
				# Don't display the error if it's been displayed already.
				if errorText != self.lastErrorMessage:
					self.errorLog(errorText)
					# Remember the error.
					self.lastErrorMessage = errorText
				return
			self.debugLog(u"Data from hub: " + r.content)
			# Convert the response to a Python object.
			try:
				bulb = json.loads(r.content)
			except Exception, e:
				# There was an error in the returned data.
				indigo.server.log(u"Error retrieving LovingColors Bloom data from hub.  Error reported: " + str(e))
				isError = True
				errorsDict['bulbId'] = u"Error retrieving LivingColors Bloom data from hub. See Indigo log."
				errorsDict['showAlertText'] += errorsDict['bulbId']
				return (False, valuesDict, errorsDict)
			if bulb.get('modelid', "") not in kLivingColorsDeviceIDs:
				isError = True
				errorsDict['bulbId'] = u"The selected device is not a LivingColors Bloom device. Plesea select a LivingColors Bloom device to control."
				errorsDict['showAlertText'] += errorsDict['bulbId']
				return (False, valuesDict, errorsDict)
				
			# Make sure the bulb ID isn't used by another device.
			for otherDeviceId in self.deviceList:
				if otherDeviceId != deviceId:
					otherDevice = indigo.devices[otherDeviceId]
					if valuesDict['bulbId'] == otherDevice.pluginProps.get('bulbId', 0):
						otherDevice = indigo.devices[otherDeviceId]
						isError = True
						errorsDict['bulbId'] = u"This LivingColors Bloom device is already being controlled by the \"" + otherDevice.name + "\" Indigo device. Choose a different device to control."
						errorsDict['showAlertText'] += errorsDict['bulbId'] + "\n\n"
				
			# Validate the default brightness is reasonable.
			if valuesDict.get('defaultBrightness', "") != "":
				try:
					defaultBrightness = int(valuesDict['defaultBrightness'])
					if defaultBrightness < 1 or defaultBrightness > 100:
						isError = True
						errorsDict['defaultBrightness'] = u"The Default Brightness must be a number between 1 and 100."
						errorsDict['showAlertText'] += errorsDict['defaultBrightness'] + "\n\n"
				except ValueError:
					isError = True
					errorsDict['defaultBrightness'] = u"The Default Brightness must be a number between 1 and 100."
					errorsDict['showAlertText'] += errorsDict['defaultBrightness'] + "\n\n"
				except Exception, e:
					isError = True
					errorsDict['defaultBrightness'] = u"The Default Brightness must be a number between 1 and 100. Error: " + str(e)
					errorsDict['showAlertText'] += errorsDict['defaultBrightness'] + "\n\n"
					
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
				valuesDict['address'] = self.pluginPrefs.get('address', "") + " (ID " + str(valuesDict['bulbId']) + ")"
				return (True, valuesDict)
				
		#  -- LivingWhites Device --
		elif typeId == "hueLivingWhites":
			# Make sure a device was selected.
			if valuesDict.get('bulbId', "") == "":
				isError = True
				errorsDict['bulbId'] = u"Please select a LivingWhites device to control."
				errorsDict['showAlertText'] += errorsDict['bulbId']
				return (False, valuesDict, errorsDict)
			
			bulbId = valuesDict['bulbId']
			
			# Make sure the device selected is a LightStrips device.
			#   Get the device info directly from the hub.
			command = "http://%s/api/%s/lights/%s" % (self.ipAddress, self.pluginPrefs['hostId'], bulbId)
			self.debugLog(u"Sending URL request: " + command)
			try:
				r = requests.get(command, timeout=kTimeout)
			except requests.exceptions.Timeout:
				errorText = u"Failed to connect to the Hue hub at %s after %i seconds. - Check that the hub is connected and turned on." % (self.ipAddress, kTimeout)
				# Don't display the error if it's been displayed already.
				if errorText != self.lastErrorMessage:
					self.errorLog(errorText)
					# Remember the error.
					self.lastErrorMessage = errorText
				return
			except requests.exceptions.ConnectionError:
				errorText = u"Failed to connect to the Hue hub at %s. - Check that the hub is connected and turned on." % (self.ipAddress)
				# Don't display the error if it's been displayed already.
				if errorText != self.lastErrorMessage:
					self.errorLog(errorText)
					# Remember the error.
					self.lastErrorMessage = errorText
				return
			self.debugLog(u"Data from hub: " + r.content)
			# Convert the response to a Python object.
			try:
				bulb = json.loads(r.content)
			except Exception, e:
				# There was an error in the returned data.
				indigo.server.log(u"Error retrieving LivingWhites data from hub.  Error reported: " + str(e))
				isError = True
				errorsDict['bulbId'] = u"Error retrieving LivingWhites data from hub. See Indigo log."
				errorsDict['showAlertText'] += errorsDict['bulbId']
				return (False, valuesDict, errorsDict)
			if bulb.get('modelid', "") not in kLivingWhitesDeviceIDs:
				isError = True
				errorsDict['bulbId'] = u"The selected device is not a LivingWhites device. Plesea select a LightStrips device to control."
				errorsDict['showAlertText'] += errorsDict['bulbId']
				return (False, valuesDict, errorsDict)
				
			# Make sure the bulb ID isn't used by another device.
			for otherDeviceId in self.deviceList:
				if otherDeviceId != deviceId:
					otherDevice = indigo.devices[otherDeviceId]
					if valuesDict['bulbId'] == otherDevice.pluginProps.get('bulbId', 0):
						otherDevice = indigo.devices[otherDeviceId]
						isError = True
						errorsDict['bulbId'] = u"This LivingWhites device is already being controlled by the \"" + otherDevice.name + "\" Indigo device. Choose a different device to control."
						errorsDict['showAlertText'] += errorsDict['bulbId'] + "\n\n"
				
			# Validate the default brightness is reasonable.
			if valuesDict.get('defaultBrightness', "") != "":
				try:
					defaultBrightness = int(valuesDict['defaultBrightness'])
					if defaultBrightness < 1 or defaultBrightness > 100:
						isError = True
						errorsDict['defaultBrightness'] = u"The Default Brightness must be a number between 1 and 100."
						errorsDict['showAlertText'] += errorsDict['defaultBrightness'] + "\n\n"
				except ValueError:
					isError = True
					errorsDict['defaultBrightness'] = u"The Default Brightness must be a number between 1 and 100."
					errorsDict['showAlertText'] += errorsDict['defaultBrightness'] + "\n\n"
				except Exception, e:
					isError = True
					errorsDict['defaultBrightness'] = u"The Default Brightness must be a number between 1 and 100. Error: " + str(e)
					errorsDict['showAlertText'] += errorsDict['defaultBrightness'] + "\n\n"
					
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
				valuesDict['address'] = self.pluginPrefs.get('address', "") + " (ID " + str(valuesDict['bulbId']) + ")"
				return (True, valuesDict)
				
		#  -- Hue Group --
		if typeId == "hueGroup":
			# Make sure a group was selected.
			if valuesDict.get('groupId', "") == "":
				isError = True
				errorsDict['groupId'] = u"Please select a Hue Group to control."
				errorsDict['showAlertText'] += errorsDict['groupId']
				return (False, valuesDict, errorsDict)
			
			groupId = valuesDict['groupId']
			
			# Make sure the device selected is a Hue group.
			#   Get the group info directly from the hub.
			command = "http://%s/api/%s/groups/%s" % (self.ipAddress, self.pluginPrefs['hostId'], groupId)
			self.debugLog(u"Sending URL request: " + command)
			try:
				r = requests.get(command, timeout=kTimeout)
			except requests.exceptions.Timeout:
				errorText = u"Failed to connect to the Hue hub at %s after %i seconds. - Check that the hub is connected and turned on." % (self.ipAddress, kTimeout)
				# Don't display the error if it's been displayed already.
				if errorText != self.lastErrorMessage:
					self.errorLog(errorText)
					# Remember the error.
					self.lastErrorMessage = errorText
				return
			except requests.exceptions.ConnectionError:
				errorText = u"Failed to connect to the Hue hub at %s. - Check that the hub is connected and turned on." % (self.ipAddress)
				# Don't display the error if it's been displayed already.
				if errorText != self.lastErrorMessage:
					self.errorLog(errorText)
					# Remember the error.
					self.lastErrorMessage = errorText
				return
			self.debugLog(u"Data from hub: " + r.content)
			# Convert the response to a Python object.
			try:
				group = json.loads(r.content)
			except Exception, e:
				# There was an error in the returned data.
				indigo.server.log(u"Error retrieving Hue group data from hub.  Error reported: " + str(e))
				isError = True
				errorsDict['groupId'] = u"Error retrieving Hue group data from hub. See Indigo log."
				errorsDict['showAlertText'] += errorsDict['groupId']
				return (False, valuesDict, errorsDict)
			if group.get('lights', "") == "":
				isError = True
				errorsDict['groupId'] = u"The selected item is not a Hue Group. Plesea select a Hue Group to control."
				errorsDict['showAlertText'] += errorsDict['groupId']
				return (False, valuesDict, errorsDict)
				
			# Make sure the group ID isn't used by another device.
			for otherDeviceId in self.deviceList:
				if otherDeviceId != deviceId:
					otherDevice = indigo.devices[otherDeviceId]
					if valuesDict['groupId'] == otherDevice.pluginProps.get('groupId', 0):
						otherDevice = indigo.devices[otherDeviceId]
						isError = True
						errorsDict['groupId'] = u"This Hue group is already being controlled by the \"" + otherDevice.name + "\" Indigo device. Choose a different Hue group to control."
						errorsDict['showAlertText'] += errorsDict['groupId'] + "\n\n"
				
			# Validate the default brightness is reasonable.
			if valuesDict.get('defaultBrightness', "") != "":
				try:
					defaultBrightness = int(valuesDict['defaultBrightness'])
					if defaultBrightness < 1 or defaultBrightness > 100:
						isError = True
						errorsDict['defaultBrightness'] = u"The Default Brightness must be a number between 1 and 100."
						errorsDict['showAlertText'] += errorsDict['defaultBrightness'] + "\n\n"
				except ValueError:
					isError = True
					errorsDict['defaultBrightness'] = u"The Default Brightness must be a number between 1 and 100."
					errorsDict['showAlertText'] += errorsDict['defaultBrightness'] + "\n\n"
				except Exception, e:
					isError = True
					errorsDict['defaultBrightness'] = u"The Default Brightness must be a number between 1 and 100. Error: " + str(e)
					errorsDict['showAlertText'] += errorsDict['defaultBrightness'] + "\n\n"
					
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
				valuesDict['address'] = self.pluginPrefs.get('address', "") + " (GID " + str(valuesDict['groupId']) + ")"
				return (True, valuesDict)
				
		# -- Hue Device Attribute Controller (Virtual Dimmer Device) --
		elif typeId == "hueAttributeController":
			# Make sure a Hue device was selected.
			if valuesDict.get('bulbDeviceId', "") == "":
				isError = True
				errorsDict['bulbDeviceId'] = u"Please select a Hue device whose attribute will be controlled."
				errorsDict['showAlertText'] += errorsDict['bulbDeviceId']
				
			# Make sure an Attribute to Control is selected.
			if valuesDict.get('attributeToControl', "") == "":
				isError = True
				errorsDict['attributeToControl'] = u"Please select an Attribute to Control."
				errorsDict['showAlertText'] += errorsDict['attributeToControl']
				
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
					
			# Validate the default on level.
			if valuesDict.get('defaultOnLevel', "") != "":
				try:
					onLevel = int(valuesDict['defaultOnLevel'])
					if onLevel < 1 or onLevel > 100:
						isError = True
						errorsDict['defaultOnLevel'] = u"The Default On Level must be a whole number between 1 and 100."
						errorsDict['showAlertText'] += errorsDict['defaultOnLevel'] + "\n\n"
				except ValueError:
					isError = True
					errorsDict['defaultOnLevel'] = u"The Default On Level must be a whole number between 1 and 100."
					errorsDict['showAlertText'] += errorsDict['defaultOnLevel'] + "\n\n"
				except Execption, e:
					isError = True
					errorsDict['defaultOnLevel'] = u"The Default On Level must be a whole number between 1 and 100. Error: " + str(e)
					errorsDict['showAlertText'] += errorsDict['defaultOnLevel'] + "\n\n"
					
			# Show errors if there are any.
			if isError:
				errorsDict['showAlertText'] = errorsDict['showAlertText'].strip()
				return (False, valuesDict, errorsDict)

			else:
				# Define the device's address to appear in Indigo.
				# The address is the destination Hue device's device ID plus the attribute to control.
				device = indigo.devices[int(valuesDict.get('bulbDeviceId', 0))]
				valuesDict['address'] = str(device.id) + u" (" + valuesDict['attributeToControl'] + u")"
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
		modelId = device.pluginProps.get('modelId', False)
		
		# Make sure we're still paired with the Hue hub.
		if self.paired == False:
			isError = True
			errorsDict['device'] = u"Not currently paired with the Hue hub. Use the Configure... option in the Plugins -> Hue Lights menu to pair Hue Lights with the Hue hub first."
			errorsDict['showAlertText'] += errorsDict['device']
			return (False, valuesDict, errorsDict)
			
		### SET BRIGHTNESS WITH RAMP RATE ###
		if typeId == "setBrightness":
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
				errorsDict['device'] = u"This action cannot be applied to Hue Device Attribute Controllers. Please cancel the configuration dialog and select a Hue device to control."
				errorsDict['showAlertText'] += errorsDict['device'] + "\n\n"
			# If it is a valid device, check everything else.
			elif not brightnessSource:
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
			rampRate = valuesDict.get('rate', "")
			
			# First make sure this is a Hue device and not an attribute controller.
			if device.deviceTypeId == "hueAttributeController":
				isError = True
				errorsDict['device'] = u"This action cannot be applied to Hue Device Attribute Controllers. Please cancel the configuration dialog and select a Hue device to control."
				errorsDict['showAlertText'] += errorsDict['device'] + "\n\n"
			# If it is a valid device, check everything else.
			# Make sure this device can handle color.
			elif modelId not in kHueBulbDeviceIDs and modelId not in kLightStripsDeviceIDs and modelId not in kLivingColorsDeviceIDs:
				isError = True
				errorsDict['device'] = u"The \"%s\" device does not support color. Choose a different device." % (device.name)
				errorsDict['showAlertText'] += errorsDict['device'] + "\n\n"
				
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
				descString += u"set hue device RGB levels to " + str(red) + ", " + str(green) + ", " + str(blue)
				if len(valuesDict.get('rate', "")) > 0:
					descString += u" with ramp rate " + str(rampRate)
					
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
			brightness = valuesDict.get('brightness', "")
			if brightness == "":
				brightness = device.states['brightnessLevel']
				valuesDict['brightness'] = brightness
			rampRate = valuesDict.get('rate', "")
			
			# First make sure this is a Hue device and not an attribute controller.
			if device.deviceTypeId == "hueAttributeController":
				isError = True
				errorsDict['device'] = u"This action cannot be applied to Hue Device Attribute Controllers. Please cancel the configuration dialog and select a Hue device to control."
				errorsDict['showAlertText'] += errorsDict['device'] + "\n\n"
			# If it is a valid device, check everything else.
			# Make sure this device can handle color.
			elif modelId not in kHueBulbDeviceIDs and modelId not in kLightStripsDeviceIDs and modelId not in kLivingColorsDeviceIDs:
				isError = True
				errorsDict['device'] = u"The \"%s\" device does not support color. Choose a different device." % (device.name)
				errorsDict['showAlertText'] += errorsDict['device'] + "\n\n"
				
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
				errorsDict['saturation'] = "Invalid Saturation value: " + str(e)
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
				descString += u"set hue device hue, sturation, brightness to " + str(hue) + ", " + str(saturation) + ", " + str(brightness)
				if len(valuesDict.get('rate', "")) > 0:
					descString += u" with ramp rate " + str(rampRate)
					
		### SET xyY ###
		elif typeId == "setXYY":
			# Check the xyY values.
			colorX = valuesDict.get('xyy_x', 0)
			if colorX == "":
				colorX = 0
				valuesDict['xyy_x'] = colorX
			colorY = valuesDict.get('xyy_y', 0)
			if colorY == "":
				colorY = 0
				valuesDict['xyy_y'] = colorY
			brightness = valuesDict.get('xyy_Y', 0)
			if brightness == "":
				brightness = float(device.states['brightnessLevel']) / 100.0
				valuesDict['brightness'] = brightness
			rampRate = valuesDict.get('rate', "")
			
			# First make sure this is a Hue device and not an attribute controller.
			if device.deviceTypeId == "hueAttributeController":
				isError = True
				errorsDict['device'] = u"This action cannot be applied to Hue Device Attribute Controllers. Please cancel the configuration dialog and select a Hue device to control."
				errorsDict['showAlertText'] += errorsDict['device'] + "\n\n"
			# If it is a valid device, check everything else.
			# Make sure this device can handle color.
			elif modelId not in kHueBulbDeviceIDs and modelId not in kLightStripsDeviceIDs and modelId not in kLivingColorsDeviceIDs:
				isError = True
				errorsDict['device'] = u"The \"%s\" device does not support color. Choose a different device." % (device.name)
				errorsDict['showAlertText'] += errorsDict['device'] + "\n\n"
				
			try:
				colorX = float(colorX)
				if (colorX < 0) or (colorX > 1):
					isError = True
					errorsDict['xyy_x'] = "x Chromatisety values must be a number between 0 and 1.0."
					errorsDict['showAlertText'] += errorsDict['xyy_x'] + "\n\n"
			except ValueError:
				isError = True
				errorsDict['xyy_x'] = "x Chromatisety values must be a number between 0 and 1.0."
				errorsDict['showAlertText'] += errorsDict['xyy_x'] + "\n\n"
			except Exception, e:
				isError = True
				errorsDict['xyy_x'] = "Invalid x Chromatisety value: " + str(e)
				errorsDict['showAlertText'] += errorsDict['xyy_x'] + "\n\n"
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
			except Exception, e:
				isError = True
				errorsDict['xyy_y'] = "Invalid y Chromatisety value: " + str(e)
				errorsDict['showAlertText'] += errorsDict['xyy_y'] + "\n\n"
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
			except Exception, e:
				isError = True
				errorsDict['xyy_Y'] = "Invalid Y Luminosity value: " + str(e)
				errorsDict['showAlertText'] += errorsDict['xyy_Y'] + "\n\n"
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
				descString += u"set hue device xyY chromatisety to " + str(colorX) + ", " + str(colorY) + ", " + str(brightness)
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
			
			# First make sure this is a Hue device and not an attribute controller.
			if device.deviceTypeId == "hueAttributeController":
				isError = True
				errorsDict['device'] = u"This action cannot be applied to Hue Device Attribute Controllers. Please cancel the configuration dialog and select a Hue device to control."
				errorsDict['showAlertText'] += errorsDict['device'] + "\n\n"
			# If it is a valid device, check everything else.
			# Make sure this device can handle color temperature changes.
			elif device.deviceTypeId != "hueGroup" and modelId not in kHueBulbDeviceIDs:
				isError = True
				errorsDict['device'] = u"The \"%s\" device does not support variable color temperature. Choose a different device." % (device.name)
				errorsDict['showAlertText'] += errorsDict['device'] + "\n\n"
				
			# Validate that a Preset item or Custom was selected.
			if preset == False:
				isError = True
				errorsDict['preset'] = u"Please select an item from the Preset menu."
				errorsDict['showAlertText'] += errorsDict['preset'] + u"\n\n"
			elif preset == "custom":
				try:
					temperature = int(temperature)
					if (temperature < 2000) or (temperature > 6500):
						isError = True
						errorsDict['temperature'] = u"Color Temperature values must be a whole number between 2000 and 6500 Kelvin."
						errorsDict['showAlertText'] += errorsDict['temperature'] + u"\n\n"
				except ValueError:
					isError = True
					errorsDict['temperature'] = u"Color Temperature values must be a whole number between 2000 and 6500 Kelvin."
					errorsDict['showAlertText'] += errorsDict['temperature'] + u"\n\n"
				except Exception, e:
					isError = True
					errorsDict['temperature'] = u"Invalid Color Temperature value: " + str(e)
					errorsDict['showAlertText'] += errorsDict['temperature'] + u"\n\n"
				try:
					brightness = int(brightness)
					if (brightness < 0) or (brightness > 100):
						isError = True
						errorsDict['brightness'] = u"Brightness values must be a whole number between 0 and 100 percent."
						errorsDict['showAlertText'] += errorsDict['brightness'] + u"\n\n"
				except ValueError:
					isError = True
					errorsDict['brightness'] = u"Brightness values must be a whole number between 0 and 100 percent."
					errorsDict['showAlertText'] += errorsDict['brightness'] + u"\n\n"
				except Exception, e:
					isError = True
					errorsDict['brightness'] = u"Invalid Brightness value: " + str(e)
					errorsDict['showAlertText'] += errorsDict['brightness'] + u"\n\n"
			# Validate Ramp Rate.
			if len(rampRate) > 0:
				try:
					rampRate = float(rampRate)
					if (rampRate < 0) or (rampRate > 540):
						isError = True
						errorsDict['rate'] = u"Ramp Rate must be a number between 0 and 540 seconds and can be in increments of 0.1 seconds."
						errorsDict['showAlertText'] += errorsDict['rate'] + u"\n\n"
				except ValueError:
					isError = True
					errorsDict['rate'] = u"Ramp Rate must be a number between 0 and 540 seconds and can be in increments of 0.1 seconds."
					errorsDict['showAlertText'] += errorsDict['rate'] + u"\n\n"
				except Exception, e:
					isError = True
					errorsDict['rate'] = u"Invalid Ramp Rate value: " + str(e)
					errorsDict['showAlertText'] += errorsDict['rate'] + u"\n\n"
			if not isError:
				if preset != "custom":
					descString += u"set hue device color temperature to preset \"" + preset + "\""
				else:
					descString += u"set hue device color temperature to custom value " + str(temperature) + " K at " + str(brightness) + "% brightness"
				if len(valuesDict.get('rate', "")) > 0:
					descString += u" with ramp rate " + str(rampRate)
					
		### EFFECT ###
		elif typeId == "effect":
			# First make sure this is a Hue device and not an attribute controller.
			if device.deviceTypeId == "hueAttributeController":
				isError = True
				errorsDict['device'] = u"This action cannot be applied to Hue Device Attribute Controllers. Please cancel the configuration dialog and select a Hue device to control."
				errorsDict['showAlertText'] += errorsDict['device'] + "\n\n"
			# If it is a valid device, check everything else.
			# Make sure this device can handle the color effect.
			elif device.deviceTypeId != "hueGroup" and modelId not in kHueBulbDeviceIDs and modelId not in kLightStripsDeviceIDs and modelId not in kLivingColorsDeviceIDs:
				isError = True
				errorsDict['device'] = u"The \"%s\" device does not support color effects. Choose a different device." % (device.name)
				errorsDict['showAlertText'] += errorsDict['device'] + "\n\n"
				
			# Make sure an effect was specified.
			effect = valuesDict.get('effect', "")
			if not effect:
				isError = True
				errorsDict['effect'] = u"No effect setting was selected."
				errorsDict['showAlertText'] += errorsDict['effect'] + u"\n\n"
			else:
				descString = u"set hue device effect to \"" + effect + u"\""
				
		### SAVE PRESET ###
		elif typeId == "savePreset":
			# First make sure this is a Hue device and not an attribute controller.
			if device.deviceTypeId == "hueAttributeController":
				isError = True
				errorsDict['device'] = u"This action cannot be applied to Hue Device Attribute Controllers. Please cancel the configuration dialog and select a Hue device to control."
				errorsDict['showAlertText'] += errorsDict['device'] + "\n\n"
			# If it is a valid device, check everything else.
			# Make sure this device can handle the color effect.
			elif modelId not in kCompatibleDeviceIDs:
				isError = True
				errorsDict['device'] = u"The \"%s\" device is not a compatible Hue device. Please choose a different device." % (device.name)
				errorsDict['showAlertText'] += errorsDict['device'] + "\n\n"
				
			# Make sure the Preset Name isn't too long.
			if len(valuesDict.get('presetName', "")) > 50:
				isError = True
				errorsDict['presetName'] = u"The Preset Name is too long. Please use a name that is no more than 50 characters long."
				errorsDict['showAlertText'] += errorsDict['presetName'] + "\n\n"
				
			# Make sure a Preset was selected.
			presetId = valuesDict.get('presetId', "")
			if presetId == "":
				isError = True
				errorsDict['presetId'] = u"No Preset was selected."
				errorsDict['showAlertText'] += errorsDict['presetId'] + u"\n\n"
			else:
				descString = u"save hue device settings to preset " + str(presetId)
			
			# Validate Ramp Rate.
			rampRate = valuesDict.get('rate', "")
			if len(rampRate) > 0:
				try:
					rampRate = float(rampRate)
					if (rampRate < 0) or (rampRate > 540):
						isError = True
						errorsDict['rate'] = u"Ramp Rate must be a number between 0 and 540 seconds and can be in increments of 0.1 seconds."
						errorsDict['showAlertText'] += errorsDict['rate'] + u"\n\n"
				except ValueError:
					isError = True
					errorsDict['rate'] = u"Ramp Rate must be a number between 0 and 540 seconds and can be in increments of 0.1 seconds."
					errorsDict['showAlertText'] += errorsDict['rate'] + u"\n\n"
				except Exception, e:
					isError = True
					errorsDict['rate'] = u"Invalid Ramp Rate value: " + str(e)
					errorsDict['showAlertText'] += errorsDict['rate'] + u"\n\n"
				
		### RECALL PRESET ###
		elif typeId == "recallPreset":
			# First make sure this is a Hue device and not an attribute controller.
			if device.deviceTypeId == "hueAttributeController":
				isError = True
				errorsDict['device'] = u"This action cannot be applied to Hue Device Attribute Controllers. Please cancel the configuration dialog and select a Hue device to control."
				errorsDict['showAlertText'] += errorsDict['device'] + "\n\n"
			# If it is a valid device, check everything else.
			# Make sure this device can handle the color effect.
			elif modelId not in kCompatibleDeviceIDs:
				isError = True
				errorsDict['device'] = u"The \"%s\" device is not a compatible Hue device. Please choose a different device." % (device.name)
				errorsDict['showAlertText'] += errorsDict['device'] + "\n\n"
				
			# Make sure a Preset was selected.
			presetId = valuesDict.get('presetId', "")
			if presetId == "":
				isError = True
				errorsDict['presetId'] = u"No Preset was selected."
				errorsDict['showAlertText'] += errorsDict['presetId'] + u"\n\n"
			else:
				# Make sure the preset isn't empty.
				if len(self.pluginPrefs['presets'][int(presetId) - 1][1]) < 1:
					isError = True
					errorsDict['presetId'] = u"This Preset is empty. Please choose a Preset with data already saved to it (one with an asterisk (*) next to the number)."
					errorsDict['showAlertText'] += errorsDict['presetId'] + u"\n\n"
				else:
					descString = u"recall hue device settings from preset " + str(presetId)
					
			# Validate Ramp Rate.
			rampRate = valuesDict.get('rate', "")
			if len(rampRate) > 0:
				try:
					rampRate = float(rampRate)
					if (rampRate < 0) or (rampRate > 540):
						isError = True
						errorsDict['rate'] = u"Ramp Rate must be a number between 0 and 540 seconds and can be in increments of 0.1 seconds."
						errorsDict['showAlertText'] += errorsDict['rate'] + u"\n\n"
				except ValueError:
					isError = True
					errorsDict['rate'] = u"Ramp Rate must be a number between 0 and 540 seconds and can be in increments of 0.1 seconds."
					errorsDict['showAlertText'] += errorsDict['rate'] + u"\n\n"
				except Exception, e:
					isError = True
					errorsDict['rate'] = u"Invalid Ramp Rate value: " + str(e)
					errorsDict['showAlertText'] += errorsDict['rate'] + u"\n\n"

		### CATCH ALL ###
		else:
			isError = True
			errorsDict['presetId'] = u"The typeId \"" + str(typeId) + "\" wasn't recognized."
			errorsDict['showAlertText'] += errorsDict['presetId'] + u"\n\n"
			
		# Define the description value.
		valuesDict['description'] = descString
		# Return an error if one exists.
		if isError:
			errorsDict['showAlertText'] = errorsDict['showAlertText'].strip()
			return (False, valuesDict, errorsDict)
			
		return (True, valuesDict)
		
	# Bulb List Generator
	########################################
	def bulbListGenerator(self, filter="", valuesDict=None, typeId="", targetId=0):
		returnBulbList = list()
		# Used in actions that need a list of Hue hub devices.
		self.debugLog(u"bulbListGenerator called.\n  filter: %s\n  valuesDict: %s\n  typeId: %s\n  targetId: %s" % (filter, valuesDict, typeId, targetId))
		
		# Iterate over our bulbs, and return the available list in Indigo's format
		for bulbId, bulbDetails in self.lightsDict.items():
			# First, get the device info directly from the hub (if the typeId is not blank).
			if typeId != "":
				command = "http://%s/api/%s/lights/%s" % (self.ipAddress, self.pluginPrefs['hostId'], bulbId)
				self.debugLog(u"Sending URL request: " + command)
				try:
					r = requests.get(command, timeout=kTimeout)
				except requests.exceptions.Timeout:
					errorText = u"Failed to connect to the Hue hub at %s after %i seconds. - Check that the hub is connected and turned on." % (self.ipAddress, kTimeout)
					# Don't display the error if it's been displayed already.
					if errorText != self.lastErrorMessage:
						self.errorLog(errorText)
						# Remember the error.
						self.lastErrorMessage = errorText
				except requests.exceptions.ConnectionError:
					errorText = u"Failed to connect to the Hue hub at %s. - Check that the hub is connected and turned on." % (self.ipAddress)
					# Don't display the error if it's been displayed already.
					if errorText != self.lastErrorMessage:
						self.errorLog(errorText)
						# Remember the error.
						self.lastErrorMessage = errorText
				try:
					# If the content contains non-ASCII characters, this will fail.
					self.debugLog(u"Data from hub: " + r.content)
				except Exception, e:
					self.debugLog(u"Data from hub could not be displayed because of an error: " + str(e))
				# Convert the response to a Python object.
				try:
					bulb = json.loads(r.content)
				except Exception, e:
					# There was an error in the returned data.
					indigo.server.log(u"Error retrieving Hue bulb data from hub.  Error reported: " + str(e))
					
					
			# Next, limit the list to the type of devices indicated in the filter variable.
			if typeId == "":
				# If no typeId exists, list all devices.
				returnBulbList.append([bulbId, bulbDetails["name"]])
			elif typeId == "hueBulb" and bulb.get('modelid', "") in kHueBulbDeviceIDs:
				returnBulbList.append([bulbId, bulbDetails["name"]])
			elif typeId == "hueLightStrips" and bulb.get('modelid', "") in kLightStripsDeviceIDs:
				returnBulbList.append([bulbId, bulbDetails["name"]])
			elif typeId == "hueLivingColorsBloom" and bulb.get('modelid', "") in kLivingColorsDeviceIDs:
				returnBulbList.append([bulbId, bulbDetails["name"]])
			elif typeId == "hueLivingWhites" and bulb.get('modelid', "") in kLivingWhitesDeviceIDs:
				returnBulbList.append([bulbId, bulbDetails["name"]])
			
		# Debug
		self.debugLog(u"Return bulb list is %s" % returnBulbList)
		
		return returnBulbList
		
	# Group List Generator
	########################################
	def groupListGenerator(self, filter="", valuesDict=None, typeId="", targetId=0):
		returnGroupList = list()
		# Used in actions that need a list of Hue hub groups.
		self.debugLog(u"groupListGenerator called.\n  filter: %s\n  valuesDict: %s\n  typeId: %s\n  targetId: %s" % (filter, valuesDict, typeId, targetId))
		
		# Add the special default zero group to the beginning of the list.
		returnGroupList.append([0, "0: (All Hue Devices)"])

		# Iterate over our groups, and return the available list in Indigo's format
		for groupId, groupDetails in self.groupsDict.items():
			# First, get the group info directly from the hub (if the typeId is not blank).
			if typeId != "":
				command = "http://%s/api/%s/groups/%s" % (self.ipAddress, self.pluginPrefs['hostId'], groupId)
				self.debugLog(u"Sending URL request: " + command)
				try:
					r = requests.get(command, timeout=kTimeout)
				except requests.exceptions.Timeout:
					errorText = u"Failed to connect to the Hue hub at %s after %i seconds. - Check that the hub is connected and turned on." % (self.ipAddress, kTimeout)
					# Don't display the error if it's been displayed already.
					if errorText != self.lastErrorMessage:
						self.errorLog(errorText)
						# Remember the error.
						self.lastErrorMessage = errorText
				except requests.exceptions.ConnectionError:
					errorText = u"Failed to connect to the Hue hub at %s. - Check that the hub is connected and turned on." % (self.ipAddress)
					# Don't display the error if it's been displayed already.
					if errorText != self.lastErrorMessage:
						self.errorLog(errorText)
						# Remember the error.
						self.lastErrorMessage = errorText
				try:
					# If the content contains non-ASCII characters, this will fail.
					self.debugLog(u"Data from hub: " + r.content)
				except Exception, e:
					self.debugLog(u"Data from hub could not be displayed because of an error: " + str(e))
				# Convert the response to a Python object.
				try:
					group = json.loads(r.content)
				except Exception, e:
					# There was an error in the returned data.
					indigo.server.log(u"Error retrieving Hue group data from hub.  Error reported: " + str(e))
					
			returnGroupList.append([groupId, str(groupId) + ": " + groupDetails["name"]])
			
		# Debug
		self.debugLog(u"Return group list is %s" % returnGroupList)
		
		return returnGroupList
		
	# Bulb Device List Generator
	########################################
	def bulbDeviceListGenerator(self, filter="", valuesDict=None, typeId="", targetId=0):
		returnDeviceList = list()
		# Used in actions that need a list of Hue Lights plugin devices that aren't
		#   attribute controllers or groups.
		
		# Iterate over our devices, and return the available devices as a 2-tupple list.
		for deviceId in self.deviceList:
			device = indigo.devices[deviceId]
			if device.deviceTypeId != "hueAttributeController":
				returnDeviceList.append([deviceId, device.name])
			
		# Debug
		self.debugLog(u"Return Hue device list is %s" % returnDeviceList)
		
		return returnDeviceList
		
	# Generate Presets List
	########################################
	def presetListGenerator(self, filter="", valuesDict=None, typeId="", deviceId=0):
		self.debugLog(u"presetListGenerator called. typeId: " + str(typeId) + u", targetId: " + str(deviceId))
		
		theList = list()	# Menu item list.
		
		presets = self.pluginPrefs.get('presets', None)
		self.debugLog(u"Presets in plugin prefs:\n" + str(presets))
		
		if presets != None:
			presetNumber = 0
				
			for preset in presets:
				# Determine whether the Preset has saved data or not.
				hasData = ""
				if len(presets[presetNumber][1]) > 0:
					hasData = "*"
					
				presetNumber += 1
				presetName = preset[0]
				theList.append((presetNumber, hasData + str(presetNumber) + ": " + presetName))
		else:
			theList.append((0, "-- no presets --"))
			
		return theList
		
	# Did Device Communications Properties Change?
	########################################
	def didDeviceCommPropertyChange(self, origDev, newDev):
		# Automatically called by plugin host when device properties change.
		self.debugLog("didDeviceCommPropertyChange called.")
		# We only want to reload the device if the bulbId changes.
		if origDev.deviceTypeId != "hueAttributeController" and origDev.deviceTypeId != "hueGroup":
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
			if newValue.__class__ == float:
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
		# Get device status.
		
		device = indigo.devices[deviceId]
		self.debugLog(u"Get device status for " + device.name)
		# Proceed based on the device type.
		if device.deviceTypeId == "hueGroup":
			# This is a Hue Group device. Redirect the call to the group status update.
			self.getGroupStatus(deviceId)
			return
		else:
			# Get the bulbId from the device properties.
			bulbId = device.pluginProps.get('bulbId', False)
			# if the bulbId exists, get the device status.
			if bulbId:
				command = "http://%s/api/%s/lights/%s" % (self.ipAddress, self.pluginPrefs['hostId'], bulbId)
				self.debugLog(u"Sending URL request: " + command)
				try:
					r = requests.get(command, timeout=kTimeout)
				except requests.exceptions.Timeout:
					errorText = u"Failed to connect to the Hue hub at %s after %i seconds. - Check that the hub is connected and turned on." % (self.ipAddress, kTimeout)
					# Don't display the error if it's been displayed already.
					if errorText != self.lastErrorMessage:
						self.errorLog(errorText)
						# Remember the error.
						self.lastErrorMessage = errorText
					return
				except requests.exceptions.ConnectionError:
					errorText = u"Failed to connect to the Hue hub at %s. - Check that the hub is connected and turned on." % (self.ipAddress)
					# Don't display the error if it's been displayed already.
					if errorText != self.lastErrorMessage:
						self.errorLog(errorText)
						# Remember the error.
						self.lastErrorMessage = errorText
					return
			# The Indigo device
			#   must not yet be configured. Just return gracefully.
			else:
				self.debugLog(u"No bulbId exists in the \"%s\" device. New device perhaps." % (device.name))
				return
			
		self.debugLog(u"Data from hub: " + r.content)
		# Convert the response to a Python object.
		try:
			bulb = json.loads(r.content)
		except Exception, e:
			indigo.server.log(u"Error retrieving Hue bulb status: " + str(e))
			return False
			
		#
		### Parse Data
		#
		# Data common to all device types...
		#   Value assignments.
		brightness = bulb['state']['bri']
		onState = bulb['state']['on']
		alert = bulb['state']['alert']
		effect = bulb['state']['effect']
		online = bulb['state']['reachable']
		nameOnHub = bulb['name']
		modelId = bulb['modelid']
		
		#   Value manipulation.
		# Convert brightness from 0-255 range to 0-100 range.
		brightnessLevel = int(round(brightness / 255.0 * 100.0))
		# Compensate for incorrect rounding to zero if original brightness is not zero.
		if brightnessLevel == 0 and brightness > 0:
			brightnessLevel = 1
		# If the "on" state is False, it doesn't matter what brightness the hub
		#   is reporting, the effective brightness is zero.
		if onState == False:
			brightnessLevel = 0
		
		#   Update Indigo states and properties common to all Hue devices.	
		tempProps = device.pluginProps
		# Update the Hue device name.
		if nameOnHub != device.pluginProps.get('nameOnHub', False):
			tempProps['nameOnHub'] = nameOnHub
			self.updateDeviceProps(device, tempProps)
		# Update the modelId.
		if modelId != device.pluginProps.get('modelId', ""):
			tempProps['modelId'] = modelId
			self.updateDeviceProps(device, tempProps)
		# Update the online status of the Hue device.
		self.updateDeviceState(device, 'online', online)
		# Update the error state if needed.
		if not online:
			device.setErrorStateOnServer("disconnected")
		else:
			device.setErrorStateOnServer("")
		# Update the alert state of the Hue device.
		self.updateDeviceState(device, 'alertMode', alert)
		# Update the effect state of the Hue device.
		self.updateDeviceState(device, 'effect', effect)
			
		# Device-type-specific data...
		# -- Hue Bulbs --
		if modelId in kHueBulbDeviceIDs:
			#   Value assignment.
			hue = bulb['state']['hue']
			saturation = bulb['state']['sat']
			colorX = bulb['state']['xy'][0]
			colorY = bulb['state']['xy'][1]
			colorRed = 255		# Initialize for later
			colorGreen = 255	# Initialize for later
			colorBlue = 255		# Initialize for later
			colorTemp = bulb['state']['ct']
			colorMode = bulb['state']['colormode']
			
			#   Value manipulation.
			# Convert from HSB to RGB, scaling the hue and saturation values appropriately.
			hsb = HSVColor(hue / 182.0, saturation / 255.0, brightness / 255.0)
			rgb = hsb.convert_to('rgb', rgb_type='wide_gamut_rgb')
			colorRed = int(round(rgb.rgb_r))
			colorGreen = int(round(rgb.rgb_g))
			colorBlue = int(round(rgb.rgb_b))
			# Convert saturation from 0-255 scale to 0-100 scale.
			saturation = int(round(saturation / 255.0 * 100.0))
			# Convert hue from 0-65535 scale to 0-360 scale.
			hue = int(round(hue / 182.0))
			# Must first test color temp value. If it's zero, the formula throws a divide by zero execption.
			if colorTemp > 0:
				# Converting from mireds to Kelvin.
				colorTemp = int(round(1000000.0/colorTemp))
			else:
				colorTemp = 0

			# Update the Indigo device if the Hue device is on.
			if onState == True:
				# Update the brightness level if it's different.
				if device.states['brightnessLevel'] != brightnessLevel:
					# Log the update.
					indigo.server.log(u"\"" + device.name + "\" on to " + str(brightnessLevel), 'Updated')
					self.updateDeviceState(device, 'brightnessLevel', brightnessLevel)
				# Hue Degrees (0-360).
				self.updateDeviceState(device, 'hue', hue)
				# Saturation (0-100).
				self.updateDeviceState(device, 'saturation', saturation)
				# CIE XY Cromaticity.
				self.updateDeviceState(device, 'colorX', colorX)
				self.updateDeviceState(device, 'colorY', colorY)
				# Color Temperature (converted from 154-500 mireds to 6494-2000 K).
				self.updateDeviceState(device, 'colorTemp', colorTemp)
				# Color Mode.
				self.updateDeviceState(device, 'colorMode', colorMode)
				# Red, Green, Blue.
				self.updateDeviceState(device, 'colorRed', colorRed)
				self.updateDeviceState(device, 'colorGreen', colorGreen)
				self.updateDeviceState(device, 'colorBlue', colorBlue)
				
			elif onState == False:
				# Hue device is off. Set brightness to zero.
				if device.states['brightnessLevel'] != 0:
					# Log the update.
					indigo.server.log(u"\"" + device.name + "\" off", 'Updated')
					self.updateDeviceState(device, 'brightnessLevel', 0)
				# Hue Degrees (convert from 0-65535 to 0-360).
				self.updateDeviceState(device, 'hue', hue)
				# Saturation (convert from 0-255 to 0-100).
				self.updateDeviceState(device, 'saturation', saturation)
				# CIE XY Cromaticity.
				self.updateDeviceState(device, 'colorX', colorX)
				self.updateDeviceState(device, 'colorY', colorY)
				# Color Temperature (convert from 154-500 mireds to 6494-2000 K).
				self.updateDeviceState(device, 'colorTemp', colorTemp)
				# Color Mode.
				self.updateDeviceState(device, 'colorMode', colorMode)
				# Red, Green, and Blue Color.
				#    If the bulb is off, all RGB values should be 0.
				self.updateDeviceState(device, 'colorRed', 0)
				self.updateDeviceState(device, 'colorGreen', 0)
				self.updateDeviceState(device, 'colorBlue', 0)
			else:
				# Unrecognized on state, but not important enough to mention in regular log.
				self.debugLog(u"Hue bulb unrecognized on state given by hub: " + str(bulb['state']['on']))
				
			# Update any Hue Device Attribute Controller virtual dimmers associated with this bulb.
			for controlDeviceId in self.controlDeviceList:
				controlDevice = indigo.devices[int(controlDeviceId)]
				attributeToControl = controlDevice.pluginProps.get('attributeToControl', None)
				if deviceId == int(controlDevice.pluginProps.get('bulbDeviceId', None)):
					# Device has attributes controlled by a Hue Device Attribute Controler.
					#   Update the controller device based on current bulb device states.
					#   But if the control destination device is off, update the value of the
					#   controller (virtual dimmer) to 0.
					if device.onState == True:
						# Destination Hue Bulb device is on, update Attribute Controller brightness.
						if attributeToControl == "hue":
							# Convert hue scale from 0-360 to 0-100.
							self.updateDeviceState(controlDevice, 'brightnessLevel', int(round(hue / 360.0 * 100.0)))
						elif attributeToControl == "saturation":
							self.updateDeviceState(controlDevice, 'brightnessLevel', saturation)
						elif attributeToControl == "colorRed":
							# Convert RGB scale from 0-255 to 0-100.
							self.updateDeviceState(controlDevice, 'brightnessLevel', int(round(colorRed / 255.0 * 100.0)))
						elif attributeToControl == "colorGreen":
							# Convert RGB scale from 0-255 to 0-100.
							self.updateDeviceState(controlDevice, 'brightnessLevel', int(round(colorGreen / 255.0 * 100.0)))
						elif attributeToControl == "colorBlue":
							# Convert RGB scale from 0-255 to 0-100.
							self.updateDeviceState(controlDevice, 'brightnessLevel', int(round(colorBlue / 255.0 * 100.0)))
						elif attributeToControl == "colorTemp":
							# Convert color temperature scale from 2000-6500 to 0-100.
							self.updateDeviceState(controlDevice, 'brightnessLevel', int(round((colorTemp - 2000.0) / 4500.0 * 100.0)))
					else:
						# Hue Device is off.  Set Attribute Controller device brightness level to 0.
						self.updateDeviceState(controlDevice, 'brightnessLevel', 0)
						
		# -- LightStrips --
		elif modelId in kLightStripsDeviceIDs:
			#   Value assignment.
			saturation = bulb['state']['sat']
			hue = bulb['state']['hue']
			colorX = bulb['state']['xy'][0]
			colorY = bulb['state']['xy'][1]
			colorRed = 255		# Initialize for later
			colorGreen = 255	# Initialize for later
			colorBlue = 255		# Initialize for later
			colorMode = bulb['state']['colormode']
			
			#   Value manipulation.
			# Convert from HSB to RGB, scaling the hue and saturation values appropriately.
			hsb = HSVColor(hue / 182.0, saturation / 255.0, brightness / 255.0)
			rgb = hsb.convert_to('rgb', rgb_type='wide_gamut_rgb')
			colorRed = int(round(rgb.rgb_r))
			colorGreen = int(round(rgb.rgb_g))
			colorBlue = int(round(rgb.rgb_b))
			# Convert saturation from 0-255 scale to 0-100 scale.
			saturation = int(round(saturation / 255.0 * 100.0))
			# Convert hue from 0-65535 scale to 0-360 scale.
			hue = int(round(hue / 182.0))
			
			# Update the Indigo device if the Hue device is on.
			if onState == True:
				# Update the brightness level if it's different.
				if device.states['brightnessLevel'] != brightnessLevel:
					# Log the update.
					indigo.server.log(u"\"" + device.name + "\" on to " + str(brightnessLevel), 'Updated')
					self.updateDeviceState(device, 'brightnessLevel', brightnessLevel)
				# Hue Degrees (0-360).
				self.updateDeviceState(device, 'hue', hue)
				#   Saturation (0-100).
				self.updateDeviceState(device, 'saturation', saturation)
				#   CIE XY Cromaticity.
				self.updateDeviceState(device, 'colorX', colorX)
				self.updateDeviceState(device, 'colorY', colorY)
				#   Color Mode.
				self.updateDeviceState(device, 'colorMode', colorMode)
				#   Red, Green, Blue.
				self.updateDeviceState(device, 'colorRed', colorRed)
				self.updateDeviceState(device, 'colorGreen', colorGreen)
				self.updateDeviceState(device, 'colorBlue', colorBlue)
				
			elif onState == False:
				# Hue device is off. Set brightness to zero.
				if device.states['brightnessLevel'] != 0:
					# Log the update.
					indigo.server.log(u"\"" + device.name + "\" off", 'Updated')
					self.updateDeviceState(device, 'brightnessLevel', 0)
				# Hue Degrees (convert from 0-65535 to 0-360).
				self.updateDeviceState(device, 'hue', hue)
				# Saturation (convert from 0-255 to 0-100).
				self.updateDeviceState(device, 'saturation', saturation)
				# CIE XY Cromaticity.
				self.updateDeviceState(device, 'colorX', colorX)
				self.updateDeviceState(device, 'colorY', colorY)
				# Color Mode.
				self.updateDeviceState(device, 'colorMode', colorMode)
				# Red, Green, and Blue Color.
				#    If the bulb is off, all RGB values should be 0.
				self.updateDeviceState(device, 'colorRed', 0)
				self.updateDeviceState(device, 'colorGreen', 0)
				self.updateDeviceState(device, 'colorBlue', 0)
			else:
				# Unrecognized on state, but not important enough to mention in regular log.
				self.debugLog(u"LightStrips unrecognized on state given by hub: " + str(bulb['state']['on']))
				
			# Update any Hue Device Attribute Controller virtual dimmers associated with this bulb.
			for controlDeviceId in self.controlDeviceList:
				controlDevice = indigo.devices[int(controlDeviceId)]
				attributeToControl = controlDevice.pluginProps.get('attributeToControl', None)
				if deviceId == int(controlDevice.pluginProps.get('bulbDeviceId', None)):
					# Device has attributes controlled by a Hue Device Attribute Controler.
					#   Update the controller device based on current bulb device states.
					#   But if the control destination device is off, update the value of the
					#   controller (virtual dimmer) to 0.
					if device.onState == True:
						# Destination Hue Bulb device is on, update Attribute Controller brightness.
						if attributeToControl == "hue":
							# Convert hue scale from 0-360 to 0-100.
							self.updateDeviceState(controlDevice, 'brightnessLevel', int(round(hue / 360.0 * 100.0)))
						elif attributeToControl == "saturation":
							self.updateDeviceState(controlDevice, 'brightnessLevel', saturation)
						elif attributeToControl == "colorRed":
							# Convert RGB scale from 0-255 to 0-100.
							self.updateDeviceState(controlDevice, 'brightnessLevel', int(round(colorRed / 255.0 * 100.0)))
						elif attributeToControl == "colorGreen":
							# Convert RGB scale from 0-255 to 0-100.
							self.updateDeviceState(controlDevice, 'brightnessLevel', int(round(colorGreen / 255.0 * 100.0)))
						elif attributeToControl == "colorBlue":
							# Convert RGB scale from 0-255 to 0-100.
							self.updateDeviceState(controlDevice, 'brightnessLevel', int(round(colorBlue / 255.0 * 100.0)))
					else:
						# Hue Device is off.  Set Attribute Controller device brightness level to 0.
						self.updateDeviceState(controlDevice, 'brightnessLevel', 0)
						
		# -- LivingColors Bloom --
		elif modelId in kLivingColorsDeviceIDs:
			#   Value assignment.
			saturation = bulb['state']['sat']
			hue = bulb['state']['hue']
			colorX = bulb['state']['xy'][0]
			colorY = bulb['state']['xy'][1]
			colorRed = 255		# Initialize for later
			colorGreen = 255	# Initialize for later
			colorBlue = 255		# Initialize for later
			colorMode = bulb['state']['colormode']
			
			#   Value manipulation.
			# Convert from HSB to RGB, scaling the hue and saturation values appropriately.
			hsb = HSVColor(hue / 182.0, saturation / 255.0, brightness / 255.0)
			rgb = hsb.convert_to('rgb', rgb_type='wide_gamut_rgb')
			colorRed = int(round(rgb.rgb_r))
			colorGreen = int(round(rgb.rgb_g))
			colorBlue = int(round(rgb.rgb_b))
			# Convert saturation from 0-255 scale to 0-100 scale.
			saturation = int(round(saturation / 255.0 * 100.0))
			# Convert hue from 0-65535 scale to 0-360 scale.
			hue = int(round(hue / 182.0))

			# Update the Indigo device if the Hue device is on.
			if onState == True:
				# Update the brightness level if it's different.
				if device.states['brightnessLevel'] != brightnessLevel:
					# Log the update.
					indigo.server.log(u"\"" + device.name + "\" on to " + str(brightnessLevel), 'Updated')
					self.updateDeviceState(device, 'brightnessLevel', brightnessLevel)
				# Hue Degrees (0-360).
				self.updateDeviceState(device, 'hue', hue)
				#   Saturation (0-100).
				self.updateDeviceState(device, 'saturation', saturation)
				#   CIE XY Cromaticity.
				self.updateDeviceState(device, 'colorX', colorX)
				self.updateDeviceState(device, 'colorY', colorY)
				#   Color Mode.
				self.updateDeviceState(device, 'colorMode', colorMode)
				#   Red, Green, Blue.
				self.updateDeviceState(device, 'colorRed', colorRed)
				self.updateDeviceState(device, 'colorGreen', colorGreen)
				self.updateDeviceState(device, 'colorBlue', colorBlue)
				
			elif onState == False:
				# Hue device is off. Set brightness to zero.
				if device.states['brightnessLevel'] != 0:
					# Log the update.
					indigo.server.log(u"\"" + device.name + "\" off", 'Updated')
					self.updateDeviceState(device, 'brightnessLevel', 0)
				# Hue Degrees (convert from 0-65535 to 0-360).
				self.updateDeviceState(device, 'hue', hue)
				# Saturation (convert from 0-255 to 0-100).
				self.updateDeviceState(device, 'saturation', saturation)
				# CIE XY Cromaticity.
				self.updateDeviceState(device, 'colorX', colorX)
				self.updateDeviceState(device, 'colorY', colorY)
				# Color Mode.
				self.updateDeviceState(device, 'colorMode', colorMode)
				# Red, Green, and Blue Color.
				#    If the bulb is off, all RGB values should be 0.
				self.updateDeviceState(device, 'colorRed', 0)
				self.updateDeviceState(device, 'colorGreen', 0)
				self.updateDeviceState(device, 'colorBlue', 0)
			else:
				# Unrecognized on state, but not important enough to mention in regular log.
				self.debugLog(u"LivingColors unrecognized on state given by hub: " + str(bulb['state']['on']))
				
			# Update any Hue Device Attribute Controller virtual dimmers associated with this bulb.
			for controlDeviceId in self.controlDeviceList:
				controlDevice = indigo.devices[int(controlDeviceId)]
				attributeToControl = controlDevice.pluginProps.get('attributeToControl', None)
				if deviceId == int(controlDevice.pluginProps.get('bulbDeviceId', None)):
					# Device has attributes controlled by a Hue Device Attribute Controler.
					#   Update the controller device based on current bulb device states.
					#   But if the control destination device is off, update the value of the
					#   controller (virtual dimmer) to 0.
					if device.onState == True:
						# Destination Hue Bulb device is on, update Attribute Controller brightness.
						if attributeToControl == "hue":
							# Convert hue scale from 0-360 to 0-100.
							self.updateDeviceState(controlDevice, 'brightnessLevel', int(round(hue / 360.0 * 100.0)))
						elif attributeToControl == "saturation":
							self.updateDeviceState(controlDevice, 'brightnessLevel', saturation)
						elif attributeToControl == "colorRed":
							# Convert RGB scale from 0-255 to 0-100.
							self.updateDeviceState(controlDevice, 'brightnessLevel', int(round(colorRed / 255.0 * 100.0)))
						elif attributeToControl == "colorGreen":
							# Convert RGB scale from 0-255 to 0-100.
							self.updateDeviceState(controlDevice, 'brightnessLevel', int(round(colorGreen / 255.0 * 100.0)))
						elif attributeToControl == "colorBlue":
							# Convert RGB scale from 0-255 to 0-100.
							self.updateDeviceState(controlDevice, 'brightnessLevel', int(round(colorBlue / 255.0 * 100.0)))
					else:
						# Hue Device is off.  Set Attribute Controller device brightness level to 0.
						self.updateDeviceState(controlDevice, 'brightnessLevel', 0)
						
		# -- LivingWhites --
		elif modelId in kLivingWhitesDeviceIDs:
			# Update the Indigo device if the Hue device is on.
			if onState == True:
				# Update the brightness level if it's different.
				if device.states['brightnessLevel'] != brightnessLevel:
					# Log the update.
					indigo.server.log(u"\"" + device.name + "\" on to " + str(brightnessLevel), 'Updated')
					self.updateDeviceState(device, 'brightnessLevel', brightnessLevel)
			elif onState == False:
				# Hue device is off. Set brightness to zero.
				if device.states['brightnessLevel'] != 0:
					# Log the update.
					indigo.server.log(u"\"" + device.name + "\" off", 'Updated')
					self.updateDeviceState(device, 'brightnessLevel', 0)
			else:
				# Unrecognized on state, but not important enough to mention in regular log.
				self.debugLog(u"LivingWhites unrecognized on state given by hub: " + str(bulb['state']['on']))
				
			# Update any Hue Device Attribute Controller virtual dimmers associated with this bulb.
			for controlDeviceId in self.controlDeviceList:
				controlDevice = indigo.devices[int(controlDeviceId)]
				attributeToControl = controlDevice.pluginProps.get('attributeToControl', None)
				if deviceId == int(controlDevice.pluginProps.get('bulbDeviceId', None)):
					# Device has attributes controlled by a Hue Device Attribute Controler.
					#   Update the controller device based on current bulb device states.
					#   But if the control destination device is off, update the value of the
					#   controller (virtual dimmer) to 0.
					if device.onState == True:
						# Destination Hue Bulb device is on, update Attribute Controller brightness.
						if attributeToControl == "hue":
							# Convert hue scale from 0-360 to 0-100.
							self.updateDeviceState(controlDevice, 'brightnessLevel', int(round(hue / 360.0 * 100.0)))
						elif attributeToControl == "saturation":
							self.updateDeviceState(controlDevice, 'brightnessLevel', saturation)
						elif attributeToControl == "colorRed":
							# Convert RGB scale from 0-255 to 0-100.
							self.updateDeviceState(controlDevice, 'brightnessLevel', int(round(colorRed / 255.0 * 100.0)))
						elif attributeToControl == "colorGreen":
							# Convert RGB scale from 0-255 to 0-100.
							self.updateDeviceState(controlDevice, 'brightnessLevel', int(round(colorGreen / 255.0 * 100.0)))
						elif attributeToControl == "colorBlue":
							# Convert RGB scale from 0-255 to 0-100.
							self.updateDeviceState(controlDevice, 'brightnessLevel', int(round(colorBlue / 255.0 * 100.0)))
					else:
						# Hue Device is off.  Set Attribute Controller device brightness level to 0.
						self.updateDeviceState(controlDevice, 'brightnessLevel', 0)
						
		else:
			# Unrecognized model ID.
			if not self.unsupportedDeviceWarned:
				errorText = u"The \"" + device.name + u"\" device has an unrecognized model ID of \"" + bulb.get('modelid', "") + u"\". Hue Lights plugin does not support this device."
				self.errorLog(errorText)
				# Remember the error.
				self.lastErrorMessage = errorText 
				self.unsupportedDeviceWarned = True
				
	# Get Group Status
	########################################
	def getGroupStatus(self, deviceId):
		# Get group status.
		
		device = indigo.devices[deviceId]
		# Get the bulbId from the device properties.
		groupId = device.pluginProps.get('groupId', -1)
		self.debugLog(u"Get group status for group %s." % (groupId))
		# if the groupId exists, get the group status.
		if groupId > -1:
			command = "http://%s/api/%s/groups/%s" % (self.ipAddress, self.pluginPrefs['hostId'], groupId)
			self.debugLog(u"Sending URL request: " + command)
			try:
				r = requests.get(command, timeout=kTimeout)
			except requests.exceptions.Timeout:
				errorText = u"Failed to connect to the Hue hub at %s after %i seconds. - Check that the hub is connected and turned on." % (self.ipAddress, kTimeout)
				# Don't display the error if it's been displayed already.
				if errorText != self.lastErrorMessage:
					self.errorLog(errorText)
					# Remember the error.
					self.lastErrorMessage = errorText
				return
			except requests.exceptions.ConnectionError:
				errorText = u"Failed to connect to the Hue hub at %s. - Check that the hub is connected and turned on." % (self.ipAddress)
				# Don't display the error if it's been displayed already.
				if errorText != self.lastErrorMessage:
					self.errorLog(errorText)
					# Remember the error.
					self.lastErrorMessage = errorText
				return
		# There's no groupId provided.
		else:
			self.debugLog(u"No group ID was provided.")
			return
		
		self.debugLog(u"Data from hub: " + r.content)
		
		# Convert the response to a Python object.
		try:
			group = json.loads(r.content)
		except Exception, e:
			indigo.server.log(u"Error retrieving Hue group status: " + str(e))
			return False
			
		#
		### Parse Data
		#
		# Value assignments.
		brightness = group['action']['bri']
		onState = group['action']['on']
		effect = group['action']['effect']
		hue = group['action']['hue']
		saturation = group['action']['sat']
		colorX = group['action']['xy'][0]
		colorY = group['action']['xy'][1]
		colorRed = 255		# Initialize for later
		colorGreen = 255	# Initialize for later
		colorBlue = 255		# Initialize for later
		colorTemp = group['action']['ct']
		colorMode = group['action']['colormode']
		i = 0		# To count members in group.
		for tempMemberID in group['lights']:
			if i > 0:
				groupMemberIDs = groupMemberIDs + ", " + str(tempMemberID)
			else:
				groupMemberIDs = tempMemberID
			i += 1
		nameOnHub = group['name']
		
		#   Value manipulation.
		# Convert brightness from 0-255 range to 0-100 range.
		brightnessLevel = int(round(brightness / 255.0 * 100.0))
		# Compensate for incorrect rounding to zero if original brightness is not zero.
		if brightnessLevel == 0 and brightness > 0:
			brightnessLevel = 1
		# If the "on" state is False, it doesn't matter what brightness the hub
		#   is reporting, the effective brightness is zero.
		if onState == False:
			brightnessLevel = 0
		# Convert from HSB to RGB, scaling the hue and saturation values appropriately.
		hsb = HSVColor(hue / 182.0, saturation / 255.0, brightness / 255.0)
		rgb = hsb.convert_to('rgb', rgb_type='wide_gamut_rgb')
		colorRed = int(round(rgb.rgb_r))
		colorGreen = int(round(rgb.rgb_g))
		colorBlue = int(round(rgb.rgb_b))
		# Convert saturation from 0-255 scale to 0-100 scale.
		saturation = int(round(saturation / 255.0 * 100.0))
		# Convert hue from 0-65535 scale to 0-360 scale.
		hue = int(round(hue / 182.0))
		# Must first test color temp value. If it's zero, the formula throws a divide by zero execption.
		if colorTemp > 0:
			# Converting from mireds to Kelvin.
			colorTemp = int(round(1000000.0/colorTemp))
		else:
			colorTemp = 0
			
		#   Update Indigo states and properties common to all Hue devices.	
		tempProps = device.pluginProps
		# Update the Hue device name.
		if nameOnHub != device.pluginProps.get('nameOnHub', False):
			tempProps['nameOnHub'] = nameOnHub
			self.updateDeviceProps(device, tempProps)
		# Update the effect state of the Hue device.
		self.updateDeviceState(device, 'effect', effect)
		# Update the group member IDs.
		self.updateDeviceState(device, 'groupMemberIDs', groupMemberIDs)
		
		# Update the Indigo device if the Hue group is on.
		if onState == True:
			# Update the brightness level if it's different.
			if device.states['brightnessLevel'] != brightnessLevel:
				# Log the update.
				indigo.server.log(u"\"" + device.name + "\" on to " + str(brightnessLevel), 'Updated')
				self.updateDeviceState(device, 'brightnessLevel', brightnessLevel)
			# Hue Degrees (0-360).
			self.updateDeviceState(device, 'hue', hue)
			# Saturation (0-100).
			self.updateDeviceState(device, 'saturation', saturation)
			# CIE XY Cromaticity.
			self.updateDeviceState(device, 'colorX', colorX)
			self.updateDeviceState(device, 'colorY', colorY)
			# Color Temperature (converted from 154-500 mireds to 6494-2000 K).
			self.updateDeviceState(device, 'colorTemp', colorTemp)
			# Color Mode.
			self.updateDeviceState(device, 'colorMode', colorMode)
			# Red, Green, Blue.
			self.updateDeviceState(device, 'colorRed', colorRed)
			self.updateDeviceState(device, 'colorGreen', colorGreen)
			self.updateDeviceState(device, 'colorBlue', colorBlue)
			
		elif onState == False:
			# Hue group is off. Set brightness to zero.
			if device.states['brightnessLevel'] != 0:
				# Log the update.
				indigo.server.log(u"\"" + device.name + "\" off", 'Updated')
				self.updateDeviceState(device, 'brightnessLevel', 0)
			# Hue Degrees (convert from 0-65535 to 0-360).
			self.updateDeviceState(device, 'hue', hue)
			# Saturation (convert from 0-255 to 0-100).
			self.updateDeviceState(device, 'saturation', saturation)
			# CIE XY Cromaticity.
			self.updateDeviceState(device, 'colorX', colorX)
			self.updateDeviceState(device, 'colorY', colorY)
			# Color Temperature (convert from 154-500 mireds to 6494-2000 K).
			self.updateDeviceState(device, 'colorTemp', colorTemp)
			# Color Mode.
			self.updateDeviceState(device, 'colorMode', colorMode)
			# Red, Green, and Blue Color.
			#    If the bulb is off, all RGB values should be 0.
			self.updateDeviceState(device, 'colorRed', 0)
			self.updateDeviceState(device, 'colorGreen', 0)
			self.updateDeviceState(device, 'colorBlue', 0)
		else:
			# Unrecognized on state, but not important enough to mention in regular log.
			self.debugLog(u"Hue group unrecognized on state given by hub: " + str(group['action']['on']))
			
		# Update any Hue Device Attribute Controller virtual dimmers associated with this bulb.
		for controlDeviceId in self.controlDeviceList:
			controlDevice = indigo.devices[int(controlDeviceId)]
			attributeToControl = controlDevice.pluginProps.get('attributeToControl', None)
			if deviceId == int(controlDevice.pluginProps.get('bulbDeviceId', None)):
				# Device has attributes controlled by a Hue Device Attribute Controler.
				#   Update the controller device based on current bulb device states.
				#   But if the control destination device is off, update the value of the
				#   controller (virtual dimmer) to 0.
				if device.onState == True:
					# Destination Hue Bulb device is on, update Attribute Controller brightness.
					if attributeToControl == "hue":
						# Convert hue scale from 0-360 to 0-100.
						self.updateDeviceState(controlDevice, 'brightnessLevel', int(round(hue / 360.0 * 100.0)))
					elif attributeToControl == "saturation":
						self.updateDeviceState(controlDevice, 'brightnessLevel', saturation)
					elif attributeToControl == "colorRed":
						# Convert RGB scale from 0-255 to 0-100.
						self.updateDeviceState(controlDevice, 'brightnessLevel', int(round(colorRed / 255.0 * 100.0)))
					elif attributeToControl == "colorGreen":
						# Convert RGB scale from 0-255 to 0-100.
						self.updateDeviceState(controlDevice, 'brightnessLevel', int(round(colorGreen / 255.0 * 100.0)))
					elif attributeToControl == "colorBlue":
						# Convert RGB scale from 0-255 to 0-100.
						self.updateDeviceState(controlDevice, 'brightnessLevel', int(round(colorBlue / 255.0 * 100.0)))
					elif attributeToControl == "colorTemp":
						# Convert color temperature scale from 2000-6500 to 0-100.
						self.updateDeviceState(controlDevice, 'brightnessLevel', int(round((colorTemp - 2000.0) / 4500.0 * 100.0)))
				else:
					# Indigo Device is off.  Set Attribute Controller device brightness level to 0.
					self.updateDeviceState(controlDevice, 'brightnessLevel', 0)
					
					
	# Turn Device On or Off
	########################################
	def doOnOff(self, device, onState, rampRate=-1):
		# onState:		Boolean on state.  True = on. False = off.
		# rampRate:		Optional float from 0 to 540.0 (higher values will probably work too).
		
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
			except Exception, e:
				errorText = u"Default ramp rate could not be obtained: " + str(e)
				self.errorLog(errorText)
				# Remember the error.
				self.lastErrorMessage = errorText
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
		if defaultBrightness > 0:
			# Convert default brightness from percentage to 1-255 range.
			savedBrightness = int(round(defaultBrightness / 100.0 * 255.0))
		# If the currentBrightness is less than 100% and is the same as the savedBrightness, go to 100%
		if currentBrightness < 100 and currentBrightness == int(round(savedBrightness / 255.0 * 100.0)):
			savedBrightness = 255
		
		# Sanity check for an IP address
		self.ipAddress = self.pluginPrefs.get('address', None)
		if self.ipAddress is None:
			errorText = u"No IP address set for the Hue hub. You can get this information from the My Settings page at http://www.meethue.com"
			self.errorLog(errorText)
			# Remember the error.
			self.lastErrorMessage = errorText
			return
		
		# Act based on device type.
		if device.deviceTypeId == "hueGroup":
			# Sanity check on group ID
			groupId = device.pluginProps.get('groupId', None)
			if groupId is None or groupId == 0:
				errorText = u"No group ID selected for device \"%s\". Check settings for this device and select a Hue Group to control." % (device.name)
				self.errorLog(errorText)
				# Remember the error.
				self.lastErrorMessage = errorText
				return
		else:
			# Sanity check on bulb ID
			bulbId = device.pluginProps.get('bulbId', None)
			if bulbId is None or bulbId == 0:
				errorText = u"No bulb ID selected for device \"%s\". Check settings for this device and select a Hue Device to control." % (device.name)
				self.errorLog(errorText)
				# Remember the error.
				self.lastErrorMessage = errorText
				return
		
		# If the requested onState is True (on), then use the
		#   saved brightness level (which was determined above).
		if onState == True:
			# If the bulb's saved brightness is zero or less (for some reason), use a default value of 100% on (255).
			if savedBrightness <= 0:
				savedBrightness = 255
			# Create the JSON object and send the command to the hub.
			requestData = json.dumps({"bri": savedBrightness, "on": onState, "transitiontime": rampRate})
			# Create the command based on whether this is a light or group device.
			if device.deviceTypeId == "hueGroup":
				command = "http://%s/api/%s/groups/%s/action" % (self.ipAddress, self.pluginPrefs['hostId'], groupId)
			else:
				command = "http://%s/api/%s/lights/%s/state" % (self.ipAddress, self.pluginPrefs['hostId'], bulbId)
			self.debugLog("Sending URL request: " + command)
			try:
				r = requests.put(command, data=requestData, timeout=kTimeout)
			except requests.exceptions.Timeout:
				errorText = u"Failed to connect to the Hue hub at %s after %i seconds. - Check that the hub is connected and turned on." % (self.ipAddress, kTimeout)
				# Don't display the error if it's been displayed already.
				if errorText != self.lastErrorMessage:
					self.errorLog(errorText)
					# Remember the error.
					self.lastErrorMessage = errorText
				return
			except requests.exceptions.ConnectionError:
				errorText = u"Failed to connect to the Hue hub at %s. - Check that the hub is connected and turned on." % (self.ipAddress)
				# Don't display the error if it's been displayed already.
				if errorText != self.lastErrorMessage:
					self.errorLog(errorText)
					# Remember the error.
					self.lastErrorMessage = errorText
				return
			self.debugLog("Got response - %s" % r.content)
			# Log the change.
			tempBrightness = int(round(savedBrightness / 255.0 * 100.0))
			# Compensate for rounding to zero.
			if tempBrightness == 0:
				tempBrightness = 1
			indigo.server.log(u"\"" + device.name + u"\" on to " + str(tempBrightness) + u" at ramp rate " + str(rampRate / 10.0) + u" sec.", 'Sent Hue Lights')
			# Update the Indigo device.
			self.updateDeviceState(device, 'brightnessLevel', tempBrightness)
		else:
			# Bulb is being turned off.
			# If the current brightness is lower than 6%, use a ramp rate of 0
			#   because dimming from that low of a brightness level to 0 isn't noticeable.
			if currentBrightness < 6:
				rampRate = 0
			# Create the JSON object and send the command to the hub.
			requestData = json.dumps({"on": onState, "transitiontime": rampRate})
			# Create the command based on whether this is a light or group device.
			if device.deviceTypeId == "hueGroup":
				command = "http://%s/api/%s/groups/%s/action" % (self.ipAddress, self.pluginPrefs['hostId'], groupId)
			else:
				command = "http://%s/api/%s/lights/%s/state" % (self.ipAddress, self.pluginPrefs['hostId'], bulbId)
			self.debugLog(u"Sending URL request: " + command)
			try:
				r = requests.put(command, data=requestData, timeout=kTimeout)
			except requests.exceptions.Timeout:
				errorText = u"Failed to connect to the Hue hub at %s after %i seconds. - Check that the hub is connected and turned on." % (self.ipAddress, kTimeout)
				# Don't display the error if it's been displayed already.
				if errorText != self.lastErrorMessage:
					self.errorLog(errorText)
					# Remember the error.
					self.lastErrorMessage = errorText
				return
			except requests.exceptions.ConnectionError:
				errorText = u"Failed to connect to the Hue hub at %s. - Check that the hub is connected and turned on." % (self.ipAddress)
				# Don't display the error if it's been displayed already.
				if errorText != self.lastErrorMessage:
					self.errorLog(errorText)
					# Remember the error.
					self.lastErrorMessage = errorText
				return
			self.debugLog(u"Got response - %s" % r.content)
			# Log the change.
			indigo.server.log(u"\"" + device.name + u"\" off at ramp rate " + str(rampRate / 10.0) + u" sec.", 'Sent Hue Lights')
			# Update the Indigo device.
			self.updateDeviceState(device, 'brightnessLevel', 0)
	
	# Set Brightness
	########################################
	def doBrightness(self, device, brightness, rampRate=-1, showLog=True):
		# brightness:	Integer from 0 to 255.
		# rampRate:		Optional float from 0 to 540.0 (higher values will probably work too).
		# showLog:		Optional boolean. False = hide change from Indigo log.
		
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
			except Exception, e:
				errorText = u"Default ramp rate could not be obtained: " + str(e)
				self.errorLog(errorText)
				# Remember the error.
				self.lastErrorMessage = errorText
				rampRate = 5
		else:
			rampRate = int(round(float(rampRate) * 10))
		
		# Get the current brightness level.
		currentBrightness = device.states.get('brightnessLevel', 100)

		# Sanity check for an IP address
		self.ipAddress = self.pluginPrefs.get('address', None)
		if self.ipAddress is None:
			errorText = u"No IP address set for the Hue hub. You can get this information from the My Settings page at http://www.meethue.com"
			self.errorLog(errorText)
			# Remember the error.
			self.lastErrorMessage = errorText
			return
		
		# Act based on device type.
		if device.deviceTypeId == "hueGroup":
			# Sanity check on group ID
			groupId = device.pluginProps.get('groupId', None)
			if groupId is None or groupId == 0:
				errorText = u"No group ID selected for device \"%s\". Check settings for this device and select a Hue Group to control." % (device.name)
				self.errorLog(errorText)
				# Remember the error.
				self.lastErrorMessage = errorText
				return
		else:
			# Sanity check on bulb ID
			bulbId = device.pluginProps.get('bulbId', None)
			if bulbId is None or bulbId == 0:
				errorText = u"No bulb ID selected for device \"%s\". Check settings for this device and select a Hue Device to control." % (device.name)
				self.errorLog(errorText)
				# Remember the error.
				self.lastErrorMessage = errorText
				return
		
		# If requested brightness is greater than 0, proceed. Otherwise, turn off the bulb.
		if brightness > 0:
			requestData = json.dumps({"bri": int(brightness), "on": True, "transitiontime": rampRate})
			# Create the command based on whether this is a light or group device.
			if device.deviceTypeId == "hueGroup":
				command = "http://%s/api/%s/groups/%s/action" % (self.ipAddress, self.pluginPrefs['hostId'], groupId)
			else:
				command = "http://%s/api/%s/lights/%s/state" % (self.ipAddress, self.pluginPrefs['hostId'], bulbId)
			self.debugLog("Sending URL request: " + command)
			try:
				r = requests.put(command, data=requestData, timeout=kTimeout)
			except requests.exceptions.Timeout:
				errorText = u"Failed to connect to the Hue hub at %s after %i seconds. - Check that the hub is connected and turned on." % (self.ipAddress, kTimeout)
				# Don't display the error if it's been displayed already.
				if errorText != self.lastErrorMessage:
					self.errorLog(errorText)
					# Remember the error.
					self.lastErrorMessage = errorText
				return
			except requests.exceptions.ConnectionError:
				errorText = u"Failed to connect to the Hue hub at %s. - Check that the hub is connected and turned on." % (self.ipAddress)
				# Don't display the error if it's been displayed already.
				if errorText != self.lastErrorMessage:
					self.errorLog(errorText)
					# Remember the error.
					self.lastErrorMessage = errorText
				return
			self.debugLog("Got response - %s" % r.content)
			# Log the change.
			tempBrightness = int(round(brightness / 255.0 * 100.0))
			# Compensate for rounding to zero.
			if tempBrightness == 0:
				tempBrightness = 1
			# Only log changes if we're supposed to.
			if showLog:
				indigo.server.log(u"\"" + device.name + u"\" on to " + str(tempBrightness) + u" at ramp rate " + str(rampRate / 10.0) + u" sec.", 'Sent Hue Lights')
			# Update the device brightness (which automatically changes on state).
			self.updateDeviceState(device, 'brightnessLevel', int(tempBrightness))
		else:
			# Requested brightness is 0 (off).
			# If the current brightness is lower than 6%, use a ramp rate of 0
			#   because dimming from that low of a brightness level to 0 isn't noticeable.
			if currentBrightness < 6:
				rampRate = 0
			# Create the JSON request.
			requestData = json.dumps({"transitiontime": rampRate, "on": False})
			# Create the command based on whether this is a light or group device.
			if device.deviceTypeId == "hueGroup":
				command = "http://%s/api/%s/groups/%s/action" % (self.ipAddress, self.pluginPrefs['hostId'], groupId)
			else:
				command = "http://%s/api/%s/lights/%s/state" % (self.ipAddress, self.pluginPrefs['hostId'], bulbId)
			self.debugLog(u"Sending URL request: " + command)
			try:
				r = requests.put(command, data=requestData, timeout=kTimeout)
			except requests.exceptions.Timeout:
				errorText = u"Failed to connect to the Hue hub at %s after %i seconds. - Check that the hub is connected and turned on." % (self.ipAddress, kTimeout)
				# Don't display the error if it's been displayed already.
				if errorText != self.lastErrorMessage:
					self.errorLog(errorText)
					# Remember the error.
					self.lastErrorMessage = errorText
				return
			except requests.exceptions.ConnectionError:
				errorText = u"Failed to connect to the Hue hub at %s. - Check that the hub is connected and turned on." % (self.ipAddress)
				# Don't display the error if it's been displayed already.
				if errorText != self.lastErrorMessage:
					self.errorLog(errorText)
					# Remember the error.
					self.lastErrorMessage = errorText
				return
			self.debugLog(u"Got response - %s" % r.content)
			# Log the change.
			if showLog:
				indigo.server.log(u"\"" + device.name + u"\" off at ramp rate " + str(rampRate / 10.0) + u" sec.", 'Sent Hue Lights')
			# Update the device brightness (which automatically changes on state).
			self.updateDeviceState(device, 'brightnessLevel', 0)
	
	# Set RGB Levels
	########################################
	def doRGB(self, device, red, green, blue, rampRate=-1):
		self.debugLog(u"doRGB called. RGB: %s, %s, %s. Device: %s" % (red, green, blue, device))
		# red:			Integer from 0 to 255.
		# green:		Integer from 0 to 255.
		# blue:			Integer from 0 to 255.
		# rampRate:		Optional float from 0 to 540.0 (higher values will probably work too).
		
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
			except Exception, e:
				errorText = u"Default ramp rate could not be obtained: " + str(e)
				self.errorLog(errorText)
				# Remember the error.
				self.lastErrorMessage = errorText
				rampRate = 5
		else:
			rampRate = int(round(float(rampRate) * 10))
		
		# Get the current brightness.
		currentBrightness = device.states.get('brightnessLevel', 100)
		
		# Convert RGB to HSL (same as HSB)
		rgb = RGBColor(red, green, blue, rgb_type='wide_gamut_rgb')
		hsb = rgb.convert_to('hsv')
		# Convert hue, saturation, and brightness to Hue system compatible ranges
		hue = int(round(hsb.hsv_h * 182.0))
		saturation = int(round(hsb.hsv_s * 255.0))
		brightness = int(round(hsb.hsv_v * 255.0))
		
		# Sanity check for an IP address
		self.ipAddress = self.pluginPrefs.get('address', None)
		if self.ipAddress is None:
			errorText = u"No IP address set for the Hue hub. You can get this information from the My Settings page at http://www.meethue.com"
			self.errorLog(errorText)
			# Remember the error.
			self.lastErrorMessage = errorText
			return
		
		# Act based on device type.
		if device.deviceTypeId == "hueGroup":
			# Sanity check on group ID
			groupId = device.pluginProps.get('groupId', None)
			if groupId is None or groupId == 0:
				errorText = u"No group ID selected for device \"%s\". Check settings for this device and select a Hue Group to control." % (device.name)
				self.errorLog(errorText)
				# Remember the error.
				self.lastErrorMessage = errorText
				return
		else:
			# Sanity check on bulb ID
			bulbId = device.pluginProps.get('bulbId', None)
			if bulbId is None or bulbId == 0:
				errorText = u"No bulb ID selected for device \"%s\". Check settings for this device and select a Hue Device to control." % (device.name)
				self.errorLog(errorText)
				# Remember the error.
				self.lastErrorMessage = errorText
				return
		
		# Make sure the device is capable of rendering color.
		if modelId not in kHueBulbDeviceIDs and modelId not in kLightStripsDeviceIDs and modelId not in kLivingColorsDeviceIDs and device.deviceTypeId != "hueGroup":
			errorText = u"Cannot set RGB values. The \"%s\" device does not support color." % (device.name)
			self.errorLog(errorText)
			# Remember the error.
			self.lastErrorMessage = errorText
			return
			
		# Send to Hue (Create JSON request based on whether brightness is zero or not).
		if brightness > 0:
			requestData = json.dumps({"bri": brightness, "colormode": 'hs', "hue": hue, "sat": saturation, "transitiontime": int(rampRate), "on": True})
		else:
			# If the current brightness is below 6%, set the ramp rate to 0.
			if currentBrightness < 6:
				rampRate = 0
			# We create a separate command for when brightness is 0 (or below) because if
			#   the "on" state in the request was True, the Hue light wouldn't turn off.
			#   We also explicity state the X and Y values (equivilant to RGB of 1, 1, 1)
			#   because the xyy object contains invalid "NaN" values when all RGB values are 0.
			requestData = json.dumps({"bri": 0, "colormode": 'hs', "hue": 0, "sat": 0, "transitiontime": int(rampRate), "on": False})
			
		# Create the HTTP command and send it to the hub.
		# Create the command based on whether this is a light or group device.
		if device.deviceTypeId == "hueGroup":
			command = "http://%s/api/%s/groups/%s/action" % (self.ipAddress, self.pluginPrefs['hostId'], groupId)
		else:
			command = "http://%s/api/%s/lights/%s/state" % (self.ipAddress, self.pluginPrefs['hostId'], bulbId)
		self.debugLog(u"Data: " + str(requestData) + u", URL: " + command)
		try:
			r = requests.put(command, data=requestData, timeout=kTimeout)
		except requests.exceptions.Timeout:
			errorText = u"Failed to connect to the Hue hub at %s after %i seconds. - Check that the hub is connected and turned on." % (self.ipAddress, kTimeout)
			# Don't display the error if it's been displayed already.
			if errorText != self.lastErrorMessage:
				self.errorLog(errorText)
				# Remember the error.
				self.lastErrorMessage = errorText
			return
		except requests.exceptions.ConnectionError:
			errorText = u"Failed to connect to the Hue hub at %s. - Check that the hub is connected and turned on." % (self.ipAddress)
			# Don't display the error if it's been displayed already.
			if errorText != self.lastErrorMessage:
				self.errorLog(errorText)
				# Remember the error.
				self.lastErrorMessage = errorText
			return
		self.debugLog(u"Got response - %s" % r.content)
		
		# Update on Indigo
		if brightness > 0:
			# Convert brightness to a percentage.
			brightness = int(round(brightness / 255.0 * 100.0))
			# Log the change.
			indigo.server.log(u"\"" + device.name + u"\" on to " + str(brightness) + u" with RGB values " + str(red) + u", " + str(green) + u" and " + str(blue) + u" at ramp rate " + str(rampRate / 10.0) + u" sec.", 'Sent Hue Lights')
			# Update the device state.
			self.updateDeviceState(device, 'brightnessLevel', brightness)
		else:
			# Log the change.
			indigo.server.log(u"\"" + device.name + u"\" off at ramp rate " + str(rampRate / 10.0) + u" sec.", 'Sent Hue Lights')
			# Update the device state.
			self.updateDeviceState(device, 'brightnessLevel', 0)
		# Update the other device states.
		self.updateDeviceState(device, 'colorMode', "hs")
		self.updateDeviceState(device, 'hue', hue)
		self.updateDeviceState(device, 'saturation', saturation)
		# We don't set the colorRed, colorGreen, and colorBlue states
		#   because Hue devices are not capable of the full RGB color
		#   gamut and when the Hue hub updates the HSB values to reflect
		#   actual displayed light, the interpreted RGB values will not
		#   match the values entered by the user in the Action dialog.
		
	# Set Hue, Saturation and Brightness
	########################################
	def doHSB(self, device, hue, saturation, brightness, rampRate=-1):
		# hue:			Integer from 0 to 65535.
		# saturation:	Integer from 0 to 255.
		# brightness:	Integer from 0 to 255.
		# rampRate:		Optional float from 0 to 540.0 (higher values will probably work too).
		
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
			except Exception, e:
				errorText = u"Default ramp rate could not be obtained: " + str(e)
				self.errorLog(errorText)
				# Remember the error.
				self.lastErrorMessage = errorText
				rampRate = 5
		else:
			rampRate = int(round(float(rampRate) * 10.0))
		
		# Get the current brightness level.
		currentBrightness = device.states.get('brightnessLevel', 100)
		
		# Sanity check for an IP address
		self.ipAddress = self.pluginPrefs.get('address', None)
		if self.ipAddress is None:
			errorText = u"No IP address set for the Hue hub. You can get this information from the My Settings page at http://www.meethue.com"
			self.errorLog(errorText)
			# Remember the error.
			self.lastErrorMessage = errorText
			return
		
		# Act based on device type.
		if device.deviceTypeId == "hueGroup":
			# Sanity check on group ID
			groupId = device.pluginProps.get('groupId', None)
			if groupId is None or groupId == 0:
				errorText = u"No group ID selected for device \"%s\". Check settings for this device and select a Hue Group to control." % (device.name)
				self.errorLog(errorText)
				# Remember the error.
				self.lastErrorMessage = errorText
				return
		else:
			# Sanity check on bulb ID
			bulbId = device.pluginProps.get('bulbId', None)
			if bulbId is None or bulbId == 0:
				errorText = u"No bulb ID selected for device \"%s\". Check settings for this device and select a Hue Device to control." % (device.name)
				self.errorLog(errorText)
				# Remember the error.
				self.lastErrorMessage = errorText
				return
		
		# Make sure this device supports color.
		modelId = device.pluginProps.get('modelId', "")
		if modelId in kLivingWhitesDeviceIDs:
			errorText = u"Cannot set HSB values. The \"%s\" device does not support color." % (device.name)
			self.errorLog(errorText)
			# Remember the error.
			self.lastErrorMessage = errorText
			return
			
		# If the current brightness is below 6% and the requested brightness is
		#   greater than 0, set the ramp rate to 0.
		if currentBrightness < 6 and brightness == 0:
			rampRate = 0
		
		# Send to Hue (Create JSON request based on whether brightness is zero or not).
		if brightness > 0:
			requestData = json.dumps({"bri":brightness, "colormode": 'hs', "hue":hue, "sat":saturation, "on":True, "transitiontime":rampRate})
		else:
			requestData = json.dumps({"bri":brightness, "colormode": 'hs', "hue":hue, "sat":saturation, "on":False, "transitiontime":rampRate})
			
		# Create the command based on whether this is a light or group device.
		if device.deviceTypeId == "hueGroup":
			command = "http://%s/api/%s/groups/%s/action" % (self.ipAddress, self.pluginPrefs['hostId'], groupId)
		else:
			command = "http://%s/api/%s/lights/%s/state" % (self.ipAddress, self.pluginPrefs['hostId'], bulbId)
		self.debugLog(u"Request is %s" % requestData)
		try:
			r = requests.put(command, data=requestData, timeout=kTimeout)
		except requests.exceptions.Timeout:
			errorText = u"Failed to connect to the Hue hub at %s after %i seconds. - Check that the hub is connected and turned on." % (self.ipAddress, kTimeout)
			# Don't display the error if it's been displayed already.
			if errorText != self.lastErrorMessage:
				self.errorLog(errorText)
				# Remember the error.
				self.lastErrorMessage = errorText
			return
		except requests.exceptions.ConnectionError:
			errorText = u"Failed to connect to the Hue hub at %s. - Check that the hub is connected and turned on." % (self.ipAddress)
			# Don't display the error if it's been displayed already.
			if errorText != self.lastErrorMessage:
				self.errorLog(errorText)
				# Remember the error.
				self.lastErrorMessage = errorText
			return
		self.debugLog(u"Got response - %s" % r.content)
		
		# Update on Indigo
		if int(round(brightness/255.0*100.0)) > 0:
			# Log the change.
			indigo.server.log(u"\"" + device.name + u"\" on to " + str(int(round(brightness / 255.0 * 100.0))) + u" with hue " + str(int(round(hue / 182.0))) + u"° saturation " + str(int(round(saturation / 255.0 * 100.0))) + u"% at ramp rate " + str(rampRate / 10.0) + u" sec.", 'Sent Hue Lights')
			# Change the Indigo device.
			self.updateDeviceState(device, 'brightnessLevel', int(round(brightness / 255.0 * 100.0)))
		else:
			# Log the change.
			indigo.server.log(u"\"" + device.name + u"\" off at ramp rate " + str(rampRate / 10.0) + u" sec.", 'Sent Hue Lights')
			# Change the Indigo device.
			self.updateDeviceState(device, 'brightnessLevel', 0)
		# Update the other device states.
		self.updateDeviceState(device, 'colorMode', "hs")
		self.updateDeviceState(device, 'hue', int(round(hue / 182.0)))
		self.updateDeviceState(device, 'saturation', int(saturation / 255.0 * 100.0))

	# Set CIE 1939 xyY Values
	########################################
	def doXYY(self, device, colorX, colorY, brightness, rampRate=-1):
		# colorX:		Integer from 0 to 1.0.
		# colorY:		Integer from 0 to 1.0.
		# brightness:	Integer from 0 to 255.
		# rampRate:		Optional float from 0 to 540.0 (higher values will probably work too).
		
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
			except Exception, e:
				errorText = u"Default ramp rate could not be obtained: " + str(e)
				self.errorLog(errorText)
				# Remember the error.
				self.lastErrorMessage = errorText
				rampRate = 5
		else:
			rampRate = int(round(float(rampRate) * 10.0))
		
		# Get the current brightness level.
		currentBrightness = device.states.get('brightnessLevel', 100)
		
		# Sanity check for an IP address
		self.ipAddress = self.pluginPrefs.get('address', None)
		if self.ipAddress is None:
			errorText = u"No IP address set for the Hue hub. You can get this information from the My Settings page at http://www.meethue.com"
			self.errorLog(errorText)
			# Remember the error.
			self.lastErrorMessage = errorText
			return
		
		# Act based on device type.
		if device.deviceTypeId == "hueGroup":
			# Sanity check on group ID
			groupId = device.pluginProps.get('groupId', None)
			if groupId is None or groupId == 0:
				errorText = u"No group ID selected for device \"%s\". Check settings for this device and select a Hue Group to control." % (device.name)
				self.errorLog(errorText)
				# Remember the error.
				self.lastErrorMessage = errorText
				return
		else:
			# Sanity check on bulb ID
			bulbId = device.pluginProps.get('bulbId', None)
			if bulbId is None or bulbId == 0:
				errorText = u"No bulb ID selected for device \"%s\". Check settings for this device and select a Hue Device to control." % (device.name)
				self.errorLog(errorText)
				# Remember the error.
				self.lastErrorMessage = errorText
				return
		
		# Make sure this device supports color.
		modelId = device.pluginProps.get('modelId', "")
		if modelId in kLivingWhitesDeviceIDs:
			errorText = u"Cannot set xyY values. The \"%s\" device does not support color." % (device.name)
			self.errorLog(errorText)
			# Remember the error.
			self.lastErrorMessage = errorText
			return
			
		# Make sure the X and Y values are sane.
		if colorX < 0 or colorX > 1:
			errorText = u"The specified X chromatisety value \"%s\" for the \"%s\" device is outside the acceptable range of 0.0 to 1.0." % (colorX, device.name)
			self.errorLog(errorText)
			# Remember the error.
			self.lastErrorMessage = errorText
			return
		if colorY < 0 or colorY > 1:
			errorText = u"The specified Y chromatisety value \"%s\" for the \"%s\" device is outside the acceptable range of 0.0 to 1.0." % (colorX, device.name)
			self.errorLog(errorText)
			# Remember the error.
			self.lastErrorMessage = errorText
			return
			
		# If the current brightness is below 6% and the requested brightness is
		#   greater than 0, set the ramp rate to 0.
		if currentBrightness < 6 and brightness == 0:
			rampRate = 0
		
		# Send to Hue (Create JSON request based on whether brightness is zero or not).
		if brightness > 0:
			requestData = json.dumps({"bri":brightness, "colormode": 'xy', "xy":[colorX, colorY], "on":True, "transitiontime":rampRate})
		else:
			requestData = json.dumps({"bri":brightness, "colormode": 'xy', "xy":[colorX, colorY], "on":False, "transitiontime":rampRate})
			
		# Create the command based on whether this is a light or group device.
		if device.deviceTypeId == "hueGroup":
			command = "http://%s/api/%s/groups/%s/action" % (self.ipAddress, self.pluginPrefs['hostId'], groupId)
		else:
			command = "http://%s/api/%s/lights/%s/state" % (self.ipAddress, self.pluginPrefs['hostId'], bulbId)
		self.debugLog(u"Request is %s" % requestData)
		try:
			r = requests.put(command, data=requestData, timeout=kTimeout)
		except requests.exceptions.Timeout:
			errorText = u"Failed to connect to the Hue hub at %s after %i seconds. - Check that the hub is connected and turned on." % (self.ipAddress, kTimeout)
			# Don't display the error if it's been displayed already.
			if errorText != self.lastErrorMessage:
				self.errorLog(errorText)
				# Remember the error.
				self.lastErrorMessage = errorText
			return
		except requests.exceptions.ConnectionError:
			errorText = u"Failed to connect to the Hue hub at %s. - Check that the hub is connected and turned on." % (self.ipAddress)
			# Don't display the error if it's been displayed already.
			if errorText != self.lastErrorMessage:
				self.errorLog(errorText)
				# Remember the error.
				self.lastErrorMessage = errorText
			return
		self.debugLog(u"Got response - %s" % r.content)
		
		# Update on Indigo
		if int(round(brightness/255.0*100.0)) > 0:
			# Log the change.
			indigo.server.log(u"\"" + device.name + u"\" on to " + str(int(round(brightness / 255.0 * 100.0))) + u" with x/y chromatisety values of " + str(round(colorX, 4)) + u"/" + str(round(colorY, 4)) + u" at ramp rate " + str(rampRate / 10.0) + u" sec.", 'Sent Hue Lights')
			# Change the Indigo device.
			self.updateDeviceState(device, 'brightnessLevel', int(round(brightness / 255.0 * 100.0)))
		else:
			# Log the change.
			indigo.server.log(u"\"" + device.name + u"\" off at ramp rate " + str(rampRate / 10.0) + u" sec.", 'Sent Hue Lights')
			# Change the Indigo device.
			self.updateDeviceState(device, 'brightnessLevel', 0)
		# Update the other device states.
		self.updateDeviceState(device, 'colorMode', "xy")
		self.updateDeviceState(device, 'colorX', int(round(colorX, 4)))
		self.updateDeviceState(device, 'colorY', int(round(colorY, 4)))

	# Set Color Temperature
	########################################
	def doColorTemperature(self, device, temperature, brightness, rampRate=-1):
		# temperature:	Integer from 2000 to 6500.
		# brightness:	Integer from 0 to 255.
		# rampRate:		Optional float from 0 to 540.0 (higher values will probably work too).
		
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
			except Exception, e:
				errorText = u"Default ramp rate could not be obtained: " + str(e)
				self.errorLog(errorText)
				# Remember the error.
				self.lastErrorMessage = errorText
				rampRate = 5
		else:
			rampRate = int(round(float(rampRate) * 10))
		
		# Get the current brightness level.
		currentBrightness = device.states.get('brightnessLevel', 100)
		
		# Save the submitted color temperature into another variable.
		colorTemp = temperature
		
		# Convert temperature from K to mireds.
		#   Use the ceil and add 3 to help compensate for Hue behavior that "rounds up" to
		#   the next highest compatible mired value for the device.
		temperature = int(3 + ceil(1000000.0 / temperature))
		
		# Sanity check for an IP address
		self.ipAddress = self.pluginPrefs.get('address', None)
		if self.ipAddress is None:
			errorText = u"No IP address set for the Hue hub. You can get this information from the My Settings page at http://www.meethue.com"
			self.errorLog(errorText)
			# Remember the error.
			self.lastErrorMessage = errorText
			return
		
		# Act based on device type.
		if device.deviceTypeId == "hueGroup":
			# Sanity check on group ID
			groupId = device.pluginProps.get('groupId', None)
			if groupId is None or groupId == 0:
				errorText = u"No group ID selected for device \"%s\". Check settings for this device and select a Hue Group to control." % (device.name)
				self.errorLog(errorText)
				# Remember the error.
				self.lastErrorMessage = errorText
				return
		else:
			# Sanity check on bulb ID
			bulbId = device.pluginProps.get('bulbId', None)
			if bulbId is None or bulbId == 0:
				errorText = u"No bulb ID selected for device \"%s\". Check settings for this device and select a Hue Device to control." % (device.name)
				self.errorLog(errorText)
				# Remember the error.
				self.lastErrorMessage = errorText
				return
		
		# Make sure this device supports color.
		modelId = device.pluginProps.get('modelId', "")
		if modelId in kLivingWhitesDeviceIDs:
			errorText = u"Cannot set Color Temperature values. The \"%s\" device does not support variable color tmperature." % (device.name)
			self.errorLog(errorText)
			# Remember the error.
			self.lastErrorMessage = errorText
			return
			
		# If the current brightness is below 6% and the requested
		#   brightness is 0, set the ramp rate to 0.
		if currentBrightness < 6 and brightness == 0:
			rampRate = 0
		
		# Send to Hue (Create JSON request based on whether brightness is zero or not).
		if brightness > 0:
			requestData = json.dumps({"bri": brightness, "colormode": 'ct', "ct": temperature, "on": True, "transitiontime": int(rampRate)})
		else:
			requestData = json.dumps({"bri": brightness, "colormode": 'ct', "ct": temperature, "on": False, "transitiontime": int(rampRate)})
			
		# Create the command based on whether this is a light or group device.
		if device.deviceTypeId == "hueGroup":
			command = "http://%s/api/%s/groups/%s/action" % (self.ipAddress, self.pluginPrefs['hostId'], groupId)
		else:
			command = "http://%s/api/%s/lights/%s/state" % (self.ipAddress, self.pluginPrefs['hostId'], bulbId)
		self.debugLog(u"Request is %s" % requestData)
		try:
			r = requests.put(command, data=requestData, timeout=kTimeout)
		except requests.exceptions.Timeout:
			errorText = u"Failed to connect to the Hue hub at %s after %i seconds. - Check that the hub is connected and turned on." % (self.ipAddress, kTimeout)
			# Don't display the error if it's been displayed already.
			if errorText != self.lastErrorMessage:
				self.errorLog(errorText)
				# Remember the error.
				self.lastErrorMessage = errorText
			return
		except requests.exceptions.ConnectionError:
			errorText = u"Failed to connect to the Hue hub at %s. - Check that the hub is connected and turned on." % (self.ipAddress)
			# Don't display the error if it's been displayed already.
			if errorText != self.lastErrorMessage:
				self.errorLog(errorText)
				# Remember the error.
				self.lastErrorMessage = errorText
			return
		self.debugLog(u"Got response - %s" % r.content)
		
		# Update on Indigo
		if brightness > 0:
			# Log the change.
			tempBrightness = int(round(brightness / 255.0 * 100.0))
			# Compensate for rounding errors where it rounds down even though brightness is > 0.
			if tempBrightness == 0 and brightness > 0:
				tempBrightness = 1
			# Use originally submitted color temperature in the log version.
			indigo.server.log(u"\"" + device.name + u"\" on to " + str(tempBrightness) + u" using color temperature " + str(colorTemp) + u" K at ramp rate " + str(rampRate / 10.0) + u" sec.", 'Sent Hue Lights')
			self.updateDeviceState(device, 'brightnessLevel', int(round(brightness / 255.0 * 100.0)))
		else:
			# Log the change.
			indigo.server.log(u"\"" + device.name + u"\" off at ramp rate " + str(rampRate / 10.0) + u" sec.", 'Sent Hue Lights')
			self.updateDeviceState(device, 'brightnessLevel', 0)
		# Update the color mode state.
		self.updateDeviceState(device, 'colorMode', "ct")
		# Update the color temperature state (it's in mireds now, convert to Kelvin).
		self.updateDeviceState(device, 'colorTemp', colorTemp)
	
	# Start Alert (Blinking)
	########################################
	def doAlert(self, device, alertType="lselect"):
		# alertType:	Optional string.  String options are:
		#					lselect		: Long alert (default if nothing specified)
		#					select		: Short alert
		#					none		: Stop any running alerts
		
		# Sanity check for an IP address
		self.ipAddress = self.pluginPrefs.get('address', None)
		if self.ipAddress is None:
			errorText = u"No IP address set for the Hue hub. You can get this information from the My Settings page at http://www.meethue.com"
			self.errorLog(errorText)
			# Remember the error.
			self.lastErrorMessage = errorText
			return
		
		# Act based on device type.
		if device.deviceTypeId == "hueGroup":
			# Sanity check on group ID
			groupId = device.pluginProps.get('groupId', None)
			if groupId is None or groupId == 0:
				errorText = u"No group ID selected for device \"%s\". Check settings for this device and select a Hue Group to control." % (device.name)
				self.errorLog(errorText)
				# Remember the error.
				self.lastErrorMessage = errorText
				return
		else:
			# Sanity check on bulb ID
			bulbId = device.pluginProps.get('bulbId', None)
			if bulbId is None or bulbId == 0:
				errorText = u"No bulb ID selected for device \"%s\". Check settings for this device and select a Hue Device to control." % (device.name)
				self.errorLog(errorText)
				# Remember the error.
				self.lastErrorMessage = errorText
				return
		
		requestData = json.dumps({"alert": alertType})
		# Create the command based on whether this is a light or group device.
		if device.deviceTypeId == "hueGroup":
			command = "http://%s/api/%s/groups/%s/action" % (self.ipAddress, self.pluginPrefs['hostId'], groupId)
		else:
			command = "http://%s/api/%s/lights/%s/state" % (self.ipAddress, self.pluginPrefs['hostId'], bulbId)
		try:
			r = requests.put(command, data=requestData, timeout=kTimeout)
		except requests.exceptions.Timeout:
			errorText = u"Failed to connect to the Hue hub at %s after %i seconds. - Check that the hub is connected and turned on." % (self.ipAddress, kTimeout)
			# Don't display the error if it's been displayed already.
			if errorText != self.lastErrorMessage:
				self.errorLog(errorText)
				# Remember the error.
				self.lastErrorMessage = errorText
			return
		except requests.exceptions.ConnectionError:
			errorText = u"Failed to connect to the Hue hub at %s. - Check that the hub is connected and turned on." % (self.ipAddress)
			# Don't display the error if it's been displayed already.
			if errorText != self.lastErrorMessage:
				self.errorLog(errorText)
				# Remember the error.
				self.lastErrorMessage = errorText
			return
		self.debugLog(u"Got response - %s" % r.content)
		
		# Log the change.
		if alertType == "select":
			indigo.server.log(u"\"" + device.name + u"\" start short alert blink.", 'Sent Hue Lights')
		elif alertType == "lselect":
			indigo.server.log(u"\"" + device.name + u"\" start long alert blink.", 'Sent Hue Lights')
		elif alertType == "none":
			indigo.server.log(u"\"" + device.name + u"\" stop alert blink.", 'Sent Hue Lights')
		# Update the device state.
		self.updateDeviceState(device, 'alertMode', alertType)
			
	# Set Effect Status
	########################################
	def doEffect(self, device, effect):
		# effect:		String specifying the effect to use.  Hue supported effects are:
		#					none		: Stop any current effect
		#					colorloop	: Cycle through all hues at current brightness/saturation.
		#				Other effects may be supported by Hue with future firmware updates.
		
		# Sanity check for an IP address
		self.ipAddress = self.pluginPrefs.get('address', None)
		if self.ipAddress is None:
			errorText = u"No IP address set for the Hue hub. You can get this information from the My Settings page at http://www.meethue.com"
			self.errorLog(errorText)
			# Remember the error.
			self.lastErrorMessage = errorText
			return False
		
		# Act based on device type.
		if device.deviceTypeId == "hueGroup":
			# Sanity check on group ID
			groupId = device.pluginProps.get('groupId', None)
			if groupId is None or groupId == 0:
				errorText = u"No group ID selected for device \"%s\". Check settings for this device and select a Hue Group to control." % (device.name)
				self.errorLog(errorText)
				# Remember the error.
				self.lastErrorMessage = errorText
				return
		else:
			# Sanity check on bulb ID
			bulbId = device.pluginProps.get('bulbId', None)
			if bulbId is None or bulbId == 0:
				errorText = u"No bulb ID selected for device \"%s\". Check settings for this device and select a Hue Device to control." % (device.name)
				self.errorLog(errorText)
				# Remember the error.
				self.lastErrorMessage = errorText
				return
		
		# Submit to Hue
		requestData = json.dumps({"effect": effect})
		self.debugLog(u"Request is %s" % requestData)
		# Create the command based on whether this is a light or group device.
		if device.deviceTypeId == "hueGroup":
			command = "http://%s/api/%s/groups/%s/action" % (self.ipAddress, self.pluginPrefs['hostId'], groupId)
		else:
			command = "http://%s/api/%s/lights/%s/state" % (self.ipAddress, self.pluginPrefs['hostId'], bulbId)
		self.debugLog(u"URL: " + command)
		try:
			r = requests.put(command, data=requestData, timeout=kTimeout)
		except requests.exceptions.Timeout:
			errorText = u"Failed to connect to the Hue hub at %s after %i seconds. - Check that the hub is connected and turned on." % (self.ipAddress, kTimeout)
			# Don't display the error if it's been displayed already.
			if errorText != self.lastErrorMessage:
				self.errorLog(errorText)
				# Remember the error.
				self.lastErrorMessage = errorText
			return
		except requests.exceptions.ConnectionError:
			errorText = u"Failed to connect to the Hue hub at %s. - Check that the hub is connected and turned on." % (self.ipAddress)
			# Don't display the error if it's been displayed already.
			if errorText != self.lastErrorMessage:
				self.errorLog(errorText)
				# Remember the error.
				self.lastErrorMessage = errorText
			return
		self.debugLog(u"Got response - %s" % r.content)
		
		# Log the change.
		indigo.server.log(u"\"" + device.name + u"\" set effect to \"" + effect + u"\"", 'Sent Hue Lights')
		# Update the device state.
		self.updateDeviceState(device, 'effect', effect)
	
	# Update Lights List
	########################################
	def updateLightsList(self):
		# Sanity check for an IP address
		self.ipAddress = self.pluginPrefs.get('address', None)
		if self.ipAddress is None:
			errorText = u"No IP address set for the Hue hub. You can get this information from the My Settings page at http://www.meethue.com."
			self.errorLog(errorText)
			# Remember the error.
			self.lastErrorMessage = errorText
			return
		
		# Force a timeout
		socket.setdefaulttimeout(kTimeout)
		
		try:
			# Parse the response
			command = "http://%s/api/%s/lights" % (self.ipAddress, self.pluginPrefs.get('hostId', "ERROR"))
			r = requests.get(command, timeout=kTimeout)
			lightsListResponseData = json.loads(r.content)
			self.debugLog(u"Got response %s" % lightsListResponseData)
			
			# We should have a dictionary. If so, it's a light list
			if isinstance(lightsListResponseData, dict):
				self.debugLog(u"Loaded lights list - %s" % (lightsListResponseData))
				self.lightsDict = lightsListResponseData
				if len(self.lightsDict) != 1:
					indigo.server.log(u"Loaded %i lights." % len(self.lightsDict))
				else:
					indigo.server.log(u"Loaded %i light." % len(self.lightsDict))
				# Make sure the plugin knows it's actually paired now.
				self.paired = True
				
			elif isinstance(lightsListResponseData, list):
				# Get the first item
				firstResponseItem = lightsListResponseData[0]
				
				# Did we get an error?
				errorDict = firstResponseItem.get('error', None)
				if errorDict is not None:
					
					errorCode = errorDict.get('type', None)
					
					# Is this a link button not pressed error?
					if errorCode == 1:
						errorText = u"Not paired with the Hue hub. Press the middle button on the Hue hub, then press the Start/Finish button in the Plugin Settings (Plugins menu)."
						self.errorLog(errorText)
						# Remember the error.
						self.lastErrorMessage = errorText
						self.paired = False
						
					else:
						errorText = u"Error #%i from Hue hub when loading available devices. Description is \"%s\"." % (errorCode, errorDict.get('description', u"(no description"))
						self.errorLog(errorText)
						# Remember the error.
						self.lastErrorMessage = errorText
						self.paired = False
					
				else:
					indigo.server.log(u"Unexpected response from Hue hub (%s) when loading available devices!" % (lightsListResponseData))
					
			else:
				indigo.server.log(u"Unexpected response from Hue hub (%s) when loading available devices!" % (lightsListResponseData))
			
		except requests.exceptions.Timeout:
			errorText = u"Failed to load lights list from the Hue hub at %s after %i seconds - check settings and retry." % (self.ipAddress, kTimeout)
			# Don't display the error if it's been displayed already.
			if errorText != self.lastErrorMessage:
				self.errorLog(errorText)
				# Remember the error.
				self.lastErrorMessage = errorText
			
		except requests.exceptions.ConnectionError:
			errorText = u"Failed to connect to the Hue hub at %s. - Check that the hub is connected, turned on and the network settings are correct." % (self.ipAddress)
			# Don't display the error if it's been displayed already.
			if errorText != self.lastErrorMessage:
				self.errorLog(errorText)
				# Remember the error.
				self.lastErrorMessage = errorText
			return
			
		except Exception, e:
			errorText = u"Unable to obtain list of Hue lights from the hub." + str(e)
			# Don't display the error if it's been displayed already.
			if errorText != self.lastErrorMessage:
				self.errorLog(errorText)
				# Remember the error.
				self.lastErrorMessage = errorText
	
	# Update Groups List
	########################################
	def updateGroupsList(self):
		# Sanity check for an IP address
		self.ipAddress = self.pluginPrefs.get('address', None)
		if self.ipAddress is None:
			errorText = u"No IP address set for the Hue hub. You can get this information from the My Settings page at http://www.meethue.com."
			self.errorLog(errorText)
			# Remember the error.
			self.lastErrorMessage = errorText
			return
		
		# Force a timeout
		socket.setdefaulttimeout(kTimeout)
		
		try:
			# Parse the response
			command = "http://%s/api/%s/groups" % (self.ipAddress, self.pluginPrefs.get('hostId', "ERROR"))
			r = requests.get(command, timeout=kTimeout)
			groupsListResponseData = json.loads(r.content)
			self.debugLog(u"Got response %s" % groupsListResponseData)
			
			# We should have a dictionary. If so, it's a group list
			if isinstance(groupsListResponseData, dict):
				self.debugLog(u"Loaded groups list - %s" % (groupsListResponseData))
				self.groupsDict = groupsListResponseData
				if len(self.groupsDict) != 1:
					indigo.server.log(u"Loaded %i groups." % len(self.groupsDict))
				else:
					indigo.server.log(u"Loaded %i group." % len(self.groupsDict))
				# Make sure the plugin knows it's actually paired now.
				self.paired = True
				
			elif isinstance(groupsListResponseData, list):
				# Get the first item
				firstResponseItem = groupsListResponseData[0]
				
				# Did we get an error?
				errorDict = firstResponseItem.get('error', None)
				if errorDict is not None:
					
					errorCode = errorDict.get('type', None)
					
					# Is this a link button not pressed error?
					if errorCode == 1:
						errorText = u"Not paired with the Hue hub. Press the middle button on the Hue hub, then press the Start/Finish button in the Plugin Settings (Plugins menu)."
						self.errorLog(errorText)
						# Remember the error.
						self.lastErrorMessage = errorText
						self.paired = False
						
					else:
						errorText = u"Error #%i from Hue hub when loading available groups. Description is \"%s\"." % (errorCode, errorDict.get('description', u"(no description"))
						self.errorLog(errorText)
						# Remember the error.
						self.lastErrorMessage = errorText
						self.paired = False
					
				else:
					indigo.server.log(u"Unexpected response from Hue hub (%s) when loading available groups!" % (groupsListResponseData))
					
			else:
				indigo.server.log(u"Unexpected response from Hue hub (%s) when loading available groups!" % (groupsListResponseData))
			
		except requests.exceptions.Timeout:
			errorText = u"Failed to load groups list from the Hue hub at %s after %i seconds - check settings and retry." % (self.ipAddress, kTimeout)
			# Don't display the error if it's been displayed already.
			if errorText != self.lastErrorMessage:
				self.errorLog(errorText)
				# Remember the error.
				self.lastErrorMessage = errorText
			
		except requests.exceptions.ConnectionError:
			errorText = u"Failed to connect to the Hue hub at %s. - Check that the hub is connected, turned on and the network settings are correct." % (self.ipAddress)
			# Don't display the error if it's been displayed already.
			if errorText != self.lastErrorMessage:
				self.errorLog(errorText)
				# Remember the error.
				self.lastErrorMessage = errorText
			return
			
		except Exception, e:
			self.errorLog(u"Unable to obtain list of Hue groups from the hub." + str(e))
	
	
	########################################
	# Hue Hub Registration Methods
	########################################

	# Update Registration State
	########################################
	def updateRegistrationState(self):
		# Sanity check for an IP address
		self.ipAddress = self.pluginPrefs.get("address", None)
		if self.ipAddress is None:
			errorText = u"No IP address set for the Hue hub. You can get this information from the My Settings page at http://www.meethue.com."
			self.errorLog(errorText)
			self.lastErrorMessage = errorText
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
						errorText = u"Could not pair with Hue. Press the middle button on the Hue hub, then press the Start/Finish button in Plugin Settings."
						self.errorLog(errorText)
						# Remember the error.
						self.lastErrorMessage = errorText
						self.paired = False
						
					else:
						errorText = u"Error #%i from Hue hub when checking pairing. Description is \"%s\"." % (errorCode, errorDict.get("description", u"(No Description"))
						self.errorLog(errorText)
						# Remember the error.
						self.lastErrorMessage = errorText
						self.paired = False
					
				# Were we successful?
				successDict = firstResponseItem.get('success', None)
				if successDict is not None:
					indigo.server.log(u"Connected to Hue hub successfully.")
					self.paired = True
				
			else:
				errorText = u"Invalid response from Hue. Check the IP address and try again."
				self.errorLog(errorText)
				# Remember the error.
				self.lastErrorMessage = errorText
				
		except requests.exceptions.Timeout:
			errorText = u"Failed to connect to Hue hub at %s after %i seconds - check the IP address and try again." % (self.ipAddress, kTimeout)
			self.errorLog(errorText)
			# Remember the error.
			self.lastErrorMessage = errorText
		except requests.exceptions.ConnectionError:
			errorText = u"Failed to connect to the Hue hub at %s. - Check that the hub is connected and turned on and that the network settings are correct." % (self.ipAddress)
			self.errorLog(errorText)
			# Remember the error.
			self.lastErrorMessage = errorText
			return

	# Restart Pairing with Hue Hub
	########################################
	def restartPairing(self, valuesDict):
		if not self.paired:
			self.updateRegistrationState()
		else:
			errorText = u"Already paired. No need to update registration"
			self.errorLog(errorText)
			# Remember the error.
			self.lastErrorMessage = errorText
			
			
	########################################
	# Indigo UI Control Methods
	########################################
	
	# Dimmer/Relay Control Actions
	########################################
	def actionControlDimmerRelay(self, action, device):
		try:
			self.debugLog(u"actionControlDimmerRelay called for device " + device.name + u". action: " + str(action) + u"\n\ndevice: " + str(device))
		except Exception, e:
			self.debugLog(u"actionControlDimmerRelay called for device " + device.name + u". (Unable to display action or device data due to error: " + str(e) + u")")
		# Get the current brightness and on-state of the device.
		currentBrightness = device.states['brightnessLevel']
		currentOnState = device.states['onOffState']
		# Get key variables
		command = action.deviceAction
		
		# Act based on the type of device.
		#
		# -- Hue Bulbs --
		#
		if device.deviceTypeId == "hueBulb":
			bulbId = device.pluginProps.get('bulbId', None)
			hostId = self.pluginPrefs.get('hostId', None)
			self.ipAddress = self.pluginPrefs.get('address', None)
			self.debugLog(u"Command is %s, Bulb is %s" % (command, bulbId))
			
			##### TURN ON #####
			if command == indigo.kDeviceAction.TurnOn:
				try:
					self.debugLog(u"device on:\n%s" % action)
				except Exception, e:
					self.debugLog(u"device on: (Unable to display action data due to error: " + str(e) + u")")
				# Turn it on.
				self.doOnOff(device, True)
				
			##### TURN OFF #####
			elif command == indigo.kDeviceAction.TurnOff:
				try:
					self.debugLog(u"device off:\n%s" % action)
				except Exception, e:
					self.debugLog(u"device off: (Unable to display action data due to error: " + str(e) + u")")
				# Turn it off by setting the brightness to minimum.
				self.doOnOff(device, False)

			##### TOGGLE #####
			elif command == indigo.kDeviceAction.Toggle:
				try:
					self.debugLog(u"device toggle:\n%s" % action)
				except Exception, e:
					self.debugLog(u"device toggle: (Unable to display action due to error: " + str(e) + u")")
				if currentOnState == True:
					# It's on. Turn it off.
					self.doOnOff(device, False)
				else:
					# It's off. Turn it on.
					self.doOnOff(device, True)
			
			##### SET BRIGHTNESS #####
			elif command == indigo.kDeviceAction.SetBrightness:
				try:
					self.debugLog(u"device set brightness:\n%s" % action)
				except Exception, e:
					self.debugLog(u"device set brightness: (Unable to display action data due to error: " + str(e) + u")")
				brightnessLevel = int(round(action.actionValue / 100.0 * 255.0))
				# Save the new brightness level into the device properties.
				tempProps = device.pluginProps
				tempProps['savedBrightness'] = brightnessLevel
				self.updateDeviceProps(device, tempProps)
				# Set the new brightness level on the bulb.
				self.doBrightness(device, brightnessLevel)

			##### BRIGHTEN BY #####
			elif command == indigo.kDeviceAction.BrightenBy:
				try:
					self.debugLog(u"device increase brightness by:\n%s" % action)
				except Exception, e:
					self.debugLog(u"device increase brightness by: (Unable to display action data due to error: " + str(e) + u")")
				brightnessLevel = currentBrightness + action.actionValue
				if brightnessLevel > 100:
					brightnessLevel = 100
				# Save the new brightness level into the device properties.
				tempProps = device.pluginProps
				tempProps['savedBrightness'] = int(round(brightnessLevel / 100.0 * 255.0))
				self.updateDeviceProps(device, tempProps)
				# Set the new brightness level on the bulb.
				self.doBrightness(device, int(round(brightnessLevel / 100.0 * 255.0)))
				
			##### DIM BY #####
			elif command == indigo.kDeviceAction.DimBy:
				try:
					self.debugLog(u"device decrease brightness by:\n%s" % action)
				except Exception, e:
					self.debugLog(u"device decrease brightness by: (Unable to display action data due to error: " + str(e) + u")")
				brightnessLevel = currentBrightness - action.actionValue
				if brightnessLevel < 0:
					brightnessLevel = 0
				# Save the new brightness level into the device properties.
				tempProps = device.pluginProps
				tempProps['savedBrightness'] = int(round(brightnessLevel / 100.0 * 255.0))
				self.updateDeviceProps(device, tempProps)
				# Set the new brightness level on the bulb.
				self.doBrightness(device, int(round(brightnessLevel / 100.0 * 255.0)))
				
			##### REQUEST STATUS #####
			elif command == indigo.kDeviceAction.RequestStatus:
				try:
					self.debugLog(u"device request status:\n%s" % action)
				except Exception, e:
					self.debugLog(u"device request status: (Unable to display action data due to error: " + str(e) + u")")
				self.getBulbStatus(device.id)
				# Log the new brightnss.
				indigo.server.log(u"\"" + device.name + u"\" status request (received: " + str(device.states['brightnessLevel']) + u")", 'Sent Hue Lights')

			#### CATCH ALL #####
			else:
				indigo.server.log(u"Unhandled command \"%s\"" % (command))
			pass
		
		#
		# -- LightStrips --
		#
		elif device.deviceTypeId == "hueLightStrips":
			bulbId = device.pluginProps.get('bulbId', None)
			hostId = self.pluginPrefs.get('hostId', None)
			self.ipAddress = self.pluginPrefs.get('address', None)
			self.debugLog(u"Command is %s, LightStrips device is %s" % (command, bulbId))
			
			##### TURN ON #####
			if command == indigo.kDeviceAction.TurnOn:
				try:
					self.debugLog(u"device on:\n%s" % action)
				except Exception, e:
					self.debugLog(u"device on: (Unable to display action data due to error: " + str(e) + u")")
				# Turn it on.
				self.doOnOff(device, True)
				
			##### TURN OFF #####
			elif command == indigo.kDeviceAction.TurnOff:
				try:
					self.debugLog(u"device off:\n%s" % action)
				except Exception, e:
					self.debugLog(u"device off: (Unable to display action data due to error: " + str(e) + u")")
				# Turn it off by setting the brightness to minimum.
				self.doOnOff(device, False)

			##### TOGGLE #####
			elif command == indigo.kDeviceAction.Toggle:
				try:
					self.debugLog(u"device toggle:\n%s" % action)
				except Exception, e:
					self.debugLog(u"device toggle: (Unable to display action due to error: " + str(e) + u")")
				if currentOnState == True:
					# It's on. Turn it off.
					self.doOnOff(device, False)
				else:
					# It's off. Turn it on.
					self.doOnOff(device, True)
			
			##### SET BRIGHTNESS #####
			elif command == indigo.kDeviceAction.SetBrightness:
				try:
					self.debugLog(u"device set brightness:\n%s" % action)
				except Exception, e:
					self.debugLog(u"device set brightness: (Unable to display action data due to error: " + str(e) + u")")
				brightnessLevel = int(round(action.actionValue / 100.0 * 255.0))
				# Save the new brightness level into the device properties.
				tempProps = device.pluginProps
				tempProps['savedBrightness'] = brightnessLevel
				self.updateDeviceProps(device, tempProps)
				# Set the new brightness level on the bulb.
				self.doBrightness(device, brightnessLevel)

			##### BRIGHTEN BY #####
			elif command == indigo.kDeviceAction.BrightenBy:
				try:
					self.debugLog(u"device increase brightness by:\n%s" % action)
				except Exception, e:
					self.debugLog(u"device increase brightness by: (Unable to display action data due to error: " + str(e) + u")")
				brightnessLevel = currentBrightness + action.actionValue
				if brightnessLevel > 100:
					brightnessLevel = 100
				# Save the new brightness level into the device properties.
				tempProps = device.pluginProps
				tempProps['savedBrightness'] = int(round(brightnessLevel / 100.0 * 255.0))
				self.updateDeviceProps(device, tempProps)
				# Set the new brightness level on the bulb.
				self.doBrightness(device, int(round(brightnessLevel / 100.0 * 255.0)))
				
			##### DIM BY #####
			elif command == indigo.kDeviceAction.DimBy:
				try:
					self.debugLog(u"device decrease brightness by:\n%s" % action)
				except Exception, e:
					self.debugLog(u"device decrease brightness by: (Unable to display action data due to error: " + str(e) + u")")
				brightnessLevel = currentBrightness - action.actionValue
				if brightnessLevel < 0:
					brightnessLevel = 0
				# Save the new brightness level into the device properties.
				tempProps = device.pluginProps
				tempProps['savedBrightness'] = int(round(brightnessLevel / 100.0 * 255.0))
				self.updateDeviceProps(device, tempProps)
				# Set the new brightness level on the device.
				self.doBrightness(device, int(round(brightnessLevel / 100.0 * 255.0)))
				
			##### REQUEST STATUS #####
			elif command == indigo.kDeviceAction.RequestStatus:
				try:
					self.debugLog(u"device request status:\n%s" % action)
				except Exception, e:
					self.debugLog(u"device request status: (Unable to display action data due to error: " + str(e) + u")")
				self.getBulbStatus(device.id)
				# Log the new brightnss.
				indigo.server.log(u"\"" + device.name + u"\" status request (received: " + str(device.states['brightnessLevel']) + u")", 'Sent Hue Lights')

			#### CATCH ALL #####
			else:
				indigo.server.log(u"Unhandled command \"%s\"" % (command))
			pass
		
		#
		# -- LivingColors Bloom --
		#
		elif device.deviceTypeId == "hueLivingColorsBloom":
			bulbId = device.pluginProps.get('bulbId', None)
			hostId = self.pluginPrefs.get('hostId', None)
			self.ipAddress = self.pluginPrefs.get('address', None)
			self.debugLog(u"Command is %s, LivingColors Bloom device is %s" % (command, bulbId))
			
			##### TURN ON #####
			if command == indigo.kDeviceAction.TurnOn:
				try:
					self.debugLog(u"device on:\n%s" % action)
				except Exception, e:
					self.debugLog(u"device on: (Unable to display action data due to error: " + str(e) + u")")
				# Turn it on.
				self.doOnOff(device, True)
				
			##### TURN OFF #####
			elif command == indigo.kDeviceAction.TurnOff:
				try:
					self.debugLog(u"device off:\n%s" % action)
				except Exception, e:
					self.debugLog(u"device off: (Unable to display action data due to error: " + str(e) + u")")
				# Turn it off by setting the brightness to minimum.
				self.doOnOff(device, False)

			##### TOGGLE #####
			elif command == indigo.kDeviceAction.Toggle:
				try:
					self.debugLog(u"device toggle:\n%s" % action)
				except Exception, e:
					self.debugLog(u"device toggle: (Unable to display action due to error: " + str(e) + u")")
				if currentOnState == True:
					# It's on. Turn it off.
					self.doOnOff(device, False)
				else:
					# It's off. Turn it on.
					self.doOnOff(device, True)
			
			##### SET BRIGHTNESS #####
			elif command == indigo.kDeviceAction.SetBrightness:
				try:
					self.debugLog(u"device set brightness:\n%s" % action)
				except Exception, e:
					self.debugLog(u"device set brightness: (Unable to display action data due to error: " + str(e) + u")")
				brightnessLevel = int(round(action.actionValue / 100.0 * 255.0))
				# Save the new brightness level into the device properties.
				tempProps = device.pluginProps
				tempProps['savedBrightness'] = brightnessLevel
				self.updateDeviceProps(device, tempProps)
				# Set the new brightness level on the bulb.
				self.doBrightness(device, brightnessLevel)

			##### BRIGHTEN BY #####
			elif command == indigo.kDeviceAction.BrightenBy:
				try:
					self.debugLog(u"device increase brightness by:\n%s" % action)
				except Exception, e:
					self.debugLog(u"device increase brightness by: (Unable to display action data due to error: " + str(e) + u")")
				brightnessLevel = currentBrightness + action.actionValue
				if brightnessLevel > 100:
					brightnessLevel = 100
				# Save the new brightness level into the device properties.
				tempProps = device.pluginProps
				tempProps['savedBrightness'] = int(round(brightnessLevel / 100.0 * 255.0))
				self.updateDeviceProps(device, tempProps)
				# Set the new brightness level on the bulb.
				self.doBrightness(device, int(round(brightnessLevel / 100.0 * 255.0)))
				
			##### DIM BY #####
			elif command == indigo.kDeviceAction.DimBy:
				try:
					self.debugLog(u"device decrease brightness by:\n%s" % action)
				except Exception, e:
					self.debugLog(u"device decrease brightness by: (Unable to display action data due to error: " + str(e) + u")")
				brightnessLevel = currentBrightness - action.actionValue
				if brightnessLevel < 0:
					brightnessLevel = 0
				# Save the new brightness level into the device properties.
				tempProps = device.pluginProps
				tempProps['savedBrightness'] = int(round(brightnessLevel / 100.0 * 255.0))
				self.updateDeviceProps(device, tempProps)
				# Set the new brightness level on the device.
				self.doBrightness(device, int(round(brightnessLevel / 100.0 * 255.0)))
				
			##### REQUEST STATUS #####
			elif command == indigo.kDeviceAction.RequestStatus:
				try:
					self.debugLog(u"device request status:\n%s" % action)
				except Exception, e:
					self.debugLog(u"device request status: (Unable to display action data due to error: " + str(e) + u")")
				self.getBulbStatus(device.id)
				# Log the new brightnss.
				indigo.server.log(u"\"" + device.name + u"\" status request (received: " + str(device.states['brightnessLevel']) + u")", 'Sent Hue Lights')

			#### CATCH ALL #####
			else:
				indigo.server.log(u"Unhandled command \"%s\"" % (command))
			pass
		
		#
		# -- LivingWhites --
		#
		elif device.deviceTypeId == "hueLivingWhites":
			bulbId = device.pluginProps.get('bulbId', None)
			hostId = self.pluginPrefs.get('hostId', None)
			self.ipAddress = self.pluginPrefs.get('address', None)
			self.debugLog(u"Command is %s, LivingWhites device is %s" % (command, bulbId))
			
			##### TURN ON #####
			if command == indigo.kDeviceAction.TurnOn:
				try:
					self.debugLog(u"device on:\n%s" % action)
				except Exception, e:
					self.debugLog(u"device on: (Unable to display action data due to error: " + str(e) + u")")
				# Turn it on.
				self.doOnOff(device, True)
				
			##### TURN OFF #####
			elif command == indigo.kDeviceAction.TurnOff:
				try:
					self.debugLog(u"device off:\n%s" % action)
				except Exception, e:
					self.debugLog(u"device off: (Unable to display action data due to error: " + str(e) + u")")
				# Turn it off by setting the brightness to minimum.
				self.doOnOff(device, False)

			##### TOGGLE #####
			elif command == indigo.kDeviceAction.Toggle:
				try:
					self.debugLog(u"device toggle:\n%s" % action)
				except Exception, e:
					self.debugLog(u"device toggle: (Unable to display action due to error: " + str(e) + u")")
				if currentOnState == True:
					# It's on. Turn it off.
					self.doOnOff(device, False)
				else:
					# It's off. Turn it on.
					self.doOnOff(device, True)
			
			##### SET BRIGHTNESS #####
			elif command == indigo.kDeviceAction.SetBrightness:
				try:
					self.debugLog(u"device set brightness:\n%s" % action)
				except Exception, e:
					self.debugLog(u"device set brightness: (Unable to display action data due to error: " + str(e) + u")")
				brightnessLevel = int(round(action.actionValue / 100.0 * 255.0))
				# Save the new brightness level into the device properties.
				tempProps = device.pluginProps
				tempProps['savedBrightness'] = brightnessLevel
				self.updateDeviceProps(device, tempProps)
				# Set the new brightness level on the bulb.
				self.doBrightness(device, brightnessLevel)

			##### BRIGHTEN BY #####
			elif command == indigo.kDeviceAction.BrightenBy:
				try:
					self.debugLog(u"device increase brightness by:\n%s" % action)
				except Exception, e:
					self.debugLog(u"device increase brightness by: (Unable to display action data due to error: " + str(e) + u")")
				brightnessLevel = currentBrightness + action.actionValue
				if brightnessLevel > 100:
					brightnessLevel = 100
				# Save the new brightness level into the device properties.
				tempProps = device.pluginProps
				tempProps['savedBrightness'] = int(round(brightnessLevel / 100.0 * 255.0))
				self.updateDeviceProps(device, tempProps)
				# Set the new brightness level on the bulb.
				self.doBrightness(device, int(round(brightnessLevel / 100.0 * 255.0)))
				
			##### DIM BY #####
			elif command == indigo.kDeviceAction.DimBy:
				try:
					self.debugLog(u"device decrease brightness by:\n%s" % action)
				except Exception, e:
					self.debugLog(u"device decrease brightness by: (Unable to display action data due to error: " + str(e) + u")")
				brightnessLevel = currentBrightness - action.actionValue
				if brightnessLevel < 0:
					brightnessLevel = 0
				# Save the new brightness level into the device properties.
				tempProps = device.pluginProps
				tempProps['savedBrightness'] = int(round(brightnessLevel / 100.0 * 255.0))
				self.updateDeviceProps(device, tempProps)
				# Set the new brightness level on the device.
				self.doBrightness(device, int(round(brightnessLevel / 100.0 * 255.0)))
				
			##### REQUEST STATUS #####
			elif command == indigo.kDeviceAction.RequestStatus:
				try:
					self.debugLog(u"device request status:\n%s" % action)
				except Exception, e:
					self.debugLog(u"device request status: (Unable to display action data due to error: " + str(e) + u")")
				self.getBulbStatus(device.id)
				# Log the new brightnss.
				indigo.server.log(u"\"" + device.name + u"\" status request (received: " + str(device.states['brightnessLevel']) + u")", 'Sent Hue Lights')

			#### CATCH ALL #####
			else:
				indigo.server.log(u"Unhandled command \"%s\"" % (command))
			pass

		#
		# -- Hue Group --
		#
		if device.deviceTypeId == "hueGroup":
			groupId = device.pluginProps.get('groupId', None)
			hostId = self.pluginPrefs.get('hostId', None)
			self.ipAddress = self.pluginPrefs.get('address', None)
			self.debugLog(u"Command is %s, Group is %s" % (command, groupId))
			
			##### TURN ON #####
			if command == indigo.kDeviceAction.TurnOn:
				try:
					self.debugLog(u"device on:\n%s" % action)
				except Exception, e:
					self.debugLog(u"device on: (Unable to display action data due to error: " + str(e) + u")")
				# Turn it on.
				self.doOnOff(device, True)
				
			##### TURN OFF #####
			elif command == indigo.kDeviceAction.TurnOff:
				try:
					self.debugLog(u"device off:\n%s" % action)
				except Exception, e:
					self.debugLog(u"device off: (Unable to display action data due to error: " + str(e) + u")")
				# Turn it off by setting the brightness to minimum.
				self.doOnOff(device, False)

			##### TOGGLE #####
			elif command == indigo.kDeviceAction.Toggle:
				try:
					self.debugLog(u"device toggle:\n%s" % action)
				except Exception, e:
					self.debugLog(u"device toggle: (Unable to display action due to error: " + str(e) + u")")
				if currentOnState == True:
					# It's on. Turn it off.
					self.doOnOff(device, False)
				else:
					# It's off. Turn it on.
					self.doOnOff(device, True)
			
			##### SET BRIGHTNESS #####
			elif command == indigo.kDeviceAction.SetBrightness:
				try:
					self.debugLog(u"device set brightness:\n%s" % action)
				except Exception, e:
					self.debugLog(u"device set brightness: (Unable to display action data due to error: " + str(e) + u")")
				brightnessLevel = int(round(action.actionValue / 100.0 * 255.0))
				# Save the new brightness level into the device properties.
				tempProps = device.pluginProps
				tempProps['savedBrightness'] = brightnessLevel
				self.updateDeviceProps(device, tempProps)
				# Set the new brightness level on the bulb.
				self.doBrightness(device, brightnessLevel)

			##### BRIGHTEN BY #####
			elif command == indigo.kDeviceAction.BrightenBy:
				try:
					self.debugLog(u"device increase brightness by:\n%s" % action)
				except Exception, e:
					self.debugLog(u"device increase brightness by: (Unable to display action data due to error: " + str(e) + u")")
				brightnessLevel = currentBrightness + action.actionValue
				if brightnessLevel > 100:
					brightnessLevel = 100
				# Save the new brightness level into the device properties.
				tempProps = device.pluginProps
				tempProps['savedBrightness'] = int(round(brightnessLevel / 100.0 * 255.0))
				self.updateDeviceProps(device, tempProps)
				# Set the new brightness level on the bulb.
				self.doBrightness(device, int(round(brightnessLevel / 100.0 * 255.0)))
				
			##### DIM BY #####
			elif command == indigo.kDeviceAction.DimBy:
				try:
					self.debugLog(u"device decrease brightness by:\n%s" % action)
				except Exception, e:
					self.debugLog(u"device decrease brightness by: (Unable to display action data due to error: " + str(e) + u")")
				brightnessLevel = currentBrightness - action.actionValue
				if brightnessLevel < 0:
					brightnessLevel = 0
				# Save the new brightness level into the device properties.
				tempProps = device.pluginProps
				tempProps['savedBrightness'] = int(round(brightnessLevel / 100.0 * 255.0))
				self.updateDeviceProps(device, tempProps)
				# Set the new brightness level on the bulb.
				self.doBrightness(device, int(round(brightnessLevel / 100.0 * 255.0)))
				
			##### REQUEST STATUS #####
			elif command == indigo.kDeviceAction.RequestStatus:
				try:
					self.debugLog(u"device request status:\n%s" % action)
				except Exception, e:
					self.debugLog(u"device request status: (Unable to display action data due to error: " + str(e) + u")")
				self.getGroupStatus(device.id)
				# Log the new brightnss.
				indigo.server.log(u"\"" + device.name + u"\" status request (received: " + str(device.states['brightnessLevel']) + u")", 'Sent Hue Lights')

			#### CATCH ALL #####
			else:
				indigo.server.log(u"Unhandled command \"%s\"" % (command))
			pass
		
		#
		# -- Hue Attribute Controller --
		#
		elif device.deviceTypeId == "hueAttributeController":
			bulbDeviceId = device.pluginProps.get('bulbDeviceId', None)
			attributeToControl = device.pluginProps.get('attributeToControl', None)
			rate = device.pluginProps.get('rate', "")
			onLevel = device.pluginProps.get('defaultOnLevel', "")
			
			if bulbDeviceId == None:
				indigo.server.log(u"Hue Attribute Controller \"" + device.name + u"\" has no Hue Bulb device defined as the control destination. Action ignored.", isError=True)
				return None
			else:
				# Define the control destination device object and related variables.
				bulbDevice = indigo.devices[int(bulbDeviceId)]
				bulbDeviceProps = bulbDevice.pluginProps
				brightnessLevel = bulbDevice.states.get('brightnessLevel', 0)
				saturation = bulbDevice.states.get('saturation', 0)
				hue = bulbDevice.states.get('hue', 0)
				colorRed = bulbDevice.states.get('colorRed', 0)
				colorGreen = bulbDevice.states.get('colorGreen', 0)
				colorBlue = bulbDevice.states.get('colorBlue', 0)
				colorTemp = bulbDevice.states.get('colorTemp', 2000)
				# Convert attribute scales to work with the doHSB method.
				brightnessLevel = int(round(brightnessLevel / 100.0) * 255.0)
				saturation = int(round(saturation / 100.0 * 255.0))
				hue = int(hue * 182.0)
				
			if attributeToControl == None:
				errorText = u"Hue Attribute Controller \"" + device.name + u"\" has no Attribute to Control specified. Action ignored."
				self.errorLog(errorText)
				# Remember the error.
				self.lastErrorMessage = errorText
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
				except Exception, e:
					self.debugLog(u"Invalid rate value. Error: " + str(e))
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
				except Exception, e:
					onLevel = 100
			convertedOnLevel = onLevel
				
			self.debugLog(u"Command is %s, Bulb device ID is %s" % (command, bulbDeviceId))
			
			##### TURN ON #####
			if command == indigo.kDeviceAction.TurnOn:
				try:
					self.debugLog(u"device on:\n%s" % action)
				except Exception, e:
					self.debugLog(u"device on: (Unable to display action data due to error: " + str(e) + ")")
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
					convertedOnLevel = int(onLevel / 100.0 * 255.0)
					self.doHSB(bulbDevice, hue, convertedOnLevel, brightnessLevel, rate)
				elif attributeToControl == "colorRed":
					# RGB (Red)
					#   (255 is the maximum value allowed).
					# Convert onLevel to valid RGB number.
					convertedOnLevel = int(onLevel / 100.0 * 255.0)
					self.doRGB(bulbDevice, convertedOnLevel, colorGreen, colorBlue, rate)
				elif attributeToControl == "colorGreen":
					# RGB (Green)
					#   (255 is the maximum value allowed).
					# Convert onLevel to valid RGB number.
					convertedOnLevel = int(onLevel / 100.0 * 255.0)
					self.doRGB(bulbDevice, colorRed, convertedOnLevel, colorBlue, rate)
				elif attributeToControl == "colorBlue":
					# RGB (Blue)
					#   (255 is the maximum value allowed).
					# Convert onLevel to valid RGB number.
					convertedOnLevel = int(onLevel / 100.0 * 255.0)
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
					self.debugLog(u"device off:\n%s" % action)
				except Exception, e:
					self.debugLog(u"device off: (Unable to display action data due to error: " + str(e) + u")")
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
					self.debugLog(u"device toggle:\n%s" % action)
				except Exception, e:
					self.debugLog(u"device toggle: (Unable to display action due to error: " + str(e) + u")")
				# Set the destination attribute to either maximum or minimum.
				if attributeToControl == "hue":
					# Hue
					#   (0 or 65535)
					if currentOnState == True:
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
					if currentOnState == True:
						# It's something other than 0. Turn it off by setting the value to minimum.
						self.doHSB(bulbDevice, hue, 0, brightnessLevel, rate)
					else:
						# It's 0. Turn it on by setting the value to maximum.
						# Convert onLevel to valid saturation number.
						convertedOnLevel = int(onLevel / 100.0 * 255.0)
						self.doHSB(bulbDevice, hue, convertedOnLevel, brightnessLevel, rate)
				elif attributeToControl == "colorRed":
					# RGB (Red)
					#   (0 to 255)
					if currentOnState == True:
						# It's something other than 0. Turn it off by setting the value to minimum.
						self.doRGB(bulbDevice, 0, colorGreen, colorBlue, rate)
					else:
						# It's 0. Turn it on by setting the value to maximum.
						# Convert onLevel to valid RGB number.
						convertedOnLevel = int(onLevel / 100.0 * 255.0)
						self.doRGB(bulbDevice, convertedOnLevel, colorGreen, colorBlue, rate)
				elif attributeToControl == "colorGreen":
					# RGB (Green)
					#   (0 to 255)
					if currentOnState == True:
						# It's something other than 0. Turn it off by setting the value to minimum.
						self.doRGB(bulbDevice, colorRed, 0, colorBlue, rate)
					else:
						# It's 0. Turn it on by setting the value to maximum.
						# Convert onLevel to valid RGB number.
						convertedOnLevel = int(onLevel / 100.0 * 255.0)
						self.doRGB(bulbDevice, colorGreen, convertedOnLevel, colorBlue, rate)
				elif attributeToControl == "colorBlue":
					# RGB (Blue)
					#   (0 to 255)
					if currentOnState == True:
						# It's something other than 0. Turn it off by setting the value to minimum.
						self.doRGB(bulbDevice, colorRed, colorGreen, 0, rate)
					else:
						# It's 0. Turn it on by setting the value to maximum.
						# Convert onLevel to valid RGB number.
						convertedOnLevel = int(onLevel / 100.0 * 255.0)
						self.doRGB(bulbDevice, colorRed, colorGreen, convertedOnLevel, rate)
				elif attributeToControl == "colorTemp":
					# Color Temperature
					#   (2000 to 6500)
					if currentOnState == True:
						# It's something other than 0. Turn it off by setting the value to minimum.
						self.doColorTemperature(bulbDevice, 2000, brightnessLevel, rate)
					else:
						# It's 0. Turn it on by setting the value to maximum.
						# Convert onLevel to valid color temperature number.
						convertedOnLevel = int(onLevel / 100.0 * 4500 + 2000)
						self.doColorTemperature(bulbDevice, convertedOnLevel, brightnessLevel, rate)
				# Update the virtual dimmer device.
				if currentOnState == True:
					self.updateDeviceState(device, 'brightnessLevel', 0)
				else:
					self.updateDeviceState(device, 'brightnessLevel', onLevel)
			
			##### SET BRIGHTNESS #####
			elif command == indigo.kDeviceAction.SetBrightness:
				try:
					self.debugLog(u"device set brightness:\n%s" % action)
				except Exception, e:
					self.debugLog(u"device set brightness: (Unable to display action data due to error: " + str(e) + u")")
				# Set the destination attribute to maximum.
				if attributeToControl == "hue":
					# Hue
					#   (0 to 65535. actionValue will be in the range 0 to 100 though, so convert).
					self.doHSB(bulbDevice, int(round(action.actionValue / 100.0 * 360.0 * 182.0)), saturation, brightnessLevel, rate)
				elif attributeToControl == "saturation":
					# Saturation
					#   (0 to 255. actionValue will be in the range 0 to 100 though, so convert).
					self.doHSB(bulbDevice, hue, int(round(action.actionValue / 100.0 * 255.0)), brightnessLevel, rate)
				elif attributeToControl == "colorRed":
					# RGB (Red)
					#   (0 to 255. actionValue will be in the range 0 to 100 though, so convert).
					self.doRGB(bulbDevice, int(round(action.actionValue / 100.0 * 255.0)), colorGreen, colorBlue, rate)
				elif attributeToControl == "colorGreen":
					# RGB (Green)
					#   (0 to 255. actionValue will be in the range 0 to 100 though, so convert).
					self.doRGB(bulbDevice, colorRed, int(round(action.actionValue / 100.0 * 255.0)), colorBlue, rate)
				elif attributeToControl == "colorBlue":
					# RGB (Blue)
					#   (0 to 255. actionValue will be in the range 0 to 100 though, so convert).
					self.doRGB(bulbDevice, colorRed, colorGreen, int(round(action.actionValue / 100.0 * 255.0)), rate)
				elif attributeToControl == "colorTemp":
					# Color Temperature
					#   (2000 to 6500. actionValue will be in range 0 to 100 though, so convert).
					self.doColorTemperature(bulbDevice, int(round(action.actionValue / 100.0 * 4500.0 + 2000.0)), brightnessLevel, rate)
				# Update the virtual dimmer device.
				self.updateDeviceState(device, 'brightnessLevel', action.actionValue)
				
			##### BRIGHTEN BY #####
			elif command == indigo.kDeviceAction.BrightenBy:
				try:
					self.debugLog(u"device increase brightness by:\n%s" % action)
				except Exception, e:
					self.debugLog(u"device increase brightness by: (Unable to display action data due to error: " + str(e) + u")")
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
					self.doHSB(bulbDevice, hue, int(round(newValue / 100.0 * 255.0)), brightnessLevel, rate)
				elif attributeToControl == "colorRed":
					# RGB (Red)
					#   (0 to 255. actionValue will be in the range 0 to 100 though, so convert).
					self.doRGB(bulbDevice, int(round(newValue / 100.0 * 255.0)), colorGreen, colorBlue, rate)
				elif attributeToControl == "colorGreen":
					# RGB (Green)
					#   (0 to 255. actionValue will be in the range 0 to 100 though, so convert).
					self.doRGB(bulbDevice, colorRed, int(round(newValue / 100.0 * 255.0)), colorBlue, rate)
				elif attributeToControl == "colorBlue":
					# RGB (Blue)
					#   (0 to 255. actionValue will be in the range 0 to 100 though, so convert).
					self.doRGB(bulbDevice, colorRed, colorGreen, int(round(newValue / 100.0 * 255.0)), rate)
				elif attributeToControl == "colorTemp":
					# Color Temperature
					#   (2000 to 6500. actionValue will be in range 0 to 100 though, so convert).
					self.doColorTemperature(bulbDevice, int(round(newValue / 100.0 * 4500.0 + 2000.0)), brightnessLevel, rate)
				# Update the virtual dimmer device.
				self.updateDeviceState(device, 'brightnessLevel', newValue)
				
			##### DIM BY #####
			elif command == indigo.kDeviceAction.DimBy:
				try:
					self.debugLog(u"device decrease brightness by:\n%s" % action)
				except Exception, e:
					self.debugLog(u"device decrease brightness by: (Unable to display action data due to error: " + str(e) + u")")
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
					self.doHSB(bulbDevice, hue, int(round(newValue / 100.0 * 255.0)), brightnessLevel, rate)
				elif attributeToControl == "colorRed":
					# RGB (Red)
					#   (0 to 255. actionValue will be in the range 0 to 100 though, so convert).
					self.doRGB(bulbDevice, int(round(newValue / 100.0 * 255.0)), colorGreen, colorBlue, rate)
				elif attributeToControl == "colorGreen":
					# RGB (Green)
					#   (0 to 255. actionValue will be in the range 0 to 100 though, so convert).
					self.doRGB(bulbDevice, colorRed, int(round(newValue / 100.0 * 255.0)), colorBlue, rate)
				elif attributeToControl == "colorBlue":
					# RGB (Blue)
					#   (0 to 255. actionValue will be in the range 0 to 100 though, so convert).
					self.doRGB(bulbDevice, colorRed, colorGreen, int(round(newValue / 100.0 * 255.0)), rate)
				elif attributeToControl == "colorTemp":
					# Color Temperature
					#   (2000 to 6500. actionValue will be in range 0 to 100 though, so convert).
					self.doColorTemperature(bulbDevice, int(round(newValue / 100.0 * 4500.0 + 2000.0)), brightnessLevel, rate)
				# Update the virtual dimmer device.
				self.updateDeviceState(device, 'brightnessLevel', newValue)
				
			##### REQUEST STATUS #####
			elif command == indigo.kDeviceAction.RequestStatus:
				try:
					self.debugLog(u"device request status:\n%s" % action)
				except Exception, e:
					self.debugLog(u"device request status: (Unable to display action data due to error: " + str(e) + u")")
				# This actually requests the status of the virtual dimmer device's destination Hue device/group.
				self.getBulbStatus(bulbDeviceId)
				# Show the current virtual dimmer level in the log.  There will likely be a delay for
				#   the destination Hue device status, so we're not going to wait for that status update.
				#   We'll just return the current virtual device brightness level in the log.
				indigo.server.log(u"\"" + device.name + u"\" status request (currently: " + str(currentBrightness) + u")")

			#### CATCH ALL #####
			else:
				indigo.server.log(u"Unhandled Hue Attribute Controller command \"%s\"" % (command))
			pass
	
	########################################
	# Action Handling Methods
	########################################
	
	# Start/Stop Brightening
	########################################
	def startStopBrightening(self, action, device):
		# Catch if no device was passed in the action call.
		if device == None:
			errorText = u"No device was selected for the \"" + action.name + u"\" action. Please edit the action and select a Hue Light device."
			self.errorLog(errorText)
			# Remember the error.
			self.lastErrorMessage = errorText
			return
			
		self.debugLog(u"startStopBrightening: device: " + device.name + u", action:\n" + str(action))
		# Make sure the device is in the deviceList.
		if device.id in self.deviceList:
			
			# First, remove from the dimmingList if it's there.
			if device.id in self.dimmingList:
				# Log the event to Indigo log.
				indigo.server.log(u"\"" + device.name + u"\" stop dimming", 'Sent Hue Lights')
				# Remove from list.
				self.dimmingList.remove(device.id)
				
			# Now remove from brighteningList if it's in the list and add if not.
			if device.id in self.brighteningList:
				# Log the event to Indigo log.
				indigo.server.log(u"\"" + device.name + u"\" stop brightening", 'Sent Hue Lights')
				# Remove from list.
				self.brighteningList.remove(device.id)
				# Get the bulb status
				self.getBulbStatus(device.id)
				# Log the new brightnss.
				indigo.server.log(u"\"" + device.name + u"\" status request (received: " + str(device.states['brightnessLevel']) + u")", 'Sent Hue Lights')
			else:
				# Only begin brightening if current brightness is less than 100%.
				if device.states['brightnessLevel'] < 100:
					# Log the event in Indigo log.
					indigo.server.log(u"\"" + device.name + u"\" start brightening", 'Sent Hue Lights')
					# Add to list.
					self.brighteningList.append(device.id)
				
		return
		
	# Start/Stop Dimming
	########################################
	def startStopDimming(self, action, device):
		# Catch if no device was passed in the action call.
		if device == None:
			errorText = u"No device was selected for the \"" + action.name + "\" action. Please edit the action and select a Hue Light device."
			self.errorLog(errorText)
			# Remember the error.
			self.lastErrorMessage = errorText
			return
			
		self.debugLog(u"startStopDimming: device: " + device.name + ", action:\n" + str(action))
		# Make sure the device is in the deviceList.
		if device.id in self.deviceList:
			# First, remove from brighteningList if it's there.
			if device.id in self.brighteningList:
				# Log the event to Indigo log.
				indigo.server.log(u"\"" + device.name + u"\" stop brightening", 'Sent Hue Lights')
				# Remove from list.
				self.brighteningList.remove(device.id)
				
			# Now remove from dimmingList if it's in the list and add if not.
			if device.id in self.dimmingList:
				# Log the event to Indigo log.
				indigo.server.log(u"\"" + device.name + u"\" stop dimming", 'Sent Hue Lights')
				# Remove from list.
				self.dimmingList.remove(device.id)
				# Get the bulb status
				self.getBulbStatus(device.id)
				# Log the new brightnss.
				indigo.server.log(u"\"" + device.name + u"\" status request (received: " + str(device.states['brightnessLevel']) + ")", 'Sent Hue Lights')
			else:
				# Only begin dimming if current brightness is greater than 0%.
				if device.states['brightnessLevel'] > 0:
					# Log the event in Indigo log.
					indigo.server.log(u"\"" + device.name + u"\" start dimming", 'Sent Hue Lights')
					# Add to list.
					self.dimmingList.append(device.id)

		return
	
	# Set Brightness
	########################################
	def setBrightness(self, action, device):
		self.debugLog(u"setBrightness: device: " + device.name + u", action:\n" + str(action))
		
		brightnessSource = action.props.get('brightnessSource', False)
		brightness = action.props.get('brightness', False)
		brightnessVarId = action.props.get('brightnessVariable', False)
		brightnessDevId = action.props.get('brightnessDevice', False)
		useRateVariable = action.props.get('useRateVariable', False)
		rate = action.props.get('rate', False)
		rateVarId = action.props.get('rateVariable', False)
		delay = action.props.get('delay', False)
		retries = action.props.get('retries', False)
		
		# Act based on device type.
		if device.deviceTypeId == "hueGroup":
			# Sanity check on group ID
			groupId = device.pluginProps.get('groupId', None)
			if groupId is None or groupId == 0:
				errorText = u"No group ID selected for device \"%s\". Check settings for this device and select a Hue Group to control." % (device.name)
				self.errorLog(errorText)
				# Remember the error.
				self.lastErrorMessage = errorText
				return
		else:
			# Sanity check on bulb ID
			bulbId = device.pluginProps.get('bulbId', None)
			if bulbId is None or bulbId == 0:
				errorText = u"No bulb ID selected for device \"%s\". Check settings for this device and select a Hue Device to control." % (device.name)
				self.errorLog(errorText)
				# Remember the error.
				self.lastErrorMessage = errorText
				return
		
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
				errorText = u"No brightness source information was provided."
				self.errorLog(errorText)
				# Remember the error.
				self.lastErrorMessage = errorText
				return None
		
		if brightnessSource == "custom":
			if brightness == False and brightness.__class__ != int:
				errorText = u"No brightness level was specified."
				self.errorLog(errorText)
				# Remember the error.
				self.lastErrorMessage = errorText
				return None
			else:
				try:
					brightness = int(brightness)
					if brightness < 0 or brightness > 100:
						errorText = u"Brightness level " + str(brightness) + u" is outside the acceptable range of 0 to 100."
						self.errorLog(errorText)
						# Remember the error.
						self.lastErrorMessage = errorText
						return None
				except ValueError:
					errorText = u"Brightness level \"" + str(brightness) + u"\" is invalid. Brightness values can only contain numbers."
					self.errorLog(errorText)
					# Remember the error.
					self.lastErrorMessage = errorText
					return None
			self.debugLog(u"Brightness (source: custom): " + str(brightness) + u", class: " + str(brightness.__class__))
		
		elif brightnessSource == "variable":
			if not brightnessVarId:
				errorText = u"No variable containing the brightness level was specified."
				self.errorLog(errorText)
				# Remember the error.
				self.lastErrorMessage = errorText
				return None
			else:
				try:
					brightnessVar = indigo.variables[int(brightnessVarId)]
					# Embedding float method inside int method allows for fractional
					#   data but just drops everything after the decimal.
					brightness = int(float(brightnessVar.value))
					if brightness < 0 or brightness > 100:
						errorText = u"Brightness level " + str(brightness) + u" found in variable \"" + brightnessVar.name + u"\" is outside the acceptable range of 0 to 100."
						self.errorLog(errorText)
						# Remember the error.
						self.lastErrorMessage = errorText
						return None
				except ValueError:
					errorText = u"Brightness level \"" + str(brightnessVar.value) + u"\" found in variable \"" + brightnessVar.name + u"\" is invalid. Brightness values can only contain numbers."
					self.errorLog(errorText)
					# Remember the error.
					self.lastErrorMessage = errorText
					return None
				except IndexError:
					errorText = u"The specified variable (ID " + str(brightnessVarId) + u") does not exist in the Indigo database."
					self.errorLog(errorText)
					# Remember the error.
					self.lastErrorMessage = errorText
					return None
			self.debugLog(u"Brightness (source: variable): " + str(brightness) + u", class: " + str(brightness.__class__))
		
		elif brightnessSource == "dimmer":
			if not brightnessDevId:
				errorText = u"No dimmer was specified as the brightness level source."
				self.errorLog(errorText)
				# Remember the error.
				self.lastErrorMessage = errorText
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
						errorText = u"No device with the name \"" + str(brightnessDevId) + u"\" could be found in the Indigo database."
						self.errorLog(errorText)
						# Remember the error.
						self.lastErrorMessage = errorText
						return None
				try:
					brightnessDev = indigo.devices[brightnessDevId]
					brightness = int(brightnessDev.states.get('brightnessLevel', None))
					if brightness == None:
						# Looks like this isn't a dimmer after all.
						errorText = u"Device \"" + brightnessDev.name + u"\" does not appear to be a dimmer. Only dimmers can be used as brightness sources."
						self.errorLog(errorText)
						# Remember the error.
						self.lastErrorMessage = errorText
						return None
					elif brightness < 0 or brightness > 100:
						errorText = u"Brightness level " + str(brightness) + u" of device \"" + brightnessDev.name + u"\" is outside the acceptable range of 0 to 100."
						self.errorLog(errorText)
						# Remember the error.
						self.lastErrorMessage = errorText
						return None
				except ValueError:
					errorText = u"The device \"" + brightnessDev.name + u"\" does not have a brightness level. Please ensure that the device is a dimmer."
					self.errorLog(errorText)
					# Remember the error.
					self.lastErrorMessage = errorText
					return None
				except KeyError:
					errorText = u"The specified device (ID " + str(brightnessDevId) + u") does not exist in the Indigo database."
					self.errorLog(errorText)
					# Remember the error.
					self.lastErrorMessage = errorText
					return None
			self.debugLog(u"Brightness (source: other dimmer): " + str(brightness) + u", class: " + str(brightness.__class__))
		
		else:
			errorText = u"Unrecognized brightness source \"" + str(brightnessSource) + u"\". Valid brightness sources are \"custom\", \"variable\", and \"dimmer\"."
			self.errorLog(errorText)
			# Remember the error.
			self.lastErrorMessage = errorText
			return None
		
		if not useRateVariable:
			if not rate and rate.__class__ == bool:
				errorText = u"No ramp rate was specified."
				self.errorLog(errorText)
				# Remember the error.
				self.lastErrorMessage = errorText
				return None
			else:
				try:
					rate = float(rate)
					if rate < 0 or rate > 540:
						errorText = u"Ramp rate value " + str(rate) + u" is outside the acceptible range of 0 to 540."
						self.errorLog(errorText)
						# Remember the error.
						self.lastErrorMessage = errorText
						return None
				except ValueError:
					errorText = u"Ramp rate value \"" + str(rate) + u" is an invalid value. Ramp rate values can only contain numbers."
					self.errorLog(errorText)
					# Remember the error.
					self.lastErrorMessage = errorText
					return None
			self.debugLog(u"Rate: " + str(rate))
		
		else:
			if not rateVarId:
				errorText = u"No variable containing the ramp rate time was specified."
				self.errorLog(errorText)
				# Remember the error.
				self.lastErrorMessage = errorText
				return None
			else:
				try:
					# Make sure rate is set to ""
					rate = ""
					rateVar = indigo.variables[int(rateVarId)]
					rate = float(rateVar.value)
					if rate < 0 or rate > 540:
						errorText = u"Ramp rate value \"" + str(rate) + u"\" found in variable \"" + rateVar.name + u"\" is outside the acceptible range of 0 to 540."
						self.errorLog(errorText)
						# Remember the error.
						self.lastErrorMessage = errorText
						return None
				except ValueError:
					errorText = u"Ramp rate value \"" + str(rate) + u"\" found in variable \"" + rateVar.name + u"\" is an invalid value. Ramp rate values can only contain numbers."
					self.errorLog(errorText)
					# Remember the error.
					self.lastErrorMessage = errorText
					return None
				except IndexError:
					errorText = u"The specified variable (ID " + str(brightnessVarId) + u") does not exist in the Indigo database."
					self.errorLog(errorText)
					# Remember the error.
					self.lastErrorMessage = errorText
			self.debugLog(u"Rate: " + str(rate))
		
		# Save the new brightness level into the device properties.
		if brightness > 0:
			tempProps = device.pluginProps
			tempProps['savedBrightness'] = brightness
			self.updateDeviceProps(device, tempProps)
		
		# Send the command.
		self.doBrightness(device, int(round(brightness / 100.0 * 255.0)), rate)
		
	# Set RGB Level Action
	########################################
	def setRGB(self, action, device):
		self.debugLog(u"setRGB: device: " + device.name + ", action:\n" + str(action))
		
		# Act based on device type.
		if device.deviceTypeId == "hueGroup":
			# Sanity check on group ID
			groupId = device.pluginProps.get('groupId', None)
			if groupId is None or groupId == 0:
				errorText = u"No group ID selected for device \"%s\". Check settings for this device and select a Hue Group to control." % (device.name)
				self.errorLog(errorText)
				# Remember the error.
				self.lastErrorMessage = errorText
				return
		else:
			# Sanity check on bulb ID
			bulbId = device.pluginProps.get('bulbId', None)
			if bulbId is None or bulbId == 0:
				errorText = u"No bulb ID selected for device \"%s\". Check settings for this device and select a Hue Device to control." % (device.name)
				self.errorLog(errorText)
				# Remember the error.
				self.lastErrorMessage = errorText
				return
		
		try:
			red = int(action.props.get('red', 0))
		except ValueError:
			errorText = u"Red color value specified for \"" + device.name + u"\" is invalid."
			self.errorLog(errorText)
			# Remember the error.
			self.lastErrorMessage = errorText
			return
			
		try:
			green = int(action.props.get('green', 0))
		except ValueError:
			errorText = u"Green color value specified for \"" + device.name + u"\" is invalid."
			self.errorLog(errorText)
			# Remember the error.
			self.lastErrorMessage = errorText
			return
			
		try:
			blue = int(action.props.get('blue', 0))
		except ValueError:
			errorText = u"Blue color value specified for \"" + device.name + u"\" is invalid."
			self.errorLog(errorText)
			# Remember the error.
			self.lastErrorMessage = errorText
			return
			
		try:
			rampRate = action.props.get('rate', -1)
			if rampRate == -1 or rampRate == "":
			    rampRate = float(device.pluginProps.get('rate', 0.5))
			else:
			    rampRate = float(rampRate)
		except ValueError:
			errorText = u"Ramp Rate value specified for \"" + device.name + u"\" is invalid."
			self.errorLog(errorText)
			# Remember the error.
			self.lastErrorMessage = errorText
			return
			
		# Determine the brightness based on the highest RGB value.
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
		
	# Set HSB Action
	########################################
	def setHSB(self, action, device):
		self.debugLog(u"setHSB: device: " + device.name + u", action:\n" + str(action))
		
		# Act based on device type.
		if device.deviceTypeId == "hueGroup":
			# Sanity check on group ID
			groupId = device.pluginProps.get('groupId', None)
			if groupId is None or groupId == 0:
				errorText = u"No group ID selected for device \"%s\". Check settings for this device and select a Hue Group to control." % (device.name)
				self.errorLog(errorText)
				# Remember the error.
				self.lastErrorMessage = errorText
				return
		else:
			# Sanity check on bulb ID
			bulbId = device.pluginProps.get('bulbId', None)
			if bulbId is None or bulbId == 0:
				errorText = u"No bulb ID selected for device \"%s\". Check settings for this device and select a Hue Device to control." % (device.name)
				self.errorLog(errorText)
				# Remember the error.
				self.lastErrorMessage = errorText
				return
		
		try:
			hue = float(action.props.get('hue', 0))
		except ValueError:
			# The float() cast above might fail if the user didn't enter a number:
			errorText = u"Set Hue, Saturation, Brightness for device \"%s\" -- invalid hue value (must range 0-360)" % (device.name,)
			self.errorLog(errorText)
			# Remember the error.
			self.lastErrorMessage = errorText
			return
			
		try:
			saturation = int(action.props.get('saturation', 0))
		except ValueError:
			# The int() cast above might fail if the user didn't enter a number:
			errorText = u"Set Hue, Saturation, Brightness for device \"%s\" -- invalid saturation value (must range 0-100)" % (device.name,)
			self.errorLog(errorText)
			# Remember the error.
			self.lastErrorMessage = errorText
			return
			
		try:
			brightness = int(action.props.get('brightness', 100))
		except ValueError:
			# The int() cast above might fail if the user didn't enter a number:
			errorText = u"Set Hue, Saturation, Brightness for device \"%s\" -- invalid brightness percentage (must range 0-100)" % (device.name,)
			self.errorLog(errorText)
			# Remember the error.
			self.lastErrorMessage = errorText
			return
		
		try:
			rampRate = action.props.get('rate', -1)
			if rampRate == -1 or rampRate == "":
			    rampRate = float(device.pluginProps.get('rate', 0.5))
			else:
			    rampRate = float(rampRate)
		except ValueError:
			errorText = u"Ramp Rate value specified for \"" + device.name + u"\" is invalid."
			self.errorLog(errorText)
			# Remember the error.
			self.lastErrorMessage = errorText
			return
			
		# Scale these values to match Hue
		brightness = int(ceil(brightness / 100.0 * 255.0))
		saturation = int(ceil(saturation / 100.0 * 255.0))
		hue = int(round(hue * 182.0))
		
		# Save the new brightness level into the device properties.
		if brightness > 0:
			tempProps = device.pluginProps
			tempProps['savedBrightness'] = brightness
			self.updateDeviceProps(device, tempProps)
			
		# Send the command.
		self.doHSB(device, hue, saturation, brightness, rampRate)
		
	# Set xyY Action
	########################################
	def setXYY(self, action, device):
		self.debugLog(u"setXYY calld. device: " + device.name + u", action:\n" + str(action))
		
		# Act based on device type.
		if device.deviceTypeId == "hueGroup":
			# Sanity check on group ID
			groupId = device.pluginProps.get('groupId', None)
			if groupId is None or groupId == 0:
				errorText = u"No group ID selected for device \"%s\". Check settings for this device and select a Hue Group to control." % (device.name)
				self.errorLog(errorText)
				# Remember the error.
				self.lastErrorMessage = errorText
				return
		else:
			# Sanity check on bulb ID
			bulbId = device.pluginProps.get('bulbId', None)
			if bulbId is None or bulbId == 0:
				errorText = u"No bulb ID selected for device \"%s\". Check settings for this device and select a Hue Device to control." % (device.name)
				self.errorLog(errorText)
				# Remember the error.
				self.lastErrorMessage = errorText
				return
		
		try:
			colorX = float(action.props.get('xyy_x', 0))
		except ValueError:
			# The float() cast above might fail if the user didn't enter a number:
			errorText = u"Set chromatisety x, y, and Y values for the device \"%s\" -- invalid x value (must be in the range of 0.0-1.0)" % (device.name,)
			self.errorLog(errorText)
			# Remember the error.
			self.lastErrorMessage = errorText
			return
			
		try:
			colorY = float(action.props.get('xyy_y', 0))
		except ValueError:
			# The float() cast above might fail if the user didn't enter a number:
			errorText = u"Set chromatisety x, y, and Y values for the device \"%s\" -- invalid y value (must be in the range of 0.0-1.0)" % (device.name,)
			self.errorLog(errorText)
			# Remember the error.
			self.lastErrorMessage = errorText
			return
			
		try:
			brightness = float(action.props.get('xyy_Y', 0))
		except ValueError:
			# The float() cast above might fail if the user didn't enter a number:
			errorText = u"Set chromatisety x, y, and Y values for the device \"%s\" -- invalid Y value (must be in the range of 0.0-1.0)" % (device.name,)
			self.errorLog(errorText)
			# Remember the error.
			self.lastErrorMessage = errorText
			return
			
		try:
			rampRate = action.props.get('rate', -1)
			if rampRate == -1 or rampRate == "":
			    rampRate = float(device.pluginProps.get('rate', 0.5))
			else:
			    rampRate = float(rampRate)
		except ValueError:
			errorText = u"Ramp Rate value specified for \"" + device.name + u"\" is invalid."
			self.errorLog(errorText)
			# Remember the error.
			self.lastErrorMessage = errorText
			return
			
		# Scale the brightness values to match Hue system requirements.
		brightness = int(ceil(brightness * 255.0))
		
		# Save the new brightness level into the device properties.
		if brightness > 0:
			tempProps = device.pluginProps
			tempProps['savedBrightness'] = brightness
			self.updateDeviceProps(device, tempProps)
			
		# Send the command.
		self.doXYY(device, colorX, colorY, brightness, rampRate)
		
	# Set Color Temperature Action
	########################################
	def setColorTemperature(self, action, device):
		self.debugLog(u"setColorTemperature: device: " + device.name + ", action:\n" + str(action))
		
		# Act based on device type.
		if device.deviceTypeId == "hueGroup":
			# Sanity check on group ID
			groupId = device.pluginProps.get('groupId', None)
			if groupId is None or groupId == 0:
				errorText = u"No group ID selected for device \"%s\". Check settings for this device and select a Hue Group to control." % (device.name)
				self.errorLog(errorText)
				# Remember the error.
				self.lastErrorMessage = errorText
				return
		else:
			# Sanity check on bulb ID
			bulbId = device.pluginProps.get('bulbId', None)
			if bulbId is None or bulbId == 0:
				errorText = u"No bulb ID selected for device \"%s\". Check settings for this device and select a Hue Device to control." % (device.name)
				self.errorLog(errorText)
				# Remember the error.
				self.lastErrorMessage = errorText
				return
		
		preset = action.props.get('preset', "custom")
		try:
			temperature = int(action.props.get('temperature', 2800))
		except ValueError:
			# The int() cast above might fail if the user didn't enter a number:
			errorText = u"Set Color Temperature for device \"%s\" -- invalid color temperature (must range 2000-6500)" % (device.name,)
			self.errorLog(errorText)
			# Remember the error.
			self.lastErrorMessage = errorText
			return
		
		if preset == "custom":
			brightness = action.props.get('brightness', False)
			if brightness:
				try:
					brightness = int(brightness)
				except ValueError:
					errorText = u"Set Color Temperature for device \"%s\" -- invalid brightness (must be in the range 0-100)" % (device.name,)
					self.errorLog(errorText)
					# Remember the error.
					self.lastErrorMessage = errorText
			else:
				brightness = device.states['brightnessLevel']
				
			# Scale the brightness value for use with Hue.
			brightness = int(round(brightness / 100.0 * 255.0))
		
		try:
			rampRate = action.props.get('rate', -1)
			if rampRate == -1 or rampRate == "":
			    rampRate = float(device.pluginProps.get('rate', 0.5))
			else:
			    rampRate = float(rampRate)
		except ValueError:
			errorText = u"Ramp Rate value specified for \"" + device.name + u"\" is invalid."
			self.errorLog(errorText)
			# Remember the error.
			self.lastErrorMessage = errorText
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
			
		# Save the new brightness level into the device properties.
		if brightness > 0:
			tempProps = device.pluginProps
			tempProps['savedBrightness'] = brightness
			self.updateDeviceProps(device, tempProps)
		
		# Send the command.
		self.doColorTemperature(device, temperature, brightness, rampRate)
		
	# Set Single Alert Action
	########################################
	def alertOnce(self, action, device):
		self.debugLog(u"alertOnce: device: " + device.name + u", action:\n" + str(action))
		
		# Act based on device type.
		if device.deviceTypeId == "hueGroup":
			# Sanity check on group ID
			groupId = device.pluginProps.get('groupId', None)
			if groupId is None or groupId == 0:
				errorText = u"No group ID selected for device \"%s\". Check settings for this device and select a Hue Group to control." % (device.name)
				self.errorLog(errorText)
				# Remember the error.
				self.lastErrorMessage = errorText
				return
		else:
			# Sanity check on bulb ID
			bulbId = device.pluginProps.get('bulbId', None)
			if bulbId is None or bulbId == 0:
				errorText = u"No bulb ID selected for device \"%s\". Check settings for this device and select a Hue Device to control." % (device.name)
				self.errorLog(errorText)
				# Remember the error.
				self.lastErrorMessage = errorText
				return
		
		self.doAlert(device, "select")
		
	# Set Long Alert Action
	########################################
	def longAlert(self, action, device):
		self.debugLog(u"longAlert: device: " + device.name + u", action:\n" + str(action))
		
		# Act based on device type.
		if device.deviceTypeId == "hueGroup":
			# Sanity check on group ID
			groupId = device.pluginProps.get('groupId', None)
			if groupId is None or groupId == 0:
				errorText = u"No group ID selected for device \"%s\". Check settings for this device and select a Hue Group to control." % (device.name)
				self.errorLog(errorText)
				# Remember the error.
				self.lastErrorMessage = errorText
				return
		else:
			# Sanity check on bulb ID
			bulbId = device.pluginProps.get('bulbId', None)
			if bulbId is None or bulbId == 0:
				errorText = u"No bulb ID selected for device \"%s\". Check settings for this device and select a Hue Device to control." % (device.name)
				self.errorLog(errorText)
				# Remember the error.
				self.lastErrorMessage = errorText
				return
		
		self.doAlert(device, "lselect")
		
	# Stop Alert Action
	########################################
	def stopAlert(self, action, device):
		self.debugLog(u"stopAlert: device: " + device.name + u", action:\n" + str(action))
		
		# Act based on device type.
		if device.deviceTypeId == "hueGroup":
			# Sanity check on group ID
			groupId = device.pluginProps.get('groupId', None)
			if groupId is None or groupId == 0:
				errorText = u"No group ID selected for device \"%s\". Check settings for this device and select a Hue Group to control." % (device.name)
				self.errorLog(errorText)
				# Remember the error.
				self.lastErrorMessage = errorText
				return
		else:
			# Sanity check on bulb ID
			bulbId = device.pluginProps.get('bulbId', None)
			if bulbId is None or bulbId == 0:
				errorText = u"No bulb ID selected for device \"%s\". Check settings for this device and select a Hue Device to control." % (device.name)
				self.errorLog(errorText)
				# Remember the error.
				self.lastErrorMessage = errorText
				return
		
		self.doAlert(device, "none")
	
	# Set Effect Action
	########################################
	def effect(self, action, device):
		self.debugLog(u"effect: device: " + device.name + u", action:\n" + str(action))
		
		# Act based on device type.
		if device.deviceTypeId == "hueGroup":
			# Sanity check on group ID
			groupId = device.pluginProps.get('groupId', None)
			if groupId is None or groupId == 0:
				errorText = u"No group ID selected for device \"%s\". Check settings for this device and select a Hue Group to control." % (device.name)
				self.errorLog(errorText)
				# Remember the error.
				self.lastErrorMessage = errorText
				return
		else:
			# Sanity check on bulb ID
			bulbId = device.pluginProps.get('bulbId', None)
			if bulbId is None or bulbId == 0:
				errorText = u"No bulb ID selected for device \"%s\". Check settings for this device and select a Hue Device to control." % (device.name)
				self.errorLog(errorText)
				# Remember the error.
				self.lastErrorMessage = errorText
				return
		
		effect = action.props.get('effect', False)
		if not effect:
			errorText = u"No effect specified."
			self.errorLog(errorText)
			# Remember the error.
			self.lastErrorMessage = errorText
			return False
		else:
			self.doEffect(device, effect)
			
	# Save Preset Action
	########################################
	def savePreset(self, action, device):
		self.debugLog(u"savePreset called. action values:\n" + str(action) + u"\nDevice/Type ID:\n" + str(device) + "\n")
		errorsDict = indigo.Dict()
		errorsDict['showAlertText'] = u""
		actionType = "action"
		# Work with both Menu and Action actions.
		try:
			device = indigo.devices[int(action.get('deviceId', 0))]
			actionType = "menu"
		except AttributeError:
			# This is an action, not a menu call.
			pass
			
		# Sanity check on bulb ID
		bulbId = device.pluginProps.get('bulbId', None)
		if bulbId is None or bulbId == 0:
			errorText = u"No Hue device ID selected for \"%s\". Check settings and select a Hue device to control." % (device.name)
			self.errorLog(errorText)
			# Remember the error.
			self.lastErrorMessage = errorText
			return
			
		# Get the presetId.
		if actionType == "menu":
			presetId = action.get('presetId', False)
		else:
			presetId = action.props.get('presetId', False)
			
		if not presetId:
			errorText = u"No Preset specified."
			self.errorLog(errorText)
			# Remember the error.
			self.lastErrorMessage = errorText
			return False
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
						errorsDict['rate'] = u"Ramp Rate must be a number between 0 and 540 seconds and can be in increments of 0.1 seconds."
						errorsDict['showAlertText'] += errorsDict['rate']
						return (False, action, errorsDict)
				except ValueError:
					errorsDict['rate'] = u"Ramp Rate must be a number between 0 and 540 seconds and can be in increments of 0.1 seconds."
					errorsDict['showAlertText'] += errorsDict['rate']
					return (False, action, errorsDict)
				except Exception, e:
					errorsDict['rate'] = u"Invalid Ramp Rate value: " + str(e)
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
				errorsDict['presetName'] = u"The Preset Name is too long. Please choose a name that is 50 or fewer characters long."
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
		for key, value in device.states.iteritems():
			# (Index 1 = preset data).
			presets[presetId][1][key] = value

		# Add the Ramp Rate to the Preset.
		if rampRate != -1:	# May still be a sring if passed by embedded script call.
			try:
				rampRate = float(rampRate)
				if (rampRate < 0) or (rampRate > 540):
					errorText = u"Ramp Rate must be a number between 0 and 540 seconds and can be in increments of 0.1 seconds. Value \"" + str(rampRate) + u"\" ignored."
					self.errorLog(errorText)
					# Remember the error.
					self.lastErrorMessage = errorText
					rampRate = -1
			except ValueError:
				errorText = u"Ramp Rate must be a number between 0 and 540 seconds and can be in increments of 0.1 seconds. Value \"" + str(rampRate) + u"\" ignored."
				self.errorLog(errorText)
				# Remember the error.
				self.lastErrorMessage = errorText
				rampRate = -1
			except Exception, e:
				errorText = u"Invalid Ramp Rate value \"" + str(rampRate) + u"\". Error was: " + str(e)
				self.errorLog(errorText)
				# Remember the error.
				self.lastErrorMessage = errorText
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
			indigo.server.log(u"\"" + device.name + u"\" states saved to Preset " + str(presetId + 1) + u" (" + presetName + u")")
		else:
			indigo.server.log(u"\"" + device.name + u"\" states saved to Preset " + str(presetId + 1) + u" (" + presetName + u") with ramp rate " + str(rampRate) + u" sec.")
			
		# Return a tuple if this is a menu item action.
		if actionType == "menu":
			return (True, action)
			
	# Recall Preset Action
	########################################
	def recallPreset(self, action, device):
		self.debugLog(u"recallPreset called. action values:\n" + str(action) + u"\nDevice/Type ID:\n" + str(device) + u"\n")
		errorsDict = indigo.Dict()
		errorsDict['showAlertText'] = u""
		actionType = "action"
		# Work with both Menu and Action actions.
		try:
			device = indigo.devices[int(action.get('deviceId', 0))]
			actionType = "menu"
		except AttributeError:
			# This is an action, not a menu call.
			pass
		
		# Sanity check on bulb ID
		bulbId = device.pluginProps.get('bulbId', None)
		if bulbId is None or bulbId == 0:
			errorText = u"No Hue device ID selected for \"%s\". Check settings and select a Hue device to control." % (device.name)
			self.errorLog(errorText)
			# Remember the error.
			self.lastErrorMessage = errorText
			return
			
		# Get the presetId.
		if actionType == "menu":
			presetId = action.get('presetId', False)
		else:
			presetId = action.props.get('presetId', False)
			
		if not presetId:
			errorText = u"No Preset specified."
			self.errorLog(errorText)
			# Remember the error.
			self.lastErrorMessage = errorText
			return False
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
					# Round the number to the nearest 10th.
					rampRate = round(rampRate, 1)
					if (rampRate < 0) or (rampRate > 540):
						errorsDict['rate'] = u"Ramp Rate must be a number between 0 and 540 seconds and can be in increments of 0.1 seconds."
						errorsDict['showAlertText'] += errorsDict['rate']
						return (False, action, errorsDict)
				except ValueError:
					errorsDict['rate'] = u"Ramp Rate must be a number between 0 and 540 seconds and can be in increments of 0.1 seconds."
					errorsDict['showAlertText'] += errorsDict['rate']
					return (False, action, errorsDict)
				except Exception, e:
					errorsDict['rate'] = u"Invalid Ramp Rate value: " + str(e)
					errorsDict['showAlertText'] += errorsDict['rate']
					return (False, action, errorsDict)
		else:
			rampRate = action.props.get('rate', "")
			
		# If there is no Ramp Rate specified, use -1.
		if rampRate == "":
			rampRate = -1
			
		# Get the modelId from the device.
		modelId = device.pluginProps.get('modelId', False)
		if not modelId:
			errorText = u"The \"" + device.name + u"\" devuce is not a Hue device. Please select a Hue device for this action."
			self.errorLog(errorText)
			# Remember the error.
			self.lastErrorMessage = errorText
			return
			
		elif modelId not in kCompatibleDeviceIDs:
			errorText = u"The \"" + device.name + u"\" device is not a compatible Hue device. Please select a compatible Hue device."
			self.errorLog(errorText)
			# Remember the error.
			self.lastErrorMessage = errorText
			return
			
		# Get the data from the preset in the plugin prefs.
		presetName = self.pluginPrefs['presets'][presetId][0]
		presetData = self.pluginPrefs['presets'][presetId][1]
		try:
			# Prior to version 1.2.4, this key did not exist in the presets.
			presetRate = self.pluginPrefs['presets'][presetId][2]
			# Round the saved preset ramp rate to the nearest 10th.
			presetRate = round(presetRate, 1)
		except Exception, e:
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
				errorsDict['presetId'] = u"This Preset is empty. Please select a Preset that contains data (the number will have an asterisk (*) next to it)."
				errorsDict['showAlertText'] += errorsDict['presetId']
				return (False, action, errorsDict)
			else:
				errorText = u"Preset " + str(presetId + 1) + u" (" + presetName + u") is empty. The \"" + device.name + u"\" device was not chnaged."
				self.errorLog(errorText)
				# Remember the error.
				self.lastErrorMessage = errorText
				return

		# Determine whether the target device supports color.
		supportsColor = True
		if modelId in kLivingWhitesDeviceIDs:
			supportsColor = False

		# Determine whether the target device supports color temperature.
		supportsColorTemperature = False
		if modelId in kHueBulbDeviceIDs:
			supportsColorTemperature = True

		# Get the brightness level (which is common to all devices).
		brightnessLevel = presetData.get('brightnessLevel', 100)
		# Convert the brightnessLevel to 0-255 range for use in the light
		#   changing method calls.
		brightness = int(round(brightnessLevel / 100.0 * 255.0))
		
		# Act based on the capabilities of the target device.
		if supportsColor:
			if supportsColorTemperature:
				# This device supports all currently known color modes.
				#   Now determine which mode was saved in the preset and use
				#   use it with the target device (use "ct" as the default).
				colorMode = presetData.get('colorMode', "ct")
				
				if colorMode == "ct":
					# Get the color temperature state (use 2800 as default).
					colorTemp = presetData.get('colorTemp', 2800)
					
					# Make the change to the light.
					self.doColorTemperature(device, colorTemp, brightness, rampRate)
					
				elif colorMode == "hs":
					# Get the hue (use 0 as the default).
					hue = presetData.get('hue', 0)
					# Conver the hue from 0-360 range to 0-65535 range.
					hue = int(round(hue * 182.0))
					# Get the saturation (use 100 as the default).
					saturation = presetData.get('saturation', 100)
					# Convert from 0-100 range to 0-255 range.
					saturation = int(round(saturation / 100.0 * 255.0))
					
					# Make the light change.
					self.doHSB(device, hue, saturation, brightness, rampRate)
					
				elif colorMode == "xy":
					# Get the x and y values (using 0.35 as default for both).
					colorX = presetData.get('colorX', 0.35)
					colorY = presetData.get('colorY', 0.35)
					
					# Make the light change.
					self.doXYY(device, colorX, colorY, brightness, rampRate)
					
			else:
				# This device supports color, but not color temperature.
				#   Now determine which mode was saved in the preset and use
				#   use it with the target device (use "hs" as the default).
				colorMode = presetData.get('colorMode', "hs")
				
				if colorMode == "ct":
					# The target device doesn't suppor color temperature.
					#   Use an alternate color rendering method such as HSB.
					colorMode = "xy"
					
				if colorMode == "hs":
					# Get the hue (use 0 as the default).
					hue = presetData.get('hue', 0)
					# Conver the hue from 0-360 range to 0-65535 range.
					hue = int(round(hue * 182.0))
					# Get the saturation (use 100 as the default).
					saturation = presetData.get('saturation', 100)
					# Convert from 0-100 range to 0-255 range.
					saturation = int(round(saturation / 100.0 * 255.0))
					
					# Make the light change.
					self.doHSB(device, hue, saturation, brightness, rampRate)
					
				elif colorMode == "xy":
					# Get the x and y values (using 0.35 as default for both).
					colorX = presetData.get('colorX', 0.35)
					colorY = presetData.get('colorY', 0.35)
					
					# Make the light change.
					self.doXYY(device, colorX, colorY, brightness, rampRate)
					
		else:
			# This device doesn't support color.  Just set the brightness.
			self.doBrightness(device, brightness, rampRate)
			
		# Log the action.
		if rampRate == -1:
			indigo.server.log(u"\"" + device.name + u"\" states set to Preset " + str(presetId + 1) + u" (" + presetName + u")")
		else:
			indigo.server.log(u"\"" + device.name + u"\" states set to Preset " + str(presetId + 1) + u" (" + presetName + u") at ramp rate " + str(rampRate) + u" sec.")

		# Return a tuple if this is a menu item action.
		if actionType == "menu":
			return (True, action)

	# Display Preset Menu Action
	########################################
	def displayPreset(self, valuesDict, typeId):
		self.debugLog(u"displayPreset called. action values:\n" + str(valuesDict) + u"\nType ID:\n" + str(typeId) + "\n")
		errorsDict = indigo.Dict()
		errorsDict['showAlertText'] = u""
		
		# Get the presetId.
		presetId = valuesDict.get('presetId', False)
			
		if not presetId:
			errorsDict['presetId'] = u"No Preset is selected."
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
		except Exception, e:
			# Key probably doesn't exist. Proceed as if no rate was saved.
			presetRate = -1
			pass
		
		# Return an error if the Preset is empty (since there's nothing to display).
		if len(presetData) < 1:
			errorsDict['presetId'] = u"This Preset is empty. Please select a Preset that contains data (the number will have an asterisk (*) next to it)."
			errorsDict['showAlertText'] += errorsDict['presetId']
			return (False, valuesDict, errorsDict)
		
		# Display the Preset data in the Indigo log.
		logRampRate = str(presetRate) + u" sec."
		if presetRate == -1:
			logRampRate = u"(none specified)"
		indigo.server.log(u"Displaying Preset " + str(presetId + 1) + u" (" + presetName + u") stored data:\nRamp Rate: " + logRampRate + u"\n" + str(presetData))

		# Return a tuple to dismiss the menu item dialog.
		return (True, valuesDict)

