#! /usr/bin/env python
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
#	Version 1.8.1
#
#	See the "VERSION_HISTORY.txt" file in the same location as this plugin.py
#	file for a complete version change history.
#
################################################################################

import os
import sys
import logging
import requests
import socket
from colormath.color_objects import RGBColor, xyYColor, HSVColor
from math import ceil, floor, pow
import simplejson as json
import indigoPluginUpdateChecker
from supportedDevices import *

# Default timeout.
kTimeout = 4		# seconds
# Default connection retries.
requests.defaults.defaults['max_retries'] = 3
# Turn off the HTTP connection "keep alive" feature.
requests.defaults.defaults['keep_alive'] = False
# Set the Python logging level to "WARNING" to override the Requests library
#   default of "INFO", which causes a log entry in Indigo 6.1.8+ for every
#   HTTP connection made to the Hue bridge.
logging.getLogger("requests").setLevel(logging.WARNING)


################################################################################
class Plugin(indigo.PluginBase):
    ########################################
    # Loading and Starting Methods
    ########################################

    # Load Plugin
    ########################################
    def __init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs):
        super(Plugin, self).__init__(pluginId, pluginDisplayName, pluginVersion, pluginPrefs)
        self.debug = pluginPrefs.get('showDebugInfo', False)
        if self.debug:
            self.plugin_file_handler.setLevel(logging.DEBUG) # This controls what level of logging shows up in the plugin's log file
            self.debugLog(u"Debug logging started at plugin initialization.")
        else:
            self.plugin_file_handler.setLevel(logging.INFO)
        self.debugLog(u"Starting plugin initialization.")
        self.hostId = pluginPrefs.get('hostId', "")	# Username/key used to access Hue bridge Old
        self.hostIds = json.loads(pluginPrefs.get('hostIds', '{"0":""}'))	# Username/key used to access Hue bridge for multiple bridge
        self.threadsList = []		    # list of threads used for various processes outside runConcurrentThread.
        ### one list for all devices on all bridges related to indigo devices 
        self.deviceList = []		    # list of device IDs to monitor (one list for all devices on all bridges)
        self.controlDeviceList = []	    # list of virtual dimmer device IDs that control bulb devices
        self.brighteningList = []	    # list of device IDs being brightened
        self.dimmingList = []		    # list of device IDs being dimmed
        ### one for each bridge read from bridge
        self.paired = {"0":False}		# if paired with Hue bridge or not
        self.hueConfigDict = {"0":{}}   # Entire Hue bridge configuration dictionary.
        self.lightsDict = {"0":{}}	    # Hue devices dict.
        self.groupsDict = {"0":{}}	    # Hue groups dict.
        self.resourcesDict = {"0":{}}   # Hue resource links dict.
        self.sensorsDict = {"0":{}}	    # Hue sensors dict.
        self.usersDict = {"0":{}}		# Hue users dict.
        self.scenesDict = {"0":{}}	    # Hue scenes dict.
        self.rulesDict = {"0":{}}		# Hue trigger rules dict.
        self.schedulesDict = {"0":{}}	# Hue schedules dict.
        self.ipAddresses = {"0":{}}	    # Hue bridge IP addresses 

        self.hubNumberSelected = "0"    # default hub number 
        self.lastErrorMessage = u""	    # last error message displayed in log
        self.unsupportedDeviceWarned = False	# Boolean. Was user warned this device isn't supported?
        self.usersListSelection = ""	# String. The Hue whilelist user ID selected in action UIs.
        self.sceneListSelection = ""	# String. The Hue scene ID selected in action UIs.
        self.groupListSelection = ""	# String. The Hue group ID selected in action UIs.
        self.maxPresetCount = int(pluginPrefs.get('maxPresetCount', "30"))	# Integer. The maximum number of Presets to use and store.
        # Load the update checker module.
        self.updater = indigoPluginUpdateChecker.updateChecker(self, 'http://www.nathansheldon.com/files/PluginVersions/Hue-Lights.html')
        self.hubNumberSelected = ""
    # Unload Plugin
    ########################################
    def __del__(self):
        indigo.PluginBase.__del__(self)

    # Startup
    ########################################
    def startup(self):
        self.debugLog(u"Startup called.")
        # Perform an initial version check.
        self.debugLog(u"Running plugin version check (if enabled).")
        self.updater.checkVersionPoll()

        # Prior to version 1.2.0, the "presets" property did not exist in the plugin preferences.
        #   If that property does not exist, add it.
        # As of version 1.2.6, there were 30 presets instead of 10.
        # As of 1.6.11, the maximum number of presets is now a global variable that can be changed later.
        if not self.pluginPrefs.get('presets', False):
            self.debugLog(u"pluginPrefs lacks presets.  Adding.")
            # Add the empty presets list to the prefs.
            self.pluginPrefs['presets'] = list()
            # Start a new list of empty presets.
            presets = list()
            for aNumber in range(1,self.maxPresetCount + 1):
                # Create a blank sub-list for storing preset name and preset states.
                preset = list()
                # Add the preset name.
                preset.append(u"Preset {}".format(aNumber))
                # Add the empty preset states Indigo dictionary
                preset.append(indigo.Dict())
                # Add the sub-list to the empty presets list.
                presets.append(preset)
            # Add the new list of empty presets to the prefs.
            self.pluginPrefs['presets'] = presets
            self.debugLog(u"pluginPrefs now contains {} Presets.".format(self.maxPresetCount) )
        # If presets exist, make sure there are the correct number of them.
        else:
            presets = self.pluginPrefs.get('presets', "")
            presetCount = len(presets)
            self.debugLog(u"pluginPrefs contains {} presets.".format(presetCount))
            # If there are fewer Presets in the prefs than the maxPresetCount, add the reset.
            if presetCount < self.maxPresetCount:
                indigo.server.log(u"Preset Memories number increased to .".format(self.maxPresetCount))
                self.debugLog(u"... Adding {} presets to bring total to {}.".format(self.maxPresetCount - presetCount, self.maxPresetCount) )
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
                indigo.server.log(u"... {} Presets added.  There are now {} Presets.".format(self.maxPresetCount - presetCount, self.maxPresetCount) )
            # If there are more presets than are allowed by maxPresetCount, remove the extra Presets.
            elif presetCount > self.maxPresetCount:
                self.debugLog(u"... Deleting the last {} Presets to bring the total to {}.".format(presetCount - self.maxPresetCount, self.maxPresetCount))
                indigo.server.log(u"WARNING:  You've decreased the number of Preset Memories, so we're deleting the last {} Presets to bring the total to {}.  This cannot be undone.".format(presetCount - self.maxPresetCount, self.maxPresetCount) )
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
                            presetRate = self.pluginPrefs['presets'][presetId][2]
                            # Round the saved preset ramp rate to the nearest 10th.
                            presetRate = round(presetRate, 1)
                        except Exception, e:
                            # Key probably doesn't exist. Proceed as if no rate was saved.
                            presetRate = -1
                            pass

                        # Display the Preset data in the Indigo log.
                        logRampRate = u"{} sec.".format(presetRate)
                        if presetRate == -1:
                            logRampRate = u"(none specified)"
                        indigo.server.log(u"... Preset {} ({}) has data. The following data will be deleted:\nRamp Rate: {}\n{}".format(aNumber + 1, presetName, logRampRate, presetData))
                    # Now delete the Preset.
                    del presets[aNumber]
                    indigo.server.log(u"... Preset {} deleted.".format(aNumber + 1))

        self.debugLog(u"pluginPrefs are:\n{}".format(self.pluginPrefs))

        self.updateAllHueLists()
        return 

    # Start Devices
    ########################################
    def deviceStartComm(self, device):
        self.debugLog(u"Starting device: {}".format(device.name))
        try:
            # Clear any device error states first.
            device.setErrorStateOnServer("")

            # Rebuild the device if needed (fixes missing states and properties).
            self.rebuildDevice(device)

            # Update the device lists and the device states and props.

            # Hue Device Attribute Controller
            if device.id not in self.controlDeviceList:
                try:
                    self.debugLog(u"Attribute Control device definition:\n{}".format(device))
                except Exception, e:
                    self.debugLog(u"Attribute Control device definition cannot be displayed because: {}".format(e))
                self.controlDeviceList.append(device.id)


            if device.deviceTypeId == "hueAttributeController":
                if device.id not in self.controlDeviceList:
                    try:
                        self.debugLog(u"Attribute Control device definition:\n{}".format(device))
                    except Exception, e:
                        self.debugLog(u"Attribute Control device definition cannot be displayed because: {}".format(e))
                    self.controlDeviceList.append(device.id)
            # Hue Groups
            elif device.deviceTypeId in kGroupDeviceTypeIDs:
                if device.id not in self.deviceList:
                    try:
                        self.debugLog(u"Hue Group device definition:\n{}".format(device))
                    except Exception, e:
                        self.debugLog(u"Hue Group device definition cannot be displayed because: {}".format(e))
                    self.deviceList.append(device.id)
            # Other Hue Devices
            else:
                if device.id not in self.deviceList:
                    try:
                        self.debugLog(u"Hue device definition:\n{}".format(device))
                    except Exception, e:
                        # With versions of Indigo sometime prior to 6.0, if any device name had
                        #   non-ASCII characters, the above "try" will fail, so we have to show
                        #   this error instead of the actual bulb definition.
                        self.debugLog(u"Hue device definition cannot be displayed because: {}".format(e))
                    self.deviceList.append(device.id)
        except Exception, e:
            indigo.server.log(u"Line {} has error={}".format(sys.exc_traceback.tb_lineno, e))
        return 


    # Stop Devices
    ########################################
    def deviceStopComm(self, device):
        self.debugLog(u"Stopping device: {}".format(device.name) )
        if device.deviceTypeId == "hueAttributeController":
            if device.id in self.controlDeviceList:
                self.controlDeviceList.remove(device.id)
        else:
            if device.id in self.deviceList:
                self.deviceList.remove(device.id)
            ## must also be removed from control dev list KW
            if device.id in self.controlDeviceList:
                self.controlDeviceList.remove(device.id)

    # Shutdown
    ########################################
    def shutdown(self):
        self.debugLog(u"Plugin shutdown called.")


    ########################################
    # Standard Plugin Methods
    ########################################

    # Run a Concurrent Thread for Status Updates
    ########################################
    def runConcurrentThread(self):
        self.debugLog(u"Starting runConcurrentThread.")

        # Set initial values for activity flags
        goBrightenDim			= True
        loopsForBrightenDim		= 4		# At least 0.4 sec delay
        goSensorRefresh			= True
        loopsForSensorRefresh	= 10	# At least 1 sec delay
        goLightsRefresh			= True
        loopsForLightsRefresh	= 50    # At least 5 sec delay
        goGroupsRefresh			= True
        loopsForGroupsRefresh	= 50    # At least 5 sec delay
        goSensorDataDump		= True
        loopsForSensorDataDump	= 100	# At least 10 sec delay
        goUpdateCheck         	= True
        loopsForUpdateCheck   	= 600   # At least 60 sec delay
        goErrorReset          	= True
        loopsForErrorReset    	= 1200  # At least 120 sec delay
        loopCount             	= 0     # Loop counter
        # Set the maximum loop counter value based on the highest of the above activity threshold variables.
        loopCountMax = max([loopsForBrightenDim, loopsForSensorRefresh, loopsForSensorDataDump, loopsForLightsRefresh, loopsForGroupsRefresh, loopsForUpdateCheck, loopsForErrorReset])

        try:
            while True:
                # We're using some primitive time sharing techniques here based on
                # the number of loops (assuming a 0.1 second delay between loops).
                # Each activity is activated after a specific number of loops.

                ## Give Indigo Some Time ##
                self.sleep(0.1)

                ## Brightening and Dimming Devices ##
                # Go through the devices waiting to be brightened
                if goBrightenDim:
                    for brightenDeviceId in self.brighteningList:
                        # Make sure the device is in the deviceList.
                        if brightenDeviceId in self.deviceList:
                            # Increase the brightness level by 10 percent.
                            brightenDevice = indigo.devices[brightenDeviceId]
                            hubNumber = brightenDevice.pluginpros['hubNumber']
                            brightness = brightenDevice.states['brightnessLevel']
                            self.debugLog(u"Brightness: {}".format(brightness))
                            brightness += 12
                            self.debugLog(u"Updated to: {}".format(brightness))
                            if brightness >= 100:
                                brightness = 100
                                # Log the event to Indigo log.
                                indigo.server.log(u"\"{}\" stop brightening", 'Sent Hue Lights'.format(brightenDevice.name))
                                self.brighteningList.remove(brightenDeviceId)
                                # Get the bulb status (but only if paired with the bridge).
                                if self.paired[hubNumber]:
                                    self.getBulbStatus(brightenDeviceId)
                                    # Log the new brightnss.
                                    indigo.server.log(u"\"{}\" status request (received: 100)", 'Sent Hue Lights'.format(brightenDevice.name))
                                else:
                                    self.debugLog(u"Not currently paired with Hue bridge. Status update skipped.")
                            # Convert percent-based brightness to 255-based brightness.
                            brightness = int(round(brightness / 100.0 * 255.0))
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
                            hubNumber = dimDevice.pluginpros['hubNumber']
                            brightness = dimDevice.states['brightnessLevel']
                            brightness -= 12
                            if brightness <= 0:
                                brightness = 0
                                # Log the event to Indigo log.
                                indigo.server.log(u"\"{}\" stop dimming", 'Sent Hue Lights'.format(dimDevice.name ))
                                self.dimmingList.remove(dimDeviceId)
                                # Get the bulb status (but only if we're paired with the bridge).
                                if self.paired[hubNumber]:
                                    self.getBulbStatus(dimDeviceId)
                                    # Log the new brightnss.
                                    indigo.server.log(u"\"{}\" status request (received: 0)".format(dimDevice.name ), 'Sent Hue Lights')
                                else:
                                    self.debugLog(u"Not currently paired with Hue bridge. Status update skipped.")
                            # Convert percent-based brightness to 255-based brightness.
                            brightness = int(round(brightness / 100.0 * 255.0))
                            # Set brightness to new value, with 0.5 sec ramp rate and no logging.
                            self.doBrightness(dimDevice, brightness, 0.5, False)
                        # End if dimDeviceId is in self.deviceList.
                    # End loop through self.dimmingList.
                    # Reset the action flag.
                    goBrightenDim = False
                # End it's time to go through brightening and dimming loops.

                ## Update Sensors List ##
                if goSensorRefresh:
                    if goSensorDataDump:
                        self.updateSensorsList(goSensorDataDump)
                        goSensorDataDump = False
                    else:
                        self.updateSensorsList()
                    self.parseAllHueSensorsData()
                    # Reset the action flag.
                    goSensorRefresh = False

                ## Update Lights List ##
                if goLightsRefresh:
                    self.updateLightsList()
                    self.parseAllHueLightsData()
                    # Reset the action flag.
                    goLightsRefresh = False

                ## Update Groups List ##
                if goGroupsRefresh:
                    self.updateGroupsList()
                    self.parseAllHueGroupsData()
                    # Reset the action flag.
                    goGroupsRefresh = False

                ## Check for Newer Plugin Versions ##
                if goUpdateCheck:
                    self.updater.checkVersionPoll()
                    # Reset the action flag.
                    goUpdateCheck = False

                ## Reset lastErrorMessage ##
                if goErrorReset:
                    self.lastErrorMessage = u""
                    # Reset the action flag.
                    goErrorReset = False

                # Increment the loop counter.
                loopCount += 1

                # Set action flags based on loop counter.
                if loopCount % loopsForBrightenDim == 0:
                    goBrightenDim = True
                if loopCount % loopsForSensorRefresh == 0:
                    goSensorRefresh = True
                if loopCount % loopsForLightsRefresh == 0:
                    goLightsRefresh = True
                if loopCount % loopsForGroupsRefresh == 0:
                    goGroupsRefresh = True
                if loopCount % loopsForSensorDataDump == 0:
                    goSensorDataDump = True
                if loopCount % loopsForUpdateCheck == 0:
                    goUpdateCheck = True
                if loopCount % loopsForErrorReset == 0:
                    goErrorReset = True

                # Reset the loop counter if it's reached its maximum.
                if loopCount == loopCountMax:
                    loopCount = 0

            # End While True loop.

        except self.StopThread:
            self.debugLog(u"runConcurrentThread stopped.")
            pass

        self.debugLog(u"runConcurrentThread exiting.")

    # Validate Device Configuration
    ########################################
    def validateDeviceConfigUi(self, valuesDict, typeId, deviceId):
        self.debugLog(u"Starting validateDeviceConfigUi.\n  valuesDict: {}\n  typeId: {}\n  deviceId: {}".format(valuesDict, typeId, deviceId))
        errorsDict = indigo.Dict()
        errorsDict['showAlertText'] = ""
        isError = False

        hubNumber = valuesDict['hubNumber']
        ipAddress = self.ipAddresses[hubNumber]
        hostId = self.hostIds[hubNumber]

        # Make sure we're still paired with the Hue bridge.
        if not self.paired[hubNumber]:
            isError = True
            errorsDict['bulbId'] = u"Not currently paired with the Hue bridge. Close this window and use the Configure... option in the Plugins -> Hue Lights menu to pair Hue Lights with the Hue bridge first."
            errorsDict['showAlertText'] += errorsDict['bulbId']
            return (False, valuesDict, errorsDict)

        # Check data based on which device config UI was returned.
        #  -- Lights and On/Off Devices --
        if typeId in kLightDeviceTypeIDs:
            # Make sure a bulb was selected.
            if valuesDict.get('bulbId', "") == "":
                errorsDict['bulbId'] = u"Please select a Hue device to control."
                errorsDict['showAlertText'] += errorsDict['bulbId']
                return (False, valuesDict, errorsDict)

            bulbId = valuesDict['bulbId']

            # Make sure the device selected is a Hue device.
            #   Get the device info directly from the bridge.
            command = "http://{}/api/{}/lights/{}" .format(ipAddress, self.hostIds[hubNumber], bulbId)
            self.debugLog(u"Sending URL request: {}".format(command) )
            try:
                r = requests.get(command, timeout=kTimeout)
            except requests.exceptions.Timeout:
                errorText = u"Failed to connect to the Hue bridge at {} after {} seconds. - Check that the bridge is connected and turned on.".format(ipAddress, kTimeout)
                # Don't display the error if it's been displayed already.
                if errorText != self.lastErrorMessage:
                    self.errorLog(errorText)
                    # Remember the error.
                    self.lastErrorMessage = errorText
                errorsDict['bulbId'] = errorText
                errorsDict['showAlertText'] += errorsDict['bulbId']
                return (False, valuesDict, errorsDict)
            except requests.exceptions.ConnectionError:
                errorText = u"Failed to connect to the Hue bridge at {}. - Check that the bridge is connected and turned on.".format(ipAddress)
                # Don't display the error if it's been displayed already.
                if errorText != self.lastErrorMessage:
                    self.errorLog(errorText)
                    # Remember the error.
                    self.lastErrorMessage = errorText
                errorsDict['bulbId'] = errorText
                errorsDict['showAlertText'] += errorsDict['bulbId']
                return (False, valuesDict, errorsDict)

            self.debugLog(u"Data from bridge: {}".format(r.content.decode("utf-8")) )
            # Convert the response to a Python object.
            try:
                bulb = json.loads(r.content)
            except Exception, e:
                # There was an error in the returned data.
                indigo.server.log(u"Error retrieving Hue device data from bridge.  Error reported: {}".format(e))
                errorsDict['bulbId'] = u"Error retrieving Hue device data from bridge. See Indigo log."
                errorsDict['showAlertText'] += errorsDict['bulbId']
                return (False, valuesDict, errorsDict)

            # Populate the appropriate values in the valuesDict.
            valuesDict['manufacturerName'] = bulb.get('manufacturername', "")
            valuesDict['modelId'] = bulb.get('modelid', "")
            valuesDict['nameOnHub'] = bulb.get('name', "")
            valuesDict['swVersion'] = bulb.get('swversion', "")
            valuesDict['type'] = bulb.get('type', "")
            valuesDict['uniqueId'] = bulb.get('uniqueid', "")

            # Make sure the bulb ID isn't used by another device.
            for otherDeviceId in self.deviceList:
                if otherDeviceId != deviceId:
                    otherDevice = indigo.devices[otherDeviceId]
                    if valuesDict['bulbId'] == otherDevice.pluginProps.get('bulbId', 0):
                        otherDevice = indigo.devices[otherDeviceId]
                        errorsDict['bulbId'] = u"This Hue device is already being controlled by the \"{}\" Indigo device. Choose a different Hue bulb to control.".format(otherDevice.name)
                        errorsDict['showAlertText'] += errorsDict['bulbId'] + "\n\n"
                        return (False, valuesDict, errorsDict)

        #  -- Hue Bulb --
        if typeId == "hueBulb":
            # Make sure this is a Hue color/ambiance light.
            if bulb.get('type', "") != kHueBulbDeviceIDType:
            #if bulb.get('modelid', "") not in kHueBulbDeviceIDs:
                errorsDict['bulbId'] = u"The selected device is not a Hue Color/Ambiance light. Please select a Hue Color/Ambiance light to control."
                errorsDict['showAlertText'] += errorsDict['bulbId']
                return (False, valuesDict, errorsDict)

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
                    errorsDict['defaultBrightness'] = u"The Default Brightness must be a number between 1 and 100. Error: {}".format(e)
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
                    errorsDict['rate'] = u"The Ramp Rate must be a number between 0 and 540 in increments of 0.1 seconds. Error: {}".format(e)
                    errorsDict['showAlertText'] += errorsDict['rate'] + "\n\n"

            # Show errors if there are any.
            if isError:
                errorsDict['showAlertText'] = errorsDict['showAlertText'].strip()
                return (False, valuesDict, errorsDict)

            else:
                # Define the device's address to appear in Indigo.
                valuesDict['address'] =  u"{} (ID:{}-{})".format(ipAddress, hubNumber, valuesDict['bulbId'])
                return (True, valuesDict)

        #  -- Ambiance Lights --
        if typeId == "hueAmbiance":
            # Make sure an ambiance light was selected.
            if bulb.get('type', "") != kAmbianceDeviceIDType:
            #if bulb.get('modelid', "") not in kAmbianceDeviceIDs:
                errorsDict['bulbId'] = u"The selected device is not an Ambiance light. Please select an Ambiance light to control."
                errorsDict['showAlertText'] += errorsDict['bulbId']
                return (False, valuesDict, errorsDict)

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
                    errorsDict['defaultBrightness'] = u"The Default Brightness must be a number between 1 and 100. Error: {}".format(e)
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
                    errorsDict['rate'] = u"The Ramp Rate must be a number between 0 and 540 in increments of 0.1 seconds. Error: {}".format(e)
                    errorsDict['showAlertText'] += errorsDict['rate'] + "\n\n"

            # Show errors if there are any.
            if isError:
                errorsDict['showAlertText'] = errorsDict['showAlertText'].strip()
                return (False, valuesDict, errorsDict)

            else:
                # Define the device's address to appear in Indigo.
                valuesDict['address'] =  u"{} (Lid:{}-{})".format(ipAddress, hubNumber, valuesDict['bulbId'])
                return (True, valuesDict)

        #  -- LightStrips Device --
        elif typeId == "hueLightStrips":
            # Make sure it's a Light Strip device.
            if bulb.get('type', "") != kLightStripsDeviceIDType:
                errorsDict['bulbId'] = u"The selected device is not a Light Strip device. Please select a Light Strip device to control."
                errorsDict['showAlertText'] += errorsDict['bulbId']
                return (False, valuesDict, errorsDict)

            # Assign Indigo color support properties based on Hue lighting device type.
            if bulb.get('type', "") in [u'Extended color light', u'Color light', u'Color temperature light']:
                valuesDict['SupportsColor'] = True
                if bulb.get('type', "") in [u'Extended color light', u'Color light']:
                    valuesDict['SupportsRGB'] = True
                else:
                    valuesDict['SupportsRGB'] = False
                if bulb.get('type', "") in [u'Extended color light', u'Color temperature light']:
                    valuesDict['SupportsWhite'] = True
                    valuesDict['SupportsWhiteTemperature'] = True
                    valuesDict['WhiteTemperatureMin'] = "2000"
                    valuesDict['WhiteTemperatureMax'] = "6500"
                else:
                    valuesDict['SupportsWhite'] = False
                    valuesDict['SupportsWhiteTemperature'] = False
                    if valuesDict.get('WhiteTemperatureMin', False):
                        del valuesDict['WhiteTemperatureMin']
                    if valuesDict.get('WhiteTemperatureMax', False):
                        del valuesDict['WhiteTemperatureMax']
                # No Hue bridge controlled device supports both RGB and white balance control simultaniously.
                if bulb.get('type', "") == u"Extended color light":
                    valuesDict['SupportsRGBandWhiteSimultaneously'] = False
            else:
                valuesDict['SupportsColor'] = False

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
                    errorsDict['defaultBrightness'] = u"The Default Brightness must be a number between 1 and 100. Error: {}".format(e)
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
                    errorsDict['rate'] = u"The Ramp Rate must be a number between 0 and 540 in increments of 0.1 seconds. Error: {}".format(e)
                    errorsDict['showAlertText'] += errorsDict['rate'] + "\n\n"

            # Show errors if there are any.
            if isError:
                errorsDict['showAlertText'] = errorsDict['showAlertText'].strip()
                return (False, valuesDict, errorsDict)

            else:
                # Define the device's address to appear in Indigo.
                valuesDict['address'] =  u"{} (Lid:{}-{})".format(ipAddress, hubNumber, valuesDict['bulbId'])
                return (True, valuesDict)

        #  -- LivingColors Bloom Device --
        elif typeId == "hueLivingColorsBloom":
            # Make sure a Living Colors device was selected.

            if bulb.get('type', "")  != kLivingColorsDeviceIDType:
            #if bulb.get('modelid', "") not in kLivingColorsDeviceIDs:
                isError = True
                errorsDict['bulbId'] = u"The selected device is not a LivingColors type device. Please select a LivingColors type device to control."
                errorsDict['showAlertText'] += errorsDict['bulbId']
                return (False, valuesDict, errorsDict)

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
                    errorsDict['defaultBrightness'] = u"The Default Brightness must be a number between 1 and 100. Error: {}".format(e)
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
                    errorsDict['rate'] = u"The Ramp Rate must be a number between 0 and 540 in increments of 0.1 seconds. Error: {}".format(e)
                    errorsDict['showAlertText'] += errorsDict['rate'] + "\n\n"

            # Show errors if there are any.
            if isError:
                errorsDict['showAlertText'] = errorsDict['showAlertText'].strip()
                return (False, valuesDict, errorsDict)

            else:
                # Define the device's address to appear in Indigo.
                valuesDict['address'] = u"{} (Lid:{}-{})".format(ipAddress, hubNumber, valuesDict['bulbId'])
                return (True, valuesDict)

        #  -- LivingWhites Device --
        elif typeId == "hueLivingWhites":
            # Make sure a Living Whites device was selected.
            if bulb.get('type', "") != kLivingWhitesDeviceIDType:
                isError = True
                errorsDict['bulbId'] = u"The selected device is not a LivingWhites device. Please select a LivingWhites device to control."
                errorsDict['showAlertText'] += errorsDict['bulbId']
                return (False, valuesDict, errorsDict)

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
                    errorsDict['defaultBrightness'] = u"The Default Brightness must be a number between 1 and 100. Error: {}".format(e)
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
                    errorsDict['rate'] = u"The Ramp Rate must be a number between 0 and 540 in increments of 0.1 seconds. Error: {}".format(e)
                    errorsDict['showAlertText'] += errorsDict['rate'] + "\n\n"

            # Show errors if there are any.
            if isError:
                errorsDict['showAlertText'] = errorsDict['showAlertText'].strip()
                return (False, valuesDict, errorsDict)

            else:
                # Define the device's address to appear in Indigo.
                valuesDict['address'] = u"{} (Lid:{}-{})".format(ipAddress, hubNumber, valuesDict['bulbId'])
                return (True, valuesDict)

        #  -- On/Off Device --
        elif typeId == "hueOnOffDevice":
            # Make sure an on/off device was selected.
            if bulb.get('type', "")[0:len(kOnOffOnlyDeviceIDType)] != kOnOffOnlyDeviceIDType:
            #if bulb.get('modelid', "") not in kOnOffOnlyDeviceIDs:
                isError = True
                errorsDict['bulbId'] = u"The selected device is not an On/Off device. Please select an On/Off device to control."
                errorsDict['showAlertText'] += errorsDict['bulbId']
                return (False, valuesDict, errorsDict)

            # Define the device's address to appear in Indigo.
            valuesDict['address'] = u"{} (Lid:{}-{})".format(ipAddress, hubNumber, valuesDict['bulbId'])
            return (True, valuesDict)

        #  -- Hue Group --
        elif typeId == "hueGroup":
            # Make sure a group was selected.
            if valuesDict.get('groupId', "") == "":
                isError = True
                errorsDict['groupId'] = u"Please select a Hue Group to control."
                errorsDict['showAlertText'] += errorsDict['groupId']
                return (False, valuesDict, errorsDict)

            groupId = valuesDict['groupId']

            # Make sure the device selected is a Hue group.
            #   Get the group info directly from the bridge.
            command = "http://{}/api/{}/groups/{}".format(ipAddress, self.hostIds[hubNumber], groupId)
            self.debugLog(u"Sending URL request: {}".format(command) )
            try:
                r = requests.get(command, timeout=kTimeout)
            except requests.exceptions.Timeout:
                errorText = u"Failed to connect to the Hue bridge at {} after {} seconds. - Check that the bridge is connected and turned on.".format(ipAddress, kTimeout)
                # Don't display the error if it's been displayed already.
                if errorText != self.lastErrorMessage:
                    self.errorLog(errorText)
                    # Remember the error.
                    self.lastErrorMessage = errorText
                return
            except requests.exceptions.ConnectionError:
                errorText = u"Failed to connect to the Hue bridge at {}. - Check that the bridge is connected and turned on.".format(ipAddress)
                # Don't display the error if it's been displayed already.
                if errorText != self.lastErrorMessage:
                    self.errorLog(errorText)
                    # Remember the error.
                    self.lastErrorMessage = errorText
                return
            self.debugLog(u"Data from bridge: {}".format(r.content.decode("utf-8")) )
            # Convert the response to a Python object.
            try:
                group = json.loads(r.content)
            except Exception, e:
                # There was an error in the returned data.
                indigo.server.log(u"Error retrieving Hue group data from bridge.  Error reported: {}".format(e))
                isError = True
                errorsDict['groupId'] = u"Error retrieving Hue group data from bridge. See Indigo log."
                errorsDict['showAlertText'] += errorsDict['groupId']
                return (False, valuesDict, errorsDict)
            if group.get('lights', "") == "":
                isError = True
                errorsDict['groupId'] = u"The selected item is not a Hue Group. Please select a Hue Group to control."
                errorsDict['showAlertText'] += errorsDict['groupId']
                return (False, valuesDict, errorsDict)

            # Populate the appropriate values in the valuesDict.
            valuesDict['groupClass'] = group.get('class', "")
            valuesDict['nameOnHub'] = group.get('name', "")
            valuesDict['type'] = group.get('type', "")

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
                    errorsDict['defaultBrightness'] = u"The Default Brightness must be a number between 1 and 100. Error: {}".format(e)
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
                    errorsDict['rate'] = u"The Ramp Rate must be a number between 0 and 540 in increments of 0.1 seconds. Error: {}".format(e)
                    errorsDict['showAlertText'] += errorsDict['rate'] + "\n\n"

            # Show errors if there are any.
            if isError:
                errorsDict['showAlertText'] = errorsDict['showAlertText'].strip()
                return (False, valuesDict, errorsDict)

            else:
                # Define the device's address to appear in Indigo.
                valuesDict['address'] = u"{} (Gid:{}-{})".format(ipAddress, hubNumber, valuesDict['groupId'])
                return (True, valuesDict)

        # -- Hue Device Attribute Controller (Virtual Dimmer Device) --
        elif typeId == "hueAttributeController":
            # Make sure a Hue device was selected.
            if valuesDict.get('bulbDeviceId', "") == "":
                isError = True
                errorsDict['bulbDeviceId'] = u"Please select a Hue device whose attribute will be controlled."
                errorsDict['showAlertText'] += errorsDict['bulbDeviceId']
            elif valuesDict.get('type', "") == kLivingWhitesDeviceIDType:
                isError = True
                errorsDict['blubDeviceId'] = u"LivingWhites type devices have no attributes that can be controlled. Please select a Hue device that supports color or color temperature."
                errorsDict['showAlertText'] += errorsDict['bulbDeviceId']
            elif valuesDict.get('type', "")[0:len(kOnOffOnlyDeviceIDType)] == kOnOffOnlyDeviceIDType:
                isError = True
                errorsDict['blubDeviceId'] = u"On/Off Only type devices have no attributes that can be controlled. Please select a Hue device that supports color or color temperature."
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
                    errorsDict['rate'] = u"The Ramp Rate must be a number between 0 and 540 in increments of 0.1 seconds. Error: {}".format(e)
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
                    errorsDict['defaultOnLevel'] = u"The Default On Level must be a whole number between 1 and 100. Error: {}".format(e)
                    errorsDict['showAlertText'] += errorsDict['defaultOnLevel'] + "\n\n"

            # Show errors if there are any.
            if isError:
                errorsDict['showAlertText'] = errorsDict['showAlertText'].strip()
                return (False, valuesDict, errorsDict)

            else:
                # Define the device's address to appear in Indigo.
                # The address is the destination Hue device's device ID plus the attribute to control.
                device = indigo.devices[int(valuesDict.get('bulbDeviceId', 0))]
                valuesDict['address'] = u"{}. (Aid:{}-{})".format(device.id, hubNumber, valuesDict['attributeToControl'])
                return (True, valuesDict)

        #  -- Hue Motion Sensor (Motion) --
        elif typeId == "hueMotionSensor":
            # Make sure a motion sensor was selected.
            if valuesDict.get('sensorId', "") == "":
                isError = True
                errorsDict['sensorId'] = u"Please select a Hue Motion Sensor."
                errorsDict['showAlertText'] += errorsDict['sensorId']
                return (False, valuesDict, errorsDict)

            sensorId = valuesDict['sensorId']

            # Make sure the device selected is a Hue sensor device.
            #   Get the device info directly from the bridge.
            command = "http://{}/api/{}/sensors/{}".format(ipAddress, self.hostIds[hubNumber], sensorId)
            self.debugLog(u"Sending URL request: {}".format(command) )
            try:
                r = requests.get(command, timeout=kTimeout)
            except requests.exceptions.Timeout:
                errorText = u"Failed to connect to the Hue bridge at {} after {} seconds. - Check that the bridge is connected and turned on." .format(ipAddress, kTimeout)
                # Don't display the error if it's been displayed already.
                if errorText != self.lastErrorMessage:
                    self.errorLog(errorText)
                    # Remember the error.
                    self.lastErrorMessage = errorText
                return
            except requests.exceptions.ConnectionError:
                errorText = u"Failed to connect to the Hue bridge at {}. - Check that the bridge is connected and turned on.".format(ipAddress)
                # Don't display the error if it's been displayed already.
                if errorText != self.lastErrorMessage:
                    self.errorLog(errorText)
                    # Remember the error.
                    self.lastErrorMessage = errorText
                return
            self.debugLog(u"Data from bridge: {}".format(r.content.decode("utf-8")) )
            # Convert the response to a Python object.
            try:
                sensor = json.loads(r.content)
            except Exception, e:
                # There was an error in the returned data.
                indigo.server.log(u"Error retrieving Hue device data from bridge.  Error reported: {}".format(e))
                isError = True
                errorsDict['sensorId'] = u"Error retrieving Hue device data from bridge. See Indigo log."
                errorsDict['showAlertText'] += errorsDict['sensorId']
                return (False, valuesDict, errorsDict)

            if sensor.get('modelid', "")[0:len(kMotionSensorDeviceIDs)] != kMotionSensorDeviceIDs:
                isError = True
                errorsDict['sensorId'] = u"The selected device is not a Hue Motion Sensor. Please select a Hue Motion Sensor device."
                errorsDict['showAlertText'] += errorsDict['sensorId']
                return (False, valuesDict, errorsDict)

            # Make sure the sensor ID isn't used by another device.
            for otherDeviceId in self.deviceList:
                if otherDeviceId != deviceId:
                    otherDevice = indigo.devices[otherDeviceId]
                    if sensorId == otherDevice.pluginProps.get('sensorId', 0):
                        otherDevice = indigo.devices[otherDeviceId]
                        isError = True
                        errorsDict['sensorId'] = u"This Hue device is already being controlled by the \"" + otherDevice.name + "\" Indigo device. Choose a different Hue Motion Sensor."
                        errorsDict['showAlertText'] += errorsDict['sensorId'] + "\n\n"

            # Show errors if there are any.
            if isError:
                errorsDict['showAlertText'] = errorsDict['showAlertText'].strip()
                return (False, valuesDict, errorsDict)

            else:
                # Define the device's address to appear in Indigo.
                valuesDict['address'] = u"{} (Sid:{}-{})".format(ipAddress, hubNumber, valuesDict['sensorId'])
                # If this was a copied device, some properties could
                #   be invalid for this device type.  Let's make sure they're not.
                valuesDict['SupportsOnState'] = True
                valuesDict['SupportsSensorValue'] = False
                valuesDict['enabledOnHub'] = True
                valuesDict['manufacturerName'] = sensor.get('manufacturername', "")
                valuesDict['modelId'] = sensor.get('modelid', "")
                valuesDict['productId'] = sensor.get('productname', "")
                valuesDict['nameOnHub'] = sensor.get('name', "")
                valuesDict['swVersion'] = sensor.get('swversion', "")
                valuesDict['type'] = sensor.get('type', "")
                valuesDict['uniqueId'] = sensor.get('uniqueid', "")
                if valuesDict.get('sensorOffset', False):
                    valuesDict['sensorOffset'] = ""
                if valuesDict.get('temperatureScale', False):
                    valuesDict['temperatureScale'] = ""
                return (True, valuesDict)

        #  -- Hue Motion Sensor (Temperature) --
        elif typeId == "hueMotionTemperatureSensor":
            # Make sure a motion sensor was selected.
            if valuesDict.get('sensorId', "") == "":
                isError = True
                errorsDict['sensorId'] = u"Please select a temperature sensor."
                errorsDict['showAlertText'] += errorsDict['sensorId']
                return (False, valuesDict, errorsDict)

            sensorId = valuesDict.get('sensorId', "0")

            # Make sure the device selected is a Hue sensor device.
            #   Get the device info directly from the bridge.
            command = "http://{}/api/{}/sensors/{}".format(ipAddress, self.hostIds[hubNumber], sensorId)
            self.debugLog(u"Sending URL request: {}".format(command) )
            try:
                r = requests.get(command, timeout=kTimeout)
            except requests.exceptions.Timeout:
                errorText = u"Failed to connect to the Hue bridge at {} after {} seconds. - Check that the bridge is connected and turned on.".format(ipAddress, kTimeout)
                # Don't display the error if it's been displayed already.
                if errorText != self.lastErrorMessage:
                    self.errorLog(errorText)
                    # Remember the error.
                    self.lastErrorMessage = errorText
                return
            except requests.exceptions.ConnectionError:
                errorText = u"Failed to connect to the Hue bridge at {}. - Check that the bridge is connected and turned on.".format(ipAddress)
                # Don't display the error if it's been displayed already.
                if errorText != self.lastErrorMessage:
                    self.errorLog(errorText)
                    # Remember the error.
                    self.lastErrorMessage = errorText
                return
            self.debugLog(u"Data from bridge: {}".format(r.content.decode("utf-8")) )

            # Convert the response to a Python object.
            try:
                sensor = json.loads(r.content)
            except Exception, e:
                # There was an error in the returned data.
                indigo.server.log(u"Error retrieving Hue device data from bridge.  Error reported: {}".format(e))
                isError = True
                errorsDict['sensorId'] = u"Error retrieving Hue device data from bridge. See Indigo log."
                errorsDict['showAlertText'] += errorsDict['sensorId']
                return (False, valuesDict, errorsDict)

            if sensor.get('modelid', "")[0:len(kTemperatureSensorDeviceIDs)] != kTemperatureSensorDeviceIDs:
                isError = True
                errorsDict['sensorId'] = u"The selected device is not a temperature sensor. Please select a temperature sensor device."
                errorsDict['showAlertText'] += errorsDict['sensorId']
                return (False, valuesDict, errorsDict)

            # Make sure the sensor ID isn't used by another device.
            for otherDeviceId in self.deviceList:
                if otherDeviceId != deviceId:
                    otherDevice = indigo.devices[otherDeviceId]
                    if valuesDict['sensorId'] == otherDevice.pluginProps.get('sensorId', 0):
                        otherDevice = indigo.devices[otherDeviceId]
                        isError = True
                        errorsDict['sensorId'] = u"This Hue device is already being controlled by the \"" + otherDevice.name + "\" Indigo device. Choose a different temperature sensor."
                        errorsDict['showAlertText'] += errorsDict['sensorId'] + "\n\n"

            # Validate the sensor offset (calibration offset).
            if valuesDict.get('sensorOffset', "") != "":
                try:
                    sensorOffset = round(float(valuesDict.get('sensorOffset', 0)), 1)
                    if sensorOffset < -10.0 or sensorOffset > 10.0:
                        isError = True
                        errorsDict['sensorOffset'] = u"The Calibration Offset must be a number between -10 and 10."
                        errorsDict['showAlertText'] += errorsDict['sensorOffset'] + "\n\n"
                except ValueError:
                    isError = True
                    errorsDict['sensorOffset'] = u"The Calibration Offset must be a number between -10 and 10."
                    errorsDict['showAlertText'] += errorsDict['sensorOffset'] + "\n\n"
                except Exception, e:
                    isError = True
                    errorsDict['sensorOffset'] = u"The Calibration Offset must be a number between -10 and 10. Error: {}".format(e)
                    errorsDict['showAlertText'] += errorsDict['sensorOffset'] + "\n\n"

            # Validate the temperature scale.
            if valuesDict.get('temperatureScale', "") != "":
                try:
                    temperatureScale = valuesDict.get('temperatureScale', "c")
                except Exception, e:
                    isError = True
                    errorsDict['temperatureScale'] = u"The Temperature Scale must be either Celsius or Fahrenheit. Error: {}".format(e)
                    errorsDict['showAlertText'] += errorsDict['temperatureScale'] + "\n\n"
            else:
                valuesDict['temperatureScale'] = "c"

            # Show errors if there are any.
            if isError:
                errorsDict['showAlertText'] = errorsDict['showAlertText'].strip()
                return (False, valuesDict, errorsDict)

            else:
                # Define the device's address to appear in Indigo.
                valuesDict['address'] = u"{} (Sid:{}-{})".format(ipAddress, hubNumber, valuesDict['sensorId'])
                # If this was a copied device, some properties could
                #   be invalid for this device type.  Let's make sure they're not.
                valuesDict['SupportsOnState'] = False
                valuesDict['SupportsSensorValue'] = True
                valuesDict['enabledOnHub'] = True
                valuesDict['manufacturerName'] = sensor.get('manufacturername', "")
                valuesDict['modelId'] = sensor.get('modelid', "")
                valuesDict['productId'] = sensor.get('productname', "")
                valuesDict['nameOnHub'] = sensor.get('name', "")
                valuesDict['swVersion'] = sensor.get('swversion', "")
                valuesDict['type'] = sensor.get('type', "")
                valuesDict['uniqueId'] = sensor.get('uniqueid', "")
                return (True, valuesDict)

        #  -- Hue Motion Sensor (Luminance) --
        elif typeId == "hueMotionLightSensor":
            # Make sure a motion sensor was selected.
            if valuesDict.get('sensorId', "") == "":
                isError = True
                errorsDict['sensorId'] = u"Please select a light sensor."
                errorsDict['showAlertText'] += errorsDict['sensorId']
                return (False, valuesDict, errorsDict)

            sensorId = valuesDict['sensorId']

            # Make sure the device selected is a Hue sensor device.
            #   Get the device info directly from the bridge.
            command = "http://{}/api/{}/sensors/{}".format(ipAddress, self.hostIds[hubNumber], sensorId)
            self.debugLog(u"Sending URL request: {}".format(command) )
            try:
                r = requests.get(command, timeout=kTimeout)
            except requests.exceptions.Timeout:
                errorText = u"Failed to connect to the Hue bridge at {} after {} seconds. - Check that the bridge is connected and turned on.".format(ipAddress, kTimeout)
                # Don't display the error if it's been displayed already.
                if errorText != self.lastErrorMessage:
                    self.errorLog(errorText)
                    # Remember the error.
                    self.lastErrorMessage = errorText
                return
            except requests.exceptions.ConnectionError:
                errorText = u"Failed to connect to the Hue bridge at {}. - Check that the bridge is connected and turned on.".format(ipAddress)
                # Don't display the error if it's been displayed already.
                if errorText != self.lastErrorMessage:
                    self.errorLog(errorText)
                    # Remember the error.
                    self.lastErrorMessage = errorText
                return
            self.debugLog(u"Data from bridge: {}".format(r.content.decode("utf-8")) )

            # Convert the response to a Python object.
            try:
                sensor = json.loads(r.content)
            except Exception, e:
                # There was an error in the returned data.
                indigo.server.log(u"Error retrieving Hue device data from bridge.  Error reported: {}".format(e))
                isError = True
                errorsDict['sensorId'] = u"Error retrieving Hue device data from bridge. See Indigo log."
                errorsDict['showAlertText'] += errorsDict['sensorId']
                return (False, valuesDict, errorsDict)

            if sensor.get('modelid', "")[0:len(kLightSensorDeviceIDs)] != kLightSensorDeviceIDs:
                isError = True
                errorsDict['sensorId'] = u"The selected device is not a light sensor. Please select a light sensor device."
                errorsDict['showAlertText'] += errorsDict['sensorId']
                return (False, valuesDict, errorsDict)

            # Make sure the sensor ID isn't used by another device.
            for otherDeviceId in self.deviceList:
                if otherDeviceId != deviceId:
                    otherDevice = indigo.devices[otherDeviceId]
                    if valuesDict['sensorId'] == otherDevice.pluginProps.get('sensorId', 0):
                        otherDevice = indigo.devices[otherDeviceId]
                        isError = True
                        errorsDict['sensorId'] = u"This Hue device is already being controlled by the \"" + otherDevice.name + "\" Indigo device. Choose a different light sensor."
                        errorsDict['showAlertText'] += errorsDict['sensorId'] + "\n\n"

            # Show errors if there are any.
            if isError:
                errorsDict['showAlertText'] = errorsDict['showAlertText'].strip()
                return (False, valuesDict, errorsDict)

            else:
                # Define the device's address to appear in Indigo.
                valuesDict['address'] = u"{} (Sid:{}-{})".format(ipAddress, hubNumber, valuesDict['sensorId'])
                # If this was a copied device, some properties could
                #   be invalid for this device type.  Let's make sure they're not.
                valuesDict['SupportsOnState'] = False
                valuesDict['SupportsSensorValue'] = True
                valuesDict['enabledOnHub'] = True
                valuesDict['manufacturerName'] = sensor.get('manufacturername', "")
                valuesDict['modelId'] = sensor.get('modelid', "")
                valuesDict['productId'] = sensor.get('productname', "")
                valuesDict['nameOnHub'] = sensor.get('name', "")
                valuesDict['swVersion'] = sensor.get('swversion', "")
                valuesDict['type'] = sensor.get('type', "")
                valuesDict['uniqueId'] = sensor.get('uniqueid', "")
                if valuesDict.get('sensorOffset', False):
                    valuesDict['sensorOffset'] = ""
                if valuesDict.get('temperatureScale', False):
                    valuesDict['temperatureScale'] = ""
                return (True, valuesDict)

        #  -- Hue Tap Switch --
        elif typeId == "hueTapSwitch":
            # Make sure a tap switch was selected.
            if valuesDict.get('sensorId', "") == "":
                isError = True
                errorsDict['sensorId'] = u"Please select a Hue Tap Switch."
                errorsDict['showAlertText'] += errorsDict['sensorId']
                return (False, valuesDict, errorsDict)

            sensorId = valuesDict['sensorId']

            # Make sure the device selected is a Hue sensor device.
            #   Get the device info directly from the bridge.
            command = "http://{}/api/{}/sensors/{}".format(ipAddress, self.hostIds[hubNumber], sensorId)
            self.debugLog(u"Sending URL request: {}".format(command) )
            try:
                r = requests.get(command, timeout=kTimeout)
            except requests.exceptions.Timeout:
                errorText = u"Failed to connect to the Hue bridge at {} after {} seconds. - Check that the bridge is connected and turned on.".format(ipAddress, kTimeout)
                # Don't display the error if it's been displayed already.
                if errorText != self.lastErrorMessage:
                    self.errorLog(errorText)
                    # Remember the error.
                    self.lastErrorMessage = errorText
                return
            except requests.exceptions.ConnectionError:
                errorText = u"Failed to connect to the Hue bridge at {}. - Check that the bridge is connected and turned on.".format(ipAddress)
                # Don't display the error if it's been displayed already.
                if errorText != self.lastErrorMessage:
                    self.errorLog(errorText)
                    # Remember the error.
                    self.lastErrorMessage = errorText
                return
            self.debugLog(u"Data from bridge: {}".format(r.content.decode("utf-8")) )

            # Convert the response to a Python object.
            try:
                sensor = json.loads(r.content)
            except Exception, e:
                # There was an error in the returned data.
                indigo.server.log(u"Error retrieving Hue device data from bridge.  Error reported: {}".format(e))
                isError = True
                errorsDict['sensorId'] = u"Error retrieving Hue device data from bridge. See Indigo log."
                errorsDict['showAlertText'] += errorsDict['sensorId']
                return (False, valuesDict, errorsDict)

            if sensor.get('modelid', "") not in kSwitchDeviceIDs:
                isError = True
                errorsDict['sensorId'] = u"The selected device is not a Hue Tap Switch. Please select a Hue Tap Switch device."
                errorsDict['showAlertText'] += errorsDict['sensorId']
                return (False, valuesDict, errorsDict)

            # Make sure the sensor ID isn't used by another device.
            for otherDeviceId in self.deviceList:
                if otherDeviceId != deviceId:
                    otherDevice = indigo.devices[otherDeviceId]
                    if sensorId == otherDevice.pluginProps.get('sensorId', 0):
                        otherDevice = indigo.devices[otherDeviceId]
                        isError = True
                        errorsDict['sensorId'] = u"This Hue device is already being controlled by the \"" + otherDevice.name + "\" Indigo device. Choose a different Hue Tap Switch."
                        errorsDict['showAlertText'] += errorsDict['sensorId'] + "\n\n"

            # Show errors if there are any.
            if isError:
                errorsDict['showAlertText'] = errorsDict['showAlertText'].strip()
                return (False, valuesDict, errorsDict)

            else:
                # Define the device's address to appear in Indigo.
                valuesDict['address'] = u"{} (Sid:{}-{})".format(ipAddress, hubNumber, valuesDict['sensorId'])
                # If this was a copied device, some properties could
                #   be invalid for this device type.  Let's make sure they're not.
                valuesDict['SupportsOnState'] = True
                valuesDict['SupportsSensorValue'] = False
                valuesDict['SupportsBatteryLevel'] = False
                valuesDict['enabledOnHub'] = True
                valuesDict['manufacturerName'] = sensor.get('manufacturername', "")
                valuesDict['modelId'] = sensor.get('modelid', "")
                valuesDict['nameOnHub'] = sensor.get('name', "")
                valuesDict['swVersion'] = sensor.get('swversion', "")
                valuesDict['type'] = sensor.get('type', "")
                valuesDict['uniqueId'] = sensor.get('uniqueid', "")

                return (True, valuesDict)

        #  -- Hue Dimmer Switch --
        elif typeId == "hueDimmerSwitch":
            # Make sure a dimmer switch was selected.
            if valuesDict.get('sensorId', "") == "":
                isError = True
                errorsDict['sensorId'] = u"Please select a Hue Dimmer Switch."
                errorsDict['showAlertText'] += errorsDict['sensorId']
                return (False, valuesDict, errorsDict)

            sensorId = valuesDict['sensorId']

            # Make sure the device selected is a Hue sensor device.
            #   Get the device info directly from the bridge.
            command = "http://{}/api/{}/sensors/{}".format(ipAddress, self.hostIds[hubNumber], sensorId)
            self.debugLog(u"Sending URL request: {}".format(command) )
            try:
                r = requests.get(command, timeout=kTimeout)
            except requests.exceptions.Timeout:
                errorText = u"Failed to connect to the Hue bridge at {} after {} seconds. - Check that the bridge is connected and turned on.".format(ipAddress, kTimeout)
                # Don't display the error if it's been displayed already.
                if errorText != self.lastErrorMessage:
                    self.errorLog(errorText)
                    # Remember the error.
                    self.lastErrorMessage = errorText
                return
            except requests.exceptions.ConnectionError:
                errorText = u"Failed to connect to the Hue bridge at {}. - Check that the bridge is connected and turned on.".format(ipAddress)
                # Don't display the error if it's been displayed already.
                if errorText != self.lastErrorMessage:
                    self.errorLog(errorText)
                    # Remember the error.
                    self.lastErrorMessage = errorText
                return
            self.debugLog(u"Data from bridge: {}".format(r.content.decode("utf-8")) )

            # Convert the response to a Python object.
            try:
                sensor = json.loads(r.content)
            except Exception, e:
                # There was an error in the returned data.
                indigo.server.log(u"Error retrieving Hue device data from bridge.  Error reported: {}".format(e))
                isError = True
                errorsDict['sensorId'] = u"Error retrieving Hue device data from bridge. See Indigo log."
                errorsDict['showAlertText'] += errorsDict['sensorId']
                return (False, valuesDict, errorsDict)

            if sensor.get('modelid', "") not in kSwitchDeviceIDs:
                isError = True
                errorsDict['sensorId'] = u"The selected device is not a Hue Dimmer Switch. Please select a Hue Dimmer Switch device."
                errorsDict['showAlertText'] += errorsDict['sensorId']
                return (False, valuesDict, errorsDict)

            # Make sure the sensor ID isn't used by another device.
            for otherDeviceId in self.deviceList:
                if otherDeviceId != deviceId:
                    otherDevice = indigo.devices[otherDeviceId]
                    if sensorId == otherDevice.pluginProps.get('sensorId', 0):
                        otherDevice = indigo.devices[otherDeviceId]
                        isError = True
                        errorsDict['sensorId'] = u"This Hue device is already being controlled by the \"" + otherDevice.name + "\" Indigo device. Choose a different Hue Dimmer Switch."
                        errorsDict['showAlertText'] += errorsDict['sensorId'] + "\n\n"

            # Show errors if there are any.
            if isError:
                errorsDict['showAlertText'] = errorsDict['showAlertText'].strip()
                return (False, valuesDict, errorsDict)

            else:
                # Define the device's address to appear in Indigo.
                valuesDict['address'] = u"{} (Sid:{}-{})".format(ipAddress, hubNumber, valuesDict['sensorId'])
                # If this was a copied device, some properties could
                #   be invalid for this device type.  Let's make sure they're not.
                valuesDict['SupportsOnState'] = True
                valuesDict['SupportsSensorValue'] = False
                valuesDict['SupportsBatteryLevel'] = True
                valuesDict['enabledOnHub'] = True
                valuesDict['manufacturerName'] = sensor.get('manufacturername', "")
                valuesDict['modelId'] = sensor.get('modelid', "")
                valuesDict['productId'] = sensor.get('productname', "")
                valuesDict['nameOnHub'] = sensor.get('name', "")
                valuesDict['swVersion'] = sensor.get('swversion', "")
                valuesDict['type'] = sensor.get('type', "")
                valuesDict['uniqueId'] = sensor.get('uniqueid', "")

                return (True, valuesDict)

        #  -- Hue Smart Button --
        elif typeId == "hueSmartButton":
            # Make sure a smart button was selected.
            if valuesDict.get('sensorId', "") == "":
                isError = True
                errorsDict['sensorId'] = u"Please select a Hue Smart Button."
                errorsDict['showAlertText'] += errorsDict['sensorId']
                return (False, valuesDict, errorsDict)

            sensorId = valuesDict['sensorId']

            # Make sure the device selected is a Hue sensor device.
            #   Get the device info directly from the bridge.
            command = "http://{}/api/{}/sensors/{}".format(ipAddress, self.hostIds[hubNumber], sensorId)
            self.debugLog(u"Sending URL request: {}".format(command) )
            try:
                r = requests.get(command, timeout=kTimeout)
            except requests.exceptions.Timeout:
                errorText = u"Failed to connect to the Hue bridge at {} after {} seconds. - Check that the bridge is connected and turned on.".format(ipAddress, kTimeout)
                # Don't display the error if it's been displayed already.
                if errorText != self.lastErrorMessage:
                    self.errorLog(errorText)
                    # Remember the error.
                    self.lastErrorMessage = errorText
                return
            except requests.exceptions.ConnectionError:
                errorText = u"Failed to connect to the Hue bridge at {}. - Check that the bridge is connected and turned on.".format(ipAddress)
                # Don't display the error if it's been displayed already.
                if errorText != self.lastErrorMessage:
                    self.errorLog(errorText)
                    # Remember the error.
                    self.lastErrorMessage = errorText
                return
            self.debugLog(u"Data from bridge: {}".format(r.content.decode("utf-8")) )

            # Convert the response to a Python object.
            try:
                sensor = json.loads(r.content)
            except Exception, e:
                # There was an error in the returned data.
                indigo.server.log(u"Error retrieving Hue device data from bridge.  Error reported: {}".format(e))
                isError = True
                errorsDict['sensorId'] = u"Error retrieving Hue device data from bridge. See Indigo log."
                errorsDict['showAlertText'] += errorsDict['sensorId']
                return (False, valuesDict, errorsDict)

            if sensor.get('modelid', "") not in kSwitchDeviceIDs:
                isError = True
                errorsDict['sensorId'] = u"The selected device is not a Hue Smart Button. Please select a Hue Smart Button device."
                errorsDict['showAlertText'] += errorsDict['sensorId']
                return (False, valuesDict, errorsDict)

            # Make sure the sensor ID isn't used by another device.
            for otherDeviceId in self.deviceList:
                if otherDeviceId != deviceId:
                    otherDevice = indigo.devices[otherDeviceId]
                    if sensorId == otherDevice.pluginProps.get('sensorId', 0):
                        otherDevice = indigo.devices[otherDeviceId]
                        isError = True
                        errorsDict['sensorId'] = u"This Hue device is already being controlled by the \"" + otherDevice.name + "\" Indigo device. Choose a different Hue Smart Button."
                        errorsDict['showAlertText'] += errorsDict['sensorId'] + "\n\n"

            # Show errors if there are any.
            if isError:
                errorsDict['showAlertText'] = errorsDict['showAlertText'].strip()
                return (False, valuesDict, errorsDict)

            else:
                # Define the device's address to appear in Indigo.
                valuesDict['address'] = u"{} (Sid:{}-{})".format(ipAddress, hubNumber, valuesDict['sensorId'])
                # If this was a copied device, some properties could
                #   be invalid for this device type.  Let's make sure they're not.
                valuesDict['SupportsOnState'] = True
                valuesDict['SupportsSensorValue'] = False
                valuesDict['SupportsBatteryLevel'] = True
                valuesDict['enabledOnHub'] = True
                valuesDict['manufacturerName'] = sensor.get('manufacturername', "")
                valuesDict['modelId'] = sensor.get('modelid', "")
                valuesDict['productId'] = sensor.get('productname', "")
                valuesDict['nameOnHub'] = sensor.get('name', "")
                valuesDict['swVersion'] = sensor.get('swversion', "")
                valuesDict['type'] = sensor.get('type', "")
                valuesDict['uniqueId'] = sensor.get('uniqueid', "")

                return (True, valuesDict)

        #  -- Hue Wall Switch Module --
        elif typeId == "hueWallSwitchModule":
            # Make sure a smart button was selected.
            if valuesDict.get('sensorId', "") == "":
                isError = True
                errorsDict['sensorId'] = u"Please select a Hue Wall Switch Module."
                errorsDict['showAlertText'] += errorsDict['sensorId']
                return (False, valuesDict, errorsDict)

            sensorId = valuesDict['sensorId']

            # Make sure the device selected is a Hue sensor device.
            #   Get the device info directly from the bridge.
            command = "http://{}/api/{}/sensors/{}".format(ipAddress, self.self.hostIds[hubNumber][hubNumber], sensorId)
            self.debugLog(u"Sending URL request: " + command)
            try:
                r = requests.get(command, timeout=kTimeout)
            except requests.exceptions.Timeout:
                errorText = u"Failed to connect to the Hue bridge at {} after {} seconds. - Check that the bridge is connected and turned on.".format(ipAddress, kTimeout)
                # Don't display the error if it's been displayed already.
                if errorText != self.lastErrorMessage:
                    self.errorLog(errorText)
                    # Remember the error.
                    self.lastErrorMessage = errorText
                return
            except requests.exceptions.ConnectionError:
                errorText = u"Failed to connect to the Hue bridge at {}. - Check that the bridge is connected and turned on.".format(ipAddress)
                # Don't display the error if it's been displayed already.
                if errorText != self.lastErrorMessage:
                    self.errorLog(errorText)
                    # Remember the error.
                    self.lastErrorMessage = errorText
                return
            self.debugLog(u"Data from bridge: " + r.content.decode("utf-8"))

            # Convert the response to a Python object.
            try:
                sensor = json.loads(r.content)
            except Exception, e:
                # There was an error in the returned data.
                indigo.server.log(u"Error retrieving Hue device data from bridge.  Error reported: {}".format(e))
                isError = True
                errorsDict['sensorId'] = u"Error retrieving Hue device data from bridge. See Indigo log."
                errorsDict['showAlertText'] += errorsDict['sensorId']
                return (False, valuesDict, errorsDict)

            if sensor.get('modelid', "") not in kSwitchDeviceIDs:
                isError = True
                errorsDict['sensorId'] = u"The selected device is not a Hue Wall Switch Module. Please select a Hue Wall Switch Module device."
                errorsDict['showAlertText'] += errorsDict['sensorId']
                return (False, valuesDict, errorsDict)

            # Make sure the sensor ID isn't used by another device.
            for otherDeviceId in self.deviceList:
                if otherDeviceId != deviceId:
                    otherDevice = indigo.devices[otherDeviceId]
                    if sensorId == otherDevice.pluginProps.get('sensorId', 0):
                        otherDevice = indigo.devices[otherDeviceId]
                        isError = True
                        errorsDict['sensorId'] = u"This Hue device is already being controlled by the \"{}\" Indigo device. Choose a different Hue Wall Switch Module.".format(otherDevice.name)
                        errorsDict['showAlertText'] += errorsDict['sensorId'] + "\n\n"

            # Show errors if there are any.
            if isError:
                errorsDict['showAlertText'] = errorsDict['showAlertText'].strip()
                return (False, valuesDict, errorsDict)

            else:
                # Define the device's address to appear in Indigo.
                valuesDict['address'] = u"{} (Sid:{}-{})".format(ipAddress, hubNumber, valuesDict['sensorId'])
                # If this was a copied device, some properties could
                #   be invalid for this device type.  Let's make sure they're not.
                valuesDict['SupportsOnState'] = True
                valuesDict['SupportsSensorValue'] = False
                valuesDict['SupportsBatteryLevel'] = True
                valuesDict['enabledOnHub'] = True
                valuesDict['manufacturerName'] = sensor.get('manufacturername', "")
                valuesDict['modelId'] = sensor.get('modelid', "")
                valuesDict['productId'] = sensor.get('productname', "")
                valuesDict['nameOnHub'] = sensor.get('name', "")
                valuesDict['swVersion'] = sensor.get('swversion', "")
                valuesDict['type'] = sensor.get('type', "")
                valuesDict['uniqueId'] = sensor.get('uniqueid', "")
                valuesDict['deviceMode'] = sensor.get('devicemode', "")

                return (True, valuesDict)

        #  -- Run Less Wire or Niko Switch --
        elif typeId == "runLessWireSwitch":
            # Make sure a Run Less Wire or Niko switch was selected.
            if valuesDict.get('sensorId', "") == "":
                isError = True
                errorsDict['sensorId'] = u"Please select a Run Less Wire or Niko Switch."
                errorsDict['showAlertText'] += errorsDict['sensorId']
                return (False, valuesDict, errorsDict)

            sensorId = valuesDict['sensorId']

            # Make sure the device selected is a Hue sensor device.
            #   Get the device info directly from the bridge.
            command = "http://{}/api/{}/sensors/{}".format(ipAddress, self.hostIds[hubNumber], sensorId)
            self.debugLog(u"Sending URL request: {}".format(command) )
            try:
                r = requests.get(command, timeout=kTimeout)
            except requests.exceptions.Timeout:
                errorText = u"Failed to connect to the Hue bridge at {} after {} seconds. - Check that the bridge is connected and turned on.".format(ipAddress, kTimeout)
                # Don't display the error if it's been displayed already.
                if errorText != self.lastErrorMessage:
                    self.errorLog(errorText)
                    # Remember the error.
                    self.lastErrorMessage = errorText
                return
            except requests.exceptions.ConnectionError:
                errorText = u"Failed to connect to the Hue bridge at {} - Check that the bridge is connected and turned on.".format(ipAddress)
                # Don't display the error if it's been displayed already.
                if errorText != self.lastErrorMessage:
                    self.errorLog(errorText)
                    # Remember the error.
                    self.lastErrorMessage = errorText
                return
            self.debugLog(u"Data from bridge: {}".format(r.content.decode("utf-8")) )

            # Convert the response to a Python object.
            try:
                sensor = json.loads(r.content)
            except Exception, e:
                # There was an error in the returned data.
                indigo.server.log(u"Error retrieving Hue device data from bridge.  Error reported: {}".format(e))
                isError = True
                errorsDict['sensorId'] = u"Error retrieving Hue device data from bridge. See Indigo log."
                errorsDict['showAlertText'] += errorsDict['sensorId']
                return (False, valuesDict, errorsDict)

            if sensor.get('modelid', "") not in kSwitchDeviceIDs:
                isError = True
                errorsDict['sensorId'] = u"The selected device is not a Run Less Wire or Niko Switch. Please select a Run Less Wire or Niko Switch device."
                errorsDict['showAlertText'] += errorsDict['sensorId']
                return (False, valuesDict, errorsDict)

            # Make sure the sensor ID isn't used by another device.
            for otherDeviceId in self.deviceList:
                if otherDeviceId != deviceId:
                    otherDevice = indigo.devices[otherDeviceId]
                    if sensorId == otherDevice.pluginProps.get('sensorId', 0):
                        otherDevice = indigo.devices[otherDeviceId]
                        isError = True
                        errorsDict['sensorId'] = u"This Hue connected device is already being controlled by the \"\" Indigo device. Choose a different Run Less Wire Switch.".format(otherDevice.name)
                        errorsDict['showAlertText'] += errorsDict['sensorId'] + "\n\n"

            # Show errors if there are any.
            if isError:
                errorsDict['showAlertText'] = errorsDict['showAlertText'].strip()
                return (False, valuesDict, errorsDict)

            else:
                # Define the device's address to appear in Indigo.
                valuesDict['address'] = u"{} (Sid:{}-{})".format(ipAddress, hubNumber, valuesDict['sensorId'])
                # If this was a copied device, some properties could
                #   be invalid for this device type.  Let's make sure they're not.
                valuesDict['SupportsOnState'] = True
                valuesDict['SupportsSensorValue'] = False
                valuesDict['SupportsBatteryLevel'] = False
                valuesDict['enabledOnHub'] = True
                valuesDict['manufacturerName'] = sensor.get('manufacturername', "")
                valuesDict['modelId'] = sensor.get('modelid', "")
                valuesDict['productId'] = sensor.get('productname', "")
                valuesDict['nameOnHub'] = sensor.get('name', "")
                valuesDict['swVersion'] = sensor.get('swversion', "")
                valuesDict['type'] = sensor.get('type', "")
                valuesDict['uniqueId'] = sensor.get('uniqueid', "")

                self.hubNumberSelected = ""
                return (True, valuesDict)
        else:
            isError = True
            errorsDict['showAlertText'] = u"No compatible device type was selected. Please cancel the device setup and try selecting the device type again."
            errorsDict['showAlertText'] = errorsDict['showAlertText'].strip()
            self.errorLog(errorsDict['showAlertText'])
            return (False, valuesDict, errorsDict)

    # Closed Device Configuration.
    ########################################
    def closedDeviceConfigUi(self, valuesDict, userCancelled, typeId, deviceId):
        self.debugLog(u"Starting closedDeviceConfigUi.  valuesDict: {}, userCancelled: {}, typeId: {}, deviceId: {}".format(valuesDict, userCancelled, typeId, deviceId))
        # If the user didn't cancel the changes, take any needed actions as a result of the changes made.
        if not userCancelled:
            # Configuration was saved.  Rebuild the device if needed.
            device = indigo.devices[deviceId]
            self.rebuildDevice(device)

    # Validate Action Configuration.
    ########################################
    def validateActionConfigUi(self, valuesDict, typeId, deviceId):
        self.debugLog(u"Starting validateActionConfigUi.  valuesDict: {}, typeId: {}, deviceId: {}".format(valuesDict,  typeId, deviceId))
        hubNumber = "0"
        if deviceId == 0:
            device = None
            modelId = 0
            type = 0
            if "hubNumber" in valuesDict: hubNumber = valuesDict['hubNumber']
        else:
            device = indigo.devices[deviceId]
            modelId = device.pluginProps.get('modelId', False)
            type = device.pluginProps.get('type', False)
            hubNumber = device.pluginProps.get('hubNumber', "0")
        isError = False
        errorsDict = indigo.Dict()
        errorsDict['showAlertText'] = ""
        descString = u""

        # Make sure we're still paired with the Hue bridge.
        if not self.paired[hubNumber]:
            isError = True
            errorsDict['device'] = u"Not currently paired with the Hue bridge. Use the Configure... option in the Plugins -> Hue Lights menu to pair Hue Lights with the Hue bridge first."
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
                sceneName = self.scenesDict[hubNumber][sceneId]['name']
                descString += u" " + sceneName
            else:
                isError = True
                errorsDict['sceneId'] = u"A Scene must be selected."
                errorsDict['showAlertText'] += errorsDict['sceneId'] + "\n\n"

            if userId != "":
                if userId != "all":
                    if userId in self.usersDict[hubNumber]:
                        userName = self.usersDict[hubNumber][userId]['name'].replace("#", " app on ")
                    else:
                        userName = u"(a removed scene creator)"
                    descString += u" from " + userName
                else:
                    if sceneId != "":
                        userId = self.scenesDict[hubNumber][sceneId]['owner']
                        if userId in self.usersDict[hubNumber]:
                            userName = self.usersDict[hubNumber][userId]['name'].replace("#", " app on ")
                        else:
                            userName = u"(a removed scene creator)"
                        descString += u" from " + userName
            else:
                isError = True
                errorsDict['userId'] = u"A Scene Creator must be selected."
                errorsDict['showAlertText'] += errorsDict['userId'] + "\n\n"

            if groupId != "":
                if groupId == "0":
                    groupName = "All Hue Lights"
                    descString += u" for " + groupName
                else:
                    groupName = self.groupsDict[hubNumber][groupId]['name']
                    descString += u" for the " + groupName + u" hue group"
            else:
                isError = True
                errorsDict['groupId'] = u"A Group must be selected."
                errorsDict['showAlertText'] += errorsDict['userId'] + "\n\n"

            if len(sceneLights) < 1:
                isError = True
                errorsDict['sceneLights'] = u"The selected Scene and Group Limit combination will prevent any lights from changing when this scene is recalled. Change the Scene or Group Limit selection and make sure at least 1 light is listed in the Lights Affected list."
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
                descString += u"set brightness of {} to {}%".format( device.name , brightness)
            elif brightnessSource == "variable":
                if not brightnessVarId:
                    isError = True
                    errorsDict['brightnessVariable'] = u"Please specify a variable to use for brightness level."
                    errorsDict['showAlertText'] += errorsDict['brightnessVariable'] + "\n\n"
                else:
                    try:
                        brightnessVar = indigo.variables[int(brightnessVarId)]
                        descString += u"set brightness of {} to value in variable{}".format( device.name , brightnessVar.name)
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
                        if brightnessDev.id == device.id:
                            isError = True
                            errorsDict['brightnessDevice'] = u"You cannot select the same dimmer as the one for which you're setting the brightness."
                            errorsDict['showAlertText'] += errorsDict['brightnessDevice'] + "\n\n"
                        else:
                            descString += u"set brightness of {} to current brightness of \"{}\"".format( device.name , brightnessDev.name)
                    except IndexError:
                        isError = True
                        errorsDict['brightnessDevice'] = u"The specified device does not exist in the Indigo database. Please choose a different device."
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
                descString += u" using ramp rate {} sec".format(rate) 
            else:
                if not rateVarId:
                    isError = True
                    errorsDict['rateVariable'] = u"Please select a variable to use for the ramp rate."
                    errorsDict['showAlertText'] += errorsDict['rateVariable'] + "\n\n"
                else:
                    try:
                        rateVar = indigo.variables[int(rateVarId)]
                        descString += u" using ramp rate in variable \"{}\"".format(rateVar.name)
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
            useRateVariable = valuesDict.get('useRateVariable', False)
            rateVariable = valuesDict.get('rateVariable', "")
            rampRate = valuesDict.get('rate', "")

            # First make sure this is a Hue device and not an attribute controller.
            if device.deviceTypeId == "hueAttributeController":
                isError = True
                errorsDict['device'] = u"This action cannot be applied to Hue Device Attribute Controllers. Please cancel the configuration dialog and select a Hue device to control."
                errorsDict['showAlertText'] += errorsDict['device'] + "\n\n"
            # If it is a valid device, check everything else.
            # Make sure this device can handle color.
            elif not device.pluginProps.get('SupportsRGB', False):
                isError = True
                errorsDict['device'] = u"The \"{}\" device does not support color. Choose a different device.".format(device.name)
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
            except Exception, e:
                isError = True
                errorsDict['red'] = "Invalid Red value: {}".format(e)
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
            except Exception, e:
                isError = True
                errorsDict['green'] = "Invalid Green value: {}".format(e)
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
            except Exception, e:
                isError = True
                errorsDict['blue'] = "Invalid Blue value: {}".format(e)
                errorsDict['showAlertText'] += errorsDict['blue'] + "\n\n"

            # Validate Ramp Rate.
            if not useRateVariable:
                # User entered a ramp rate value.
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
                        errorsDict['rate'] = u"Invalid Ramp Rate value: {}".format(e)
                        errorsDict['showAlertText'] += errorsDict['rate'] + u"\n\n"
            else:
                # User specified that they'd select a variable as the ramp rate source.
                # Make sure they actually selected one.
                if rateVariable == "":
                    isError = True
                    errorsDict['rateVariable'] = u"No variable was selected. Please select an Indigo variable as the ramp rate source."
                    errorsDict['showAlertText'] += errorsDict['rateVariable'] + u"\n\n"
                else:
                    # Since a variable ID was given, convert it to an integer.
                    rateVariable = int(rateVariable)

            if not isError:
                descString += u"set hue device RGB levels to {}, {}, {}".format(red, green, blue)
                if useRateVariable == True:
                    descString += u" using ramp rate in variable \"{}\".".format(indigo.variables[rateVariable].name)
                else:
                    if len(valuesDict.get('rate', "")) > 0:
                        descString += u" with ramp rate {} sec".format(rampRate)

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
                errorsDict['device'] = u"This action cannot be applied to Hue Device Attribute Controllers. Please cancel the configuration dialog and select a Hue device to control."
                errorsDict['showAlertText'] += errorsDict['device'] + "\n\n"
            # If it is a valid device, check everything else.
            # Make sure this device can handle color.
            elif not device.pluginProps.get('SupportsRGB', False):
                isError = True
                errorsDict['device'] = u"The \"{}\" device does not support color. Choose a different device.".format(device.name)
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
            except Exception, e:
                isError = True
                errorsDict['hue'] = "Invalid Hue value: {}".format(e)
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
            except Exception, e:
                isError = True
                errorsDict['saturation'] = "Invalid Saturation value: {}".format(e)
                errorsDict['showAlertText'] += errorsDict['saturation'] + "\n\n"

            # Validate the brightness value.
            if brightnessSource == "custom":
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
                    errorsDict['brightness'] = u"Invalid Brightness value: {}".format(e)
                    errorsDict['showAlertText'] += errorsDict['brightness'] + u"\n\n"
            elif brightnessSource == "variable":
                # Make sure the variable selection is valid.
                if brightnessVariable == "":
                    isError = True
                    errorsDict['brightnessVariable'] = u"No source variable selected. Please select an Indigo variable from the list."
                    errorsDict['showAlertText'] += errorsDict['brightnessVariable'] + u"\n\n"
                else:
                    # Since a variable ID was given, convert it to an integer.
                    brightnessVariable = int(brightnessVariable)
            elif brightnessSource == "dimmer":
                # Make sure the device selection is valid.
                if brightnessDevice == "":
                    isError = True
                    errorsDict['brightnessDevice'] = u"No source device selected. Please select an Indigo dimmer device from the list."
                    errorsDict['showAlertText'] += errorsDict['brightnessDevice'] + u"\n\n"
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
                            errorsDict['rate'] = u"Ramp Rate must be a number between 0 and 540 seconds and can be in increments of 0.1 seconds."
                            errorsDict['showAlertText'] += errorsDict['rate'] + u"\n\n"
                    except ValueError:
                        isError = True
                        errorsDict['rate'] = u"Ramp Rate must be a number between 0 and 540 seconds and can be in increments of 0.1 seconds."
                        errorsDict['showAlertText'] += errorsDict['rate'] + u"\n\n"
                    except Exception, e:
                        isError = True
                        errorsDict['rate'] = u"Invalid Ramp Rate value: {}".format(e)
                        errorsDict['showAlertText'] += errorsDict['rate'] + u"\n\n"
            else:
                # User specified that they'd select a variable as the ramp rate source.
                # Make sure they actually selected one.
                if rateVariable == "":
                    isError = True
                    errorsDict['rateVariable'] = u"No variable was selected. Please select an Indigo variable as the ramp rate source."
                    errorsDict['showAlertText'] += errorsDict['rateVariable'] + u"\n\n"
                else:
                    # Since a variable ID was given, convert it to an integer.
                    rateVariable = int(rateVariable)

            if not isError:
                descString += u"set hue device hue to {}, saturation to {}  and brightness to".format(hue, saturation)
                if brightnessSource == "custom":
                    descString += u"{}".format(brightness)
                elif brightnessSource == "variable":
                    descString += u" value in variable \"{}\"".format(indigo.variables[brightnessVariable].name)
                elif brightnessSource == "dimmer":
                    descString += u" brightness of device \"{}\"".format(indigo.devices[brightnessDevice].name)

                if useRateVariable == True:
                    descString += u" using ramp rate in variable \"{}\".".format(indigo.variables[rateVariable].name )
                else:
                    if len(valuesDict.get('rate', "")) > 0:
                        descString += u" with ramp rate {} sec".format(rampRate)

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
                errorsDict['device'] = u"This action cannot be applied to Hue Device Attribute Controllers. Please cancel the configuration dialog and select a Hue device to control."
                errorsDict['showAlertText'] += errorsDict['device'] + "\n\n"
            # If it is a valid device, check everything else.
            # Make sure this device can handle color.
            elif not device.pluginProps.get('SupportsRGB', False):
                isError = True
                errorsDict['device'] = u"The \"{}\" device does not support color. Choose a different device.".format(device.name)
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
            except Exception, e:
                isError = True
                errorsDict['xyy_x'] = "Invalid x Chromatisety value: {}".format(e)
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
            except Exception, e:
                isError = True
                errorsDict['xyy_y'] = "Invalid y Chromatisety value: {}".format(e)
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
            except Exception, e:
                isError = True
                errorsDict['xyy_Y'] = "Invalid Y Luminosity value: {}".format(e)
                errorsDict['showAlertText'] += errorsDict['xyy_Y'] + "\n\n"

            # Validate Ramp Rate.
            if not useRateVariable:
                # User entered a ramp rate value.
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
                        errorsDict['rate'] = u"Invalid Ramp Rate value: {}".format(e)
                        errorsDict['showAlertText'] += errorsDict['rate'] + u"\n\n"
            else:
                # User specified that they'd select a variable as the ramp rate source.
                # Make sure they actually selected one.
                if rateVariable == "":
                    isError = True
                    errorsDict['rateVariable'] = u"No variable was selected. Please select an Indigo variable as the ramp rate source."
                    errorsDict['showAlertText'] += errorsDict['rateVariable'] + u"\n\n"
                else:
                    # Since a variable ID was given, convert it to an integer.
                    rateVariable = int(rateVariable)

            if not isError:
                descString += u"set hue device xyY chromatisety to {}, {}, {}".format(colorX, colorY, brightness)
                if useRateVariable == True:
                    descString += u" using ramp rate in variable \"{}\".".format(indigo.variables[rateVariable].name)
                else:
                    if len(valuesDict.get('rate', "")) > 0:
                        descString += u" with ramp rate {} sec".format(rampRate)

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
                errorsDict['device'] = u"This action cannot be applied to Hue Device Attribute Controllers. Please cancel the configuration dialog and select a Hue device to control."
                errorsDict['showAlertText'] += errorsDict['device'] + "\n\n"
            # If it is a valid device, check everything else.
            # Make sure this device can handle color temperature changes.
            elif not device.pluginProps.get('SupportsWhiteTemperature', False):
                isError = True
                errorsDict['device'] = u"The \"{}\" device does not support variable color temperature. Choose a different device." .format(device.name)
                errorsDict['showAlertText'] += errorsDict['device'] + "\n\n"

            # Validate that a Preset Color Recipe item or Custom was selected.
            if preset == False:
                isError = True
                errorsDict['preset'] = u"Please select an item from the Preset Color Recipe menu."
                errorsDict['showAlertText'] += errorsDict['preset'] + u"\n\n"
            elif preset == "custom":
                # Custom temperature and brightness.
                # Validate the temperature value.
                if temperatureSource == "custom":
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
                        errorsDict['temperature'] = u"Invalid Color Temperature value: {}".format(e)
                        errorsDict['showAlertText'] += errorsDict['temperature'] + u"\n\n"
                elif temperatureSource == "variable":
                    # Make sure the variable selection is valid.
                    if temperatureVariable == "":
                        isError = True
                        errorsDict['temperatureVariable'] = u"No source variable selected. Please select an Indigo variable from the list."
                        errorsDict['showAlertText'] += errorsDict['temperatureVariable'] + u"\n\n"
                    else:
                        # Since a variable ID was given, convert it to an integer.
                        temperatureVariable = int(temperatureVariable)
                # Validate the brightness value.
                if brightnessSource == "custom":
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
                        errorsDict['brightness'] = u"Invalid Brightness value: {}".format(e)
                        errorsDict['showAlertText'] += errorsDict['brightness'] + u"\n\n"
                elif brightnessSource == "variable":
                    # Make sure the variable selection is valid.
                    if brightnessVariable == "":
                        isError = True
                        errorsDict['brightnessVariable'] = u"No source variable selected. Please select an Indigo variable from the list."
                        errorsDict['showAlertText'] += errorsDict['brightnessVariable'] + u"\n\n"
                    else:
                        # Since a variable ID was given, convert it to an integer.
                        brightnessVariable = int(brightnessVariable)
                elif brightnessSource == "dimmer":
                    # Make sure the device selection is valid.
                    if brightnessDevice == "":
                        isError = True
                        errorsDict['brightnessDevice'] = u"No source device selected. Please select an Indigo dimmer device from the list."
                        errorsDict['showAlertText'] += errorsDict['brightnessDevice'] + u"\n\n"
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
                            errorsDict['rate'] = u"Ramp Rate must be a number between 0 and 540 seconds and can be in increments of 0.1 seconds."
                            errorsDict['showAlertText'] += errorsDict['rate'] + u"\n\n"
                    except ValueError:
                        isError = True
                        errorsDict['rate'] = u"Ramp Rate must be a number between 0 and 540 seconds and can be in increments of 0.1 seconds."
                        errorsDict['showAlertText'] += errorsDict['rate'] + u"\n\n"
                    except Exception, e:
                        isError = True
                        errorsDict['rate'] = u"Invalid Ramp Rate value: {}".format(e)
                        errorsDict['showAlertText'] += errorsDict['rate'] + u"\n\n"
            else:
                # User specified that they'd select a variable as the ramp rate source.
                # Make sure they actually selected one.
                if rateVariable == "":
                    isError = True
                    errorsDict['rateVariable'] = u"No variable was selected. Please select an Indigo variable as the ramp rate source."
                    errorsDict['showAlertText'] += errorsDict['rateVariable'] + u"\n\n"
                else:
                    # Since a variable ID was given, convert it to an integer.
                    rateVariable = int(rateVariable)

            # If there were no errors...
            if not isError:
                descString += u"set hue device color temperature to"
                if preset != "custom":
                    descString += u" preset color recipe \"{}\"".format(preset) 
                else:
                    if temperatureSource == "custom":
                        descString += u" custom value {}K".format(temperature)
                    elif temperatureSource == "variable":
                        descString += u" value in variable \"{}\"".format(indigo.variables[temperatureVariable].name)

                    if brightnessSource == "custom":
                        descString += u" at {} % brightness".format(brightness)
                    elif brightnessSource == "variable":
                        descString += u" using brightness value in variable \"{}\"".format(indigo.variables[brightnessVariable].name)
                    elif brightnessSource == "dimmer":
                        descString += u" using brightness of device \"{}\"".format(indigo.devices[brightnessDevice].name)

                if useRateVariable == True:
                    descString += u" using ramp rate in variable \"{}\"".format(indigo.variables[rateVariable].name)
                else:
                    if len(valuesDict.get('rate', "")) > 0:
                        descString += u" with ramp rate {} sec".format(rampRate) 

        ### EFFECT ###
        elif typeId == "effect":
            # First make sure this is a Hue device and not an attribute controller.
            if device.deviceTypeId == u"hueAttributeController":
                isError = True
                errorsDict['device'] = u"This action cannot be applied to Hue Device Attribute Controllers. Please cancel the configuration dialog and select a Hue device to control."
                errorsDict['showAlertText'] += errorsDict['device'] + "\n\n"
            # If it is a valid device, check everything else.
            # Make sure this device can handle the color effect.
            elif device.pluginProps.get('SupportsRGB', False) == False:
                isError = True
                errorsDict['device'] = u"The \"{}\" device does not support color effects. Choose a different device.".format(device.name)
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
            if device.deviceTypeId == u"hueAttributeController":
                isError = True
                errorsDict['device'] = u"This action cannot be applied to Hue Device Attribute Controllers. Please cancel the configuration dialog and select a Hue device to control."
                errorsDict['showAlertText'] += errorsDict['device'] + "\n\n"
            # If it is a valid device, check everything else.
            elif device.deviceTypeId in kLightDeviceTypeIDs:
                if type not in kCompatibleDeviceIDType:
                #if modelId not in kCompatibleDeviceIDs:
                    isError = True
                    errorsDict['device'] = u"The \"{}\" device is not a compatible Hue device. Please choose a different device.".format(device.name)
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
                descString = u"save hue device settings to preset {}".format(presetId)

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
                    errorsDict['rate'] = u"Invalid Ramp Rate value: {}".format(e)
                    errorsDict['showAlertText'] += errorsDict['rate'] + u"\n\n"

        ### RECALL PRESET ###
        elif typeId == "recallPreset":
            # First make sure this is a Hue device and not an attribute controller.
            if device.deviceTypeId == u"hueAttributeController":
                isError = True
                errorsDict['device'] = u"This action cannot be applied to Hue Device Attribute Controllers. Please cancel the configuration dialog and select a Hue device to control."
                errorsDict['showAlertText'] += errorsDict['device'] + "\n\n"
            # Make sure the model is a supported light model and the device is a light (as opposed to a sensor, etc).
            elif device.deviceTypeId not in kLightDeviceTypeIDs and device.deviceTypeId not in kGroupDeviceTypeIDs:
                isError = True
                errorsDict['device'] = u"The \"{}\" device is not a compatible Hue device. Please choose a Hue light or group device.".format(device.name)
                errorsDict['showAlertText'] += errorsDict['device'] + "\n\n"
            elif device.deviceTypeId in kLightDeviceTypeIDs and type not in kCompatibleDeviceIDType:
                isError = True
                errorsDict['device'] = u"The \"{}\" device is not a compatible Hue device. Please choose a Hue light or group device.".format(device.name)
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
                    descString = u"recall hue device settings from preset {}".format(presetId)

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
                    errorsDict['rate'] = u"Invalid Ramp Rate value: {}".format(e)
                    errorsDict['showAlertText'] += errorsDict['rate'] + u"\n\n"

        ### CATCH ALL ###
        else:
            isError = True
            errorsDict['presetId'] = u"The typeId \"{}\" wasn't recognized.".format(typeId)
            errorsDict['showAlertText'] += errorsDict['presetId'] + u"\n\n"

        # Define the description value.
        valuesDict['description'] = descString
        # Return an error if one exists.
        if isError:
            errorsDict['showAlertText'] = errorsDict['showAlertText'].strip()
            return (False, valuesDict, errorsDict)

        return (True, valuesDict)



    # set deflaut Preferences Configuration.
    ########################################
    def getPrefsConfigUiValues(self):
        valuesDict = indigo.Dict()

        self.debugLog(u'Starting  getPrefsConfigUiValues(self):')
        valuesDict['hubNumber'] = "0"
        valuesDict['address'] = self.ipAddresses['0']
        valuesDict['labelHostId'] = self.hostIds['0']
        valuesDict['ipvisible'] = False

        return super(Plugin, self).getPrefsConfigUiValues()


    # set hubnumber etc after button press 
    ########################################
    def selHubNumberCallback(self, valuesDict):
        self.debugLog(u"Starting selHubNumberCallback.")
        self.debugLog(u"selHubNumberCallback: Values passed:\n{}".format(valuesDict))
        self.debugLog(u"selHubNumberCallback: ipAddresses {}".format(self.ipAddresses))
        isError = False
        errorsDict = indigo.Dict()
        errorsDict['showAlertText'] = ""
        self.debugLog(u"selHubNumberCallback: selecthubNumber   {}".format(valuesDict['hubNumber']))
        self.debugLog(u"selHubNumberCallback: hubNumberSelected {}".format(self.hubNumberSelected))
        self.hubNumberSelected = valuesDict['hubNumber']

        valuesDict['ipvisible'] = True
        gwAction = valuesDict['gwAction']
        if gwAction == "delete":
            if self.hubNumberSelected in self.ipAddresses:
                del self.ipAddresses[self.hubNumberSelected]

            if self.hubNumberSelected in self.lightsDict:
                del self.lightsDict[self.hubNumberSelected]

            if self.hubNumberSelected in self.groupsDict:
                del self.groupsDict[self.hubNumberSelected]

            if self.hubNumberSelected in self.resourcesDict:
                del self.resourcesDict[self.hubNumberSelected]

            if self.hubNumberSelected in self.sensorsDict:
                del self.sensorsDict[self.hubNumberSelected]

            if self.hubNumberSelected in self.scenesDict:
                del self.scenesDict[self.hubNumberSelected]

            if self.hubNumberSelected in self.rulesDict:
                del self.rulesDict[self.hubNumberSelected]

            if self.hubNumberSelected in self.schedulesDict:
                del self.schedulesDict[self.hubNumberSelected]

            if self.hubNumberSelected in self.hueConfigDict:
                del self.hueConfigDict[self.hubNumberSelected]

            if self.hubNumberSelected != "0":
                valuesDict['address'] = self.ipAddresses['0']
                valuesDict['hostId'] = self.hostIds['0']
                valuesDict['hostIds'] = json.dumps(self.hostIds)
                valuesDict['hubNumber'] = "0"
                self.hubNumberSelected = "0"
            else:
               valuesDict['ipvisible'] = False
               valuesDict['address'] = ""
               valuesDict['hostId'] = ""
               valuesDict['hostIds'] = json.dumps(self.hostIds)
            
            return valuesDict

        if self.hubNumberSelected in self.ipAddresses:
            valuesDict['address'] = self.ipAddresses[self.hubNumberSelected]
            valuesDict['hostId'] = self.hostIds[self.hubNumberSelected]
            valuesDict['hostIds'] = json.dumps(self.hostIds)
        elif self.hubNumberSelected == "0":
            pass
        else:
            self.ipAddresses[self.hubNumberSelected] = ""
            self.paired[self.hubNumberSelected] = False
            self.hostIds[self.hubNumberSelected] = ""
            self.lightsDict[self.hubNumberSelected] = {}
            self.groupsDict[self.hubNumberSelected] = {}
            self.resourcesDict[self.hubNumberSelected] = {}
            self.sensorsDict[self.hubNumberSelected] = {}
            self.scenesDict[self.hubNumberSelected] = {}
            self.rulesDict[self.hubNumberSelected] = {}
            self.schedulesDict[self.hubNumberSelected] = {}
            self.hueConfigDict[self.hubNumberSelected] = {}

            valuesDict['hostIds'] = json.dumps(self.hostIds)
            valuesDict['address'] = ""
            valuesDict['hostId'] = ""
        return valuesDict


    # Validate Preferences Configuration.
    ########################################
    def validatePrefsConfigUi(self, valuesDict):
        self.debugLog(u"Starting validatePrefsConfigUi.")
        self.debugLog(u"validatePrefsConfigUi: Values passed:\n{}".format(valuesDict))
        isError = False
        errorsDict = indigo.Dict()
        errorsDict['showAlertText'] = ""

        maxPresetCount = valuesDict.get('maxPresetCount', "")

        # Validate the IP Address field.
        if valuesDict.get('address', "") == "":
            # The field was left blank.
            self.debugLog(u"validatePrefsConfigUi: IP address \"{}\" is blank.".format(valuesDict['address']) )
            isError = True
            errorsDict['address'] = u"The IP Address field is blank. Please enter an IP Address for the Hue bridge."
            errorsDict['showAlertText'] += errorsDict['address'] + u"\n\n"

        else:
            # The field wasn't blank. Check to see if the format is valid.
            try:
                # Try to format the IP Address as a 32-bit binary value. If this fails, the format was invalid.
                self.debugLog(u"validatePrefsConfigUi: Validating IP address \"{}\".".format(valuesDict['address']) )
                socket.inet_aton(valuesDict['address'])

            except socket.error:
                # IP Address format was invalid.
                self.debugLog(u"validatePrefsConfigUi: IP address format is invalid.")
                isError = True
                errorsDict['address'] = u"The IP Address is not valid. Please enter a valid IP address."
                errorsDict['showAlertText'] += errorsDict['address'] + u"\n\n"

        if maxPresetCount == "":
            # The field was left blank.
            self.debugLog(u"validatePrefsConfigUi: maxPresetCount was left blank. Setting value to 30.")
            maxPresetCount = "30"
            valuesDict['maxPresetCount'] = maxPresetCount
        else:
            # Make sure this is a valid number.
            try:
                maxPresetCount = int(maxPresetCount)
                if maxPresetCount < 1 or maxPresetCount > 100:
                    isError = True
                    errorsDict['maxPresetCount'] = u"Preset Memories must be a number between 1 and 100."
                    errorsDict['showAlertText'] += errorsDict['maxPresetCount'] + "\n\n"
            except ValueError:
                isError = True
                errorsDict['maxPresetCount'] = u"The Preset Memories must be a number between 1 and 100."
                errorsDict['showAlertText'] += errorsDict['maxPresetCount'] + "\n\n"
            except Exception, e:
                isError = True
                errorsDict['maxPresetCount'] = u"The Preset Memories must be a number between 1 and 100. Error: {}".format(e)
                errorsDict['showAlertText'] += errorsDict['maxPresetCount'] + "\n\n"

        # If there haven't been any errors so far, try to connect to the Hue bridge to see
        #   if it's actually a Hue bridge.
        if not isError:
            try:
                self.debugLog(u"validatePrefsConfigUi: Verifying that a Hue bridge exists at IP address \"{}\".".format(valuesDict['address']) )
                command = "http://{}/description.xml".format(valuesDict['address'])
                self.debugLog(u"validatePrefsConfigUi: Accessing URL: {}".format(command))
                r = requests.get(command, timeout=kTimeout)
                self.debugLog(u"validatePrefsConfigUi: Got response:\n{}".format(r.content) )

                # Quick and dirty check to see if this is a Philips Hue bridge.
                if "Philips hue bridge" not in r.content:
                    # If "Philips hue bridge" doesn't exist in the response, it's not a Hue bridge.
                    self.debugLog(u"validatePrefsConfigUi: No \"Philips hue bridge\" string found in response. This isn't a Hue bridge.")
                    isError = True
                    errorsDict['address'] = u"This doesn't appear to be a Philips Hue bridge.  Please verify the IP address."
                    errorsDict['showAlertText'] += errorsDict['address'] + u"\n\n"

                else:
                    # This is likely a Hue bridge.
                    self.debugLog(u"validatePrefsConfigUi: Verified that this is a Hue bridge.")

            except requests.exceptions.Timeout:
                self.debugLog(u"validatePrefsConfigUi: Connection to {} timed out after {} seconds.".format(valuesDict['address'], kTimeout))
                isError = True
                errorsDict['address'] = u"Unable to reach the bridge. Please check the IP address and ensure that the Indigo server and Hue bridge are connected to the network."
                errorsDict['showAlertText'] += errorsDict['address'] + u"\n\n"

            except requests.exceptions.ConnectionError:
                self.debugLog(u"validatePrefsConfigUi: Connection to {} failed. There was a connection error.".format(valuesDict['address']) )
                isError = True
                errorsDict['address'] = u"Connection error. Please check the IP address and ensure that the Indigo server and Hue bridge are connected to the network."
                errorsDict['showAlertText'] += errorsDict['address'] + u"\n\n"

            except Exception, e:
                self.debugLog(u"validatePrefsConfigUi: Connection error. {}".format(e))
                isError = True
                errorsDict['address'] = u"Connection error. Please check the IP address and ensure that the Indigo server and Hue bridge are connected to the network."
                errorsDict['showAlertText'] += errorsDict['address'] + u"\n\n"

        # Return an error if one exists.
        if isError:
            errorsDict['showAlertText'] = errorsDict['showAlertText'].strip()
            return (False, valuesDict, errorsDict)
        else:
            valuesDict['addresses'] = json.dumps(self.ipAddresses)
            return (True, valuesDict)

    # Plugin Configuration Dialog Closed
    ########################################
    def closedPrefsConfigUi(self, valuesDict, userCancelled):
        self.debugLog(u"closedPrefsConfigUi: Starting closedPrefsConfigUi.")

        # If the user didn't cancel the changes, take any needed actions as a result of the changes made.
        if not userCancelled:
            # Configuration was saved.


            self.pluginPrefs['addresses'] = json.dumps(self.ipAddresses)

            # If the number of Preset Memories was changed, add or remove Presets as needed.
            self.maxPresetCount = int(valuesDict.get('maxPresetCount', "30"))
            presets = self.pluginPrefs.get('presets', "")
            presetCount = len(presets)
            self.debugLog(u"closedPrefsConfigUi: pluginPrefs contains {} presets.".format(presetCount))
            # If there are fewer Presets in the prefs than the maxPresetCount, add the reset.
            if presetCount < self.maxPresetCount:
                indigo.server.log(u"Preset Memories number increased to {}.".format(self.maxPresetCount))
                self.debugLog(u"closedPrefsConfigUi: ... Adding {} presets to bring total to {}.".format(self.maxPresetCount - presetCount, self.maxPresetCount))
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
                indigo.server.log(u"... {} Presets added.  There are now {} Presets.".format(self.maxPresetCount - presetCount, self.maxPresetCount))
            # If there are more presets than are allowed by maxPresetCount, remove the extra Presets.
            elif presetCount > self.maxPresetCount:
                self.debugLog(u"closedPrefsConfigUi: ... Deleting the last {} Presets to bring the total to {}.".format(presetCount - self.maxPresetCount, self.maxPresetCount) )
                indigo.server.log(u"WARNING:  You've decreased the number of Preset Memories, so we're deleting the last {} Presets to bring the total to {}.  This cannot be undone.".format(presetCount - self.maxPresetCount, self.maxPresetCount) )
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
                            presetRate = self.pluginPrefs['presets'][presetId][2]
                            # Round the saved preset ramp rate to the nearest 10th.
                            presetRate = round(presetRate, 1)
                        except Exception, e:
                            # Key probably doesn't exist. Proceed as if no rate was saved.
                            presetRate = -1
                            pass

                        # Display the Preset data in the Indigo log.
                        logRampRate = u"{} sec".format(presetRate)
                        if presetRate == -1:
                            logRampRate = u"(none specified)"
                        indigo.server.log(u"... Preset {} ({}) has data. The following data will be deleted:\nRamp Rate: {}\n{}".format(aNumber + 1, presetName, logRampRate, presetData))
                    # Now delete the Preset.
                    del presets[aNumber]
                    indigo.server.log(u"... Preset {} deleted.".format(aNumber + 1) )

                # Replace the list of Presets in the prefs with the new list.
                self.pluginPrefs['presets'] = presets
                self.debugLog(u"closedPrefsConfigUi: pluginPrefs now contains {} Presets.".format(self.maxPresetCount) )

            # Update debug logging state.
            self.debug = valuesDict.get('showDebugInfo', False)
            # Make a note of what changed in the Indigo log.
            if self.debug:
                indigo.server.log("Debug logging enabled")
                self.plugin_file_handler.setLevel(logging.DEBUG) # Turn on for the plugin-specific log file
                self.debugLog(u"Turning on debug logging (due to plugin prefs being updated).")
            else:
                self.debugLog(u"Turning off debug logging (due to plugin prefs being updated).")
                indigo.server.log("Debug logging disabled")
                self.plugin_file_handler.setLevel(logging.INFO) # Turn off for the plugin-specific log file.


    # Did Device Communications Properties Change?
    ########################################
    #
    # Overriding default method to reduce the number of times a device
    #   automatically recreated by Indigo.
    #
    def didDeviceCommPropertyChange(self, origDev, newDev):
        # Automatically called by plugin host when device properties change.
        self.debugLog(u"Starting didDeviceCommPropertyChange.")
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
        self.debugLog(u"Starting getDeviceStateList for the \"{}\" device".format(device.name) )
        # Get the default state list (based on the Devices.xml file in the plugin).
        stateList = indigo.PluginBase.getDeviceStateList(self, device)
        # Only proceed to modify the state list if it isn't empty.
        if stateList is not None:
            # Modify the state list based on device type.
            # -- LightStrips --
            if device.deviceTypeId == "hueLightStrips" and device.configured:
                # Iterate through the default state list and remove states that aren't appropriate
                #    for this specific device's capabilities (based on device properties).
                self.debugLog(u"Modifying default hueLightStrips Indigo device states to reflect actual states supported by this specific Hue device.")
                while True:
                    for item in range (0, len (stateList)):
                        stateDict = stateList[item]
                        # Remove all color attributes if the device doesn't support any color.
                        if not device.pluginProps.get('SupportsColor', False):
                            if stateDict['Key'] in ['colorMode', 'colorMode.ui', 'colorTemp', 'colorTemp.ui', 'whiteLevel', 'whiteLevel.ui', 'whiteTemperature', 'whiteTemperature.ui', 'colorRed', 'colorRed.ui', 'colorGreen', 'colorGreen.ui', 'colorBlue', 'colorBlue.ui', 'colorX', 'colorX.ui', 'colorY', 'colorY.ui', 'hue', 'hue.ui', 'saturation', 'saturation.ui', 'redLevel', 'redLevel.ui', 'greenLevel', 'greenLevel.ui', 'blueLevel', 'blueLevel.ui']:
                                self.debugLog(u"\"{}\" does not support any color. Removing the \"{}\" state from the device.".format(device.name, stateDict['Key']) )
                                del stateList[item]
                                # Break out of the for loop to restart it with the new length of the stateList.
                                break

                        # Remove RGB color related states.
                        if not device.pluginProps.get('SupportsRGB', False):
                            if stateDict['Key'] in ['colorRed', 'colorRed.ui', 'colorGreen', 'colorGreen.ui', 'colorBlue', 'colorBlue.ui', 'colorX', 'colorX.ui', 'colorY', 'colorY.ui', 'hue', 'hue.ui', 'saturation', 'saturation.ui', 'redLevel', 'redLevel.ui', 'greenLevel', 'greenLevel.ui', 'blueLevel', 'blueLevel.ui']:
                                self.debugLog(u"\"{}\" does not support RGB color. Removing the \"{}\" state from the device.".format(device.name, stateDict['Key']) )
                                del stateList[item]
                                # Break out of the for loop to restart it with the new length of the stateList.
                                break

                        # Remove color temperature related states.
                        if not device.pluginProps.get('SupportsWhiteTemperature', False):
                            if stateDict['Key'] in ['colorTemp', 'colorTemp.ui', 'whiteLevel', 'whiteLevel.ui', 'whiteTemperature', 'whiteTemperature.ui']:
                                self.debugLog(u"\"{}\" does not support color temperature. Removing the \"{}\" state from the device.".format(device.name, stateDict['Key']) )
                                del stateList[item]
                                # Break out of the for loop to restart it with the new length of the stateList.
                                break

                    # If the for loop wasn't broken before all the items were tested, then all states
                    #    that should be removed have been and we can break out of the while loop.
                    if item == len (stateList) - 1:
                        break

            # The below commented out lines are an example of how to add states if needed.
            ## if SomeOtherDeviceCondition:
                ## someNumState = self.getDeviceStateDictForNumberType(u"someNumState", u"Some Level Label", u"Some Level Label")
                ## someStringState = self.getDeviceStateDictForStringType(u"someStringState", u"Some Level Label", u"Some Level Label")
                ## someOnOffBoolState = self.getDeviceStateDictForBoolOnOffType(u"someOnOffBoolState", u"Some Level Label", u"Some Level Label")
                ## someYesNoBoolState = self.getDeviceStateDictForBoolYesNoType(u"someYesNoBoolState", u"Some Level Label", u"Some Level Label")
                ## someOneZeroBoolState = self.getDeviceStateDictForBoolOneZeroType(u"someOneZeroBoolState", u"Some Level Label", u"Some Level Label")
                ## someTrueFalseBoolState = self.getDeviceStateDictForBoolTrueFalseType(u"someTrueFalseBoolState", u"Some Level Label", u"Some Level Label")
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
            self.debugLog(u"Starting actionControlDimmerRelay for device {}. action: {}\n\ndevice: {}".format(device.name, action, device))
        except Exception, e:
            self.debugLog(u"Starting actionControlDimmerRelay for device {}. (Unable to display action or device data due to error: {})".format(device.name , e))
        # Get the current brightness (if it's not an on/off only device) and on/off state of the device.
        if device.deviceTypeId != "hueOnOffDevice":
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
            hubNumber, ipAddress, hostId, paired = self.getIdsFromDevice(device)
            self.debugLog(u"Command is {}, Bulb is {}".format(command, bulbId))

            ##### TURN ON #####
            if command == indigo.kDeviceAction.TurnOn:
                try:
                    self.debugLog(u"device on:\n{}".format(action))
                except Exception, e:
                    self.debugLog(u"device on: (Unable to display action data due to error: {})".format(e))
                # Turn it on.
                self.doOnOff(device, True)

            ##### TURN OFF #####
            elif command == indigo.kDeviceAction.TurnOff:
                try:
                    self.debugLog(u"device off:\n{}".format(action))
                except Exception, e:
                    self.debugLog(u"device off: (Unable to display action data due to error: {})".format(e))
                # Turn it off by setting the brightness to minimum.
                self.doOnOff(device, False)

            ##### TOGGLE #####
            elif command == indigo.kDeviceAction.Toggle:
                try:
                    self.debugLog(u"device toggle:\n{}".format(action) )
                except Exception, e:
                    self.debugLog(u"device toggle: (Unable to display action due to error: {})".format(e))
                if currentOnState == True:
                    # It's on. Turn it off.
                    self.doOnOff(device, False)
                else:
                    # It's off. Turn it on.
                    self.doOnOff(device, True)

            ##### SET BRIGHTNESS #####
            elif command == indigo.kDeviceAction.SetBrightness:
                try:
                    self.debugLog(u"device set brightness:\n{}".format(action) )
                except Exception, e:
                    self.debugLog(u"device set brightness: (Unable to display action data due to error: {})".format(e))
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
                    self.debugLog(u"device increase brightness by:\n{}".format(action) )
                except Exception, e:
                    self.debugLog(u"device increase brightness by: (Unable to display action data due to error: {})".format(e))
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
                    self.debugLog(u"device decrease brightness by:\n{}".format(action) )
                except Exception, e:
                    self.debugLog(u"device decrease brightness by: (Unable to display action data due to error: {})".format(e))
                brightnessLevel = currentBrightness - action.actionValue
                if brightnessLevel < 0:
                    brightnessLevel = 0
                # Save the new brightness level into the device properties.
                tempProps = device.pluginProps
                tempProps['savedBrightness'] = int(round(brightnessLevel / 100.0 * 255.0))
                self.updateDeviceProps(device, tempProps)
                # Set the new brightness level on the bulb.
                self.doBrightness(device, int(round(brightnessLevel / 100.0 * 255.0)))

            ##### SET COLOR LEVELS #####
            elif command == indigo.kDimmerRelayAction.SetColorLevels:
                try:
                    self.debugLog(u"device request status:\n{}".format(action))
                except Exception, e:
                    self.debugLog(u"device request status: (Unable to display action data due to error: {})".format(e))

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
                self.debugLog(u"actionControlDimmerRelay: Detected color change values of redLevel: {}, greenLevel: {}, blueLevel: {}, whiteLevel: {}, whiteTemperature: {}.".format(redLevel, greenLevel, blueLevel, whiteLevel, colorTemp))
                # The "Set RGBW Levels" action in Indigo 7.0 can have Red, Green, Blue and White levels, as well as
                #   White Temperature for devices that support both RGB and White levels (even if the device doesn't
                #   support simultaneous RGB and W settings).  We have to, therefor, make assumptions based on which
                #   keys are passed and what values are in those keys.
                #
                # Start with whiteTemperature.  If it was the only key passed, the user is making changes to the
                #   light via the Indigo UI.
                if actionColorVals.get('whiteTemperature', None) is not None:
                    self.debugLog(u"actionControlDimmerRelay: whiteTemperature is not empty.")
                    if actionColorVals.get('whiteLevel', None) is None and actionColorVals.get('redLevel', None) is None and actionColorVals.get('greenLevel', None) is None and actionColorVals.get('blueLevel', None) is None:
                        self.debugLog(u"actionControlDimmerRelay: red, green, blue and white levels are all empty")
                        # Since the whiteLevel was not sent, use the existing brightness as the whiteLevel.
                        self.doColorTemperature(device, colorTemp, int(round(currentBrightness / 100.0 * 255.0)))
                    # If both whiteTemperature and whiteLevel keys were sent at the same time, the Indigo Set RGBW
                    #    Levels action is being used, in which case, we still want to use the color temperature method,
                    #    but use the whiteLevel as the brightness instead of the current brightness if it's over zero.
                    elif actionColorVals.get('whiteLevel', None) is not None and float(actionColorVals.get('whiteLevel')) > 0:
                        self.debugLog(u"actionControlDimmerRelay: whiteLevel is not empty and is greater than zero")
                        self.doColorTemperature(device, colorTemp, whiteLevel)
                    # Otherwise, use RGB to set the color of the light.
                    else:
                        self.debugLog(u"actionControlDimmerRelay: using RGB to change device color.")
                        self.doRGB(device, redLevel, greenLevel, blueLevel)
                # Now see if we're only being sent whiteLevel.  If so, the White level slider in the Indigo UI is being
                #   used.  Treat the white level like an inverse saturation slider (100 = zero saturation).
                elif actionColorVals.get('whiteLevel', None) is not None and actionColorVals.get('redLevel', None) is None and actionColorVals.get('greenLevel', None) is None and actionColorVals.get('blueLevel', None) is None:
                    self.debugLog(u"actionControlDimmerRelay: whiteLevel is not empty, but red, green and blue levels are.")
                    newSaturation = 255 - whiteLevel
                    if newSaturation < 0:
                        newSaturation = 0
                    self.doHSB(device, device.states['hue'], newSaturation, int(round(currentBrightness / 100.0 * 255.0)))
                # If we're not changing color temperature or saturation (white level), use RGB.
                else:
                    self.debugLog(u"actionControlDimmerRelay: using RGB to change device color.")
                    self.doRGB(device, redLevel, greenLevel, blueLevel)

            ##### REQUEST STATUS #####
            elif command == indigo.kDeviceAction.RequestStatus:
                try:
                    self.debugLog(u"device request status:\n{}".format(action) )
                except Exception, e:
                    self.debugLog(u"device request status: (Unable to display action data due to error: {})".format(e))
                self.getBulbStatus(device.id)
                # Log the new brightnss.
                indigo.server.log(u"\"{}\" status request (received: {})".format( device.name, device.states['brightnessLevel']), 'Sent Hue Lights')

            #### CATCH ALL #####
            else:
                indigo.server.log(u"Unhandled command \"{}\"".format(command))
            pass

        #
        # -- Hue Ambiance --
        #
        if device.deviceTypeId == "hueAmbiance":
            bulbId = device.pluginProps.get('bulbId', None)
            hubNumber, ipAddress, hostId, paired = self.getIdsFromDevice(device)
            self.debugLog(u"Command is {}, Bulb is {}".format(command, bulbId))

            ##### TURN ON #####
            if command == indigo.kDeviceAction.TurnOn:
                try:
                    self.debugLog(u"device on:\n{}".format(action) )
                except Exception, e:
                    self.debugLog(u"device on: (Unable to display action data due to error: {})".format(e))
                # Turn it on.
                self.doOnOff(device, True)

            ##### TURN OFF #####
            elif command == indigo.kDeviceAction.TurnOff:
                try:
                    self.debugLog(u"device off:\n{}".format(action) )
                except Exception, e:
                    self.debugLog(u"device off: (Unable to display action data due to error: {})".format(e))
                # Turn it off by setting the brightness to minimum.
                self.doOnOff(device, False)

            ##### TOGGLE #####
            elif command == indigo.kDeviceAction.Toggle:
                try:
                    self.debugLog(u"device toggle:\n{}".format(action) )
                except Exception, e:
                    self.debugLog(u"device toggle: (Unable to display action due to error: {})".format(e))
                if currentOnState == True:
                    # It's on. Turn it off.
                    self.doOnOff(device, False)
                else:
                    # It's off. Turn it on.
                    self.doOnOff(device, True)

            ##### SET BRIGHTNESS #####
            elif command == indigo.kDeviceAction.SetBrightness:
                try:
                    self.debugLog(u"device set brightness:\n{}".format(action) )
                except Exception, e:
                    self.debugLog(u"device set brightness: (Unable to display action data due to error: {})".format(e))
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
                    self.debugLog(u"device increase brightness by:\n{}".format(action) )
                except Exception, e:
                    self.debugLog(u"device increase brightness by: (Unable to display action data due to error: {})".format(e))
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
                    self.debugLog(u"device decrease brightness by:\n{}".format(action) )
                except Exception, e:
                    self.debugLog(u"device decrease brightness by: (Unable to display action data due to error: {})".format(e))
                brightnessLevel = currentBrightness - action.actionValue
                if brightnessLevel < 0:
                    brightnessLevel = 0
                # Save the new brightness level into the device properties.
                tempProps = device.pluginProps
                tempProps['savedBrightness'] = int(round(brightnessLevel / 100.0 * 255.0))
                self.updateDeviceProps(device, tempProps)
                # Set the new brightness level on the bulb.
                self.doBrightness(device, int(round(brightnessLevel / 100.0 * 255.0)))

            ##### SET COLOR LEVELS #####
            elif command == indigo.kDimmerRelayAction.SetColorLevels:
                try:
                    self.debugLog(u"device request status:\n{}".format(action) )
                except Exception, e:
                    self.debugLog(u"device request status: (Unable to display action data due to error: {})".format(e))

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
                self.debugLog(u"actionControlDimmerRelay: Detected color change values of redLevel: {}, greenLevel: {}, blueLevel: {}, whiteLevel: {}, whiteTemperature: {}.".format(redLevel, greenLevel, blueLevel, whiteLevel, colorTemp))
                # The "Set RGBW Levels" action in Indigo 7.0 can have Red, Green, Blue and White levels, as well as
                #   White Temperature for devices that support both RGB and White levels (even if the device doesn't
                #   support simultaneous RGB and W settings).  We have to, therefor, make assumptions based on which
                #   keys are passed and what values are in those keys.
                #
                # Start with whiteTemperature.  If it was the only key passed, the user is making changes to the
                #   light via the Indigo UI.
                if actionColorVals.get('whiteTemperature', None) is not None:
                    self.debugLog(u"actionControlDimmerRelay: whiteTemperature is not empty.")
                    if actionColorVals.get('whiteLevel', None) is None:
                        self.debugLog(u"actionControlDimmerRelay: white level is empty")
                        # Since the whiteLevel was not sent, use the existing brightness as the whiteLevel.
                        self.doColorTemperature(device, colorTemp, int(round(currentBrightness / 100.0 * 255.0)))
                    # If both whiteTemperature and whiteLevel keys were sent at the same time, it must be a Python
                    #    script call, in which case, we still want to use the color temperature method, but use
                    #    the whiteLevel as the brightness instead of the current brightness if it's over zero.
                    else:
                        if float(actionColorVals.get('whiteLevel', 0)) > 0:
                            self.debugLog(u"actionControlDimmerRelay: whiteLevel is not empty and is greater than zero.")
                            self.doColorTemperature(device, colorTemp, whiteLevel)
                        else:
                            # A whiteLevel of 0 (or lower) is the same as a brightness of 0. Turn off the light.
                            self.debugLog(u"actionControlDimmerRelay: whiteLevel is not empty but is equal to zero.")
                            self.doOnOff(device, False)
                # Now see if we're only being sent whiteLevel.  If so, the White level slider in the Indigo UI is being
                #   used.  Treat the white level like the brightness level for ambiance lights.
                elif actionColorVals.get('whiteLevel', None) is not None:
                    self.debugLog(u"actionControlDimmerRelay: whiteTemperature is empty but whiteLevel is not empty.")
                    # Save the new brightness level into the device properties.
                    tempProps = device.pluginProps
                    tempProps['savedBrightness'] = int(round(actionColorVals.get('whiteLevel', 0) / 100.0 * 255.0))
                    self.updateDeviceProps(device, tempProps)
                    # Set the new brightness level on the bulb.
                    self.doBrightness(device, int(round(actionColorVals.get('whiteLevel', 0) / 100.0 * 255.0)))

            ##### REQUEST STATUS #####
            elif command == indigo.kDeviceAction.RequestStatus:
                try:
                    self.debugLog(u"device request status:\n{}".format(action) )
                except Exception, e:
                    self.debugLog(u"device request status: (Unable to display action data due to error: {})".format(e))
                self.getBulbStatus(device.id)
                # Log the new brightnss.
                indigo.server.log(u"\"{}\" status request (received: {})".format( device.name, device.states['brightnessLevel']), 'Sent Hue Lights')

            #### CATCH ALL #####
            else:
                indigo.server.log(u"Unhandled command \"{}\"".format(command))
            pass

        #
        # -- Light Strips --
        #
        elif device.deviceTypeId == "hueLightStrips":
            bulbId = device.pluginProps.get('bulbId', None)
            hubNumber, ipAddress, hostId, paired = self.getIdsFromDevice(device)
            self.debugLog(u"Command is {}, Light Strip device is {}".format(command, bulbId))

            ##### TURN ON #####
            if command == indigo.kDeviceAction.TurnOn:
                try:
                    self.debugLog(u"device on:\n{}".format(action) )
                except Exception, e:
                    self.debugLog(u"device on: (Unable to display action data due to error: {})".format(e))
                # Turn it on.
                self.doOnOff(device, True)

            ##### TURN OFF #####
            elif command == indigo.kDeviceAction.TurnOff:
                try:
                    self.debugLog(u"device off:\n{}".format(action) )
                except Exception, e:
                    self.debugLog(u"device off: (Unable to display action data due to error: {})".format(e))
                # Turn it off by setting the brightness to minimum.
                self.doOnOff(device, False)

            ##### TOGGLE #####
            elif command == indigo.kDeviceAction.Toggle:
                try:
                    self.debugLog(u"device toggle:\n{}".format(action) )
                except Exception, e:
                    self.debugLog(u"device toggle: (Unable to display action due to error: {})".format(e))
                if currentOnState == True:
                    # It's on. Turn it off.
                    self.doOnOff(device, False)
                else:
                    # It's off. Turn it on.
                    self.doOnOff(device, True)

            ##### SET BRIGHTNESS #####
            elif command == indigo.kDeviceAction.SetBrightness:
                try:
                    self.debugLog(u"device set brightness:\n{}".format(action) )
                except Exception, e:
                    self.debugLog(u"device set brightness: (Unable to display action data due to error: {})".format(e))
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
                    self.debugLog(u"device increase brightness by:\n{}".format(action) )
                except Exception, e:
                    self.debugLog(u"device increase brightness by: (Unable to display action data due to error: {})".format(e))
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
                    self.debugLog(u"device decrease brightness by:\n{}".format(action) )
                except Exception, e:
                    self.debugLog(u"device decrease brightness by: (Unable to display action data due to error: {})".format(e))
                brightnessLevel = currentBrightness - action.actionValue
                if brightnessLevel < 0:
                    brightnessLevel = 0
                # Save the new brightness level into the device properties.
                tempProps = device.pluginProps
                tempProps['savedBrightness'] = int(round(brightnessLevel / 100.0 * 255.0))
                self.updateDeviceProps(device, tempProps)
                # Set the new brightness level on the device.
                self.doBrightness(device, int(round(brightnessLevel / 100.0 * 255.0)))

            ##### SET COLOR LEVELS #####
            elif command == indigo.kDimmerRelayAction.SetColorLevels:
                try:
                    self.debugLog(u"device request status:\n{}".format(action) )
                except Exception, e:
                    self.debugLog(u"device request status: (Unable to display action data due to error: {})".format(e))

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
                self.debugLog(u"actionControlDimmerRelay: Detected color change values of redLevel: {}, greenLevel: {}, blueLevel: {}, whiteLevel: {}, whiteTemperature: {}.".format(redLevel, greenLevel, blueLevel, whiteLevel, colorTemp))
                # The "Set RGBW Levels" action in Indigo 7.0 can have Red, Green, Blue and White levels, as well as
                #   White Temperature for devices that support both RGB and White levels (even if the device doesn't
                #   support simultaneous RGB and W settings).  We have to, therefor, make assumptions based on which
                #   keys are passed and what values are in those keys.
                #
                # Start with whiteTemperature.  If it was the only key passed, the user is making changes to the
                #   light via the Indigo UI.
                if actionColorVals.get('whiteTemperature', None) is not None:
                    self.debugLog(u"actionControlDimmerRelay: whiteTemperature is not empty.")
                    if actionColorVals.get('whiteLevel', None) is None and actionColorVals.get('redLevel', None) is None and actionColorVals.get('greenLevel', None) is None and actionColorVals.get('blueLevel', None) is None:
                        self.debugLog(u"actionControlDimmerRelay: red, green, blue and white levels are all empty")
                        # Since the whiteLevel was not sent, use the existing brightness as the whiteLevel.
                        if device.supportsWhiteTemperature:
                            self.doColorTemperature(device, colorTemp, int(round(currentBrightness / 100.0 * 255.0)))
                        else:
                            errorText = u"The \"" + device.nsame + u"\" device does not support color temperature. The requested change was not applied."
                            self.errorLog(errorText)
                            # Remember the error.
                            self.lastErrorMessage = errorText
                    # If both whiteTemperature and whiteLevel keys were sent at the same time, the Indigo Set RGBW
                    #    Levels action is being used, in which case, we still want to use the color temperature method,
                    #    but use the whiteLevel as the brightness instead of the current brightness if it's over zero.
                    elif actionColorVals.get('whiteLevel', None) is not None and float(actionColorVals.get('whiteLevel')) > 0:
                        self.debugLog(u"actionControlDimmerRelay: whiteLevel is not empty and is greater than zero")
                        if device.supportsWhiteTemperature:
                            self.doColorTemperature(device, colorTemp, whiteLevel)
                        else:
                            errorText = u"The \"" + device.nsame + u"\" device does not support color temperature. The requested change was not applied."
                            self.errorLog(errorText)
                            # Remember the error.
                            self.lastErrorMessage = errorText
                    # Otherwise, use RGB to set the color of the light.
                    else:
                        self.debugLog(u"actionControlDimmerRelay: using RGB to change device color.")
                        self.doRGB(device, redLevel, greenLevel, blueLevel)
                # Now see if we're only being sent whiteLevel.  If so, the White level slider in the Indigo UI is being
                #   used.  Treat the white level like an inverse saturation slider (100 = zero saturation).
                elif actionColorVals.get('whiteLevel', None) is not None and actionColorVals.get('redLevel', None) is None and actionColorVals.get('greenLevel', None) is None and actionColorVals.get('blueLevel', None) is None:
                    self.debugLog(u"actionControlDimmerRelay: whiteLevel is not empty, but red, green and blue levels are.")
                    newSaturation = 255 - whiteLevel
                    if newSaturation < 0:
                        newSaturation = 0
                    self.doHSB(device, device.states['hue'], newSaturation, int(round(currentBrightness / 100.0 * 255.0)))
                # If we're not changing color temperature or saturation (white level), use RGB.
                else:
                    self.debugLog(u"actionControlDimmerRelay: using RGB to change device color.")
                    self.doRGB(device, redLevel, greenLevel, blueLevel)

            ##### REQUEST STATUS #####
            elif command == indigo.kDeviceAction.RequestStatus:
                try:
                    self.debugLog(u"device request status:\n{}".format(action) )
                except Exception, e:
                    self.debugLog(u"device request status: (Unable to display action data due to error: {})".format(e))
                self.getBulbStatus(device.id)
                # Log the new brightnss.
                indigo.server.log(u"\"{}\" status request (received: {})".format( device.name, device.states['brightnessLevel']), 'Sent Hue Lights')

            #### CATCH ALL #####
            else:
                indigo.server.log(u"Unhandled command \"{}\"" .format(command))
            pass

        #
        # -- LivingColors Bloom --
        #
        elif device.deviceTypeId == "hueLivingColorsBloom":
            bulbId = device.pluginProps.get('bulbId', None)
            hubNumber, ipAddress, hostId, paired = self.getIdsFromDevice(device)
            self.debugLog(u"Command is {}, LivingColors Bloom device is {}".format(command, bulbId))

            ##### TURN ON #####
            if command == indigo.kDeviceAction.TurnOn:
                try:
                    self.debugLog(u"device on:\n{}".format(action) )
                except Exception, e:
                    self.debugLog(u"device on: (Unable to display action data due to error: {})".format(e))
                # Turn it on.
                self.doOnOff(device, True)

            ##### TURN OFF #####
            elif command == indigo.kDeviceAction.TurnOff:
                try:
                    self.debugLog(u"device off:\n{}".format(action) )
                except Exception, e:
                    self.debugLog(u"device off: (Unable to display action data due to error: {})".format(e))
                # Turn it off by setting the brightness to minimum.
                self.doOnOff(device, False)

            ##### TOGGLE #####
            elif command == indigo.kDeviceAction.Toggle:
                try:
                    self.debugLog(u"device toggle:\n{}".format(action) )
                except Exception, e:
                    self.debugLog(u"device toggle: (Unable to display action due to error: {})".format(e))
                if currentOnState == True:
                    # It's on. Turn it off.
                    self.doOnOff(device, False)
                else:
                    # It's off. Turn it on.
                    self.doOnOff(device, True)

            ##### SET BRIGHTNESS #####
            elif command == indigo.kDeviceAction.SetBrightness:
                try:
                    self.debugLog(u"device set brightness:\n{}".format(action) )
                except Exception, e:
                    self.debugLog(u"device set brightness: (Unable to display action data due to error: {})".format(e))
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
                    self.debugLog(u"device increase brightness by:\n{}".format(action) )
                except Exception, e:
                    self.debugLog(u"device increase brightness by: (Unable to display action data due to error: {})".format(e))
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
                    self.debugLog(u"device decrease brightness by:\n{}".format(action) )
                except Exception, e:
                    self.debugLog(u"device decrease brightness by: (Unable to display action data due to error: {})".format(e))
                brightnessLevel = currentBrightness - action.actionValue
                if brightnessLevel < 0:
                    brightnessLevel = 0
                # Save the new brightness level into the device properties.
                tempProps = device.pluginProps
                tempProps['savedBrightness'] = int(round(brightnessLevel / 100.0 * 255.0))
                self.updateDeviceProps(device, tempProps)
                # Set the new brightness level on the device.
                self.doBrightness(device, int(round(brightnessLevel / 100.0 * 255.0)))

            ##### SET COLOR LEVELS #####
            elif command == indigo.kDimmerRelayAction.SetColorLevels:
                try:
                    self.debugLog(u"device request status:\n{}".format(action) )
                except Exception, e:
                    self.debugLog(u"device request status: (Unable to display action data due to error: {})".format(e))

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
                self.debugLog(u"actionControlDimmerRelay: Detected color change values of redLevel: {}, greenLevel: {}, blueLevel: {}, whiteLevel: {}, whiteTemperature: {}.".format(redLevel, greenLevel, blueLevel, whiteLevel, colorTemp))
                # The "Set RGBW Levels" action in Indigo 7.0 can have Red, Green, Blue and White levels, as well as
                #   White Temperature for devices that support both RGB and White levels (even if the device doesn't
                #   support simultaneous RGB and W settings).  We have to, therefor, make assumptions based on which
                #   keys are passed and what values are in those keys.
                #
                # Start with whiteTemperature.  If it was the only key passed, the user is making changes to the
                #   light via the Indigo UI.
                if actionColorVals.get('whiteTemperature', None) is not None:
                    self.debugLog(u"actionControlDimmerRelay: whiteTemperature is not empty.")
                    if actionColorVals.get('whiteLevel', None) is None and actionColorVals.get('redLevel', None) is None and actionColorVals.get('greenLevel', None) is None and actionColorVals.get('blueLevel', None) is None:
                        self.debugLog(u"actionControlDimmerRelay: red, green, blue and white levels are all empty")
                        # Since the whiteLevel was not sent, use the existing brightness as the whiteLevel.
                        if device.supportsWhiteTemperature:
                            self.doColorTemperature(device, colorTemp, int(round(currentBrightness / 100.0 * 255.0)))
                        else:
                            errorText = u"The \"" + device.nsame + u"\" device does not support color temperature. The requested change was not applied."
                            self.errorLog(errorText)
                            # Remember the error.
                            self.lastErrorMessage = errorText
                    # If both whiteTemperature and whiteLevel keys were sent at the same time, the Indigo Set RGBW
                    #    Levels action is being used, in which case, we still want to use the color temperature method,
                    #    but use the whiteLevel as the brightness instead of the current brightness if it's over zero.
                    elif actionColorVals.get('whiteLevel', None) is not None and float(actionColorVals.get('whiteLevel')) > 0:
                        self.debugLog(u"actionControlDimmerRelay: whiteLevel is not empty and is greater than zero")
                        if device.supportsWhiteTemperature:
                            self.doColorTemperature(device, colorTemp, whiteLevel)
                        else:
                            errorText = u"The \"" + device.nsame + u"\" device does not support color temperature. The requested change was not applied."
                            self.errorLog(errorText)
                            # Remember the error.
                            self.lastErrorMessage = errorText
                    # Otherwise, use RGB to set the color of the light.
                    else:
                        self.debugLog(u"actionControlDimmerRelay: using RGB to change device color.")
                        self.doRGB(device, redLevel, greenLevel, blueLevel)
                # Now see if we're only being sent whiteLevel.  If so, the White level slider in the Indigo UI is being
                #   used.  Treat the white level like an inverse saturation slider (100 = zero saturation).
                elif actionColorVals.get('whiteLevel', None) is not None and actionColorVals.get('redLevel', None) is None and actionColorVals.get('greenLevel', None) is None and actionColorVals.get('blueLevel', None) is None:
                    self.debugLog(u"actionControlDimmerRelay: whiteLevel is not empty, but red, green and blue levels are.")
                    newSaturation = 255 - whiteLevel
                    if newSaturation < 0:
                        newSaturation = 0
                    self.doHSB(device, device.states['hue'], newSaturation, int(round(currentBrightness / 100.0 * 255.0)))
                # If we're not changing color temperature or saturation (white level), use RGB.
                else:
                    self.debugLog(u"actionControlDimmerRelay: using RGB to change device color.")
                    self.doRGB(device, redLevel, greenLevel, blueLevel)

            ##### REQUEST STATUS #####
            elif command == indigo.kDeviceAction.RequestStatus:
                try:
                    self.debugLog(u"device request status:\n{}".format(action) )
                except Exception, e:
                    self.debugLog(u"device request status: (Unable to display action data due to error: {})".format(e))
                self.getBulbStatus(device.id)
                # Log the new brightnss.
                indigo.server.log(u"\"{}\" status request (received: {})".format( device.name, device.states['brightnessLevel']), 'Sent Hue Lights')

            #### CATCH ALL #####
            else:
                indigo.server.log(u"Unhandled command \"{}\"" .format(command))
            pass

        #
        # -- LivingWhites --
        #
        elif device.deviceTypeId == "hueLivingWhites":
            bulbId = device.pluginProps.get('bulbId', None)
            hubNumber, ipAddress, hostId, paired = self.getIdsFromDevice(device)
            self.debugLog(u"Command is {}, LivingWhites device is {}".format(command, bulbId))

            ##### TURN ON #####
            if command == indigo.kDeviceAction.TurnOn:
                try:
                    self.debugLog(u"device on:\n{}".format(action) )
                except Exception, e:
                    self.debugLog(u"device on: (Unable to display action data due to error: {})".format(e))
                # Turn it on.
                self.doOnOff(device, True)

            ##### TURN OFF #####
            elif command == indigo.kDeviceAction.TurnOff:
                try:
                    self.debugLog(u"device off:\n{}".format(action) )
                except Exception, e:
                    self.debugLog(u"device off: (Unable to display action data due to error: {})".format(e))
                # Turn it off by setting the brightness to minimum.
                self.doOnOff(device, False)

            ##### TOGGLE #####
            elif command == indigo.kDeviceAction.Toggle:
                try:
                    self.debugLog(u"device toggle:\n{}".format(action) )
                except Exception, e:
                    self.debugLog(u"device toggle: (Unable to display action due to error: {})".format(e))
                if currentOnState == True:
                    # It's on. Turn it off.
                    self.doOnOff(device, False)
                else:
                    # It's off. Turn it on.
                    self.doOnOff(device, True)

            ##### SET BRIGHTNESS #####
            elif command == indigo.kDeviceAction.SetBrightness:
                try:
                    self.debugLog(u"device set brightness:\n{}".format(action) )
                except Exception, e:
                    self.debugLog(u"device set brightness: (Unable to display action data due to error: {})".format(e))
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
                    self.debugLog(u"device increase brightness by:\n{}".format(action) )
                except Exception, e:
                    self.debugLog(u"device increase brightness by: (Unable to display action data due to error: {})".format(e))
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
                    self.debugLog(u"device decrease brightness by:\n{}".format(action) )
                except Exception, e:
                    self.debugLog(u"device decrease brightness by: (Unable to display action data due to error: {})".format(e))
                brightnessLevel = currentBrightness - action.actionValue
                if brightnessLevel < 0:
                    brightnessLevel = 0
                # Save the new brightness level into the device properties.
                tempProps = device.pluginProps
                tempProps['savedBrightness'] = int(round(brightnessLevel / 100.0 * 255.0))
                self.updateDeviceProps(device, tempProps)
                # Set the new brightness level on the device.
                self.doBrightness(device, int(round(brightnessLevel / 100.0 * 255.0)))

            ##### SET COLOR LEVELS #####
            elif command == indigo.kDimmerRelayAction.SetColorLevels:
                # This command should never be sent to this type of device because
                #   the LivingWhites devices shouldn't be defined as supporting color
                #   or variable color temperature.  But if, for some reason, they are,
                #   the code below should handle the call.
                try:
                    self.debugLog(u"device request status:\n{}".format(action) )
                except Exception, e:
                    self.debugLog(u"device request status: (Unable to display action data due to error: {})".format(e))

                errorText = u"The \"" + device.nsame + u"\" device does not support color. The requested change was not applied."
                self.errorLog(errorText)
                # Remember the error.
                self.lastErrorMessage = errorText

            ##### REQUEST STATUS #####
            elif command == indigo.kDeviceAction.RequestStatus:
                try:
                    self.debugLog(u"device request status:\n{}".format(action) )
                except Exception, e:
                    self.debugLog(u"device request status: (Unable to display action data due to error: {})".format(e))
                self.getBulbStatus(device.id)
                # Log the new brightnss.
                indigo.server.log(u"\"{}\" status request (received: {})".format( device.name, device.states['brightnessLevel']), 'Sent Hue Lights')

        #
        # -- On/Off Only Device --
        #
        elif device.deviceTypeId == "hueOnOffDevice":
            bulbId = device.pluginProps.get('bulbId', None)
            hubNumber, ipAddress, hostId, paired = self.getIdsFromDevice(device)
            self.debugLog(u"Command is {}, On/Off device is {}".format(command, bulbId))

            ##### TURN ON #####
            if command == indigo.kDeviceAction.TurnOn:
                try:
                    self.debugLog(u"device on:\n{}".format(action) )
                except Exception, e:
                    self.debugLog(u"device on: (Unable to display action data due to error: {})".format(e))
                # Turn it on.
                self.doOnOff(device, True)

            ##### TURN OFF #####
            elif command == indigo.kDeviceAction.TurnOff:
                try:
                    self.debugLog(u"device off:\n{}".format(action) )
                except Exception, e:
                    self.debugLog(u"device off: (Unable to display action data due to error: {})".format(e))
                # Turn it off by setting the brightness to minimum.
                self.doOnOff(device, False)

            ##### TOGGLE #####
            elif command == indigo.kDeviceAction.Toggle:
                try:
                    self.debugLog(u"device toggle:\n{}".format(action) )
                except Exception, e:
                    self.debugLog(u"device toggle: (Unable to display action due to error: {})".format(e))
                if currentOnState == True:
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
                    self.debugLog(u"device set brightness:\n{}".format(action) )
                except Exception, e:
                    self.debugLog(u"device set brightness: (Unable to display action data due to error: {})".format(e))
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
                    self.debugLog(u"device increase brightness by:\n{}".format(action) )
                except Exception, e:
                    self.debugLog(u"device increase brightness by: (Unable to display action data due to error: {})".format(e))
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
                    self.debugLog(u"device decrease brightness by:\n{}".format(action) )
                except Exception, e:
                    self.debugLog(u"device decrease brightness by: (Unable to display action data due to error: {})".format(e))
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
                    self.debugLog(u"device set color:\n{}".format(action) )
                except Exception, e:
                    self.debugLog(u"device set color: (Unable to display action data due to error: {})".format(e))

                errorText = u"The \"" + device.nsame + u"\" device does not support color. The requested change was not applied."
                self.errorLog(errorText)
                # Remember the error.
                self.lastErrorMessage = errorText

            ##### REQUEST STATUS #####
            elif command == indigo.kDeviceAction.RequestStatus:
                try:
                    self.debugLog(u"device request status:\n{}".format(action) )
                except Exception, e:
                    self.debugLog(u"device request status: (Unable to display action data due to error: {})".format(e))
                self.getBulbStatus(device.id)
                # Log the new brightnss.
                indigo.server.log(u"\"{}\" status request (received: {})".format(device.name, device.states['onOffState']), 'Sent Hue Lights')

            #### CATCH ALL #####
            else:
                indigo.server.log(u"Unhandled command \"{}\"" .format(command))
            pass

        #
        # -- Hue Group --
        #
        if device.deviceTypeId == "hueGroup":
            groupId = device.pluginProps.get('groupId', None)
            hubNumber, ipAddress, hostId, paired = self.getIdsFromDevice(device)
            self.debugLog(u"Command is {}, On/Off Group is {}".format(command, groupId))

            ##### TURN ON #####
            if command == indigo.kDeviceAction.TurnOn:
                try:
                    self.debugLog(u"device on:\n{}".format(action) )
                except Exception, e:
                    self.debugLog(u"device on: (Unable to display action data due to error: {})".format(e))
                # Turn it on.
                self.doOnOff(device, True)

            ##### TURN OFF #####
            elif command == indigo.kDeviceAction.TurnOff:
                try:
                    self.debugLog(u"device off:\n{}".format(action) )
                except Exception, e:
                    self.debugLog(u"device off: (Unable to display action data due to error: {})".format(e))
                # Turn it off by setting the brightness to minimum.
                self.doOnOff(device, False)

            ##### TOGGLE #####
            elif command == indigo.kDeviceAction.Toggle:
                try:
                    self.debugLog(u"device toggle:\n{}".format(action) )
                except Exception, e:
                    self.debugLog(u"device toggle: (Unable to display action due to error: {})".format(e))
                if currentOnState == True:
                    # It's on. Turn it off.
                    self.doOnOff(device, False)
                else:
                    # It's off. Turn it on.
                    self.doOnOff(device, True)

            ##### SET BRIGHTNESS #####
            elif command == indigo.kDeviceAction.SetBrightness:
                try:
                    self.debugLog(u"device set brightness:\n{}".format(action) )
                except Exception, e:
                    self.debugLog(u"device set brightness: (Unable to display action data due to error: {})".format(e))
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
                    self.debugLog(u"device increase brightness by:\n{}".format(action) )
                except Exception, e:
                    self.debugLog(u"device increase brightness by: (Unable to display action data due to error: {})".format(e))
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
                    self.debugLog(u"device decrease brightness by:\n{}".format(action) )
                except Exception, e:
                    self.debugLog(u"device decrease brightness by: (Unable to display action data due to error: {})".format(e))
                brightnessLevel = currentBrightness - action.actionValue
                if brightnessLevel < 0:
                    brightnessLevel = 0
                # Save the new brightness level into the device properties.
                tempProps = device.pluginProps
                tempProps['savedBrightness'] = int(round(brightnessLevel / 100.0 * 255.0))
                self.updateDeviceProps(device, tempProps)
                # Set the new brightness level on the bulb.
                self.doBrightness(device, int(round(brightnessLevel / 100.0 * 255.0)))

            ##### SET COLOR LEVELS #####
            elif command == indigo.kDimmerRelayAction.SetColorLevels:
                try:
                    self.debugLog(u"device request status:\n{}".format(action) )
                except Exception, e:
                    self.debugLog(u"device request status: (Unable to display action data due to error: {})".format(e))

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
                        self.doColorTemperature(device, colorTemp, int(round(currentBrightness / 100.0 * 255.0)))
                    # If both whiteTemperature and whiteLevel keys were sent at the same time, the Indigo Set RGBW
                    #    Levels action is being used, in which case, we still want to use the color temperature method,
                    #    but use the whiteLevel as the brightness instead of the current brightness.
                    elif actionColorVals.get('whiteLevel', None) is not None and float(actionColorVals.get('whiteLevel')) > 0:
                        self.doColorTemperature(device, colorTemp, whiteLevel)
                # If the user is trying to set color temperature on an older LightStrip that doesn't support color
                #   temperature, let them know in the error log.
                elif not device.supportsWhiteTemperature and actionColorVals.get('whiteTemperature', None) is not None:
                    errorText = u"The \"" + device.nsame + u"\" device does not support color temperature. The requested change was not applied."
                    self.errorLog(errorText)
                    # Remember the error.
                    self.lastErrorMessage = errorText
                # Now see if we're only being sent whiteLevel.  If so, the White level slider in the Indigo UI is being
                #   used.  Treat the white level like an inverse saturation slider (100 = zero saturation).
                elif actionColorVals.get('whiteLevel', None) is not None and actionColorVals.get('redLevel', None) is None and actionColorVals.get('greenLevel', None) is None and actionColorVals.get('blueLevel', None) is None:
                    newSaturation = device.states['saturation'] - int(round(whiteLevel / 100.0 * 255.0))
                    if newSaturation < 0:
                        newSaturation = 0
                    if device.supportsRGB:
                        self.doHSB(device, device.states['hue'], newSaturation, int(round(currentBrightness / 100.0 * 255.0)))
                    else:
                        errorText = u"The \"" + device.nsame + u"\" device does not support color. The requested change was not applied."
                        self.errorLog(errorText)
                        # Remember the error.
                        self.lastErrorMessage = errorText
                # If we're not changing color temperature or saturation (white level), use RGB.
                else:
                    if device.supportsRGB:
                        self.doRGB(device, redLevel, greenLevel, blueLevel)
                    else:
                        errorText = u"The \"" + device.nsame + u"\" device does not support color. The requested change was not applied."
                        self.errorLog(errorText)
                        # Remember the error.
                        self.lastErrorMessage = errorText

            ##### REQUEST STATUS #####
            elif command == indigo.kDeviceAction.RequestStatus:
                try:
                    self.debugLog(u"device request status:\n{}".format(action) )
                except Exception, e:
                    self.debugLog(u"device request status: (Unable to display action data due to error: {})".format(e))
                self.getGroupStatus(device.id)
                # Log the new brightnss.
                indigo.server.log(u"\"{}\" status request (received: {})".format( device.name, device.states['brightnessLevel']), 'Sent Hue Lights')

            #### CATCH ALL #####
            else:
                indigo.server.log(u"Unhandled command \"{}\"" .format(command))
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
                    self.debugLog(u"Invalid rate value. Error: {}".format(e))
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

            self.debugLog(u"Command is {}, Bulb device ID is{}" .format(command, bulbDeviceId))

            ##### TURN ON #####
            if command == indigo.kDeviceAction.TurnOn:
                try:
                    self.debugLog(u"device on:\n{}".format(action) )
                except Exception, e:
                    self.debugLog(u"device on: (Unable to display action data due to error: {}".format(e))
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
                    self.debugLog(u"device off:\n{}".format(action) )
                except Exception, e:
                    self.debugLog(u"device off: (Unable to display action data due to error: {})".format(e))
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
                    self.debugLog(u"device toggle:\n{}".format(action) )
                except Exception, e:
                    self.debugLog(u"device toggle: (Unable to display action due to error: {})".format(e))
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
                    self.debugLog(u"device set brightness:\n{}".format(action) )
                except Exception, e:
                    self.debugLog(u"device set brightness: (Unable to display action data due to error: {})".format(e))
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
                    self.debugLog(u"device increase brightness by:\n{}".format(action) )
                except Exception, e:
                    self.debugLog(u"device increase brightness by: (Unable to display action data due to error: {})".format(e))
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
                    self.debugLog(u"device decrease brightness by:\n{}".format(action) )
                except Exception, e:
                    self.debugLog(u"device decrease brightness by: (Unable to display action data due to error: {})".format(e))
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
                    self.debugLog(u"device request status:\n{}".format(action) )
                except Exception, e:
                    self.debugLog(u"device request status: (Unable to display action data due to error: {})".format(e))
                # This actually requests the status of the virtual dimmer device's destination Hue device/group.
                self.getBulbStatus(bulbDeviceId)
                # Show the current virtual dimmer level in the log.  There will likely be a delay for
                #   the destination Hue device status, so we're not going to wait for that status update.
                #   We'll just return the current virtual device brightness level in the log.
                indigo.server.log(u"\"{}\" status request (currently:{})".format(device.name, currentBrightness))

            #### CATCH ALL #####
            else:
                indigo.server.log(u"Unhandled Hue Attribute Controller command \"{}\"".format(command))
            pass

        return 


    # Sensor Action callback
    ######################
    def actionControlSensor(self, action, device):
        try:
            self.debugLog(u"Starting actionControlSensor for device {}. action: {}\n\ndevice: ".format(device.name, action, device))
        except Exception, e:
            self.debugLog(u"Starting actionControlSensor for device {}. (Unable to display action or device data due to error: {})".format(device.name, e))
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
            self.debugLog(u"Command is {}, Sensor is {}".format(action.sensorAction, sensorId))

            ###### TURN ON ######
            # Ignore turn on/off/toggle requests from clients since this is a read-only sensor.
            if action.sensorAction == indigo.kSensorAction.TurnOn:
                indigo.server.log(u"ignored \"{}\" {} request (sensor is read-only)".format(device.name, "on"))

            ###### TURN OFF ######
            # Ignore turn on/off/toggle requests from clients since this is a read-only sensor.
            elif action.sensorAction == indigo.kSensorAction.TurnOff:
                indigo.server.log(u"ignored \"{}\" {} request (sensor is read-only)".format(device.name, "off"))

            ###### TOGGLE ######
            # Ignore turn on/off/toggle requests from clients since this is a read-only sensor.
            elif action.sensorAction == indigo.kSensorAction.Toggle:
                indigo.server.log(u"ignored \"{}\" {} request (sensor is read-only)".format(device.name, "toggle"))

            ###### STATUS REQUEST ######
            elif action.sensorAction == indigo.kSensorAction.RequestStatus:
                # Query hardware module (device) for its current status here:
                indigo.server.log(u"sent \"{}\" {}".format(device.name, "status request"))
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
        self.debugLog(u"Starting isIntCompat.")
        self.debugLog(u"someValue: {}".format(someValue))
        # Check if a value is an integer or not.
        try:
            if type(someValue) == int:
                # It's already an integer. Return right away.
                return True
            # It's not an integer, so try to convert it to one.
            int(u"{}".format(someValue))
            # It converted okay, so return True.
            return True
        except (TypeError, ValueError):
            # The value didn't convert to an integer, so return False.
            return False

        return False

    def calcRgbHexValsFromRgbLevels(self, valuesDict):
        self.debugLog(u"Starting calcRgbHexValsFromRgbLevels.")
        self.debugLog(u"valuesDict: {}".format(valuesDict))
        # Convert RGB integer values to RGB hex values.
        rgbHexVals = []
        for channel in ['red', 'green', 'blue']:
            fieldValue = 0
            # Make sure the field values are integers.
            if channel in valuesDict and self.isIntCompat(valuesDict[channel]):
                fieldValue = int(valuesDict[channel])
            # Make sure the values are within valid limites.
            if fieldValue < 0:
                fieldValue = 0
            elif fieldValue > 255:
                fieldValue = 255
        # Convert integers to hexadecimal values.
        rgbHexVals.append("%02X" % fieldValue)
        # Return all 3 values as a string separated by a single space.
        return ' '.join(rgbHexVals)

    def calcRgbHexValsFromHsbLevels(self, valuesDict):
        self.debugLog(u"Starting calcRgbHexValsFromHsbLevels.")
        self.debugLogg(u"valuesDict: {}".format(valuesDict))
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
            # Make sure the values are within valid limites.
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
                    indigo.server.log(u"brightnessVarId: {}".format(brightnessVarId))
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
        self.debugLog(u"Starting rgbColorPickerUpdated.")
        self.debugLog(u"typeId: {}\ndevId: {}\nvaluesDict: {}".format(typeId, devId, valuesDict))
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
        self.debugLog(u"Starting rgbColorFieldUpdated.")
        self.debugLog(u"typeId: {}\ndevId: {}\nvaluesDict: {}".format(typeId, devId, valuesDict))
        valuesDict['rgbColor'] = self.calcRgbHexValsFromRgbLevels(valuesDict)

        # Can send a live update to the hardware here:
        #    self.sendSetRGBWCommand(valuesDict, typeId, devId)

        del valuesDict['red']
        del valuesDict['green']
        del valuesDict['blue']
        return (valuesDict)

    def hsbColorFieldUpdated(self, valuesDict, typeId, devId):
        self.debugLog(u"Starting hsbColorFieldUpdated.")
        self.debugLog(u"typeId: {}\ndevId: {}\nvaluesDict: {}".format(typeId, devId, valuesDict))
        valuesDict['rgbColor'] = self.calcRgbHexValsFromHsbLevels(valuesDict)

        # Can send a live update to the hardware here:
        #    self.sendSetRGBWCommand(valuesDict, typeId, devId)

        del valuesDict['hue']
        del valuesDict['saturation']
        del valuesDict['brightness']
        return (valuesDict)


    ########################################
    # List Generation and Support Methods
    ########################################
    def getDeviceConfigUiValues(self, pluginProps, typeId=u"", devId=0):
        theDictList =  super(Plugin, self).getDeviceConfigUiValues(pluginProps, typeId, devId)
        if "hubNumber" in theDictList:
            self.hubNumberSelected = theDictList['hubNumber']
        else:
            self.hubNumberSelected = ""
        return theDictList

    # Users List Item Selected (callback from action UI)
    ########################################
    def usersListItemSelected(self, valuesDict=None, typeId="", deviceId=0):
        self.debugLog(u"Starting usersListItemSelected.  valuesDict: {}, typeId: {}, targetId: {}".format(valuesDict, typeId, deviceId))

        self.usersListSelection = valuesDict['userId']
        # Clear these dictionary elements so the sceneLights list will be blank if the sceneId is blank.
        valuesDict['sceneLights'] = list()
        valuesDict['sceneId'] = ""

        return valuesDict

    # Scenes List Item Selected (callback from action UI)
    ########################################
    def scenesListItemSelected(self, valuesDict=None, typeId="", deviceId=0):
        self.debugLog(u"Starting scenesListItemSelected.  valuesDict: {}, typeId: {}, targetId: {}".format(valuesDict, typeId, deviceId))

        self.sceneListSelection = valuesDict['sceneId']

        return valuesDict

    # Groups List Item Selected (callback from action UI)
    ########################################
    def groupsListItemSelected(self, valuesDict=None, typeId="", deviceId=0):
        self.debugLog(u"Starting groupsListItemSelected.  valuesDict: {}, typeId: {}, targetId: {}".format(valuesDict, typeId, deviceId))

        self.groupListSelection = valuesDict['groupId']

        return valuesDict

    # Bulb List Generator
    ########################################
    def bulbListGenerator(self, filter="", valuesDict=None, typeId="", targetId=0):
        # Used in actions that need a list of Hue bridge devices.
        self.debugLog(u"Starting bulbListGenerator.  filter:{}\n valuesDict: {}, typeId: {}, targetId: {}, hubNumberSelected:{}".format(filter, valuesDict, typeId, targetId, self.hubNumberSelected))

        xList = list()
        
        # Iterate over our bulbs, and return a sorted list.
        #   The "lambda" keyword in Python creates an inline function. Here it returns the device name.
        if self.hubNumberSelected == "":
            hubNumbers = self.ipAddresses
        else:
            hubNumbers = {self.hubNumberSelected:True}

        for hubNumber in hubNumbers:
            for bulbId, bulbDetails in sorted(self.lightsDict[hubNumber].items(), key = lambda x: x[1]['name']):
                if typeId == "":
                    # If no typeId exists, list all devices.
                    xList.append([bulbId, bulbDetails['name']])

                elif typeId == "hueBulb" and bulbDetails['type'] == kHueBulbDeviceIDType:
                    xList.append([bulbId, bulbDetails['name']+'-..'+bulbDetails['uniqueid'][-10:]])

                elif typeId == "hueAmbiance" and bulbDetails['type'] == kAmbianceDeviceIDType:
                    xList.append([bulbId, bulbDetails['name']+'-..'+bulbDetails['uniqueid'][-10:]])

                elif typeId == "hueLightStrips" and bulbDetails['type'] == kHueBulbDeviceIDType:
                    xList.append([bulbId, bulbDetails['name']])

                elif typeId == "hueLivingColorsBloom" and bulbDetails['type'] == kLivingColorsDeviceIDs:
                    xList.append([bulbId, bulbDetails['name']+'-..'+bulbDetails['uniqueid'][-10:]])

                elif typeId == "hueLivingWhites" and bulbDetails['type'] == kLivingWhitesDeviceIDType:
                    xList.append([bulbId, bulbDetails['name']+'-..'+bulbDetails['uniqueid'][-10:]])

                elif typeId == "hueOnOffDevice" and bulbDetails['type'][0:len(kOnOffOnlyDeviceIDType)] == kOnOffOnlyDeviceIDType:
                    xList.append([bulbId, bulbDetails['name']+'-..'+bulbDetails['uniqueid'][-10:]])

        # Debug
        self.debugLog(u"bulbListGenerator: Return bulb list is {}".format(xList))

        return xList

    # Group List Generator
    ########################################
    def groupListGenerator(self, filter="", valuesDict=None, typeId="", targetId=0):
        # Used in actions that need a list of Hue bridge groups.
        self.debugLog(u"Starting groupListGenerator.\n  filter: {}\n  valuesDict: {}\n  typeId: {}\n  targetId: {}" .format(filter, valuesDict, typeId, targetId))

        xList = list()

        # Add the special default zero group to the beginning of the list.
        xList.append([0, "0: (All Hue Lights)"])

        # Iterate over our groups, and return a sorted list that's sorted by group ID.
        #   The "lambda" keyword in Python creates an inline function. Here it returns the group ID as an integer.
        if self.hubNumberSelected == "":
            hubNumbers = self.ipAddresses
        else:
            hubNumbers = {self.hubNumberSelected:True}

        for hubNumber in hubNumbers:
            for groupId, groupDetails in sorted(self.groupsDict[hubNumber].items(), key = lambda x: int(x[0])):

                xList.append([groupId, u"{}-{}:{}".format(hubNumber, groupId, groupDetails['name'])])

        # Debug
        self.debugLog(u"groupListGenerator: Return group list is {}".format(xList))

        return xList

    # Bulb Device List Generator
    ########################################
    def bulbAndGroupDeviceListGenerator(self, filter="", valuesDict=None, typeId="", targetId=0):
        # Used in actions that need a list of Hue Lights plugin devices that aren't
        #   attribute controllers or groups.
        self.debugLog(u"Starting bulbAndGroupDeviceListGenerator.\n  filter: {}\n  valuesDict: {}\n  typeId: {}\n  targetId: {}".format(filter, valuesDict, typeId, targetId))

        xList = list()

        # Iterate over our devices, and return the available devices as a 2-tupple list.
        for deviceId in self.deviceList:
            device = indigo.devices[deviceId]
            if device.pluginProps.get('type', "") in [u'Extended color light', u'Color light', u'Color temperature light'] or device.deviceTypeId == "hueGroup":
                xList.append([deviceId, device.name])

        # Sort the list.  Use the "lambda" Python inline function to use the 2nd item in the tuple list (device name) as the sorting key.
        xList = sorted(xList, key = lambda x: x[1])
        # Debug
        self.debugLog(u"bulbAndGroupDeviceListGenerator: Return Hue device list is {}".format(xList))

        return xList

    # Generate Presets List
    ########################################
    def presetListGenerator(self, filter="", valuesDict=None, typeId="", deviceId=0):
        # Used by action dialogs to generate a list of Presets saved in the Hue Lights plugin prefs.
        self.debugLog(u"Starting presetListGenerator.\n  filter: {}\n  valuesDict: {}\n  typeId: {}\n  deviceId: {}".format(filter, valuesDict, typeId, deviceId))

        xList = list()	# Menu item list.

        presets = self.pluginPrefs.get('presets', None)
        self.debugLog(u"presetListGenerator: Presets in plugin prefs:\n{}".format(presets))

        if presets != None:
            presetNumber = 0

            for preset in presets:
                # Determine whether the Preset has saved data or not.
                hasData = u""
                if len(presets[presetNumber][1]) > 0:
                    hasData = u"*"

                presetNumber += 1
                presetName = preset[0]
                xList.append((presetNumber,  u"{} {}: {}".format(hasData, presetNumber, presetName)))
        else:
            xList.append((0, u"-- no presets --"))

        return xList

    # Generate Users List
    ########################################
    def usersListGenerator(self, filter="", valuesDict=None, typeId="", deviceId=0):
        # Used by action dialogs to generate a list of Hue scene "owner" devices or "Creators".
        self.debugLog(u"Starting usersListGenerator.\n  filter: {}\n  valuesDict: {}\n  typeId: {}\n  deviceId: {}".format(filter, valuesDict, typeId, deviceId))

        xList = list()	# Menu item list.

        users = self.usersDict

        # Add a list item at the top for all items.
        xList.append(('all', "All Scene Creators"))

        if self.hubNumberSelected == "":
            hubNumbers = self.ipAddresses
        else:
            hubNumbers = {self.hubNumberSelected:True}

        for hubNumber in hubNumbers:
            if users[hubNumber] != None:
                for userId, userData in users[hubNumber].iteritems():
                    userName = userData.get('name', "(unknown)")
                    # Hue API convention when registering an application (a.k.a. "user")
                    #   is to name the "user" as <app name>#<device name>.  We'll translate that
                    #   here to something more readable and descriptive for the list.
                    userName = userName.replace("#", " app on ")
                    self.debugLog(u"usersListGenerator: usersListSelection value: {}, userId: {}, userData: {}".format(self.usersListSelection, userId, json.dumps(userData, indent=2)))
                    # Don't display the "Indigo Hue Lights" user as that's this plugin which
                    #   won't have any scenes associated with it, which could be confusing.
                    if userName != "Indigo Hue Lights":
                        xList.append((userId, hubNumber+"-"+userName))

        return xList

    # Generate Scenes List
    ########################################
    def scenesListGenerator(self, filter="", valuesDict=None, typeId="", deviceId=0):
        # Used by action dialogs to list Hue scenes on the Hue bridge for a particular "owner" device.
        self.debugLog(u"Starting scenesListGenerator.\n  filter: {}\n  valuesDict: {}\n  typeId: {}\n  deviceId: {}".format(filter, valuesDict, typeId, deviceId))

        xList = list()	# Menu item list.

        scenes = self.scenesDict

        if self.hubNumberSelected == "":
            hubNumbers = self.ipAddresses
        else:
            hubNumbers = {self.hubNumberSelected:True}

        for hubNumber in hubNumbers:
    
            if scenes[hubNumber] != None:
                for sceneId, sceneData in scenes[hubNumber].iteritems():
                    sceneOwner = sceneData.get('owner', "")
                    sceneName = sceneData.get('name', "(unknown)")
                    if valuesDict.get('userId', "all") == "all":
                        # In rare cases, a scene may not have an owner...
                        if sceneOwner == u"none" or sceneOwner == u"":
                            sceneDisplayName = sceneName + u" (from an unknown scene creator)"
                        else:
                            # Make sure the scene owner still exists. In rare cases they dmay not.
                            if sceneOwner in self.usersDict[hubNumber]:
                                sceneDisplayName = sceneName + u" (from " + self.usersDict[hubNumber][sceneOwner]['name'].replace("#", " app on ") + u")"
                            else:
                                sceneDisplayName = sceneName + u" (from a removed scene creator)"
                    else:
                        # Don't add the "(from ... app on ...)" string to the scene name if that Scene Creator was selected.
                        sceneDisplayName = sceneName
                    sceneLights = sceneData.get('lights', list())
                    self.debugLog(u"scenesListGenerator: usersListSelection value: {}, sceneId: {}, sceneOwner: {}, sceneName: {}, sceneData: {}".format(self.usersListSelection, sceneId, sceneOwner, sceneName, json.dumps(sceneData, indent=2)))
                    # Filter the list based on which Hue user (scene owner) is selected.
                    if sceneOwner == self.usersListSelection or self.usersListSelection == "all" or self.usersListSelection == "":
                        xList.append((sceneId, hubNumber+'-'+sceneDisplayName))

                        # Create a descriptive list of the lights that are part of this scene.
                        self.sceneDescriptionDetail = u"Lights in this scene:\n"
                        i = 0
                        for light in sceneLights:
                            if i > 0:
                                self.sceneDescriptionDetail += u", "
                            lightName = self.lightsDict[hubNumber][light]['name']
                            self.sceneDescriptionDetail += lightName
                            i += 1

        return xList

    # Generate Lights List for a Scene
    ########################################
    def sceneLightsListGenerator(self, filter="", valuesDict=None, typeId="", deviceId=0):
        # Used by action dialogs to generate a list of lights in a Hue scene, limited by Hue group.
        self.debugLog(u"Starting sceneLightsListGenerator.\n  filter: {}\n  valuesDict: {}\n  typeId: {}\n  deviceId: {}".format(filter, valuesDict, typeId, deviceId))

        xList = list()	# List item list.

        sceneId = valuesDict.get('sceneId', "")
        groupId = valuesDict.get('groupId', "")

        if self.hubNumberSelected == "":
            hubNumbers = self.ipAddresses
        else:
            hubNumbers = {self.hubNumberSelected:True}

        for hubNumber in hubNumbers:
            if sceneId == "":
                # The sceneId is blank. This only happens when the action/menu dialog is
                #   called for the first time (or without any settings already saved). This
                #   means that the first item of both scene and group lists will be displayed
                #   in the action/menu dialog, set the sceneId based on that assumption.
                try:
                    # We're using "try" here because it's possible there are 0 scenes
                    #   on the bridge.  If so, this will throw an exception.
                    sceneId = self.scenesDict[hubNumber].items()[0][0]
                    if groupId == "":
                        # If the groupId is blank as well (likely), set it to "0" so the
                        #   intersectingLights list is populated properly below.
                        groupId = "0"
                except Exception, e:
                    # Just leave the sceneId blank.
                    pass

            # If the sceneId isn't blank, get the list of lights.
            if sceneId != "" and sceneId in self.scenesDict[hubNumber]:
                # Get the list of lights in the scene.
                sceneLights = self.scenesDict[hubNumber][sceneId]['lights']
                self.debugLog(u"sceneLightsListGenerator: sceneLights value:{}".format(sceneLights))
                # Get the list of lights in the group.
                # If the groupId is 0, then the all lights group was selected.
                if groupId != "0":
                    groupLights = self.groupsDict[hubNumber][groupId]['lights']
                    self.debugLog(u"sceneLightsListGenerator: groupLights value:{}".format(groupLights))
                    # Get the intersection of scene lights and group lights.
                    intersectingLights = list(set(sceneLights) & set(groupLights))
                else:
                    # Since no group limit was selected, all lights in the scene
                    #   should appear in the list.
                    intersectingLights = sceneLights
                self.debugLog(u"sceneLightsListGenerator: intersectingLights value:{}".format(intersectingLights))

                # Get the name on the Hue bridge for each light.
                for lightId in intersectingLights:
                    lightName = self.lightsDict[hubNumber][lightId]['name']
                    xList.append((lightId, lightName))

        return xList

    # Generate Lights List for a Group
    ########################################
    def groupLightsListGenerator(self, filter="", valuesDict=None, typeId="", deviceId=0):
        # Used by action dialogs to generate lists of lights in a Hue group.
        self.debugLog(u"Starting groupLightsListGenerator.\n  filter: {}\n  valuesDict: {}\n  typeId: {}\n  deviceId: {}".format(filter, valuesDict, typeId, deviceId))

        xList = list()	# List item list.

        groupId = valuesDict.get('groupId', "")

        if self.hubNumberSelected == "":
            hubNumbers = self.ipAddresses
        else:
            hubNumbers = {self.hubNumberSelected:True}

        for hubNumber in hubNumbers:
            # If the group ID is not blank, let's try to find the current selection in the valuesDict.
            if groupId != "":
                # Get the list of lights in the group.
                # If the groupId is 0, then the all lights group was selected.
                if groupId == "0":
                    groupLights = self.lightsDict[hubNumber].keys()
                else:
                    groupLights = self.groupsDict[hubNumber][groupId]['lights']
                self.debugLog(u"groupLightsListGenerator: groupLights value:{}".format(groupLights))

                # Get the name on the Hue bridge for each light.
                for lightId in groupLights:
                    lightName = self.lightsDict[hubNumber][lightId]['name']
                    xList.append((lightId, lightName))

        return xList

    # Sensor List Generator
    ########################################
    def sensorListGenerator(self, filter="", valuesDict=None, typeId="", targetId=0):
        # Used in actions and device configuration windows that need a list of sensor devices.
        self.debugLog(u"Starting sensorListGenerator.\n  filter: {}\n  valuesDict: {}\n  typeId: {}\n  targetId: {}".format(filter, valuesDict, typeId, targetId))

        xList = list()
        if self.hubNumberSelected == "":
            hubNumbers = self.ipAddresses
        else:
            hubNumbers = {self.hubNumberSelected:True}

        for hubNumber in hubNumbers:
            # Iterate over our sensors, and return a sorted list in Indigo's format
            #   The "lambda" keyword in Python creates an inline function. Here it returns the device name.
            for sensorId, sensorDetails in self.sensorsDict[hubNumber].items():
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
                    #indigo.server.log(u"uniqueId:{}".format(uniqueId) )
                    for key, value in self.sensorsDict[hubNumber].items():
                        if value.get('uniqueid', False) and value.get('type', False):
                            #indigo.server.log(u"testing uniqueId:{}, type:{}".format(value['uniqueid'],  value['type'] ) )
                            if uniqueId in value['uniqueid'] and value['type'] == "ZLLPresence":
                                xList.append([sensorId, value['name']])

                elif filter == "hueMotionLightSensor" and sensorDetails['type'] == "ZLLLightLevel":
                    # The sensor name on the bridge is going to be generic.  Find the "parent"
                    # motion sensor name by extracting the MAC address from the uniqueid value
                    # and searching for other sensors with the same MAC address in the uniqueid.
                    uniqueId = sensorDetails['uniqueid'].split("-")[0]
                    for key, value in self.sensorsDict[hubNumber].items():
                        if value.get('uniqueid', False) and value.get('type', False):
                            if uniqueId in value['uniqueid'] and value['type'] == "ZLLPresence":
                                xList.append([sensorId, value['name']])

                elif filter == "hueDimmerSwitch" and sensorDetails['type'] == "ZLLSwitch" and sensorDetails['modelid'] in kSwitchDeviceIDs and sensorDetails['modelid'] in ['RWL020', 'RWL021', 'RWL022']:
                    xList.append([sensorId, sensorDetails['name']])

                elif filter == "hueSmartButton" and sensorDetails['type'] == "ZLLSwitch" and sensorDetails['modelid'] in kSwitchDeviceIDs and sensorDetails['modelid'] in ['ROM001']:
                    xList.append([sensorId, sensorDetails['name']])

                elif filter == "hueWallSwitchModule" and sensorDetails['type'] == "ZLLSwitch" and sensorDetails['modelid'] in kSwitchDeviceIDs and sensorDetails['modelid'] in ['RDM001']:
                    xList.append([sensorId, sensorDetails['name']])

                elif filter == "hueTapSwitch" and sensorDetails['type'] == "ZGPSwitch" and sensorDetails['modelid'] in kSwitchDeviceIDs and sensorDetails['modelid'] in ['ZGPSWITCH', 'SWT001']:
                    xList.append([sensorId, sensorDetails['name']])
                # This also shows Niko switches...

                elif filter == "runLessWireSwitch" and sensorDetails['type'] == "ZGPSwitch" and sensorDetails['modelid'] in kSwitchDeviceIDs and sensorDetails['modelid'] in ['FOHSWITCH', 'PTM215Z']:
                    xList.append([sensorId, sensorDetails['name']])

        xList = sorted(xList, key = lambda x: x[1])
        # Debug
        self.debugLog(u"sensorListGenerator: Return sensor list is {}".format(xList) )

        return xList


    # HUB List Generator
    ########################################
    def gwListGenerator(self, filter="", valuesDict=None, typeId="", targetId=0):
        # Used in actions and device configuration windows that need a list of sensor devices.
        self.debugLog(u"Starting gwListGenerator.\n  filter: {}\n  valuesDict: {}\n  typeId: {}\n  targetId: {}".format(filter, valuesDict, typeId, targetId))

        xList = list()

        # pick the gateway for this device scenario ... is associtated with
        if "hubNumber" not in valuesDict: valuesDict['hubNumber'] = "0"
        for hubNumber in self.ipAddresses:
            if hubNumber != valuesDict['hubNumber']:
                xList.append((hubNumber, hubNumber))
        xList.append((valuesDict['hubNumber'], valuesDict['hubNumber']))
                
            
        # Debug
        self.debugLog(u"gwListGenerator: Return hubNumber list is {}".format(xList) )

        return xList


    # confirm hub number selection
    ########################################
    def confirmGWNumber(self, valuesDict, dummy1, dummy2):
        self.debugLog(u"Starting confirmGWNumber.\n  filter: {}".format(valuesDict) )
        self.hubNumberSelected = valuesDict['hubNumber']
        return valuesDict

    ########################################
    # Device Update Methods
    ########################################

    # Update Device State
    ########################################
    def updateDeviceState(self, device, state, newValue=None, decimals=None, newUiValue=None, newUiImage=None):
        # Change the device state or states on the server
        #   if it's different than the current state.

        # Note that the newUiImage value, if passed, should be a valid
        # Indigo State Image Select Enumeration value as defined at
        # http://wiki.indigodomo.com/doku.php?id=indigo_7_documentation:device_class.

        # First determine if we've been sent a key/value list or a device object.
        if state.__class__ == list:
            # Create a temporary key/value list to be used for device updating.
            tempKeyValList = []
            # Loop through the key/value items in the list.
            for statesDict in state:
                # Make sure the minimum required dictionary items exist.
                if statesDict.get('key', False) == False:
                    errorText = u"updateDeviceState: One of the key/value dicts passed in a multi-state update request is missing the \"key\" item. Unable to update any states for the \"{}\" device. State update list:{}.".format(device.name, state)
                    # Don't display the error if it's been displayed already.
                    if errorText != self.lastErrorMessage:
                        self.errorLog(errorText)
                        # Remember the error.
                        self.lastErrorMessage = errorText
                    return
                else:
                    stateKey = state['key']

                if statesDict.get('value', False) == False:
                    errorText = u"updateDeviceState: One of the key/value dicts passed in a multi-state update request is missing the \"value\" item. Unable to update any states for the \"{}\" device. State update list:{}.".format(device.name, state)
                    # Don't display the error if it's been displayed already.
                    if errorText != self.lastErrorMessage:
                        self.errorLog(errorText)
                        # Remember the error.
                        self.lastErrorMessage = errorText
                    return
                else:
                    newValue = statesDict['value']

                # Get any optional dictionary items that may have been passed.
                newUiValue = statesDict.get('uiValue', None)
                decimals = statesDict.get('decimalPlaces', None)
                newUiImage = statesDict.get('uiImage', None)

                # Set the initial UI Value to the same raw value in newValue.
                if newUiValue == None:
                    newUiValue = u"{}".format(newValue)

                # First, if the state doesn't even exist on the device, force a reload
                #   of the device configuration to try to add the new state.
                if device.states.get(stateKey, None) is None:
                    self.debugLog(u"The \"{}\" device doesn't have the \"{}\" state.  Updating device.".format(device.name , stateKey))
                    device.stateListOrDisplayStateIdChanged()

                # If a decimal precision was specified, attempt to round the new value to that precision.
                if decimals is not None:
                    try:
                        # See if the newValue is a number.
                        newValue = float(newValue)
                        if decimals > 0:
                            newValue = round(newValue, decimals)
                        else:
                            newValue = int(round(newValue, decimals))
                    except ValueError:
                        # This isn't a number, don't try to make it one.
                        pass
                    except TypeError:
                        # This also isn't a number and we don't need to make it one.
                        pass
                # If no precision was specified, default to zero decimals.
                else:
                    decimals = 0

                # Now update the state if the new value (rounded if needed) is different.
                if newValue != device.states.get(stateKey, None):
                    try:
                        self.debugLog(u"updateDeviceState: Updating device \"{}\" state: {}. Old value = {}. New value = {}".format(device.name, stateKey, device.states.get(stateKey, ""), newValue))
                    except Exception, e:
                        self.debugLog(u"updateDeviceState: Updating device \"{}\" state: (Unable to display state due to error: {})".format(device.name, e))

                # Update the device UI icon if one was specified.
                if newUiImage != None:
                    device.updateStateImageOnServer(newUiImage)
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
            if newValue == None:
                errorText = u"updateDeviceState: A blank value was passed as the new \"{}\" state for the \"{}\" device. The state value was not changed. Please report this error to the plugin developer.".format(state, device.name )
                # Don't display the error if it's been displayed already.
                if errorText != self.lastErrorMessage:
                    self.errorLog(errorText)
                    # Remember the error.
                    self.lastErrorMessage = errorText
                return

            # Set the initial UI Value to the same raw value in newValue.
            if newUiValue == None:
                newUiValue = u"{}".format(newValue)

            # First, if the state doesn't even exist on the device, force a reload
            #   of the device configuration to try to add the new state.
            if device.states.get(state, None) is None:
                self.debugLog(u"The {} device doesn't have the \"{}\" state.  Updating device.".format(device.name , state))
                device.stateListOrDisplayStateIdChanged()

            # If a decimal precision was specified, attempt to round the new value to that precision.
            if decimals is not None:
                try:
                    # See if the newValue is a number.
                    newValue = float(newValue)
                    if decimals > 0:
                        newValue = round(newValue, decimals)
                    else:
                        newValue = int(round(newValue, decimals))
                except ValueError:
                    # This isn't a number, don't try to make it one.
                    pass
                except TypeError:
                    # This also isn't a number and we don't need to make it one.
                    pass
            # If no precision was specified, default to zero decimals.
            else:
                decimals = 0

            # Now update the state if the new value (rounded if needed) is different.
            if (newValue != device.states.get(state, None)):
                try:
                    self.debugLog(u"updateDeviceState: Updating device {} state: {}. Old value = {}. New value = {}".format(device.name , state, device.states.get(state, ""), newValue))
                except Exception, e:
                    self.debugLog(u"updateDeviceState: Updating device {} state: (Unable to display state due to error: {})".format(device.name , e))

                # Actually update the device state now.
                device.updateStateOnServer(key=state, value=newValue, decimalPlaces=decimals, uiValue=newUiValue)
                # Update the device UI icon if one was specified.
                if newUiImage != None:
                    device.updateStateImageOnServer(newUiImage)
        # End if state is a list or not.

        return 

    # Update Device Properties
    ########################################
    def updateDeviceProps(self, device, newProps):
        # Change the properties on the server only if there's actually been a change.
        if device.pluginProps != newProps:
            self.debugLog(u"updateDeviceProps: Updating device {} properties.".format(device.name))
            device.replacePluginPropsOnServer(newProps)

        return 

    # Rebuild Device
    ########################################
    def rebuildDevice(self, device):
        self.debugLog(u"Starting rebuildDevice.")

        self.debugLog(u"Checking if the {} device needs to be rebuilt.".format(device.name))
        self.debugLog(u"Device details before rebuild check:\n{}".format(device))
        # Copy the current device properties.
        newProps = device.pluginProps

        # Check the device for missing states and properties and fix as needed.

        # Prior to version 1.1.0, the "modelId" property did not exist in lighting devices.
        #   If that property does not exist, force an update.
        if device.deviceTypeId in kLightDeviceTypeIDs and device.pluginProps.get('modelId', u"") == u"":
            self.debugLog(u"The {} lighting device doesn't have a modelId attribute.  Adding it.".format(device.name))
            newProps['modelId'] = u""

        # Prior to version KW, the "hubNumber" did not exist, add property, set default to 0 if not present
        if "hubNumber" not in newProps: 
            newProps['hubNumber'] = "0"

        if "address" in newProps:
           if newProps['address'].find('.') == -1:
                newProps['address'] = self.ipAddresses[newProps['hubNumber']]
           oldAddress = newProps['address'].split("(")[0].strip(" ")
           if newProps['address'].find(':') == -1 or "ID" in newProps['address'] or newProps['address'].find('.') ==-1 or newProps['address'].find(" (") == -1:
                if  'bulbId'        in newProps: newProps['address'] = u"{} (Lid:{}-{})".format(oldAddress, newProps['hubNumber'], newProps['bulbId'])

                elif 'groupId'      in newProps: newProps['address'] = u"{} (Gid:{}-{})".format(oldAddress, newProps['hubNumber'], newProps['groupId'])

                elif 'sensorId'     in newProps: newProps['address'] = u"{} (Sid:{}-{})".format(oldAddress, newProps['hubNumber'], newProps['sensorId'])

                elif 'bulbDeviceId' in newProps: newProps['address'] = u"{}. (Aid:{}-{})".format(device.id, newProps['hubNumber'], newProps['bulbDeviceId'])

 
        # Prior to version 1.4, the color device properties did not exist in lighting devices.
        #   If any of those properties don't exist, update the device properties based on model ID.
        if device.deviceTypeId in kLightDeviceTypeIDs and device.configured:
            self.debugLog(u"Verifying the {} lighting device properties.".format(device.name))
            if device.pluginProps.get('type', "") in [u'Extended color light', u'Color light', u'Color temperature light']:
                newProps['SupportsColor'] = True
                if device.pluginProps.get('type', "") in [u'Extended color light', u'Color light']:
                    newProps['SupportsRGB'] = True
                else:
                    newProps['SupportsRGB'] = False
                if device.pluginProps.get('type', "") in [u'Extended color light', u'Color temperature light']:
                    newProps['SupportsWhite'] = True
                    newProps['SupportsWhiteTemperature'] = True
                    newProps['WhiteTemperatureMin'] = "2000"
                    newProps['WhiteTemperatureMax'] = "6500"
                else:
                    newProps['SupportsWhite'] = False
                    newProps['SupportsWhiteTemperature'] = False
                    if newProps.get('WhiteTemperatureMin', False):
                        del newProps['WhiteTemperatureMin']
                    if newProps.get('WhiteTemperatureMax', False):
                        del newProps['WhiteTemperatureMax']
                # No Hue bridge controlled device supports both RGB and white balance control simultaniously.
                if device.pluginProps.get('type', "") == u"Extended color light":
                    newProps['SupportsRGBandWhiteSimultaneously'] = False
            else:
                newProps['SupportsColor'] = False
        elif device.deviceTypeId in kGroupDeviceTypeIDs and device.configured:
            self.debugLog(u"Verifying the {} group device.".format(device.name))
            newProps['SupportsColor'] = True
            newProps['SupportsRGB'] = True
            newProps['SupportsWhite'] = True
            newProps['SupportsWhiteTemperature'] = True
            newProps['WhiteTemperatureMin'] = "2000"
            newProps['WhiteTemperatureMax'] = "6500"
            newProps['SupportsRGBandWhiteSimultaneously'] = False
        elif device.deviceTypeId in kMotionSensorTypeIDs and device.configured:
            self.debugLog(u"Verifying the {} motion sensor device.".format(device.name))
            newProps['SupportsOnState'] = True
            newProps['SupportsSensorValue'] = False
            newProps['SupportsBatteryLevel'] = True
        elif device.deviceTypeId in kTemperatureSensorTypeIDs and device.configured:
            self.debugLog(u"Verifying the {} temperature sensor device.".format(device.name))
            newProps['SupportsOnState'] = False
            newProps['SupportsSensorValue'] = True
            newProps['SupportsBatteryLevel'] = True
            if not newProps.get('sensorOffset', False):
                newProps['sensorOffset'] = ""
            if not newProps.get('temperatureScale', False):
                newProps['temperatureScale'] = "c"
        elif device.deviceTypeId in kLightSensorTypeIDs and device.configured:
            self.debugLog(u"Verifying the {} light sensor device.".format(device.name))
            newProps['SupportsOnState'] = False
            newProps['SupportsSensorValue'] = True
            newProps['SupportsBatteryLevel'] = True
        elif device.deviceTypeId in kSwitchTypeIDs and device.configured:
            self.debugLog(u"Verifying the {} switch device.".format(device.name))
            newProps['SupportsOnState'] = True
            newProps['SupportsSensorValue'] = False
            # The Hue Tap, Run Less Wire and Niko switches don't have a battery so don't support battery level.
            if device.pluginProps['modelId'] in ['ZGPSWITCH', 'SWT001', 'FOHSWITCH', 'PTM215Z']:
                newProps['SupportsBatteryLevel'] = False
            else:
                newProps['SupportsBatteryLevel'] = True

        if newProps != device.pluginProps:
            self.debugLog(u"Device properties have changed. New properties:\n{}".format(newProps))
            self.debugLog(u"Replacing properties on server.")
            device.replacePluginPropsOnServer(newProps)

        self.debugLog(u"Telling server to reload state list and display state.")
        device.stateListOrDisplayStateIdChanged()

        self.debugLog(u"rebuildDevice complete.")

        return 


    # Get ip number and hub id
    ########################################
    def getIdsFromDevice(self, device):
        hubNumber = device.pluginProps.get('hubNumber', "0")
        return hubNumber, self.ipAddresses[hubNumber], self.hostIds[hubNumber], self.paired[hubNumber]


    ########################################
    # Hue Communication Methods
    ########################################

    # Get Bulb Status
    ########################################
    def getBulbStatus(self, deviceId):
        # Get device status.

        device = indigo.devices[deviceId]
        hubNumber, ipAddress, hostId, paired = self.getIdsFromDevice(device)
        self.debugLog(u"Get device status for {}".format(device.name))
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
                command = "http://{}/api/{}/lights/{}".format(ipAddress, hostId, bulbId)
                self.debugLog(u"Sending URL request: {}".format(command))
                try:
                    r = requests.get(command, timeout=kTimeout)
                except requests.exceptions.Timeout:
                    errorText = u"Failed to connect to the Hue bridge at {} after {} seconds. - Check that the bridge is connected and turned on.".format(ipAddress, kTimeout)
                    # Don't display the error if it's been displayed already.
                    if errorText != self.lastErrorMessage:
                        self.errorLog(errorText)
                        # Remember the error.
                        self.lastErrorMessage = errorText
                    return
                except requests.exceptions.ConnectionError:
                    errorText = u"Failed to connect to the Hue bridge at {}. - Check that the bridge is connected and turned on.".format(ipAddress)
                    # Don't display the error if it's been displayed already.
                    if errorText != self.lastErrorMessage:
                        self.errorLog(errorText)
                        # Remember the error.
                        self.lastErrorMessage = errorText
                    return
            # The Indigo device
            #   must not yet be configured. Just return gracefully.
            else:
                self.debugLog(u"No bulbId exists in the \"{}\" device. New device perhaps.".format(device.name))
                return

        self.debugLog(u"Data from bridge: {}".format(r.content.decode("utf-8")) )
        # Convert the response to a Python object.
        try:
            bulb = json.loads(r.content)
        except Exception, e:
            indigo.server.log(u"Error retrieving Hue device status: {}".format(e))
            return False

        ### Parse Data
        #
        # Sanity check the returned data first.
        try:
            # If the bulb variable is a list, then there were processing errors.
            errorDict = bulb[0]
            errorText = u"Error retrieving Hue device status: {}".format(errorDict['error']['description'])
            self.errorLog(errorText)
            return
        except KeyError:
            errorDict = []
            # If there was a KeyError, then there were no processing errors.

        # Call the method to update the Indigo device with the Hue device info.
        self.parseOneHueLightData(bulb, device)

        return 

    # Get Group Status
    ########################################
    def getGroupStatus(self, deviceId):
        # Get group status.

        device = indigo.devices[deviceId]
        hubNumber, ipAddress, hostId, paired = self.getIdsFromDevice(device)
        # Get the groupId from the device properties.
        groupId = device.pluginProps.get('groupId', -1)
        self.debugLog(u"Get group status for group {}.".format(groupId))
        # if the groupId exists, get the group status.
        if groupId > -1:
            command = "http://{}/api/{}/groups/{}" .format(ipAddress, hostId, groupId)
            self.debugLog(u"Sending URL request: {}".format(command))
            try:
                r = requests.get(command, timeout=kTimeout)
            except requests.exceptions.Timeout:
                errorText = u"Failed to connect to the Hue bridge at {} after {} seconds. - Check that the bridge is connected and turned on.".format(ipAddress, kTimeout)
                # Don't display the error if it's been displayed already.
                if errorText != self.lastErrorMessage:
                    self.errorLog(errorText)
                    # Remember the error.
                    self.lastErrorMessage = errorText
                return
            except requests.exceptions.ConnectionError:
                errorText = u"Failed to connect to the Hue bridge at {}. - Check that the bridge is connected and turned on.".format(ipAddress)
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

        self.debugLog(u"Data from bridge: {}".format(r.content.decode("utf-8")) )

        # Convert the response to a Python object.
        try:
            group = json.loads(r.content)
        except Exception, e:
            indigo.server.log(u"Error retrieving Hue group status: {}".format(e))
            return

        ### Parse Data
        #
        # Sanity check the returned data first.
        try:
            # If the group variable is a list, then there were processing errors.
            errorDict = group[0]
            errorText = u"Error retrieving Hue device status: {}".format(errorDict['error']['description'])
            self.errorLog(errorText)
            return
        except KeyError:
            errorDict = []
            # If there was a KeyError, then there were no processing errors.

        # Call the method to update the Indigo device with the Hue group data.
        self.parseOneHueGroupData(group, device)

        return 

    # Get Sensor Status
    ########################################
    def getSensorStatus(self, deviceId):
        # Get sensor status.

        device = indigo.devices[deviceId]
        hubNumber, ipAddress, hostId, paired = self.getIdsFromDevice(device)
        # Get the sensorId from the device properties.
        sensorId = device.pluginProps.get('sensorId', -1)
        self.debugLog(u"Get sensor status for sensor {}.".format(sensorId))
        # if the sensorId exists, get the sensor status.
        if sensorId > -1:
            command = "http://{}/api/{}/sensors/{}" .format(ipAddress, hostId, sensorId)
            self.debugLog(u"Sending URL request: {}".format(command))
            try:
                r = requests.get(command, timeout=kTimeout)
            except requests.exceptions.Timeout:
                errorText = u"Failed to connect to the Hue bridge at {} after {} seconds. - Check that the bridge is connected and turned on.".format(ipAddress, kTimeout)
                # Don't display the error if it's been displayed already.
                if errorText != self.lastErrorMessage:
                    self.errorLog(errorText)
                    # Remember the error.
                    self.lastErrorMessage = errorText
                return
            except requests.exceptions.ConnectionError:
                errorText = u"Failed to connect to the Hue bridge at {}. - Check that the bridge is connected and turned on.".format(ipAddress)
                # Don't display the error if it's been displayed already.
                if errorText != self.lastErrorMessage:
                    self.errorLog(errorText)
                    # Remember the error.
                    self.lastErrorMessage = errorText
                return
            # End try to get data from bridge.
        else:
            # The Indigo device must not yet be configured. Just return gracefully.
            self.debugLog(u"No sensorId exists in the \"{}\" device. New device perhaps.".format(device.name))
            return
        # End if sensorId is defined.

        self.debugLog(u"Data from bridge: {}".format(r.content.decode("utf-8")) )
        # Convert the response to a Python object.
        try:
            sensor = json.loads(r.content)
        except Exception, e:
            indigo.server.log(u"Error retrieving Hue sensor status: {}".format(e))
            return False

        ### Parse Data
        #
        # Sanity check the returned data first.
        try:
            # If the sensor variable is a list, then there were processing errors.
            errorDict = sensor[0]
            errorText = u"Error retrieving Hue device status: {}".format(errorDict['error']['description'])
            self.errorLog(errorText)
            return
        except KeyError:
            errorDict = []
            # If there was a KeyError, then there were no processing errors.

        # Call the method to update the Indigo device with the Hue device info.
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
        self.debugLog(u"Starting getHueConfig.")
        for hubNumber in self.ipAddresses:
            # 
            ipAddress, hostId, errorCode = self.getadresses(hubNumber)
            if errorCode >0: return

            # Force a timeout
            socket.setdefaulttimeout(kTimeout)

            try:

                # Send the command and parse the response
                command = "http://{}/api/{}/".format(ipAddress, self.hostIds[hubNumber])
                self.debugLog(u"Sending command to bridge: {}".format(command))
                r = requests.get(command, timeout=kTimeout)
                responseData = json.loads(r.content)
                self.debugLog(u"Got response {}".format(responseData))

                # We should have a dictionary. If so, it's a Hue configuration response.
                if isinstance(responseData, dict):
                    self.debugLog(u"Loaded entire Hue bridge configuration - {}".format(responseData))

                    # Load the entire configuration into one big dictionary object.
                    self.hueConfigDict[hubNumber] = responseData
                    # Now separate out the component obects into various dictionaries to
                    #   be used by other methods in the plugin.
                    self.lightsDict[hubNumber]		= responseData.get('lights', dict())
                    self.groupsDict[hubNumber]		= responseData.get('groups', dict())
                    self.resourcesDict[hubNumber]	= responseData.get('resourcelinks', dict())
                    self.sensorsDict[hubNumber]		= responseData.get('sensors', dict())
                    tempDict						= responseData.get('config', dict())
                    self.usersDict[hubNumber]		= tempDict.get('whitelist', dict())
                    self.scenesDict[hubNumber]		= responseData.get('scenes', dict())
                    self.rulesDict[hubNumber]		= responseData.get('rules', dict())
                    self.schedulesDict[hubNumber]	= responseData.get('schedules', dict())
                    #self.debugLog(u"from hub response loading scenesDict:{}". format(json.dumps(self.usersDict, indent=2)))

                    # Make sure the plugin knows it's actually paired now.
                    self.paired[hubNumber] = True

                elif isinstance(responseData, list):
                    # Get the first item
                    firstResponseItem = responseData[0]

                    # Did we get an error?
                    errorDict = firstResponseItem.get('error', None)
                    if errorDict is not None:

                        errorCode = errorDict.get('type', None)

                        # Is this a link button not pressed error?
                        if errorCode == 1:
                            errorText = u"getHueConfig: Not paired with the Hue bridge. Press the middle button on the Hue bridge, then press the Pair Now button in the Hue Lights Configuration window (Plugins menu)."
                            self.errorLog(errorText)
                            # Remember the error.
                            self.lastErrorMessage = errorText
                            self.paired[hubNumber] = False

                        else:
                            errorText = u"Error #{} from Hue bridge when getting the Hue bridge configuration. Description is \"{}\"." .format(errorCode, errorDict.get('description', u"(no description"))
                            self.errorLog(errorText)
                            # Remember the error.
                            self.lastErrorMessage = errorText
                            self.paired[hubNumber] = False

                    else:
                        indigo.server.log(u"Unexpected response from Hue bridge ({}) when getting the Hue bridge configuration!" .format(hueConfigResponseData))

                else:
                    indigo.server.log(u"Unexpected response from Hue bridge ({}) when getting the Hue bridge configuration!".format(hueConfigResponseData))

            except requests.exceptions.Timeout:
                errorText = u"Failed to load the configuration from the Hue bridge at {} after {} seconds - check settings and retry.".format(ipAddress, kTimeout)
                # Don't display the error if it's been displayed already.
                if errorText != self.lastErrorMessage:
                    self.errorLog(errorText)
                    # Remember the error.
                    self.lastErrorMessage = errorText

            except requests.exceptions.ConnectionError:
                errorText = u"Failed to connect to the Hue bridge at {}. - Check that the bridge is connected, turned on and the network settings are correct.".format(ipAddress)
                # Don't display the error if it's been displayed already.
                if errorText != self.lastErrorMessage:
                    self.errorLog(errorText)
                    # Remember the error.
                    self.lastErrorMessage = errorText
                return

            except Exception, e:
                self.errorLog(u"Unable to obtain the configuration from the Hue bridge.{}".format(e))
        return

    # Update Lights List
    ########################################
    def updateLightsList(self):
        self.debugLog(u"Starting updateLightsList.")
        # 
        lastCount = {}
        for hubNumber in self.ipAddresses:
            ipAddress, hostId, errorCode = self.getadresses(hubNumber)
            if errorCode >0: return

            # Remember the current number of Hue lights to see if new ones have been added.
            if hubNumber not in self.lightsDict:
                self.lightsDict[hubNumber] ={}
            lastCount[hubNumber] = len(self.lightsDict[hubNumber])
            countChange = 0

            # Force a timeout
            socket.setdefaulttimeout(kTimeout)

            try:
                # Parse the response
                command = "http://{}/api/{}/lights".format(ipAddress, self.hostIds[hubNumber])
                self.debugLog(u"Sending command to bridge: {}".format(command))
                r = requests.get(command, timeout=kTimeout)
                responseData = json.loads(r.content)
                self.debugLog(u"Got response {}".format(responseData) )

                # We should have a dictionary. If so, it's a light list
                if isinstance(responseData, dict):
                    self.debugLog(u"Loaded lights list - {}".format(responseData))
                    self.lightsDict[hubNumber] = responseData

                    # See if there are more lights now than there were last time we checked.
                    if len(self.lightsDict[hubNumber]) > lastCount[hubNumber] and lastCount[hubNumber] is not 0:
                        countChange = len(self.lightsDict[hubNumber]) - lastCount[hubNumber]
                        if countChange == 1:
                            indigo.server.log(u"{} new Hue light found and loaded. Be sure to create an Indigo device to control the new Hue light.".format(countChange) )
                        else:
                            indigo.server.log(u"{} new Hue lights found and loaded. Be sure to create Indigo devices to control the new Hue lights.".format(countChange) )
                    elif len(self.lightsDict[hubNumber]) < lastCount:
                        countChange = lastCount[hubNumber] - len(self.lightsDict[hubNumber])
                        if countChange == 1:
                            indigo.server.log(u"{} Hue light removal was detected from the Hue bridge. Check your Hue Lights Indigo devices. One of them may have been controlling the missing Hue lights.".format(countChange) )
                        elif countChange != 0:
                            indigo.server.log(u"{} Hue light removals were detected on the Hue bridge. Check your Hue Lights Indigo devices. Some of them may have been controlling the missing Hue lights.".format(countChange) )

                    # Make sure the plugin knows it's actually paired now.
                    self.paired[hubNumber] = True

                elif isinstance(responseData, list):
                    # Get the first item
                    firstResponseItem = responseData[0]

                    # Did we get an error?
                    errorDict = firstResponseItem.get('error', None)
                    if errorDict is not None:

                        errorCode = errorDict.get('type', None)

                        # Is this a link button not pressed error?
                        if errorCode == 1:
                            errorText = u"updateLightsList: Not paired with the Hue bridge. Press the middle button on the Hue bridge, then press the Pair Now button in the Hue Lights Configuration window (Plugins menu)."
                            self.errorLog(errorText)
                            # Remember the error.
                            self.lastErrorMessage = errorText
                            self.paired[hubNumber] = False

                        elif countChange !=0:
                            errorText = u"Error #{} from Hue bridge when loading available devices. Description is \"{}\".".format(errorCode, errorDict.get('description', u"(no description"))
                            self.errorLog(errorText)
                            # Remember the error.
                            self.lastErrorMessage = errorText
                            self.paired[hubNumber] = False

                    else:
                        indigo.server.log(u"Unexpected response from Hue bridge ({}) when loading available devices!".format(lightsListResponseData))

                else:
                    indigo.server.log(u"Unexpected response from Hue bridge ({}) when loading available devices!".format(lightsListResponseData))

            except requests.exceptions.Timeout:
                errorText = u"Failed to load lights list from the Hue bridge at {} after {} seconds - check settings and retry.".format(ipAddress, kTimeout)
                # Don't display the error if it's been displayed already.
                if errorText != self.lastErrorMessage:
                    self.errorLog(errorText)
                    # Remember the error.
                    self.lastErrorMessage = errorText

            except requests.exceptions.ConnectionError:
                errorText = u"Failed to connect to the Hue bridge at {}. - Check that the bridge is connected, turned on and the network settings are correct." .format(ipAddress)
                # Don't display the error if it's been displayed already.
                if errorText != self.lastErrorMessage:
                    self.errorLog(errorText)
                    # Remember the error.
                    self.lastErrorMessage = errorText
                return

            except Exception, e:
                errorText = u"Unable to obtain list of Hue lights from the bridge. at line:{};  error msg:{}\n lastCount:{}".format(sys.exc_traceback.tb_lineno, e, lastCount) 
                # Don't display the error if it's been displayed already.
                if errorText != self.lastErrorMessage:
                    self.errorLog(errorText)
                    # Remember the error.
                    self.lastErrorMessage = errorText

    # get ip numbers etc
    ########################################
    def getadresses(self, hubNumber):
            ipAddress = self.ipAddresses[hubNumber]
            if ipAddress is None:
                errorText = u"No IP address set for the Hue bridge. You can get this information from the My Settings page at http://www.meethue.com."
                self.errorLog(errorText)
                # Remember the error.
                self.lastErrorMessage = errorText
                self.lastErrorMessage = errorText
                return 0,0,1
            if hubNumber not in self.hostIds:
                return 0,0,1
            return ipAddress, self.hostIds[hubNumber], 0

    # Update Groups List
    ########################################
    def updateGroupsList(self):
        self.debugLog(u"Starting updateGroupsList.")
        # 
        lastCount = {}
        for hubNumber in self.ipAddresses:
            # Sanity check for an IP address
            ipAddress, hostId, errorCode = self.getadresses(hubNumber)
            if errorCode >0: return

            # Remember the current number of Hue groups to see if new ones have been added.
            if hubNumber not in self.groupsDict:
                self.groupsDict[hubNumber] ={}
            lastCount[hubNumber] = len(self.groupsDict[hubNumber])

            # Force a timeout
            socket.setdefaulttimeout(kTimeout)

            try:
                # Parse the response
                command = "http://{}/api/{}/groups".format(ipAddress, self.hostIds[hubNumber])
                self.debugLog(u"Sending command to bridge:{}".format(command) )
                r = requests.get(command, timeout=kTimeout)
                responseData = json.loads(r.content)
                self.debugLog(u"Got response {}".format(responseData) )

                # We should have a dictionary. If so, it's a group list
                if isinstance(responseData, dict):
                    self.debugLog(u"Loaded groups list - {}".format(responseData) )
                    self.groupsDict[hubNumber] = responseData

                    # See if there are more groups now than there were last time we checked.
                    if len(self.groupsDict[hubNumber]) > lastCount[hubNumber] and lastCount[hubNumber] is not 0:
                        countChange = len(self.groupsDict[hubNumber]) - lastCount[hubNumber]
                        if countChange == 1:
                            indigo.server.log(u"{} new Hue group found and loaded. Be sure to create an Indigo device to control the new Hue group.".format(countChange) )
                        else:
                            indigo.server.log(u"{} new Hue groups found and loaded. Be sure to create Indigo devices to control the new Hue groups.".format(countChange) )
                    elif len(self.groupsDict[hubNumber]) < lastCount[hubNumber]:
                        countChange = lastCount[hubNumber] - len(self.groupsDict[hubNumber])
                        if countChange == 1:
                            indigo.server.log(u"{} less Hue group was found on the Hue bridge. Check your Hue Lights Indigo devices. One of them may have been controlling the missing Hue group.".format(countChange) )
                        elif countChange !=0:
                            indigo.server.log(u"{} fewer Hue groups were found on the Hue bridge. Check your Hue Lights Indigo devices. Some of them may have been controlling the missing Hue groups.".format(countChange) )
                    # Make sure the plugin knows it's actually paired now.
                    self.paired[hubNumber] = True

                elif isinstance(responseData, list):
                    # Get the first item
                    firstResponseItem = responseData[0]

                    # Did we get an error?
                    errorDict = firstResponseItem.get('error', None)
                    if errorDict is not None:

                        errorCode = errorDict.get('type', None)

                        # Is this a link button not pressed error?
                        if errorCode == 1:
                            errorText = u"updateGroupsList: Not paired with the Hue bridge. Press the middle button on the Hue bridge, then press the Pair Now button in the Hue Lights Configuration window (Plugins menu)."
                            self.errorLog(errorText)
                            # Remember the error.
                            self.lastErrorMessage = errorText
                            self.paired[hubNumber] = False

                        else:
                            errorText = u"Error #{} from Hue bridge when loading available groups. Description is \"{}\".".format(errorCode, errorDict.get('description', u"(no description"))
                            self.errorLog(errorText)
                            # Remember the error.
                            self.lastErrorMessage = errorText
                            self.paired[hubNumber] = False

                    else:
                        indigo.server.log(u"Unexpected response from Hue bridge {} when loading available groups!".format(groupsListResponseData))

                else:
                    indigo.server.log(u"Unexpected response from Hue bridge {} when loading available groups!".format(groupsListResponseData))

            except requests.exceptions.Timeout:
                errorText = u"Failed to load groups list from the Hue bridge at {} after {} seconds - check settings and retry.".format(ipAddress, kTimeout)
                # Don't display the error if it's been displayed already.
                if errorText != self.lastErrorMessage:
                    self.errorLog(errorText)
                    # Remember the error.
                    self.lastErrorMessage = errorText

            except requests.exceptions.ConnectionError:
                errorText = u"Failed to connect to the Hue bridge at {}. - Check that the bridge is connected, turned on and the network settings are correct.".format(ipAddress)
                # Don't display the error if it's been displayed already.
                if errorText != self.lastErrorMessage:
                    self.errorLog(errorText)
                    # Remember the error.
                    self.lastErrorMessage = errorText
                return

            except Exception, e:
                self.errorLog(u"Unable to obtain list of Hue groups from the bridge. at line:{};  error msg{}".format(sys.exc_traceback.tb_lineno, e))
        return 

    # Update Sensors List
    ########################################
    def updateSensorsList(self, goSensorDumpData = False):
        self.debugLog(u"Starting updateSensorsList.")
        # 
        lastCount ={}
        for hubNumber in self.ipAddresses:
            ipAddress, hostId, errorCode = self.getadresses(hubNumber)
            if errorCode >0: return

            # Remember the current number of sensors to see if new ones have been added.
            if hubNumber not in self.sensorsDict:
                self.sensorsDict[hubNumber] = {}
            lastCount[hubNumber] = len(self.sensorsDict[hubNumber])

            # Force a timeout
            socket.setdefaulttimeout(kTimeout)

            try:
                # Parse the response
                command = "http://{}/api/{}/sensors".format(ipAddress, hostId)
                if goSensorDumpData:
                    self.debugLog(u"Sending command to bridge: {}" .format(command) )
                r = requests.get(command, timeout=kTimeout)
                responseData = json.loads(r.content)
                if goSensorDumpData:
                    self.debugLog(u"Got response {}".format(responseData) )

                # We should have a dictionary. If so, it's a sensors list
                if isinstance(responseData, dict):
                    ## self.debugLog(u"Loaded sensors list - %s" % (sensorsListResponseData))
                    self.sensorsDict[hubNumber] = responseData

                    # See if there are more sensors now than there were last time we checked.
                    if len(self.sensorsDict[hubNumber]) > lastCount[hubNumber] and lastCount[hubNumber] is not 0:
                       countChange = len(self.sensorsDict[hubNumber]) - lastCount[hubNumber]
                       if countChange == 1:
                            indigo.server.log(u"{} new Hue sensor found and loaded. Be sure to create an Indigo device to control the new Hue sensor.".format(countChange) )
                       else:
                            indigo.server.log(u"{} new Hue sensors found and loaded. Be sure to create Indigo devices to control the new Hue sensors.".format(countChange) )
                    elif len(self.sensorsDict[hubNumber]) < lastCount:
                        countChange = lastCount[hubNumber] - len(self.sensorsDict[hubNumber])
                        if countChange == 1:
                            indigo.server.log(u"{} less Hue sensor was found on the Hue bridge. Check your Hue Lights Indigo devices. One of them may have been controlling the missing Hue sensor." .format(countChange) )
                        elif countChange !=0:
                            indigo.server.log(u"{} fewer Hue sensors were found on the Hue bridge. Check your Hue Lights Indigo devices. Some of them may have been controlling the missing Hue sensors.".format(countChange) )
                    # Make sure the plugin knows it's actually paired now.
                    self.paired[hubNumber] = True

                elif isinstance(responseData, list):
                    # Get the first item
                    firstResponseItem = responseData[0]

                    # Did we get an error?
                    errorDict = firstResponseItem.get('error', None)
                    if errorDict is not None:

                        errorCode = errorDict.get('type', None)

                        # Is this a link button not pressed error?
                        if errorCode == 1:
                            errorText = u"updateSensorsList: Not paired with the Hue bridge. Press the middle button on the Hue bridge, then press the Pair Now button in the Hue Lights Configuration window (Plugins menu)."
                            self.errorLog(errorText)
                            # Remember the error.
                            self.lastErrorMessage = errorText
                            self.paired[hubNumber] = False

                        else:
                            errorText = u"Error #{} from Hue bridge when loading available sensors. Description is \"{}\".".format(errorCode, errorDict.get('description', u"(no description"))
                            self.errorLog(errorText)
                            # Remember the error.
                            self.lastErrorMessage = errorText
                            self.paired[hubNumber] = False

                    else:
                        indigo.server.log(u"Unexpected response from Hue bridge ({}) when loading available sensors!".format(sensorsListResponseData))

                else:
                    indigo.server.log(u"Unexpected response from Hue bridge ({}) when loading available sensors!".format(sensorsListResponseData))

            except requests.exceptions.Timeout:
                errorText = u"Failed to load sensors list from the Hue bridge at {} after {} seconds - check settings and retry.".format (ipAddress, kTimeout)
                # Don't display the error if it's been displayed already.
                if errorText != self.lastErrorMessage:
                    self.errorLog(errorText)
                    # Remember the error.
                    self.lastErrorMessage = errorText

            except requests.exceptions.ConnectionError:
                errorText = u"Failed to connect to the Hue bridge at {}. - Check that the bridge is connected, turned on and the network settings are correct.".format(ipAddress)
                # Don't display the error if it's been displayed already.
                if errorText != self.lastErrorMessage:
                    self.errorLog(errorText)
                    # Remember the error.
                    self.lastErrorMessage = errorText
                return

            except Exception, e:
                self.errorLog(u"Unable to obtain list of Hue sensors from the bridge. at line:{};  error msg{}".format(sys.exc_traceback.tb_lineno, e))

    # Parse All Hue Lights Data
    ########################################
    def parseAllHueLightsData(self):
        self.debugLog(u"Starting parseAllHueLightsData.")

        # Itterate through all the Indigo devices and look for Hue light changes in the
        #   self.lightsDict that changed, then update the Indigo device states and properties
        #   as needed.  This method does no actual Hue bridge communication.  It just updates
        #   Indigo devices with information already obtained through the use of the
        #   self.updateLightsList.

        self.debugLog(u"parseAllHueLightsData: There are {} lights on the Hue bridge and {} Indigo devices controlling Hue devices.".format(len(self.lightsDict), len(self.deviceList)))
        # Start going through all the devices in the self.deviceList and update any Indigo
        #   devices that are controlling the Hue light devices.
        for deviceId in self.deviceList:
            device = indigo.devices[deviceId]
            # self.debugLog(u"parseAllHueLightsData: Looking at Indigo device \"%s\"." % (device.name))

            # If this Indigo device is a supported light device...
            if device.deviceTypeId in kLightDeviceTypeIDs:
                ## self.debugLog(u"parseAllHueLightsData: Indigo device \"%s\" is not for a Hue group. Proceeing." % (device.name))

                # Go through each Hue light device and see if it is controlled by this Indigo device.
                hubNumber = device.pluginProps['hubNumber']
                for bulbId in self.lightsDict[hubNumber]:
                    # Extract the bulb object from the lightsDict.
                    bulb = self.lightsDict[hubNumber][bulbId]
                    ## self.debugLog(u"parseAllHueLightsData: Parsing Hue device ID %s (\"%s\")." % (bulbId, bulb.get('name', "no name")))
                    # Is this Hue device ID the one associated with this Indigo device?
                    if bulbId == device.pluginProps['bulbId']:
                        ## self.debugLog(u"parseAllHueLightsData: Indigo device \"%s\" is controlling Hue device ID \"%s\" (\"%s\"). Updating Indigo device properties and states." % (device.name, bulbId, bulb.get('name', "no name")))
                        # Attempt to update the Indigo device with the bulb object data.
                        self.parseOneHueLightData(bulb, device)
                        # Since only 1 Hue device can be controlled by 1 Indigo device, we're done here.
                        break
                        # End if update was successful.
                    # End if the Hue bulb ID is controlled by this Indigo device.
                # End loop through self.lightsDict.
            # End check if this is not a Hue Group device.
        # End loop through self.deviceList.

    # Parse One Hue Light Data
    ########################################
    def parseOneHueLightData(self, bulb, device):
        ## self.debugLog(u"Starting parseOneHueLightData.")

        # Take the bulb passed to this method, look up the data already obtained from the Hue bridge
        # and parse the bridge data for this bulb, making changes to the Indigo device as needed.

        deviceId = device.id

        # Separate out the specific Hue bulb data.
        # Data common to all device types...
        #   Value assignments.
        onState = bulb['state'].get('on', False)
        alert = bulb['state'].get('alert', "")
        online = bulb['state'].get('reachable', False)
        nameOnBridge = bulb.get('name', "no name")
        modelId = bulb.get('modelid', "")
        manufacturerName = bulb.get('manufacturername', "")
        swVersion = bulb.get('swversion', "")
        type = bulb.get('type', "")
        uniqueId = bulb.get('uniqueid', "")

        #   Update Indigo states and properties common to all Hue devices.
        tempProps = device.pluginProps
        # -- All devices except for On/Off Only devices --
        if type[0:len(kOnOffOnlyDeviceIDType)] != kOnOffOnlyDeviceIDType:
        #if modelId not in kOnOffOnlyDeviceIDs:
            #   Value manipulation.
            brightness = bulb['state'].get('bri', 0)
            # Convert brightness from 0-255 range to 0-100 range.
            brightnessLevel = int(round(brightness / 255.0 * 100.0))
            # Compensate for incorrect rounding to zero if original brightness is not zero.
            if brightnessLevel == 0 and brightness > 0:
                brightnessLevel = 1
            # If the "on" state is False, it doesn't matter what brightness the bridge
            #   is reporting, the effective brightness is zero.
            if onState == False:
                brightnessLevel = 0
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
        if type != device.pluginProps.get('type', ""):
            tempProps['type'] = type
        # Update the unique ID (MAC address) of the Hue device.
        if uniqueId != device.pluginProps.get('uniqueId', ""):
            tempProps['uniqueId'] = uniqueId
        # If there were property changes, update the device.
        if tempProps != device.pluginProps:
            self.updateDeviceProps(device, tempProps)
        # Update the online status of the Hue device.
        self.updateDeviceState(device, 'online', online)
        # Update the error state if needed.
        if not online:
            device.setErrorStateOnServer(u"disconnected")
        else:
            device.setErrorStateOnServer(u"")
        # Update the alert state of the Hue device.
        self.updateDeviceState(device, 'alertMode', alert)

        # Device-type-specific data...

        # -- Hue Bulbs --
        if type == kHueBulbDeviceIDType:
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
            effect = bulb['state'].get('effect', "none")

            #   Value manipulation.
            # Convert from HSB to RGB, scaling the hue and saturation values appropriately.
            hsb = HSVColor(hue / 182.0, saturation / 255.0, brightness / 255.0)
            rgb = hsb.convert_to('rgb', rgb_type='wide_gamut_rgb')
            # RGB values will have a range of 0 to 255.
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
                tempProps = device.pluginProps
                # Update the brightness level if it's different.
                if device.states['brightnessLevel'] != brightnessLevel:
                    # Log the update.
                    indigo.server.log(u"\"{} on to {}".format(device.name, brightnessLevel), 'Updated')
                    self.updateDeviceState(device, 'brightnessLevel', brightnessLevel)
                # Hue Degrees (0-360).
                self.updateDeviceState(device, 'hue', hue)
                # Saturation (0-100).
                self.updateDeviceState(device, 'saturation', saturation)
                # CIE XY Cromaticity (range of 0.0 to 1.0 for X and Y)
                self.updateDeviceState(device, 'colorX', colorX, 4)		# 4 is the decimal precision.
                self.updateDeviceState(device, 'colorY', colorY, 4)		# 4 is the decimal precision.
                # Color Temperature (converted from 154-500 mireds to 6494-2000 K).
                self.updateDeviceState(device, 'colorTemp', colorTemp)
                # Color Mode.
                self.updateDeviceState(device, 'colorMode', colorMode)
                # Red, Green, Blue (0-255).
                self.updateDeviceState(device, 'colorRed', colorRed)
                self.updateDeviceState(device, 'colorGreen', colorGreen)
                self.updateDeviceState(device, 'colorBlue', colorBlue)

                ### Update inherited states for Indigo 7+ devices.
                if "whiteLevel" in device.states or "redLevel" in device.states:
                    # White Level (negative saturation, 0-100).
                    self.updateDeviceState(device, 'whiteLevel', 100 - saturation)
                    # White Temperature (0-100).
                    self.updateDeviceState(device, 'whiteTemperature', colorTemp)
                    # Red, Green, Blue levels (0-100).
                    self.updateDeviceState(device, 'redLevel', int(round(colorRed / 255.0 * 100.0)))
                    self.updateDeviceState(device, 'greenLevel', int(round(colorGreen / 255.0 * 100.0)))
                    self.updateDeviceState(device, 'blueLevel', int(round(colorBlue / 255.0 * 100.0)))

            elif onState == False:
                # Hue device is off. Set brightness to zero.
                if device.states['brightnessLevel'] != 0:
                    # Log the update.
                    indigo.server.log(u"\"{}\" off".format(device.name), 'Updated')
                    self.updateDeviceState(device, 'brightnessLevel', 0)
                # Hue Degrees (convert from 0-65535 to 0-360).
                self.updateDeviceState(device, 'hue', hue)
                # Saturation (convert from 0-255 to 0-100).
                self.updateDeviceState(device, 'saturation', saturation)
                # CIE XY Cromaticity.
                self.updateDeviceState(device, 'colorX', colorX, 4)
                self.updateDeviceState(device, 'colorY', colorY, 4)
                # Color Temperature (convert from 154-500 mireds to 6494-2000 K).
                self.updateDeviceState(device, 'colorTemp', colorTemp)
                # Color Mode.
                self.updateDeviceState(device, 'colorMode', colorMode)
                # Red, Green, and Blue Color.
                #    If the bulb is off, all RGB values should be 0.
                self.updateDeviceState(device, 'colorRed', 0)
                self.updateDeviceState(device, 'colorGreen', 0)
                self.updateDeviceState(device, 'colorBlue', 0)

                ### Update inherited states for Indigo 7+ devices.
                if "whiteLevel" in device.states or "redLevel" in device.states:
                    # White Level (negative saturation, 0-100).
                    self.updateDeviceState(device, 'whiteLevel', 100 - saturation)
                    # White Temperature (0-100).
                    self.updateDeviceState(device, 'whiteTemperature', colorTemp)
                    # Red, Green, Blue levels (0-100).
                    self.updateDeviceState(device, 'redLevel', 0)
                    self.updateDeviceState(device, 'greenLevel', 0)
                    self.updateDeviceState(device, 'blueLevel', 0)
            else:
                # Unrecognized on state, but not important enough to mention in regular log.
                self.debugLog(u"Hue bulb unrecognized on state given by bridge: {}".format(bulb['state']['on']))

            # Update the effect state (regardless of onState).
            self.updateDeviceState(device, 'effect', effect)

            # Update any Hue Device Attribute Controller virtual dimmers associated with this bulb.
            for controlDeviceId in self.controlDeviceList:
                if controlDeviceId not in indigo.devices:
                    indigo.server.log(u" control dev id:{} not in indigo device list:{}, \ntry to restart plugin".format(controlDeviceId, self.controlDeviceList))
                else:    
                    controlDevice = indigo.devices[int(controlDeviceId)]
                    attributeToControl = controlDevice.pluginProps.get('attributeToControl', None)
                    if deviceId == int(controlDevice.pluginProps.get('bulbDeviceId', -1)): # KW changed None to -1 as int(None) does not work 
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

        # -- Ambiance --
        elif type == kAmbianceDeviceIDType:
            #   Value assignment.  (Using the get() method to avoid KeyErrors).
            colorTemp = bulb['state'].get('ct', 0)
            colorMode = bulb['state'].get('colormode', "ct")
            effect = bulb['state'].get('effect', "none")

            #   Value manipulation.
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
                    indigo.server.log(u"\"{}\" on to {}".format(device.name, brightnessLevel), 'Updated')
                    self.updateDeviceState(device, 'brightnessLevel', brightnessLevel)
                # Color Temperature (converted from 154-500 mireds to 6494-2000 K).
                self.updateDeviceState(device, 'colorTemp', colorTemp)
                # Color Mode.
                self.updateDeviceState(device, 'colorMode', colorMode)

                ### Update inherited states for Indigo 7+ devices.
                if "whiteLevel" in device.states:
                    # White Level (set to the same as brightness level for ambiance lights).
                    self.updateDeviceState(device, 'whiteLevel', brightnessLevel)
                    # White Temperature (0-100).
                    self.updateDeviceState(device, 'whiteTemperature', colorTemp)

            elif onState == False:
                # Hue device is off. Set brightness to zero.
                if device.states['brightnessLevel'] != 0:
                    # Log the update.
                    indigo.server.log(u"\"{}\" off".format(device.name), 'Updated')
                    self.updateDeviceState(device, 'brightnessLevel', 0)
                # Color Temperature (converted from 154-500 mireds to 6494-2000 K).
                self.updateDeviceState(device, 'colorTemp', colorTemp)
                # Color Mode.
                self.updateDeviceState(device, 'colorMode', colorMode)

                ### Update inherited states for Indigo 7+ devices.
                if "whiteLevel" in device.states:
                    # White Level (set to 100 at all times for Ambiance bulbs).
                    self.updateDeviceState(device, 'whiteLevel', 0)
                    # White Temperature (0-100).
                    self.updateDeviceState(device, 'whiteTemperature', colorTemp)
            else:
                # Unrecognized on state, but not important enough to mention in regular log.
                self.debugLog(u"Ambiance light unrecognized \"on\" state given by bridge: {}".format(bulb['state']['on']))

            # Update the effect state (regardless of onState).
            self.updateDeviceState(device, 'effect', effect)

            # Update any Hue Device Attribute Controller virtual dimmers associated with this bulb.
            for controlDeviceId in self.controlDeviceList:
                controlDevice = indigo.devices[int(controlDeviceId)]
                attributeToControl = controlDevice.pluginProps.get('attributeToControl', None)
                if deviceId == int(controlDevice.pluginProps.get('bulbDeviceId', -1)):
                    # Device has attributes controlled by a Hue Device Attribute Controler.
                    #   Update the controller device based on current bulb device states.
                    #   But if the control destination device is off, update the value of the
                    #   controller (virtual dimmer) to 0.
                    if device.onState == True:
                        # Destination Ambiance light device is on, update Attribute Controller brightness.
                        if attributeToControl == "colorTemp":
                            # Convert color temperature scale from 2000-6500 to 0-100.
                            self.updateDeviceState(controlDevice, 'brightnessLevel', int(round((colorTemp - 2000.0) / 4500.0 * 100.0)))
                    else:
                        # Hue Device is off.  Set Attribute Controller device brightness level to 0.
                        self.updateDeviceState(controlDevice, 'brightnessLevel', 0)

        # -- Light Strips --
        elif type == kLightStripsDeviceIDType:
            #   Value assignment.  (Using the get() method to avoid KeyErrors).
            # Handle values common for "Color light" and "Extended color light" strips.
            if type in ['Color light', 'Extended color light']:
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
                saturation = int(round(saturation / 255.0 * 100.0))
                # Convert hue from 0-65535 scale to 0-360 scale.
                hue = int(round(hue / 182.0))
            # Handle color temperature values for "Extended color light" type devices.
            if type in ['Extended color light', 'Color temperature light']:
                colorTemp = bulb['state'].get('ct', 0)
                # Must first test color temp value. If it's zero, the formula throws a divide by zero execption.
                if colorTemp > 0:
                    # Converting from mireds to Kelvin.
                    colorTemp = int(round(1000000.0/colorTemp))
                else:
                    colorTemp = 0
                # Set the colorMode.
                colorMode = bulb['state'].get('colormode', "ct")
            effect = bulb['state'].get('effect', "none")

            # Update the Indigo device if the Hue device is on.
            if onState == True:
                tempProps = device.pluginProps
                # Update the brightness level if it's different.
                if device.states.get('brightnessLevel', '') != brightnessLevel:
                    # Log the update.
                    indigo.server.log(u"\"{}\" on to {}" .format(device.name, brightnessLevel), 'Updated')
                    self.updateDeviceState(device, 'brightnessLevel', brightnessLevel)
                if type in ['Color light', 'Extended color light']:
                    # We test to see if each device state actually exists with Light Strips because
                    #   a state may not exist in the device (despite the light type).
                    #
                    # Hue Degrees (0-360).
                    if 'hue' in device.states:
                        self.updateDeviceState(device, 'hue', hue)
                    # Saturation (0-100).
                    if 'saturation' in device.states:
                        self.updateDeviceState(device, 'saturation', saturation)
                    # CIE XY Cromaticity (range of 0.0 to 1.0 for X and Y)
                    if 'colorX' in device.states:
                        self.updateDeviceState(device, 'colorX', colorX, 4)
                    if 'colorY' in device.states:
                        self.updateDeviceState(device, 'colorY', colorY, 4)
                    # Red, Green, Blue (0-255).
                    if 'colorRed' in device.states:
                        self.updateDeviceState(device, 'colorRed', colorRed)
                    if 'colorGreen' in device.states:
                        self.updateDeviceState(device, 'colorGreen', colorGreen)
                    if 'colorBlue' in device.states:
                        self.updateDeviceState(device, 'colorBlue', colorBlue)
                if type in ['Extended color light', 'Color temperature light']:
                    # Color Temperature (converted from 154-500 mireds to 6494-2000 K).
                    if 'colorTemp' in device.states:
                        self.updateDeviceState(device, 'colorTemp', colorTemp)
                if type in ['Color light', 'Extended color light', 'Color temperature light']:
                    # Color Mode.
                    if 'colorMode' in device.states:
                        self.updateDeviceState(device, 'colorMode', colorMode)

                ### Update inherited states for Indigo 7+ devices.
                if "whiteLevel" in device.states or "redLevel" in device.states:
                    # Only for devices capabile of color temperature...
                    if type in ['Extended color light', 'Color temperature light']:
                        # White Level (negative saturation, 0-100).
                        if device.states.get('whiteLevel', False):
                            self.updateDeviceState(device, 'whiteLevel', 100 - saturation)
                        # White Temperature (0-100).
                        if device.states.get('whiteTemperature', False):
                            self.updateDeviceState(device, 'whiteTemperature', colorTemp)
                    if type in ['Color light', 'Extended color light']:
                        # Hue Degrees (0-360).
                        # Red, Green, Blue levels (0-100).
                        if 'redLevel' in device.states:
                            self.updateDeviceState(device, 'redLevel', int(round(colorRed / 255.0 * 100.0)))
                        if 'greenLevel' in device.states:
                            self.updateDeviceState(device, 'greenLevel', int(round(colorGreen / 255.0 * 100.0)))
                        if 'blueLevel' in device.states:
                            self.updateDeviceState(device, 'blueLevel', int(round(colorBlue / 255.0 * 100.0)))

            elif onState == False:
                # Hue device is off. Set brightness to zero.
                if device.states['brightnessLevel'] != 0:
                    # Log the update.
                    indigo.server.log(u"\"{}\" off".format(device.name), 'Updated')
                    self.updateDeviceState(device, 'brightnessLevel', 0)
                if type in ['Color light', 'Extended color light']:
                    # We test to see if each device state actually exists with Light Strips because
                    #   a state may not exist in the device (despite the light type).
                    #
                    # Hue Degrees (0-360).
                    # Hue Degrees (convert from 0-65535 to 0-360).
                    if 'hue' in device.states:
                        self.updateDeviceState(device, 'hue', hue)
                    # Saturation (convert from 0-255 to 0-100).
                    if 'saturation' in device.states:
                        self.updateDeviceState(device, 'saturation', saturation)
                    # CIE XY Cromaticity.
                    if 'colorX' in device.states:
                        self.updateDeviceState(device, 'colorX', colorX, 4)
                    if 'colorY' in device.states:
                        self.updateDeviceState(device, 'colorY', colorY, 4)
                    # Red, Green, and Blue Color.
                    #    If the bulb is off, all RGB values should be 0.
                    if 'colorRed' in device.states:
                        self.updateDeviceState(device, 'colorRed', 0)
                    if 'colorGreen' in device.states:
                        self.updateDeviceState(device, 'colorGreen', 0)
                    if 'colorBlue' in device.states:
                        self.updateDeviceState(device, 'colorBlue', 0)
                if type in ['Extended color light', 'Color temperature light']:
                    # Color Temperature (convert from 154-500 mireds to 6494-2000 K).
                    if 'colorTemp' in device.states:
                        self.updateDeviceState(device, 'colorTemp', colorTemp)
                if type in ['Color light', 'Extended color light', 'Color temperature light']:
                    # Color Mode.
                    if 'colorMode' in device.states:
                        self.updateDeviceState(device, 'colorMode', colorMode)

                ### Update inherited states for Indigo 7+ devices.
                if "whiteLevel" in device.states or "redLevel" in device.states:
                    # For color temperature devices...
                    if type in ['Color light', 'Extended color light']:
                        # Hue Degrees (0-360).
                        # Red, Green, Blue levels (0-100).
                        if 'redLevel' in device.states:
                            self.updateDeviceState(device, 'redLevel', 0)
                        if 'greenLevel' in device.states:
                            self.updateDeviceState(device, 'greenLevel', 0)
                        if 'blueLevel' in device.states:
                            self.updateDeviceState(device, 'blueLevel', 0)
                        # White Level (negative saturation, 0-100).
                        if 'whiteLevel' in device.states:
                            self.updateDeviceState(device, 'whiteLevel', 100 - saturation)
                    if type in ['Extended color light', 'Color temperature light']:
                        # White Temperature (0-100).
                        if 'whiteTemperature' in device.states:
                            self.updateDeviceState(device, 'whiteTemperature', colorTemp)
            else:
                # Unrecognized on state, but not important enough to mention in regular log.
                self.debugLog(u"LightStrip unrecognized on state given by bridge: {}".format(bulb['state']['on']))

            # Update the effect state (regardless of onState).
            if 'effect' in device.states:
                self.updateDeviceState(device, 'effect', effect)

            # Update any Hue Device Attribute Controller virtual dimmers associated with this bulb.
            for controlDeviceId in self.controlDeviceList:
                controlDevice = indigo.devices[int(controlDeviceId)]
                attributeToControl = controlDevice.pluginProps.get('attributeToControl', None)
                if deviceId == int(controlDevice.pluginProps.get('bulbDeviceId', -1)):
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
                        elif attributeToControl == "colorTemp" and type in ['Extended color light', 'Color temperature light']:
                            # Convert color temperature scale from 2000-6500 to 0-100.
                            self.updateDeviceState(controlDevice, 'brightnessLevel', int(round((colorTemp - 2000.0) / 4500.0 * 100.0)))
                    else:
                        # Hue Device is off.  Set Attribute Controller device brightness level to 0.
                        self.updateDeviceState(controlDevice, 'brightnessLevel', 0)

        # -- LivingColors --
        elif type == kLivingColorsDeviceIDType:
            #   Value assignment.
            saturation = bulb['state'].get('sat', "0")
            hue = bulb['state'].get('hue', "0")
            colorX = bulb['state'].get('xy', [0,0])[0]
            colorY = bulb['state'].get('xy', [0,0])[1]
            colorRed = 255		# Initialize for later
            colorGreen = 255	# Initialize for later
            colorBlue = 255		# Initialize for later
            colorMode = bulb['state'].get('colormode', "xy")
            effect = bulb['state'].get('effect', "none")

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
                    indigo.server.log(u"\"{}\" on to {}".format(device.name, brightnessLevel), 'Updated')
                    self.updateDeviceState(device, 'brightnessLevel', brightnessLevel)
                # Hue Degrees (0-360).
                self.updateDeviceState(device, 'hue', hue)
                #   Saturation (0-100).
                self.updateDeviceState(device, 'saturation', saturation)
                #   CIE XY Cromaticity.
                self.updateDeviceState(device, 'colorX', colorX, 4)
                self.updateDeviceState(device, 'colorY', colorY, 4)
                #   Color Mode.
                self.updateDeviceState(device, 'colorMode', colorMode)
                #   Red, Green, Blue.
                self.updateDeviceState(device, 'colorRed', colorRed)
                self.updateDeviceState(device, 'colorGreen', colorGreen)
                self.updateDeviceState(device, 'colorBlue', colorBlue)

                ### Update inherited states for Indigo 7+ devices.
                if "redLevel" in device.states:
                    # Red, Green, Blue levels (0-100).
                    self.updateDeviceState(device, 'redLevel', int(round(colorRed / 255.0 * 100.0)))
                    self.updateDeviceState(device, 'greenLevel', int(round(colorGreen / 255.0 * 100.0)))
                    self.updateDeviceState(device, 'blueLevel', int(round(colorBlue / 255.0 * 100.0)))

            elif onState == False:
                # Hue device is off. Set brightness to zero.
                if device.states['brightnessLevel'] != 0:
                    # Log the update.
                    indigo.server.log(u"\"{}\" off".format(device.name), 'Updated')
                    self.updateDeviceState(device, 'brightnessLevel', 0)
                # Hue Degrees (convert from 0-65535 to 0-360).
                self.updateDeviceState(device, 'hue', hue)
                # Saturation (convert from 0-255 to 0-100).
                self.updateDeviceState(device, 'saturation', saturation)
                # CIE XY Cromaticity.
                self.updateDeviceState(device, 'colorX', colorX, 4)
                self.updateDeviceState(device, 'colorY', colorY, 4)
                # Color Mode.
                self.updateDeviceState(device, 'colorMode', colorMode)
                # Red, Green, and Blue Color.
                #    If the bulb is off, all RGB values should be 0.
                self.updateDeviceState(device, 'colorRed', 0)
                self.updateDeviceState(device, 'colorGreen', 0)
                self.updateDeviceState(device, 'colorBlue', 0)

                ### Update inherited states for Indigo 7+ devices.
                if "redLevel" in device.states:
                    # Red, Green, Blue levels (0-100).
                    self.updateDeviceState(device, 'redLevel', int(round(colorRed / 255.0 * 100.0)))
                    self.updateDeviceState(device, 'greenLevel', int(round(colorGreen / 255.0 * 100.0)))
                    self.updateDeviceState(device, 'blueLevel', int(round(colorBlue / 255.0 * 100.0)))
            else:
                # Unrecognized on state, but not important enough to mention in regular log.
                self.debugLog(u"LivingColors unrecognized on state given by bridge: {}".format(bulb['state']['on']))

            # Update the effect state (regardless of onState).
            self.updateDeviceState(device, 'effect', effect)

            # Update any Hue Device Attribute Controller virtual dimmers associated with this bulb.
            for controlDeviceId in self.controlDeviceList:
                controlDevice = indigo.devices[int(controlDeviceId)]
                attributeToControl = controlDevice.pluginProps.get('attributeToControl', None)
                if deviceId == int(controlDevice.pluginProps.get('bulbDeviceId', -1)):
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
        elif type == kLivingWhitesDeviceIDType:
        #elif modelId in kLivingWhitesDeviceIDs:
            # Update the Indigo device if the Hue device is on.
            if onState == True:
                # Update the brightness level if it's different.
                if device.states['brightnessLevel'] != brightnessLevel:
                    # Log the update.
                    indigo.server.log(u"\"{}\" on to {}".format(device.name, brightnessLevel), 'Updated')
                    self.updateDeviceState(device, 'brightnessLevel', brightnessLevel)
            elif onState == False:
                # Hue device is off. Set brightness to zero.
                if device.states['brightnessLevel'] != 0:
                    # Log the update.
                    indigo.server.log(u"\"{}\" off".format(device.name), 'Updated')
                    self.updateDeviceState(device, 'brightnessLevel', 0)
            else:
                # Unrecognized on state, but not important enough to mention in regular log.
                self.debugLog(u"LivingWhites unrecognized on state given by bridge: {}".format(bulb['state']['on']))

            # There won't any Hue Device Attribute Controller virtual dimmers associated with this bulb,
            # so we won't bother checking them.

        # -- On/Off Only Device --
        elif type[0:len(kOnOffOnlyDeviceIDType)] == kOnOffOnlyDeviceIDType:
        #elif modelId in kOnOffOnlyDeviceIDs:
            # Update the Indigo device if the Hue device is on.
            if onState == True:
                # Update the onState if it's different.
                if device.onState != onState:
                    # Log the update.
                    indigo.server.log(u"\"" + device.name + "\" on", 'Updated')
                    self.updateDeviceState(device, 'onOffState', onState, None, "on")
            elif onState == False:
                # Update the onState if it's different.
                if device.onState != onState:
                    # Log the update.
                    indigo.server.log(u"\"{}\" off".format(device.name), 'Updated')
                    self.updateDeviceState(device, 'onOffState', onState, None, "off")
            else:
                # Unrecognized on state, but not important enough to mention in regular log.
                self.debugLog(u"On/Off device unrecognized on state given by bridge: {}".format(bulb['state']['on']))

            # There won't be any Hue Device Attribute Controller virtual dimmers associated with this device,
            # so we won't bother checking..

        else:
            # Unrecognized model ID.
            if not self.unsupportedDeviceWarned:
                errorText = u"The \"{}\" device has an unrecognized model ID:{}.  Hue Lights plugin does not support this device.".format( device.name,  bulb.get('modelid', ""))
                self.errorLog(errorText)
                # Remember the error.
                self.lastErrorMessage = errorText
                self.unsupportedDeviceWarned = True
        # End of model ID matching if/then test.


    # Parse All Hue Groups Data
    ########################################
    def parseAllHueGroupsData(self):
        self.debugLog(u"Starting parseAllHueGroupsData.")

        # Itterate through all the Indigo devices and look for Hue group changes in the
        #   self.groupsDict that changed, then update the Indigo device states and properties
        #   as needed.  This method does no actual Hue bridge communication.  It just updates
        #   Indigo devices with information already obtained through the use of the
        #   self.updateGroupsList.

        ## self.debugLog(u"parseAllHueGroupsData: There are %i groups on the Hue bridge and %i Indigo devices controlling Hue lights and groups." % (len(self.groupsDict), len(self.deviceList)))
        # Start going through all the devices in the self.deviceList and update any Indigo
        #   devices that are controlling the Hue group devices.
        for deviceId in self.deviceList:
            device = indigo.devices[deviceId]
            ## self.debugLog(u"parseAllHueGroupsData: Looking at Indigo device \"%s\"." % (device.name))

            # If this Indigo device is for a Hue Group...
            if device.deviceTypeId in kGroupDeviceTypeIDs:
                ## self.debugLog(u"parseAllHueGroupsData: Indigo device \"%s\" is for a Hue group. Proceeing." % (device.name))

                for hubNumber in self.ipAddresses:
                    # Go through each Hue group device and see if it is controlled by this Indigo device.
                    for groupId in self.groupsDict[hubNumber]:
                        # Grab the entire set of group data from the groupsDict first.
                        group = self.groupsDict[hubNumber][groupId]
                        ## self.debugLog(u"parseAllHueGroupsData: Parsing Hue group ID %s (\"%s\")." % (groupId, group.get('name', "no name")))
                        # Is this Hue group ID the one associated with this Indigo device?
                        if groupId == device.pluginProps['groupId']:
                            ## self.debugLog(u"parseAllHueGroupsData: Indigo device \"%s\" is controlling Hue group ID \"%s\" (\"%s\"). Updating Indigo device properties and states." % (device.name, groupId, group.get('name', "no name")))
                            # Attempt to update the Indigo device with the Hue group data.
                            self.parseOneHueGroupData(group, device)
                            # Since only one Hue gruop can be controlled by one Indigo device, we're done here.
                            break
                        # End if Hue group is being controlled by this Indigo device.
                    # End loop through self.groupsDict.
            # End check if this is a Hue Group device.
        # End loop through self.deviceList.

    # Parse One Hue Group Data
    ########################################
    def parseOneHueGroupData(self, group, device):
        self.debugLog(u"Starting parseOneHueGroupData.")

        # Take the groupId and device passed to this method, look up the data already obtained from the Hue bridge
        # and parse the bridge data for this group, making changes to the Indigo device as needed.

        deviceId = device.id

        # Separate out the specific Hue group data.
        nameOnBridge = group.get('name', "")
        groupType = group.get('type', "")
        groupClass = group.get('class', "")
        if "action" not in group:
            indigo.server.log(u"no action key in dev:{}, group:{}".format(device.id, group))
            return 
        brightness = group['action'].get('bri', 0)
        onState = group['action'].get('on', False)
        allOn = group['state'].get('all_on', False)
        anyOn = group['state'].get('any_on', False)
        effect = group['action'].get('effect', "")
        alert = group['action'].get('alert', "")
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

        i = 0		# To count members in group.
        for tempMemberID in group['lights']:
            if i > 0:
                groupMemberIDs = u"{}, {}".format(groupMemberIDs, tempMemberID)
            else:
                groupMemberIDs = tempMemberID
            i += 1
        # Clear the "i" variable.
        del i

        #   Value manipulation.
        # Convert brightness from 0-255 range to 0-100 range.
        brightnessLevel = int(round(brightness / 255.0 * 100.0))
        # Compensate for incorrect rounding to zero if original brightness is not zero.
        if brightnessLevel == 0 and brightness > 0:
            brightnessLevel = 1
        # If the "on" state is False, it doesn't matter what brightness the bridge
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
        self.updateDeviceState(device, 'allOn', allOn)
        # Update the anyOn state.
        self.updateDeviceState(device, 'anyOn', anyOn)
        # Update the alert state.
        self.updateDeviceState(device, 'alertMode', alert)
        # Update the effect state.
        self.updateDeviceState(device, 'effect', effect)
        # Update the group member IDs.
        self.updateDeviceState(device, 'groupMemberIDs', groupMemberIDs)

        # Update the Indigo device if the Hue group is on.
        if onState == True:
            # Update the brightness level if it's different.
            if device.states['brightnessLevel'] != brightnessLevel:
                # Log the update.
                indigo.server.log(u"\"" + device.name + "\" on to {}".format(brightnessLevel), 'Updated')
                self.updateDeviceState(device, 'brightnessLevel', brightnessLevel)
            # Hue Degrees (0-360).
            self.updateDeviceState(device, 'hue', hue)
            # Saturation (0-100).
            self.updateDeviceState(device, 'saturation', saturation)
            # CIE XY Cromaticity.
            self.updateDeviceState(device, 'colorX', colorX, 4)		# 4 is the decimal precision.
            self.updateDeviceState(device, 'colorY', colorY, 4)		# 4 is the decimal precision.
            # Color Temperature (converted from 154-500 mireds to 6494-2000 K).
            self.updateDeviceState(device, 'colorTemp', colorTemp)
            # Color Mode.
            self.updateDeviceState(device, 'colorMode', colorMode)
            # Red, Green, Blue.
            self.updateDeviceState(device, 'colorRed', colorRed)
            self.updateDeviceState(device, 'colorGreen', colorGreen)
            self.updateDeviceState(device, 'colorBlue', colorBlue)

            ### Update inherited states for Indigo 7+ devices.
            if "whiteLevel" in device.states or "redLevel" in device.states:
                # White Level (negative saturation, 0-100).
                self.updateDeviceState(device, 'whiteLevel', 100 - saturation)
                # White Temperature (0-100).
                self.updateDeviceState(device, 'whiteTemperature', colorTemp)
                # Red, Green, Blue levels (0-100).
                self.updateDeviceState(device, 'redLevel', int(round(colorRed / 255.0 * 100.0)))
                self.updateDeviceState(device, 'greenLevel', int(round(colorGreen / 255.0 * 100.0)))
                self.updateDeviceState(device, 'blueLevel', int(round(colorBlue / 255.0 * 100.0)))

        elif onState == False:
            # Hue group is off. Set brightness to zero.
            if device.states['brightnessLevel'] != 0:
                # Log the update.
                indigo.server.log(u"\"{}\" off".format(device.name), 'Updated')
                self.updateDeviceState(device, 'brightnessLevel', 0)
            # Hue Degrees (convert from 0-65535 to 0-360).
            self.updateDeviceState(device, 'hue', hue)
            # Saturation (convert from 0-255 to 0-100).
            self.updateDeviceState(device, 'saturation', saturation)
            # CIE XY Cromaticity.
            self.updateDeviceState(device, 'colorX', colorX, 4)		# 4 is the decimal precision.
            self.updateDeviceState(device, 'colorY', colorY, 4)		# 4 is the decimal precision.
            # Color Temperature (convert from 154-500 mireds to 6494-2000 K).
            self.updateDeviceState(device, 'colorTemp', colorTemp)
            # Color Mode.
            self.updateDeviceState(device, 'colorMode', colorMode)
            # Red, Green, and Blue Color.
            #    If the bulb is off, all RGB values should be 0.
            self.updateDeviceState(device, 'colorRed', 0)
            self.updateDeviceState(device, 'colorGreen', 0)
            self.updateDeviceState(device, 'colorBlue', 0)
            # Effect
            self.updateDeviceState(device, 'effect', "")
            # Alert
            self.updateDeviceState(device, 'alertMode', "")

            ### Update inherited states for Indigo 7+ devices.
            if "whiteLevel" in device.states or "redLevel" in device.states:
                # White Level (negative saturation, 0-100).
                self.updateDeviceState(device, 'whiteLevel', 100 - saturation)
                # White Temperature (0-100).
                self.updateDeviceState(device, 'whiteTemperature', colorTemp)
                # Red, Green, Blue levels (0-100).
                self.updateDeviceState(device, 'redLevel', int(round(colorRed / 255.0 * 100.0)))
                self.updateDeviceState(device, 'greenLevel', int(round(colorGreen / 255.0 * 100.0)))
                self.updateDeviceState(device, 'blueLevel', int(round(colorBlue / 255.0 * 100.0)))
        else:
            # Unrecognized on state, but not important enough to mention in regular log.
            self.debugLog(u"Hue group unrecognized on state given by bridge: {}".format(group['action']['on']))

        # Update any Hue Device Attribute Controller virtual dimmers associated with this group.
        for controlDeviceId in self.controlDeviceList:
            controlDevice = indigo.devices[int(controlDeviceId)]
            attributeToControl = controlDevice.pluginProps.get('attributeToControl', None)
            if deviceId == int(controlDevice.pluginProps.get('bulbDeviceId', -1)):
                # Device has attributes controlled by a Hue Device Attribute Controler.
                #   Update the controller device based on current group device states.
                #   But if the control destination device is off, update the value of the
                #   controller (virtual dimmer) to 0.
                if device.onState == True:
                    # Destination Hue Group device is on, update Attribute Controller brightness.
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
                # End if device onState is True.
            # End if this device is an the current attribute controller device.
        # End loop through attribute controller device list.

    # Parse All Hue Users (User Device) Data
    ########################################
    def parseAllHueUsersData(self):
        self.debugLog(u"Starting parseAllHueUsersData.")
        # Soon to be filled in.

    # Parse All Hue Scenes Data
    ########################################
    def parseAllHueScenesData(self):
        self.debugLog(u"Starting parseAllHueScenesData.")
        # Soon to be filled in.

    # Parse All Hue Sensors Data
    ########################################
    def parseAllHueSensorsData(self):
        self.debugLog(u"Starting parseAllHueSensorsData.")

        # Itterate through all the Indigo devices and look for Hue sensor changes in the
        #   self.sensorsDict that changed, then update the Indigo device states and properties
        #   as needed.  This method does no actual Hue bridge communication.  It just updates
        #   Indigo devices with information already obtained through the use of the
        #   self.updateSensorsList.

        ## self.debugLog(u"parseAllHueSensorsData: There are %i sensors on the Hue bridge and %i Indigo devices controlling Hue devices." % (len(self.sensorsDict), len(self.deviceList)))
        # Start going through all the devices in the self.deviceList and update any Indigo
        #   devices that are controlling the Hue sensors devices.
        for deviceId in self.deviceList:
            device = indigo.devices[deviceId]
            ## self.debugLog(u"parseAllHueSensorsData: Looking at Indigo device \"%s\"." % (device.name))

            # -- Hue Sensor  --
            if device.deviceTypeId in ['hueMotionSensor', 'hueMotionTemperatureSensor', 'hueMotionLightSensor', 'hueTapSwitch', 'hueDimmerSwitch', 'hueSmartButton', 'hueWallSwitchModule', 'runLessWireSwitch']:
                ## self.debugLog(u"parseAllHueSensorsData: Indigo device \"%s\" is for a Hue Motion Sensor (Motion) sensor. Proceeing." % (device.name))

                for hubNumber in self.ipAddresses:
                    # Go through each Hue sensor device and see if it is controlled by this Indigo device.
                
                    for sensorId in self.sensorsDict[hubNumber]:
                        sensor = self.sensorsDict[hubNumber][sensorId]
                        ## self.debugLog(u"parseAllHueSensorsData: Parsing Hue sensor ID %s (\"%s\")." % (sensorId, sensor.get('name', "no name")))
                        # Is this Hue sensor ID the one associated with this Indigo device?
                        if sensorId == device.pluginProps['sensorId']:
                            ## self.debugLog(u"parseAllHueSensorsData: Indigo device \"%s\" is controlling Hue sensor ID \"%s\" (\"%s\"). Updating Indigo device properties and states." % (device.name, sensorId, sensor.get('name', "no name")))

                            # It is, so call the method that assigns sensor data to the Indigo device.
                            self.parseOneHueSensorData(sensor, device)

                        # End check if this Hue Sensor device is the one associated with the Indigo device.
                    # End loop through self.sensorsDict.

        # End loop through self.deviceList.

    # Parse One Hue Sensor Data
    ########################################
    def parseOneHueSensorData(self, sensor, device):
        ## self.debugLog(u"Starting parseOneHueSensorData.")

        # -- Hue Motion Sensor (Motion) --
        if device.deviceTypeId == "hueMotionSensor":
            ## self.debugLog(u"parseOneHueSensorData: Parsing Hue sensor ID %s (\"%s\")." % (device.pluginProps.get('sensorId', ""), sensor.get('name', "no name")))

            # Separate out the specific Hue sensor data.
            nameOnBridge = sensor.get('name', "")
            uniqueId = sensor.get('uniqueid', "")
            productId = sensor.get('productid', "")
            swVersion = sensor.get('swversion', "")
            manufacturerName = sensor.get('manufacturername', "")
            sensorType = sensor.get('type', "")
            modelId = sensor.get('modelid', "")
            enabledOnbridge = sensor['config'].get('on', True)
            batteryLevel = sensor['config'].get('battery', 0)
            sensitivity = sensor['config'].get('sensitivity', 0)
            sensitivityMax = sensor['config'].get('sensitivitymax', 0)
            testMode = sensor['config'].get('usertest', False)
            ledEnabled = sensor['config'].get('ledindication', False)
            alert = sensor['config'].get('alert', "none")
            online = sensor['config'].get('reachable', False)
            onStateBool = sensor['state'].get('presence', False)
            # Convert True/False onState to on/off values.  Note that the value can be None if the sensor is disabled on the bridge.
            if onStateBool == True:
                onState = "on"
                sensorIcon = indigo.kStateImageSel.MotionSensorTripped
            elif onStateBool == False:
                onState = "off"
                sensorIcon = indigo.kStateImageSel.MotionSensor
            lastUpdated = sensor['state'].get('lastupdated', "")

            #   Update Indigo states and properties.
            tempProps = device.pluginProps
            # Update the device properties.
            tempProps['nameOnBridge'] = nameOnBridge
            tempProps['uniqueId'] = uniqueId
            tempProps['productId'] = productId
            tempProps['swVersion'] = swVersion
            tempProps['manufacturerName'] = manufacturerName
            tempProps['type'] = sensorType
            tempProps['modelId'] = modelId
            tempProps['enabledOnbridge'] = enabledOnbridge
            self.updateDeviceProps(device, tempProps)

            # Update the states on the device.
            self.updateDeviceState(device, 'alertMode', alert)
            self.updateDeviceState(device, 'sensitivity', sensitivity)
            self.updateDeviceState(device, 'sensitivityMax', sensitivityMax)
            self.updateDeviceState(device, 'online', online)
            self.updateDeviceState(device, 'testMode', testMode)
            self.updateDeviceState(device, 'ledEnabled', ledEnabled)
            self.updateDeviceState(device, 'lastUpdated', lastUpdated)
            self.updateDeviceState(device, 'batteryLevel', batteryLevel)
            # Update the device on state.  Only update if the device is enabled on the bridge though.
            if enabledOnbridge:
                # Log any change to the onState.
                if onStateBool != device.onState:
                    indigo.server.log(u"received \"" + device.name + u"\" status update is " + onState, 'Hue Lights')
                self.updateDeviceState(device, 'onOffState', onStateBool, 0, onState, sensorIcon)
            # Update the error state if needed.
            if not online:
                device.setErrorStateOnServer("disconnected")
            elif not enabledOnbridge:
                device.setErrorStateOnServer("disabled")
            else:
                device.setErrorStateOnServer("")
        # End if this is a Hue motion sensor.

        # -- Hue Motion Sensor (Temperature) --
        if device.deviceTypeId == "hueMotionTemperatureSensor":
            ## self.debugLog(u"parseOneHueSensorData: Parsing Hue sensor ID %s (\"%s\")." % (device.pluginProps.get('sensorId', ""), sensor.get('name', "no name")))

            # Separate out the specific Hue sensor data.
            # Get the name of the sensor as it appears on the Hue bridge.
            nameOnBridge = sensor.get('name', "")
            uniqueId = sensor.get('uniqueid', "")
            productId = sensor.get('productid', "")
            swVersion = sensor.get('swversion', "")
            manufacturerName = sensor.get('manufacturername', "")
            sensorType = sensor.get('type', "")
            modelId = sensor.get('modelid', "")
            enabledOnbridge = sensor['config'].get('on', True)
            batteryLevel = sensor['config'].get('battery', 0)
            testMode = sensor['config'].get('usertest', False)
            ledEnabled = sensor['config'].get('ledindication', False)
            alert = sensor['config'].get('alert', "none")
            online = sensor['config'].get('reachable', False)
            temperatureRaw = sensor['state'].get('temperature', 0)
            lastUpdated = sensor['state'].get('lastupdated', "")

            # Update Indigo properties and states.
            tempProps = device.pluginProps
            # Update the device properties.
            tempProps['nameOnBridge'] = nameOnBridge
            tempProps['uniqueId'] = uniqueId
            tempProps['productId'] = productId
            tempProps['swVersion'] = swVersion
            tempProps['manufacturerName'] = manufacturerName
            tempProps['type'] = sensorType
            tempProps['modelId'] = modelId
            tempProps['enabledOnbridge'] = enabledOnbridge
            self.updateDeviceProps(device, tempProps)

            # Get the calibration offset specified in the device settings.
            sensorOffset = device.pluginProps.get('sensorOffset', 0)
            try:
                sensorOffset = round(float(sensorOffset), 1)
            except Exception, e:
                # If there's any conversion error, just use a zero offset.
                sensorOffset = 0.0
            # Get the temperature scale specified in the device settings.
            temperatureScale = device.pluginProps.get('temperatureScale', "c")
            # Only perform temperature conversion calculations of the sensor is enabled on the bridge.
            if enabledOnbridge:
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
                    sensorUiValue = u"{} \xbaF".format(sensorValue) + u""
                else:
                    sensorValue = temperatureC
                    sensorUiValue = u"{} \xbaC".format(sensorValue) + u""

            sensorIcon = indigo.kStateImageSel.TemperatureSensor
            sensorPrecision = 1

            # Update the states on the device.
            self.updateDeviceState(device, 'alertMode', alert)
            self.updateDeviceState(device, 'online', online)
            self.updateDeviceState(device, 'testMode', testMode)
            self.updateDeviceState(device, 'ledEnabled', ledEnabled)
            self.updateDeviceState(device, 'lastUpdated', lastUpdated)
            self.updateDeviceState(device, 'batteryLevel', batteryLevel)
            # Update the device sensorValue state.  Only update if the device is enabled on the bridge though.
            if enabledOnbridge:
                # Log any change to the sensorValue.
                if sensorValue != device.sensorValue:
                    indigo.server.log(u"received \"" + device.name + u"\" sensor update to " + sensorUiValue, 'Hue Lights')
                self.updateDeviceState(device, 'temperatureC', temperatureC, sensorPrecision)
                self.updateDeviceState(device, 'temperatureF', temperatureF, sensorPrecision)
                self.updateDeviceState(device, 'sensorValue', sensorValue, sensorPrecision, sensorUiValue, sensorIcon)
            # Update the error state if needed.
            if not online:
                device.setErrorStateOnServer("disconnected")
            elif not enabledOnbridge:
                device.setErrorStateOnServer("disabled")
            else:
                device.setErrorStateOnServer("")
        # End if this is a Hue temperature sensor.

        # -- Hue Motion Sensor (Luninance) --
        if device.deviceTypeId == "hueMotionLightSensor":
            ## self.debugLog(u"parseOneHueSensorData: Parsing Hue sensor ID %s (\"%s\")." % (device.pluginProps.get('sensorId', ""), sensor.get('name', "no name")))

            # Separate out the specific Hue sensor data.
            # Get the name of the sensor as it appears on the Hue bridge.
            nameOnBridge = sensor.get('name', "")
            uniqueId = sensor.get('uniqueid', "")
            productId = sensor.get('productid', "")
            swVersion = sensor.get('swversion', "")
            manufacturerName = sensor.get('manufacturername', "")
            sensorType = sensor.get('type', "")
            modelId = sensor.get('modelid', "")
            enabledOnbridge = sensor['config'].get('on', True)
            batteryLevel = sensor['config'].get('battery', 0)
            testMode = sensor['config'].get('usertest', False)
            ledEnabled = sensor['config'].get('ledindication', False)
            alert = sensor['config'].get('alert', "none")
            online = sensor['config'].get('reachable', False)
            luminanceRaw = sensor['state'].get('lightlevel', 0)
            lastUpdated = sensor['state'].get('lastupdated', "")
            dark = sensor['state'].get('dark', True)
            # If a sensor is disabled on the bridge, the value will be None so we have to account for this.
            if dark == None:
                dark = True
            daylight = sensor['state'].get('daylight', False)
            # If a sensor is disabled on the bridge, the value will be None so we have to account for this.
            if daylight == None:
                daylight = False
            darkThreshold = sensor['config'].get('tholddark', 0)
            thresholdOffset = sensor['config'].get('tholdoffset', 0)

            #   Update Indigo properties and states.
            tempProps = device.pluginProps
            # Update the device properties.
            tempProps['nameOnBridge'] = nameOnBridge
            tempProps['uniqueId'] = uniqueId
            tempProps['productId'] = productId
            tempProps['swVersion'] = swVersion
            tempProps['manufacturerName'] = manufacturerName
            tempProps['type'] = sensorType
            tempProps['modelId'] = modelId
            tempProps['enabledOnbridge'] = enabledOnbridge
            self.updateDeviceProps(device, tempProps)

            # Only convert raw luminance values to lux if the sensor is enabled on the bridge.
            if enabledOnbridge:
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
                if 0 < luminance and luminance < 10:
                    sensorPrecision = 2
                elif 10 <= luminance and luminance < 100:
                    sensorPrecision = 1
                else:
                    sensorPrecision = 0
                # Now round and set the sensorValue.
                if sensorPrecision > 0:
                    sensorValue = round(luminance, sensorPrecision)
                else:
                    sensorValue = int(round(luminance, 0))
                sensorUiValue = u"{} lux".format(sensorValue)

            # Now do the same for the darkThreshold and thresholdOffset values.
            if 0 < darkThreshold and darkThreshold < 10:
                thresholdPrecision = 2
            elif 10 <= darkThreshold and darkThreshold < 100:
                thresholdPrecision = 1
            else:
                thresholdPrecision = 0
            if thresholdPrecision > 0:
                darkThreshold = round(darkThreshold, thresholdPrecision)
            else:
                darkThreshold = int(round(darkThreshold, 0))

            if 0 < thresholdOffset and thresholdOffset < 10:
                offsetPrecision = 2
            elif 10 <= thresholdOffset and thresholdOffset < 100:
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

            # Update the states on the device.
            self.updateDeviceState(device, 'alertMode', alert)
            self.updateDeviceState(device, 'dark', dark)
            self.updateDeviceState(device, 'darkThreshold', darkThreshold, thresholdPrecision)
            self.updateDeviceState(device, 'thresholdOffset', thresholdOffset, offsetPrecision)
            self.updateDeviceState(device, 'daylight', daylight)
            self.updateDeviceState(device, 'online', online)
            self.updateDeviceState(device, 'testMode', testMode)
            self.updateDeviceState(device, 'ledEnabled', ledEnabled)
            self.updateDeviceState(device, 'lastUpdated', lastUpdated)
            self.updateDeviceState(device, 'batteryLevel', batteryLevel)
            # Update the sensor value, but only if the sensor is enabled on the bridge.
            if enabledOnbridge:
                # Log any change to the sensorValue.
                if sensorValue != device.sensorValue:
                    indigo.server.log(u"received \"" + device.name + u"\" sensor update to " + sensorUiValue, 'Hue Lights')
                self.updateDeviceState(device, 'luminance', luminance, sensorPrecision)
                self.updateDeviceState(device, 'luminanceRaw', luminanceRaw)
                self.updateDeviceState(device, 'sensorValue', sensorValue, sensorPrecision, sensorUiValue, sensorIcon)
            # Update the error state if needed.
            if not online:
                device.setErrorStateOnServer("disconnected")
            elif not enabledOnbridge:
                device.setErrorStateOnServer("disabled")
            else:
                device.setErrorStateOnServer("")
        # End if this is a Hue luminance sensor.

        # -- Hue Tap Switch --
        if device.deviceTypeId == "hueTapSwitch":
            ## self.debugLog(u"parseOneHueSensorData: Parsing Hue sensor ID %s (\"%s\")." % (device.pluginProps.get('sensorId', ""), sensor.get('name', "no name")))

            # Separate out the specific Hue sensor data.
            nameOnBridge = sensor.get('name', "")
            uniqueId = sensor.get('uniqueid', "")
            manufacturerName = sensor.get('manufacturername', "")
            sensorType = sensor.get('type', "")
            modelId = sensor.get('modelid', "")
            enabledOnbridge = sensor['config'].get('on', True)
            buttonEventID = sensor['state'].get('buttonevent', 0)
            lastUpdated = sensor['state'].get('lastupdated', "")
            # The lastButtonPressed variable is used for the device state of the same name.
            # 0 = No button has been pressed since device was paired with Hue bridge.
            # 1 = Button 1
            # 2 = Button 2
            # 3 = Button 3
            # 4 = Button 4
            lastButtonPressed = 0
            onStateBool = False
            # Create initial value assignments for all the buttons.
            button1On			= False
            button2On			= False
            button3On			= False
            button4On			= False
            # Populate the button on/off states based on this buttonEventID.
            # -- BUTTON 1 --
            if buttonEventID == 34:
                # Update the last button pressed state variable.
                lastButtonPressed = 1
                # Only set the button ON condition if the lastUpdated value has changed.
                if lastUpdated != device.states['lastUpdated']:
                    button1On = True
                    # Log any change to the onState.
                    indigo.server.log(u"received \"" + device.name + u"\" button 1 press", 'Hue Lights')
            # -- BUTTON 2 --
            elif buttonEventID == 16:
                lastButtonPressed = 2
                if lastUpdated != device.states['lastUpdated']:
                    button2On = True
                    indigo.server.log(u"received \"" + device.name + u"\" button 2 press", 'Hue Lights')
            # -- BUTTON 3 --
            elif buttonEventID == 17:
                lastButtonPressed = 3
                if lastUpdated != device.states['lastUpdated']:
                    button3On = True
                    indigo.server.log(u"received \"" + device.name + u"\" button 3 press", 'Hue Lights')
            # -- BUTTON 4 --
            elif buttonEventID == 18:
                lastButtonPressed = 4
                if lastUpdated != device.states['lastUpdated']:
                    button4On = True
                    indigo.server.log(u"received \"" + device.name + u"\" button 4 press", 'Hue Lights')

            if button1On or button2On or button3On or button4On:
                onStateBool = True

            # Convert True/False onState to on/off values.
            if onStateBool:
                onState = "on"
                sensorIcon = indigo.kStateImageSel.PowerOn
            else:
                onState = "off"
                sensorIcon = indigo.kStateImageSel.PowerOff

            #   Update Indigo states and properties.
            tempProps = device.pluginProps
            # Update the device properties.
            tempProps['nameOnBridge'] = nameOnBridge
            tempProps['uniqueId'] = uniqueId
            tempProps['manufacturerName'] = manufacturerName
            tempProps['type'] = sensorType
            tempProps['modelId'] = modelId
            tempProps['enabledOnbridge'] = enabledOnbridge
            self.updateDeviceProps(device, tempProps)

            # Update the states on the device.
            self.updateDeviceState(device, 'button1On', button1On)
            self.updateDeviceState(device, 'button2On', button2On)
            self.updateDeviceState(device, 'button3On', button3On)
            self.updateDeviceState(device, 'button4On', button4On)
            self.updateDeviceState(device, 'lastButtonPressed', lastButtonPressed)
            self.updateDeviceState(device, 'lastUpdated', lastUpdated)
            self.updateDeviceState(device, 'buttonEventID', buttonEventID)
            # Update the device state.  Passing device object, state name, state value, decimal precision, display value, icon selection.
            self.updateDeviceState(device, 'onOffState', onStateBool, 0, onState, sensorIcon)
        # End if this is a Hue Tap Switch sensor.

        # -- Hue Dimmer Switch --
        if device.deviceTypeId == "hueDimmerSwitch":
            ## self.debugLog(u"parseOneHueSensorData: Parsing Hue sensor ID %s (\"%s\")." % (device.pluginProps.get('sensorId', ""), sensor.get('name', "no name")))

            # Separate out the specific Hue sensor data.
            nameOnBridge = sensor.get('name', "")
            uniqueId = sensor.get('uniqueid', "")
            productId = sensor.get('productid', "")
            swVersion = sensor.get('swversion', "")
            manufacturerName = sensor.get('manufacturername', "")
            sensorType = sensor.get('type', "")
            modelId = sensor.get('modelid', "")
            enabledOnbridge = sensor['config'].get('on', True)
            batteryLevel = sensor['config'].get('battery', 0)
            online = sensor['config'].get('reachable', False)
            buttonEventID = sensor['state'].get('buttonevent', 0)
            lastUpdated = sensor['state'].get('lastupdated', "")
            # The lastButtonPressed variable is used for the device state of the same name.
            # 0 = No button has been pressed since device was paired with Hue bridge.
            # 1 = ON button
            # 2 = DIM UP button
            # 3 = DIM DOWN button
            # 4 = OFF button
            lastButtonPressed = 0
            onStateBool = False
            # Create initial value assignments for all the buttons.
            button1On			= False
            button1Hold			= False
            button1ReleaseShort	= False
            button1ReleaseLong	= False
            button2On			= False
            button2Hold			= False
            button2ReleaseShort	= False
            button2ReleaseLong	= False
            button3On			= False
            button3Hold			= False
            button3ReleaseShort	= False
            button3ReleaseLong	= False
            button4On			= False
            button4Hold			= False
            button4ReleaseShort	= False
            button4ReleaseLong	= False
            # Populate the button on/off states based on this buttonEventID.
            # -- BUTTON 1 --
            if buttonEventID == 1000:
                # Update the last button pressed state variable.
                lastButtonPressed = 1
                # Sometimes the Hue bridge doesn't detect button releases from the Dimmer Switch and
                #   will continue to show the most recent button event as the initial press event.
                #   If the lastUpdated value from the Hue bridge hasn't changed, then allow the button
                #   on state to revert back to OFF (False) as set above. But if the lastUpdated value
                #   from the Hue bridge is different, then this must be a new initial button press,
                #   so set the button on state to True.
                if lastUpdated != device.states['lastUpdated']:
                    button1On = True
                    # Log any change to the onState.
                    indigo.server.log(u"received \"" + device.name + u"\" ON button press", 'Hue Lights')
            elif buttonEventID == 1001:
                lastButtonPressed = 1
                button1On = True
                button1Hold = True
                # Don't write to the Indigo log unless this is the first time this status has been seen.
                if button1Hold != device.states['button1Hold']:
                    indigo.server.log(u"received \"" + device.name + u"\" ON button press and hold", 'Hue Lights')
            elif buttonEventID == 1002:
                lastButtonPressed = 1
                button1ReleaseShort = True
                # We're checking to see if a button press event was missed since we can only check the
                #   Hue bridge every 2 seconds or so.  If the last button event was a button release
                #   but the current device state for the button shows it was never on, and the lastUpdated
                #   time on the Hue bridge is different than that in the Indigo device, then the button
                #   had to have been pressed at some point, so we'll set the button ON state to True.
                if lastUpdated != device.states['lastUpdated']:
                    # Update the Indigo log about the received button event regardless of current on state.
                    indigo.server.log(u"received \"" + device.name + u"\" ON button press with short release", 'Hue Lights')
                    if device.states['button1On'] == False:
                        button1On = True
                # Conversely, if the Indigo device state for the button is currently set to True, but
                #   the lastUpdated time on the bridge is the same as on the Indigo device, that means
                #   we set it to True the last time around and now we need to set it back to False.
                #   so we'll just leave the button1On variable set to the initial False assignment above.
            elif buttonEventID == 1003:
                lastButtonPressed = 1
                button1ReleaseLong = True
                if lastUpdated != device.states['lastUpdated']:
                    # Update the Indigo log regardless of current button on state.
                    indigo.server.log(u"received \"" + device.name + u"\" ON button press with long release", 'Hue Lights')
                    if device.states['button1On'] == False:
                        button1On = True
            # -- BUTTON 2 --
            elif buttonEventID == 2000:
                lastButtonPressed = 2
                if lastUpdated != device.states['lastUpdated']:
                    button2On = True
                    indigo.server.log(u"received \"" + device.name + u"\" DIM UP button press", 'Hue Lights')
            elif buttonEventID == 2001:
                lastButtonPressed = 2
                button2On = True
                button2Hold = True
                if button2Hold != device.states['button2Hold']:
                    indigo.server.log(u"received \"" + device.name + u"\" DIM UP button press and hold", 'Hue Lights')
            elif buttonEventID == 2002:
                lastButtonPressed = 2
                button2ReleaseShort = True
                if lastUpdated != device.states['lastUpdated']:
                    indigo.server.log(u"received \"" + device.name + u"\" DIM UP button press with short release", 'Hue Lights')
                    if device.states['button2On'] == False:
                        button2On = True
            elif buttonEventID == 2003:
                lastButtonPressed = 2
                button2ReleaseLong = True
                if lastUpdated != device.states['lastUpdated']:
                    indigo.server.log(u"received \"" + device.name + u"\" DIM UP button press with long release", 'Hue Lights')
                    if device.states['button2On'] == False:
                        button2On = True
            # -- BUTTON 3 --
            elif buttonEventID == 3000:
                lastButtonPressed = 3
                if lastUpdated != device.states['lastUpdated']:
                    button3On = True
                    indigo.server.log(u"received \"" + device.name + u"\" DIM DOWN button press", 'Hue Lights')
            elif buttonEventID == 3001:
                lastButtonPressed = 3
                button3On = True
                button3Hold = True
                if button3Hold != device.states['button3Hold']:
                    indigo.server.log(u"received \"" + device.name + u"\" DIM DOWN button press and hold", 'Hue Lights')
            elif buttonEventID == 3002:
                lastButtonPressed = 3
                button3ReleaseShort = True
                if lastUpdated != device.states['lastUpdated']:
                    indigo.server.log(u"received \"" + device.name + u"\" DIM DOWN button press with short release", 'Hue Lights')
                    if device.states['button3On'] == False:
                        button3On = True
            elif buttonEventID == 3003:
                lastButtonPressed = 3
                button3ReleaseLong = True
                if lastUpdated != device.states['lastUpdated']:
                    indigo.server.log(u"received \"" + device.name + u"\" DIM DOWN button press with long release", 'Hue Lights')
                    if device.states['button3On'] == False:
                        button3On = True
            # -- BUTTON 4 --
            elif buttonEventID == 4000:
                lastButtonPressed = 4
                if lastUpdated != device.states['lastUpdated']:
                    button4On = True
                    indigo.server.log(u"received \"" + device.name + u"\" OFF button press", 'Hue Lights')
            elif buttonEventID == 4001:
                lastButtonPressed = 4
                button4On = True
                button4Hold = True
                if button4Hold != device.states['button4Hold']:
                    indigo.server.log(u"received \"" + device.name + u"\" OFF button press and hold", 'Hue Lights')
            elif buttonEventID == 4002:
                lastButtonPressed = 4
                button4ReleaseShort = True
                if lastUpdated != device.states['lastUpdated']:
                    indigo.server.log(u"received \"" + device.name + u"\" OFF button press with short release", 'Hue Lights')
                    if device.states['button4On'] == False:
                        button4On = True
            elif buttonEventID == 4003:
                lastButtonPressed = 4
                button4ReleaseLong = True
                if lastUpdated != device.states['lastUpdated']:
                    indigo.server.log(u"received \"" + device.name + u"\" OFF button press with long release", 'Hue Lights')
                    if device.states['button4On'] == False:
                        button4On = True

            # Set the overall sensor on state to True if any button was pressed.
            if button1On or button2On or button3On or button4On:
                onStateBool = True

            # Convert True/False onState to on/off values.
            if onStateBool:
                onState = "on"
                sensorIcon = indigo.kStateImageSel.PowerOn
            else:
                onState = "off"
                sensorIcon = indigo.kStateImageSel.PowerOff

            #   Update Indigo states and properties.
            tempProps = device.pluginProps
            # Update the device properties.
            tempProps['nameOnBridge'] = nameOnBridge
            tempProps['uniqueId'] = uniqueId
            tempProps['productId'] = productId
            tempProps['swVersion'] = swVersion
            tempProps['manufacturerName'] = manufacturerName
            tempProps['type'] = sensorType
            tempProps['modelId'] = modelId
            tempProps['enabledOnbridge'] = enabledOnbridge
            self.updateDeviceProps(device, tempProps)

            # Update the states on the device.
            self.updateDeviceState(device, 'button1On', button1On)
            self.updateDeviceState(device, 'button1Hold', button1Hold)
            self.updateDeviceState(device, 'button1ReleaseShort', button1ReleaseShort)
            self.updateDeviceState(device, 'button1ReleaseLong', button1ReleaseLong)
            self.updateDeviceState(device, 'button2On', button2On)
            self.updateDeviceState(device, 'button2Hold', button2Hold)
            self.updateDeviceState(device, 'button2ReleaseShort', button2ReleaseShort)
            self.updateDeviceState(device, 'button2ReleaseLong', button2ReleaseLong)
            self.updateDeviceState(device, 'button3On', button3On)
            self.updateDeviceState(device, 'button3Hold', button3Hold)
            self.updateDeviceState(device, 'button3ReleaseShort', button3ReleaseShort)
            self.updateDeviceState(device, 'button3ReleaseLong', button3ReleaseLong)
            self.updateDeviceState(device, 'button4On', button4On)
            self.updateDeviceState(device, 'button4Hold', button4Hold)
            self.updateDeviceState(device, 'button4ReleaseShort', button4ReleaseShort)
            self.updateDeviceState(device, 'button4ReleaseLong', button4ReleaseLong)
            self.updateDeviceState(device, 'lastButtonPressed', lastButtonPressed)
            self.updateDeviceState(device, 'lastUpdated', lastUpdated)
            self.updateDeviceState(device, 'buttonEventID', buttonEventID)
            self.updateDeviceState(device, 'online', online)
            self.updateDeviceState(device, 'batteryLevel', batteryLevel)
            # Update the device state.  Passing device object, state name, state value, decimal precision, display value, icon selection.
            self.updateDeviceState(device, 'onOffState', onStateBool, 0, onState, sensorIcon)
        # End if this is a Hue Dimmer Switch sensor.

        # -- Hue Smart Button --
        if device.deviceTypeId == "hueSmartButton":
            ## self.debugLog(u"parseOneHueSensorData: Parsing Hue sensor ID %s (\"%s\")." % (device.pluginProps.get('sensorId', ""), sensor.get('name', "no name")))

            # Separate out the specific Hue sensor data.
            nameOnBridge = sensor.get('name', "")
            uniqueId = sensor.get('uniqueid', "")
            productId = sensor.get('productid', "")
            swVersion = sensor.get('swversion', "")
            manufacturerName = sensor.get('manufacturername', "")
            sensorType = sensor.get('type', "")
            modelId = sensor.get('modelid', "")
            enabledOnbridge = sensor['config'].get('on', True)
            batteryLevel = sensor['config'].get('battery', 0)
            online = sensor['config'].get('reachable', False)
            buttonEventID = sensor['state'].get('buttonevent', 0)
            lastUpdated = sensor['state'].get('lastupdated', "")
            onStateBool = False
            # Create initial value assignments for the button.
            button1On			= False
            button1Hold			= False
            button1ReleaseShort	= False
            button1ReleaseLong	= False
            # Populate the button on/off state based on the buttonEventID.
            if buttonEventID == 1000:
                # Sometimes the Hue bridge doesn't detect button releases from the Dimmer Switch and
                #   will continue to show the most recent button event as the initial press event.
                #   If the lastUpdated value from the Hue bridge hasn't changed, then allow the button
                #   on state to revert back to OFF (False) as set above. But if the lastUpdated value
                #   from the Hue bridge is different, then this must be a new initial button press,
                #   so set the button on state to True.
                if lastUpdated != device.states['lastUpdated']:
                    button1On = True
                    # Log any change to the onState.
                    indigo.server.log(u"received \"" + device.name + u"\" button press", 'Hue Lights')
            elif buttonEventID == 1001:
                button1On = True
                button1Hold = True
                # Don't write to the Indigo log unless this is the first time this status has been seen.
                if button1Hold != device.states['button1Hold']:
                    indigo.server.log(u"received \"" + device.name + u"\" button press and hold", 'Hue Lights')
            elif buttonEventID == 1002:
                button1ReleaseShort = True
                # We're checking to see if a button press event was missed since we can only check the
                #   Hue bridge every 2 seconds or so.  If the last button event was a button release
                #   but the current device state for the button shows it was never on, and the lastUpdated
                #   time on the Hue bridge is different than that in the Indigo device, then the button
                #   had to have been pressed at some point, so we'll set the button ON state to True.
                if lastUpdated != device.states['lastUpdated']:
                    # Update the Indigo log about the received button event regardless of current on state.
                    indigo.server.log(u"received \"" + device.name + u"\" button press with short release", 'Hue Lights')
                    if device.states['button1On'] == False:
                        button1On = True
                # Conversely, if the Indigo device state for the button is currently set to True, but
                #   the lastUpdated time on the bridge is the same as on the Indigo device, that means
                #   we set it to True the last time around and now we need to set it back to False.
                #   so we'll just leave the button1On variable set to the initial False assignment above.
            elif buttonEventID == 1003:
                button1ReleaseLong = True
                if lastUpdated != device.states['lastUpdated']:
                    # Update the Indigo log regardless of current button on state.
                    indigo.server.log(u"received \"" + device.name + u"\" button press with long release", 'Hue Lights')
                    if device.states['button1On'] == False:
                        button1On = True

            # Set the overall sensor on state to True if any button was pressed.
            if button1On:
                onStateBool = True

            # Convert True/False onState to on/off values.
            if onStateBool:
                onState = "on"
                sensorIcon = indigo.kStateImageSel.PowerOn
            else:
                onState = "off"
                sensorIcon = indigo.kStateImageSel.PowerOff

            #   Update Indigo states and properties.
            tempProps = device.pluginProps
            # Update the device properties.
            tempProps['nameOnBridge'] = nameOnBridge
            tempProps['uniqueId'] = uniqueId
            tempProps['productId'] = productId
            tempProps['swVersion'] = swVersion
            tempProps['manufacturerName'] = manufacturerName
            tempProps['type'] = sensorType
            tempProps['modelId'] = modelId
            tempProps['enabledOnbridge'] = enabledOnbridge
            self.updateDeviceProps(device, tempProps)

            # Update the states on the device.
            self.updateDeviceState(device, 'button1On', button1On)
            self.updateDeviceState(device, 'button1Hold', button1Hold)
            self.updateDeviceState(device, 'button1ReleaseShort', button1ReleaseShort)
            self.updateDeviceState(device, 'button1ReleaseLong', button1ReleaseLong)
            self.updateDeviceState(device, 'lastUpdated', lastUpdated)
            self.updateDeviceState(device, 'buttonEventID', buttonEventID)
            self.updateDeviceState(device, 'online', online)
            self.updateDeviceState(device, 'batteryLevel', batteryLevel)
            # Update the device state.  Passing device object, state name, state value, decimal precision, display value, icon selection.
            self.updateDeviceState(device, 'onOffState', onStateBool, 0, onState, sensorIcon)
        # End if this is a Hue Smart Button sensor.

        # -- Hue Wall Switch Module --
        if device.deviceTypeId == "hueWallSwitchModule":
            ## self.debugLog(u"parseOneHueSensorData: Parsing Hue sensor ID %s (\"%s\")." % (device.pluginProps.get('sensorId', ""), sensor.get('name', "no name")))

            # Separate out the specific Hue sensor data.
            nameOnBridge = sensor.get('name', "")
            uniqueId = sensor.get('uniqueid', "")
            productId = sensor.get('productid', "")
            swVersion = sensor.get('swversion', "")
            manufacturerName = sensor.get('manufacturername', "")
            sensorType = sensor.get('type', "")
            modelId = sensor.get('modelid', "")
            enabledOnbridge = sensor['config'].get('on', True)
            batteryLevel = sensor['config'].get('battery', 0)
            online = sensor['config'].get('reachable', False)
            deviceMode = sensor['config'].get('devicemode', "")
            buttonEventID = sensor['state'].get('buttonevent', 0)
            lastUpdated = sensor['state'].get('lastupdated', "")
            # The lastButtonPressed variable is used for the device state of the same name.
            # 0 = No button has been pressed since device was paired with Hue bridge.
            # 1 = Button 1
            # 2 = Button 2
            lastButtonPressed = 0
            onStateBool = False
            # Create initial value assignments for all the buttons.
            button1On			= False
            button1Hold			= False
            button1ReleaseShort	= False
            button1ReleaseLong	= False
            button2On			= False
            button2Hold			= False
            button2ReleaseShort	= False
            button2ReleaseLong	= False
            # Populate the button on/off states based on the buttonEventID.
            # -- BUTTON 1 --
            if buttonEventID == 1000:
                # Update the last button pressed state variable.
                lastButtonPressed = 1
                # Sometimes the Hue bridge doesn't detect button releases from the Dimmer Switch and
                #   will continue to show the most recent button event as the initial press event.
                #   If the lastUpdated value from the Hue bridge hasn't changed, then allow the button
                #   on state to revert back to OFF (False) as set above. But if the lastUpdated value
                #   from the Hue bridge is different, then this must be a new initial button press,
                #   so set the button on state to True.
                if lastUpdated != device.states['lastUpdated']:
                    button1On = True
                    # Log any change to the onState.
                    indigo.server.log(u"received \"" + device.name + u"\" button 1 press", 'Hue Lights')
            elif buttonEventID == 1001:
                lastButtonPressed = 1
                button1On = True
                button1Hold = True
                # Don't write to the Indigo log unless this is the first time this status has been seen.
                if button1Hold != device.states['button1Hold']:
                    indigo.server.log(u"received \"" + device.name + u"\" button 1 press and hold", 'Hue Lights')
            elif buttonEventID == 1002:
                lastButtonPressed = 1
                button1ReleaseShort = True
                # We're checking to see if a button press event was missed since we can only check the
                #   Hue bridge every 2 seconds or so.  If the last button event was a button release
                #   but the current device state for the button shows it was never on, and the lastUpdated
                #   time on the Hue bridge is different than that in the Indigo device, then the button
                #   had to have been pressed at some point, so we'll set the button ON state to True.
                if lastUpdated != device.states['lastUpdated']:
                    # Update the Indigo log about the received button event regardless of current on state.
                    indigo.server.log(u"received \"" + device.name + u"\" button 1 press with short release", 'Hue Lights')
                    if device.states['button1On'] == False:
                        button1On = True
                # Conversely, if the Indigo device state for the button is currently set to True, but
                #   the lastUpdated time on the bridge is the same as on the Indigo device, that means
                #   we set it to True the last time around and now we need to set it back to False.
                #   so we'll just leave the button1On variable set to the initial False assignment above.
            elif buttonEventID == 1003:
                lastButtonPressed = 1
                button1ReleaseLong = True
                if lastUpdated != device.states['lastUpdated']:
                    # Update the Indigo log regardless of current button on state.
                    indigo.server.log(u"received \"" + device.name + u"\" button 1 press with long release", 'Hue Lights')
                    if device.states['button1On'] == False:
                        button1On = True
            # -- BUTTON 2 --
            elif buttonEventID == 2000:
                lastButtonPressed = 2
                if lastUpdated != device.states['lastUpdated']:
                    button2On = True
                    indigo.server.log(u"received \"" + device.name + u"\" button 2 press", 'Hue Lights')
            elif buttonEventID == 2001:
                lastButtonPressed = 2
                button2On = True
                button2Hold = True
                if button2Hold != device.states['button2Hold']:
                    indigo.server.log(u"received \"" + device.name + u"\" button 2 press and hold", 'Hue Lights')
            elif buttonEventID == 2002:
                lastButtonPressed = 2
                button2ReleaseShort = True
                if lastUpdated != device.states['lastUpdated']:
                    indigo.server.log(u"received \"" + device.name + u"\" button 2 press with short release", 'Hue Lights')
                    if device.states['button2On'] == False:
                        button2On = True
            elif buttonEventID == 2003:
                lastButtonPressed = 2
                button2ReleaseLong = True
                if lastUpdated != device.states['lastUpdated']:
                    indigo.server.log(u"received \"" + device.name + u"\" button 2 press with long release", 'Hue Lights')
                    if device.states['button2On'] == False:
                        button2On = True

            # Set the overall sensor on state to True if any button was pressed.
            if button1On or button2On:
                onStateBool = True

            # Convert True/False onState to on/off values.
            if onStateBool:
                onState = "on"
                sensorIcon = indigo.kStateImageSel.PowerOn
            else:
                onState = "off"
                sensorIcon = indigo.kStateImageSel.PowerOff

            #   Update Indigo states and properties.
            tempProps = device.pluginProps
            # Update the device properties.
            tempProps['nameOnBridge'] = nameOnBridge
            tempProps['uniqueId'] = uniqueId
            tempProps['productId'] = productId
            tempProps['swVersion'] = swVersion
            tempProps['manufacturerName'] = manufacturerName
            tempProps['type'] = sensorType
            tempProps['modelId'] = modelId
            tempProps['enabledOnbridge'] = enabledOnbridge
            tempProps['deviceMode'] = deviceMode
            self.updateDeviceProps(device, tempProps)

            # Update the states on the device.
            self.updateDeviceState(device, 'button1On', button1On)
            self.updateDeviceState(device, 'button1Hold', button1Hold)
            self.updateDeviceState(device, 'button1ReleaseShort', button1ReleaseShort)
            self.updateDeviceState(device, 'button1ReleaseLong', button1ReleaseLong)
            self.updateDeviceState(device, 'button2On', button2On)
            self.updateDeviceState(device, 'button2Hold', button2Hold)
            self.updateDeviceState(device, 'button2ReleaseShort', button2ReleaseShort)
            self.updateDeviceState(device, 'button2ReleaseLong', button2ReleaseLong)
            self.updateDeviceState(device, 'lastButtonPressed', lastButtonPressed)
            self.updateDeviceState(device, 'lastUpdated', lastUpdated)
            self.updateDeviceState(device, 'buttonEventID', buttonEventID)
            self.updateDeviceState(device, 'online', online)
            self.updateDeviceState(device, 'batteryLevel', batteryLevel)
            # Update the device state.  Passing device object, state name, state value, decimal precision, display value, icon selection.
            self.updateDeviceState(device, 'onOffState', onStateBool, 0, onState, sensorIcon)
        # End if this is a Hue Dimmer Switch sensor.

        # -- Run Less Wire or Niko (Friends of Hue) Switch --
        if device.deviceTypeId == "runLessWireSwitch":
            ## self.debugLog(u"parseOneHueSensorData: Parsing Hue sensor ID %s (\"%s\")." % (device.pluginProps.get('sensorId', ""), sensor.get('name', "no name")))

            # Separate out the specific Hue sensor data.
            nameOnBridge = sensor.get('name', "")
            uniqueId = sensor.get('uniqueid', "")
            productId = sensor.get('productname', "")
            manufacturerName = sensor.get('manufacturername', "")
            sensorType = sensor.get('type', "")
            modelId = sensor.get('modelid', "")
            enabledOnbridge = sensor['config'].get('on', True)
            buttonEventID = sensor['state'].get('buttonevent', 0)
            lastUpdated = sensor['state'].get('lastupdated', "")
            # The lastButtonPressed variable is used for the device state of the same name.
            # 0 = No button has been pressed since device was paired with Hue bridge.
            # 1 = LEFT TOP button
            # 2 = LEFT BOTTOM button
            # 3 = RIGHT BOTTOM button
            # 4 = RIGHT TOP button
            # 14 = COMBINED TOP buttons
            # 23 = COMBINED BOTTOM buttons
            lastButtonPressed = 0
            # Track whether a button is being held.
            buttonBeingHeld = False
            # Track overall device on state.
            onStateBool = False
            # Create initial value assignments for all the buttons.
            button1On			= False
            button1Hold			= False
            button1Release		= False
            button2On			= False
            button2Hold			= False
            button2Release		= False
            button3On			= False
            button3Hold			= False
            button3Release		= False
            button4On			= False
            button4Hold			= False
            button4Release		= False
            button14On			= False
            button14Hold		= False
            button14Release		= False
            button23On			= False
            button23Hold		= False
            button23Release		= False

            # Populate the button on/off states based on this buttonEventID.
            # -- BUTTON 1 --
            if buttonEventID == 16:
                lastButtonPressed = 1
                button1On = True
                # If the lastUpdated value is different, this is a new button press. Log it.
                if lastUpdated != device.states['lastUpdated']:
                    indigo.server.log(u"received \"" + device.name + u"\" LEFT TOP button press", 'Hue Lights')
                else:
                    # Looks like the button is being held down.
                    button1Hold = True
                    buttonBeingHeld = True
                    # If the Indigo device doesn't show that a button is already being held, report a button hold in the log.
                    if buttonBeingHeld != device.pluginProps.get('buttonBeingHeld', False):
                        indigo.server.log(u"received \"" + device.name + u"\" LEFT TOP button press and hold", 'Hue Lights')
            elif buttonEventID == 20:
                lastButtonPressed = 1
                button1Release = True
                # We're checking to see if a button press event was missed since we can only check the
                #   Hue bridge every 2 seconds or so.  If the last button event was a button release
                #   but the current device state for the button shows it was never on, and the lastUpdated
                #   time on the Hue bridge is different than that in the Indigo device, then the button
                #   had to have been pressed at some point, so we'll set the button ON state to True.
                if lastUpdated != device.states['lastUpdated']:
                    # Update the Indigo log about the received button event regardless of current on state.
                    indigo.server.log(u"received \"" + device.name + u"\" LEFT TOP button press with release", 'Hue Lights')
                    if device.states['button1On'] == False:
                        button1On = True
                # Conversely, if the Indigo device state for the button is currently set to True, but
                #   the lastUpdated time on the bridge is the same as on the Indigo device, that means
                #   we set it to True the last time around and now we need to set it back to False.
                #   so we'll just leave the button1On variable set to the initial False assignment above.
            # -- BUTTON 2 --
            elif buttonEventID == 17:
                lastButtonPressed = 2
                button2On = True
                if lastUpdated != device.states['lastUpdated']:
                    indigo.server.log(u"received \"" + device.name + u"\" LEFT BOTTOM button press", 'Hue Lights')
                else:
                    button2Hold = True
                    buttonBeingHeld = True
                    if buttonBeingHeld != device.pluginProps.get('buttonBeingHeld', False):
                        indigo.server.log(u"received \"" + device.name + u"\" LEFT BOTTOM button press and hold", 'Hue Lights')
            elif buttonEventID == 21:
                lastButtonPressed = 2
                button2Release = True
                if lastUpdated != device.states['lastUpdated']:
                    indigo.server.log(u"received \"" + device.name + u"\" LEFT BOTTOM button press with release", 'Hue Lights')
                    if device.states['button2On'] == False:
                        button2On = True
            # -- BUTTON 3 --
            elif buttonEventID == 18:
                lastButtonPressed = 3
                button3On = True
                if lastUpdated != device.states['lastUpdated']:
                    indigo.server.log(u"received \"" + device.name + u"\" RIGHT BOTTOM button press", 'Hue Lights')
                else:
                    button3Hold = True
                    buttonBeingHeld = True
                    if buttonBeingHeld != device.pluginProps.get('buttonBeingHeld', False):
                        indigo.server.log(u"received \"" + device.name + u"\" RIGHT BOTTOM button press and hold", 'Hue Lights')
            elif buttonEventID == 22:
                lastButtonPressed = 3
                button3Release = True
                if lastUpdated != device.states['lastUpdated']:
                    indigo.server.log(u"received \"" + device.name + u"\" RIGHT BOTTOM button press with release", 'Hue Lights')
                    if device.states['button3On'] == False:
                        button3On = True
            # -- BUTTON 4 --
            elif buttonEventID == 19:
                lastButtonPressed = 4
                button4On = True
                if lastUpdated != device.states['lastUpdated']:
                    indigo.server.log(u"received \"" + device.name + u"\" RIGHT TOP button press", 'Hue Lights')
                else:
                    button4Hold = True
                    buttonBeingHeld = True
                    if buttonBeingHeld != device.pluginProps.get('buttonBeingHeld', False):
                        indigo.server.log(u"received \"" + device.name + u"\" RIGHT TOP button press and hold", 'Hue Lights')
            elif buttonEventID == 23:
                lastButtonPressed = 4
                button4Release = True
                if lastUpdated != device.states['lastUpdated']:
                    indigo.server.log(u"received \"" + device.name + u"\" RIGHT TOP button press with release", 'Hue Lights')
                    if device.states['button4On'] == False:
                        button4On = True
            # -- BUTTONS 14 --
            elif buttonEventID == 100:
                lastButtonPressed = 14
                button14On = True
                if lastUpdated != device.states['lastUpdated']:
                    indigo.server.log(u"received \"" + device.name + u"\" COMBINED TOP button press", 'Hue Lights')
                else:
                    button14Hold = True
                    buttonBeingHeld = True
                    if buttonBeingHeld != device.pluginProps.get('buttonBeingHeld', False):
                        indigo.server.log(u"received \"" + device.name + u"\" COMBINED TOP button press and hold", 'Hue Lights')
            elif buttonEventID == 101:
                lastButtonPressed = 14
                button14Release = True
                if lastUpdated != device.states['lastUpdated']:
                    indigo.server.log(u"received \"" + device.name + u"\" COMBINED TOP button press with release", 'Hue Lights')
                    if device.states['button14On'] == False:
                        button14On = True
            # -- BUTTONS 23 --
            elif buttonEventID == 98:
                lastButtonPressed = 23
                button23On = True
                if lastUpdated != device.states['lastUpdated']:
                    indigo.server.log(u"received \"" + device.name + u"\" COMBINED BOTTOM button press", 'Hue Lights')
                else:
                    button23Hold = True
                    buttonBeingHeld = True
                    if buttonBeingHeld != device.pluginProps.get('buttonBeingHeld', False):
                        indigo.server.log(u"received \"" + device.name + u"\" COMBINED BOTTOM button press and hold", 'Hue Lights')
            elif buttonEventID == 99:
                lastButtonPressed = 23
                button23Release = True
                if lastUpdated != device.states['lastUpdated']:
                    indigo.server.log(u"received \"" + device.name + u"\" COMBINED BOTTOM button press with release", 'Hue Lights')
                    if device.states['button23On'] == False:
                        button23On = True

            # Set the overall sensor on state to True if any button was pressed.
            if button1On or button2On or button3On or button4On or button14On or button23On:
                onStateBool = True

            # Convert True/False onState to on/off values.
            if onStateBool:
                onState = "on"
                sensorIcon = indigo.kStateImageSel.PowerOn
            else:
                onState = "off"
                sensorIcon = indigo.kStateImageSel.PowerOff

            #   Update Indigo states and properties.
            tempProps = device.pluginProps
            # Update the device properties.
            tempProps['nameOnBridge'] = nameOnBridge
            tempProps['uniqueId'] = uniqueId
            tempProps['productId'] = productId
            tempProps['manufacturerName'] = manufacturerName
            tempProps['type'] = sensorType
            tempProps['modelId'] = modelId
            tempProps['enabledOnbridge'] = enabledOnbridge
            tempProps['buttonBeingHeld'] = buttonBeingHeld
            self.updateDeviceProps(device, tempProps)

            # Update the states on the device.
            self.updateDeviceState(device, 'button1On', button1On)
            self.updateDeviceState(device, 'button1Hold', button1Hold)
            self.updateDeviceState(device, 'button1Release', button1Release)
            self.updateDeviceState(device, 'button2On', button2On)
            self.updateDeviceState(device, 'button2Hold', button2Hold)
            self.updateDeviceState(device, 'button2Release', button2Release)
            self.updateDeviceState(device, 'button3On', button3On)
            self.updateDeviceState(device, 'button3Hold', button3Hold)
            self.updateDeviceState(device, 'button3Release', button3Release)
            self.updateDeviceState(device, 'button4On', button4On)
            self.updateDeviceState(device, 'button4Hold', button4Hold)
            self.updateDeviceState(device, 'button4Release', button4Release)
            self.updateDeviceState(device, 'button14On', button14On)
            self.updateDeviceState(device, 'button14Hold', button14Hold)
            self.updateDeviceState(device, 'button14Release', button14Release)
            self.updateDeviceState(device, 'button23On', button23On)
            self.updateDeviceState(device, 'button23Hold', button23Hold)
            self.updateDeviceState(device, 'button23Release', button23Release)
            self.updateDeviceState(device, 'lastButtonPressed', lastButtonPressed)
            self.updateDeviceState(device, 'lastUpdated', lastUpdated)
            self.updateDeviceState(device, 'buttonEventID', buttonEventID)
            # Update the device state.  Passing device object, state name, state value, decimal precision, display value, icon selection.
            self.updateDeviceState(device, 'onOffState', onStateBool, 0, onState, sensorIcon)
        # End if this is a Run Less Wire Switch sensor.

    # Turn Device On or Off
    ########################################
    def doOnOff(self, device, onState, rampRate=-1, showLog=True):
        self.debugLog(u"Starting doOnOff. onState: {}, rampRate: {}. Device: {}".format(onState, rampRate, device))
        # onState:		Boolean on state.  True = on. False = off.
        # rampRate:		Optional float from 0 to 540.0 (higher values will probably work too).

        hubNumber, ipAddress, hostId, paired = self.getIdsFromDevice(device)

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
                except Exception, e:
                    errorText = u"Default ramp rate could not be obtained: {}".format(e)
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
            #   (We're using the "savedBrightness" variable as the brightness goal here).
            if defaultBrightness > 0:
                # Convert default brightness from percentage to 1-255 range.
                savedBrightness = int(round(defaultBrightness / 100.0 * 255.0))
            # If the currentBrightness is less than 100% and is the same as the savedBrightness, go to 100%
            if currentBrightness < 100 and currentBrightness == int(round(savedBrightness / 255.0 * 100.0)):
                savedBrightness = 255

        # Sanity check for an IP address
        if ipAddress is None:
            errorText = u"No IP address set for the Hue bridge. You can get this information from the My Settings page at http://www.meethue.com"
            self.errorLog(errorText)
            # Remember the error.
            self.lastErrorMessage = errorText
            return

        # Act based on device type.
        if device.deviceTypeId == "hueGroup":
            # Sanity check on group ID
            groupId = device.pluginProps.get('groupId', None)
            if groupId is None or groupId == 0:
                errorText = u"No group ID selected for device \"{}\". Check settings for this device and select a Hue Group to control.".format(device.name)
                self.errorLog(errorText)
                # Remember the error.
                self.lastErrorMessage = errorText
                return
        else:
            # Sanity check on bulb ID
            bulbId = device.pluginProps.get('bulbId', None)
            if bulbId is None or bulbId == 0:
                errorText = u"No bulb ID selected for device \"{}\". Check settings for this device and select a Hue Device to control.".format(device.name)
                self.errorLog(errorText)
                # Remember the error.
                self.lastErrorMessage = errorText
                return

        # If the requested onState is True (on), then use the
        #   saved brightness level (which was determined above).
        if onState == True:
            # Skip ramp rate and brightness stuff for on/off devices.
            if device.deviceTypeId == "hueOnOffDevice":
                # Create the JSON object, ignoring brighness level and ramp rate for on/off devices,
                # and send the command to the bridge.
                requestData = json.dumps({"on": onState})
            else:
                # If the bulb's saved brightness is zero or less (for some reason), use a default value of 100% on (255).
                if savedBrightness <= 0:
                    savedBrightness = 255
                # Create the JSON object for other types of devices based on whether they allow ON transition times.
                if device.pluginProps.get("noOnRampRate", False):
                    requestData = json.dumps({"bri": savedBrightness, "on": onState})
                else:
                    requestData = json.dumps({"bri": savedBrightness, "on": onState, "transitiontime": rampRate})
            # Create the command based on whether this is a group or light device.
            if device.deviceTypeId == "hueGroup":
                command = "http://{}/api/{}/groups/{}/action".format(ipAddress, self.hostIds[hubNumber], groupId)
            else:
                command = "http://{}/api/{}/lights/{}/state".format(ipAddress, self.hostIds[hubNumber], bulbId)
            self.debugLog("Sending URL request: {}".format(command))
            try:
                r = requests.put(command, data=requestData, timeout=kTimeout)
            except requests.exceptions.Timeout:
                errorText = u"Failed to connect to the Hue bridge at {} after {} seconds. - Check that the bridge is connected and turned on.".format(ipAddress, kTimeout)
                # Don't display the error if it's been displayed already.
                if errorText != self.lastErrorMessage:
                    self.errorLog(errorText)
                    # Remember the error.
                    self.lastErrorMessage = errorText
                return
            except requests.exceptions.ConnectionError:
                errorText = u"Failed to connect to the Hue bridge at {}. - Check that the bridge is connected and turned on.".format(ipAddress)
                # Don't display the error if it's been displayed already.
                if errorText != self.lastErrorMessage:
                    self.errorLog(errorText)
                    # Remember the error.
                    self.lastErrorMessage = errorText
                return
            self.debugLog("Got response - {}".format(r.content) )
            # Customize the log and device update based on whether this is an on/off device or not.
            if device.deviceTypeId == "hueOnOffDevice":
                # Send the log to the console if showing the log is enabled.
                if showLog:
                    indigo.server.log(u"\"" + device.name + u"\" on", 'Sent Hue Lights')
                # Update the Indigo device.
                self.updateDeviceState(device, 'onOffState', 'on')
            else:
                tempBrightness = int(round(savedBrightness / 255.0 * 100.0))
                # Compensate for rounding to zero.
                if tempBrightness == 0:
                    tempBrightness = 1
                # Log the change (if enabled).
                if showLog:
                    # Customize the log based on whether the device supports ON transition time or not.
                    if device.pluginProps.get("noOnRampRate", False):
                        indigo.server.log(u"\"{}\" on to {}.".format(device.name,tempBrightness ), "Sent Hue Lights")
                    else:
                        indigo.server.log(u"\"{}\" on to {}, at ramp rate:{} sec".format( device.name, tempBrightness, rampRate / 10.0 ), 'Sent Hue Lights')
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
                if device.pluginProps.get("noOffRampRate", False):
                    requestData = json.dumps({"on": onState})
                else:
                    requestData = json.dumps({"on": onState, "transitiontime": rampRate})
            # Create the command based on whether this is a light or group device.
            if device.deviceTypeId == "hueGroup":
                command = "http://{}/api/{}/groups/{}/action".format(ipAddress, self.hostIds[hubNumber], groupId)
            else:
                command = "http://{}/api/{}/lights/{}/state".format(ipAddress, self.hostIds[hubNumber], bulbId)
            self.debugLog(u"Sending URL request: {} with data: {}".format(command, requestData))
            try:
                r = requests.put(command, data=requestData, timeout=kTimeout)
            except requests.exceptions.Timeout:
                errorText = u"Failed to connect to the Hue bridge at {} after {} seconds. - Check that the bridge is connected and turned on.".format(ipAddress, kTimeout)
                # Don't display the error if it's been displayed already.
                if errorText != self.lastErrorMessage:
                    self.errorLog(errorText)
                    # Remember the error.
                    self.lastErrorMessage = errorText
                return
            except requests.exceptions.ConnectionError:
                errorText = u"Failed to connect to the Hue bridge at {}. - Check that the bridge is connected and turned on.".format(ipAddress)
                # Don't display the error if it's been displayed already.
                if errorText != self.lastErrorMessage:
                    self.errorLog(errorText)
                    # Remember the error.
                    self.lastErrorMessage = errorText
                return
            self.debugLog(u"Got response - {}".format(r.content) )
            # Customize the log and device update based on whether this is an on/off device or other device.
            if device.deviceTypeId == "hueOnOffDevice":
                # Log the change.
                indigo.server.log(u"\"" + device.name + u"\" off", 'Sent Hue Lights')
                # Update the Indigo device.
                self.updateDeviceState(device, 'onOffState', 'off')
            else:
                # Log the change (if showing the log is enabled).
                #   Some devices may not support transition times when turning off. Check for that.
                if showLog:
                    if device.pluginProps.get("noOffRampRate", False):
                        indigo.server.log(u"\"{}\" off.".format( device.name), 'Sent Hue Lights')
                    else:
                        indigo.server.log(u"\"{}\" off. At ramp rate {} sec.".format( device.name, rampRate / 10.0), 'Sent Hue Lights')
                # Update the Indigo device.
                self.updateDeviceState(device, 'brightnessLevel', 0)
        return

    # Set Brightness
    ########################################
    def doBrightness(self, device, brightness, rampRate=-1, showLog=True):
        self.debugLog(u"Starting doBrightness. brightness: {}, rampRate: {}, showLogs: {}. Device: {}".format(brightness, rampRate, showLog, device))
        # brightness:	Integer from 0 to 255.
        # rampRate:		Optional float from 0 to 540.0 (higher values will probably work too).
        # showLog:		Optional boolean. False = hide change from Indigo log.
        hubNumber, ipAddress, hostId, paired = self.getIdsFromDevice(device)

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
                except Exception, e:
                    errorText = u"Default ramp rate could not be obtained: {}".format(e)
                    self.errorLog(errorText)
                    # Remember the error.
                    self.lastErrorMessage = errorText
                    rampRate = 5
            else:
                rampRate = int(round(float(rampRate) * 10))

            # Get the current brightness level.
            currentBrightness = device.states.get('brightnessLevel', 100)

        # Sanity check for an IP address
        if ipAddress is None:
            errorText = u"No IP address set for the Hue bridge. You can get this information from the My Settings page at http://www.meethue.com"
            self.errorLog(errorText)
            # Remember the error.
            self.lastErrorMessage = errorText
            return

        # Act based on device type.
        if device.deviceTypeId == "hueGroup":
            # Sanity check on group ID
            groupId = device.pluginProps.get('groupId', None)
            if groupId is None or groupId == 0:
                errorText = u"No group ID selected for device \"{}\". Check settings for this device and select a Hue Group to control.".format(device.name)
                self.errorLog(errorText)
                # Remember the error.
                self.lastErrorMessage = errorText
                return
        else:
            # Sanity check on bulb ID
            bulbId = device.pluginProps.get('bulbId', None)
            if bulbId is None or bulbId == 0:
                errorText = u"No bulb ID selected for device \"{}\". Check settings for this device and select a Hue Device to control.".format(device.name)
                self.errorLog(errorText)
                # Remember the error.
                self.lastErrorMessage = errorText
                return

        # If requested brightness is greater than 0, proceed. Otherwise, turn off the bulb.
        if brightness > 0:
            # Skip ramp rate and brightness stuff for on/off only devices.
            if device.deviceTypeId == "hueOnOffDevice":
                requestData = json.dumps({"on": True})
            else:
                # Create the JSON based on if a ramp rate should be used or not and if the device is already on or not.
                if device.pluginProps.get("noOnRampRate", False) and currentBrightness == 0:
                    requestData = json.dumps({"bri": int(brightness), "on": True})
                else:
                    requestData = json.dumps({"bri": int(brightness), "on": True, "transitiontime": rampRate})
            # Create the command based on whether this is a light or group device.
            if device.deviceTypeId == "hueGroup":
                command = "http://{}/api/{}/groups/{}/action".format(ipAddress, self.hostIds[hubNumber], groupId)
            else:
                command = "http://{}/api/{}/lights/{}/state".format(ipAddress, self.hostIds[hubNumber], bulbId)
            self.debugLog("Sending URL request: {}".format(command))
            try:
                r = requests.put(command, data=requestData, timeout=kTimeout)
            except requests.exceptions.Timeout:
                errorText = u"Failed to connect to the Hue bridge at {} after {} seconds. - Check that the bridge is connected and turned on.".format(ipAddress, kTimeout)
                # Don't display the error if it's been displayed already.
                if errorText != self.lastErrorMessage:
                    self.errorLog(errorText)
                    # Remember the error.
                    self.lastErrorMessage = errorText
                return
            except requests.exceptions.ConnectionError:
                errorText = u"Failed to connect to the Hue bridge at {}. - Check that the bridge is connected and turned on.".format(ipAddress)
                # Don't display the error if it's been displayed already.
                if errorText != self.lastErrorMessage:
                    self.errorLog(errorText)
                    # Remember the error.
                    self.lastErrorMessage = errorText
                return
            self.debugLog("Got response - {}".format(r.content))
            # Log the change.
            tempBrightness = int(round(brightness / 255.0 * 100.0))
            # Compensate for rounding to zero.
            if tempBrightness == 0:
                tempBrightness = 1
            # Only log changes if we're supposed to.
            if showLog:
                if device.pluginProps.get("noOnRampRate", False) and currentBrightness == 0:
                    indigo.server.log(u"\"{}\" on to {}.".format( device.name, tempBrightness), 'Sent Hue Lights')
                else:
                    indigo.server.log(u"\"{}\" on to {}, at ramp rate:{} sec".format( device.name, tempBrightness, rampRate / 10.0 ), 'Sent Hue Lights')

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
                if device.pluginProps.get("noOffRampRate", False):
                    requestData = json.dumps({"on": False})
                else:
                    requestData = json.dumps({"transitiontime": rampRate, "on": False})
            # Create the command based on whether this is a light or group device.
            if device.deviceTypeId == "hueGroup":
                command = "http://{}/api/{}/groups/{}/action".format(ipAddress, self.hostIds[hubNumber], groupId)
            else:
                command = "http://{}/api/{}/lights/{}/state".format(ipAddress, self.hostIds[hubNumber], bulbId)
            self.debugLog(u"Sending URL request: {}".format(command))
            try:
                r = requests.put(command, data=requestData, timeout=kTimeout)
            except requests.exceptions.Timeout:
                errorText = u"Failed to connect to the Hue bridge at {} after {} seconds. - Check that the bridge is connected and turned on.".format(ipAddress, kTimeout)
                # Don't display the error if it's been displayed already.
                if errorText != self.lastErrorMessage:
                    self.errorLog(errorText)
                    # Remember the error.
                    self.lastErrorMessage = errorText
                return
            except requests.exceptions.ConnectionError:
                errorText = u"Failed to connect to the Hue bridge at {}. - Check that the bridge is connected and turned on.".format(ipAddress)
                # Don't display the error if it's been displayed already.
                if errorText != self.lastErrorMessage:
                    self.errorLog(errorText)
                    # Remember the error.
                    self.lastErrorMessage = errorText
                return
            self.debugLog(u"Got response - {}".format(r.content))
            # Log the change.
            if showLog:
                if device.pluginProps.get("noOffRampRate", False):
                    indigo.server.log(u"\"{}\" off".format( device.name ), 'Sent Hue Lights')
                else:
                    indigo.server.log(u"\"{}\" off, at ramp rate:{} sec".format( device.name, rampRate / 10.0 ), 'Sent Hue Lights')
            # Update the device brightness (which automatically changes on state).
            self.updateDeviceState(device, 'brightnessLevel', 0)

    # Set RGB Levels
    ########################################
    def doRGB(self, device, red, green, blue, rampRate=-1, showLog=True):
        self.debugLog(u"Starting doRGB. RGB: {}, {}, {}. Device: {}".format(red, green, blue, device))
        # red:			Integer from 0 to 255.
        # green:		Integer from 0 to 255.
        # blue:			Integer from 0 to 255.
        # rampRate:		Optional float from 0 to 540.0 (higher values will probably work too).
        hubNumber, ipAddress, hostId, paired = self.getIdsFromDevice(device)

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
                errorText = u"Default ramp rate could not be obtained: {}".format(e)
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
        if ipAddress is None:
            errorText = u"No IP address set for the Hue bridge. You can get this information from the My Settings page at http://www.meethue.com"
            self.errorLog(errorText)
            # Remember the error.
            self.lastErrorMessage = errorText
            return

        # Act based on device type.
        if device.deviceTypeId == "hueGroup":
            # Sanity check on group ID
            groupId = device.pluginProps.get('groupId', None)
            if groupId is None or groupId == 0:
                errorText = u"No group ID selected for device \"{}\". Check settings for this device and select a Hue Group to control.".format(device.name)
                self.errorLog(errorText)
                # Remember the error.
                self.lastErrorMessage = errorText
                return
        else:
            # Sanity check on bulb ID
            bulbId = device.pluginProps.get('bulbId', None)
            if bulbId is None or bulbId == 0:
                errorText = u"No bulb ID selected for device \"{}\". Check settings for this device and select a Hue Device to control.".format(device.name)
                self.errorLog(errorText)
                # Remember the error.
                self.lastErrorMessage = errorText
                return

        # Make sure the device is capable of rendering color.
        if device.pluginProps.get('SupportsRGB', False) == False:
            errorText = u"Cannot set RGB values. The \"{}\" device does not support color.".format(device.name)
            self.errorLog(errorText)
            # Remember the error.
            self.lastErrorMessage = errorText
            return

        # Send to Hue (Create JSON request based on whether brightness is zero or not).
        if brightness > 0:
            # Determine if a transition time should be used at all.
            if device.pluginProps.get("noOnRampRate", False) and currentBrightness == 0:
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
            if device.pluginProps.get("noOffRampRate", False):
                # We create a separate command for when brightness is 0 (or below) because if
                #   the "on" state in the request was True, the Hue light wouldn't turn off.
                #   We also explicity state the X and Y values (equivilant to RGB of 1, 1, 1)
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
        self.debugLog(u"Data: {}, URL: {}".format(requestData, command))
        try:
            r = requests.put(command, data=requestData, timeout=kTimeout)
        except requests.exceptions.Timeout:
            errorText = u"Failed to connect to the Hue bridge at {} after {} seconds. - Check that the bridge is connected and turned on.".format(ipAddress, kTimeout)
            # Don't display the error if it's been displayed already.
            if errorText != self.lastErrorMessage:
                self.errorLog(errorText)
                # Remember the error.
                self.lastErrorMessage = errorText
            return
        except requests.exceptions.ConnectionError:
            errorText = u"Failed to connect to the Hue bridge at {}. - Check that the bridge is connected and turned on.".format(ipAddress)
            # Don't display the error if it's been displayed already.
            if errorText != self.lastErrorMessage:
                self.errorLog(errorText)
                # Remember the error.
                self.lastErrorMessage = errorText
            return
        self.debugLog(u"Got response - {}".format(r.content))

        # Update on Indigo
        if brightness > 0:
            # Convert brightness to a percentage.
            brightness = int(round(brightness / 255.0 * 100.0))
            # Log the change (if enabled).
            if showLog:
                # Exclude mention of ramp rate if none was used.
                if device.pluginProps.get("noOnRampRate", False) and currentBrightness == 0:
                    indigo.server.log(u"\"{}\" on to {}  with RGB values {},{},{}.".format( device.name, brightness, red , green, blue) , 'Sent Hue Lights')
                else:
                    indigo.server.log(u"\"{}\" on to {}  with RGB values {},{},{}.  at ramp rate  {} sec.".format( device.name, brightness, red , green, blue, rampRate / 10.0 ), 'Sent Hue Lights')
            # Update the device state.
            self.updateDeviceState(device, 'brightnessLevel', brightness)
        else:
            # Log the change.
            if showLog:
                # Exclude mention of ramp rate if none was used.
                if device.pluginProps.get("noOffRampRate", False):
                    indigo.server.log(u"\"{}\" off".format( device.name ), 'Sent Hue Lights')
                else:
                    indigo.server.log(u"\"{}\" off, at ramp rate:{} sec".format( device.name, rampRate / 10.0 ), 'Sent Hue Lights')
            # Update the device state.
            self.updateDeviceState(device, 'brightnessLevel', 0)
        # Update the other device states.
        self.updateDeviceState(device, 'colorMode', "hs")
        self.updateDeviceState(device, 'hue', hue)
        self.updateDeviceState(device, 'saturation', saturation)
        # We don't set the colorRed, colorGreen, and colorBlue states
        #   because Hue devices are not capable of the full RGB color
        #   gamut and when the Hue bridge updates the HSB values to reflect
        #   actual displayed light, the interpreted RGB values will not
        #   match the values entered by the user in the Action dialog.

    # Set Hue, Saturation and Brightness
    ########################################
    def doHSB(self, device, hue, saturation, brightness, rampRate=-1, showLog=True):
        self.debugLog(u"Starting doHSB. HSB: {}, {}, {}. Device: {}" .format(hue, saturation, brightness, device))
        # hue:			Integer from 0 to 65535.
        # saturation:	Integer from 0 to 255.
        # brightness:	Integer from 0 to 255.
        # rampRate:		Optional float from 0 to 540.0 (higher values will probably work too).
        hubNumber, ipAddress, hostId, paired = self.getIdsFromDevice(device)

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
                errorText = u"Default ramp rate could not be obtained: {}".format(e)
                self.errorLog(errorText)
                # Remember the error.
                self.lastErrorMessage = errorText
                rampRate = 5
        else:
            rampRate = int(round(float(rampRate) * 10.0))

        # Get the current brightness level.
        currentBrightness = device.states.get('brightnessLevel', 100)

        # Sanity check for an IP address
        if ipAddress is None:
            errorText = u"No IP address set for the Hue bridge. You can get this information from the My Settings page at http://www.meethue.com"
            self.errorLog(errorText)
            # Remember the error.
            self.lastErrorMessage = errorText
            return

        # Act based on device type.
        if device.deviceTypeId == "hueGroup":
            # Sanity check on group ID
            groupId = device.pluginProps.get('groupId', None)
            if groupId is None or groupId == 0:
                errorText = u"No group ID selected for device \"{}\". Check settings for this device and select a Hue Group to control.".format(device.name)
                self.errorLog(errorText)
                # Remember the error.
                self.lastErrorMessage = errorText
                return
        else:
            # Sanity check on bulb ID
            bulbId = device.pluginProps.get('bulbId', None)
            if bulbId is None or bulbId == 0:
                errorText = u"No bulb ID selected for device \"{}\". Check settings for this device and select a Hue Device to control.".format(device.name)
                self.errorLog(errorText)
                # Remember the error.
                self.lastErrorMessage = errorText
                return

        # Make sure this device supports color.
        modelId = device.pluginProps.get('modelId', "")
        type = device.pluginProps.get('type', "")
        if type == kLivingWhitesDeviceIDType or type[0:len(kOnOffOnlyDeviceIDType)] == kOnOffOnlyDeviceIDType:
            errorText = u"Cannot set HSB values. The \"{}\" device does not support color.".format(device.name)
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
            # Exclude transition times if needed.
            if device.pluginProps.get("noOnRampRate", False) and currentBrightness == 0:
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
            if device.pluginProps.get("noOffRampRate", False):
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
        self.debugLog(u"Request is {}".format(requestData))
        try:
            r = requests.put(command, data=requestData, timeout=kTimeout)
        except requests.exceptions.Timeout:
            errorText = u"Failed to connect to the Hue bridge at {} after {} seconds. - Check that the bridge is connected and turned on.".format(ipAddress, kTimeout)
            # Don't display the error if it's been displayed already.
            if errorText != self.lastErrorMessage:
                self.errorLog(errorText)
                # Remember the error.
                self.lastErrorMessage = errorText
            return
        except requests.exceptions.ConnectionError:
            errorText = u"Failed to connect to the Hue bridge at {}. - Check that the bridge is connected and turned on.".format(ipAddress)
            # Don't display the error if it's been displayed already.
            if errorText != self.lastErrorMessage:
                self.errorLog(errorText)
                # Remember the error.
                self.lastErrorMessage = errorText
            return
        self.debugLog(u"Got response - {}".format(r.content))

        # Update on Indigo
        if int(round(brightness/255.0*100.0)) > 0:
            # Log the change (if enabled).
            if showLog:
                # Exclude mention of ramp rate if none was used.
                if device.pluginProps.get("noOnRampRate", False) and currentBrightness == 0:
                    indigo.server.log(u"\{}\" on to {} with hue {}° saturation {}%.".format(device.name, int(round(brightness / 255.0 * 100.0)), int(round(hue / 182.0)), int(round(saturation / 255.0 * 100.0)) ), 'Sent Hue Lights')
                else:
                    indigo.server.log(u"\{}\" on to {} with hue {}° saturation {}%. % at ramp rate {}sec.".format(device.name, int(round(brightness / 255.0 * 100.0)), int(round(hue / 182.0)), int(round(saturation / 255.0 * 100.0)), rampRate / 10.0 ), 'Sent Hue Lights')
            # Change the Indigo device.
            self.updateDeviceState(device, 'brightnessLevel', int(round(brightness / 255.0 * 100.0)))
        else:
            # Log the change.
            if showLog:
                # Exclude mention of ramp rate if none was used.
                if device.pluginProps.get("noOffRampRate", False):
                    indigo.server.log(u"\"{}\" off.".format(device.name), 'Sent Hue Lights')
                else:
                    indigo.server.log(u"\"{}\" off at ramp rate {} sec.".format(device.namerampRate / 10.0), 'Sent Hue Lights')
            # Change the Indigo device.
            self.updateDeviceState(device, 'brightnessLevel', 0)
        # Update the other device states.
        self.updateDeviceState(device, 'colorMode', "hs")
        self.updateDeviceState(device, 'hue', int(round(hue / 182.0)))
        self.updateDeviceState(device, 'saturation', int(saturation / 255.0 * 100.0))

    # Set CIE 1939 xyY Values
    ########################################
    def doXYY(self, device, colorX, colorY, brightness, rampRate=-1, showLog=True):
        self.debugLog(u"Starting doXYY. xyY: {}, {}, {}. Device: {}".format(colorX, colorY, brightness, device))
        # colorX:		Integer from 0 to 1.0.
        # colorY:		Integer from 0 to 1.0.
        # brightness:	Integer from 0 to 255.
        # rampRate:		Optional float from 0 to 540.0 (higher values will probably work too).
        hubNumber, ipAddress, hostId, paired = self.getIdsFromDevice(device)

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
                errorText = u"Default ramp rate could not be obtained: {}".format(e)
                self.errorLog(errorText)
                # Remember the error.
                self.lastErrorMessage = errorText
                rampRate = 5
        else:
            rampRate = int(round(float(rampRate) * 10.0))

        # Get the current brightness level.
        currentBrightness = device.states.get('brightnessLevel', 100)

        # Sanity check for an IP address
        if ipAddress is None:
            errorText = u"No IP address set for the Hue bridge. You can get this information from the My Settings page at http://www.meethue.com"
            self.errorLog(errorText)
            # Remember the error.
            self.lastErrorMessage = errorText
            return

        # Act based on device type.
        if device.deviceTypeId == "hueGroup":
            # Sanity check on group ID
            groupId = device.pluginProps.get('groupId', None)
            if groupId is None or groupId == 0:
                errorText = u"No group ID selected for device \"{}\". Check settings for this device and select a Hue Group to control." .format(device.name)
                self.errorLog(errorText)
                # Remember the error.
                self.lastErrorMessage = errorText
                return
        else:
            # Sanity check on bulb ID
            bulbId = device.pluginProps.get('bulbId', None)
            if bulbId is None or bulbId == 0:
                errorText = u"No bulb ID selected for device \"{}\". Check settings for this device and select a Hue Device to control.".format(device.name)
                self.errorLog(errorText)
                # Remember the error.
                self.lastErrorMessage = errorText
                return

        # Make sure this device supports color.
        modelId = device.pluginProps.get('modelId', "")
        type = device.pluginProps.get('type', "")
        if type == kLivingWhitesDeviceIDType or type[0:len(kOnOffOnlyDeviceIDType)] == kOnOffOnlyDeviceIDType:
            errorText = u"Cannot set xyY values. The \"{}\" device does not support color.".format(device.name)
            self.errorLog(errorText)
            # Remember the error.
            self.lastErrorMessage = errorText
            return

        # Make sure the X and Y values are sane.
        if colorX < 0.0 or colorX > 1.0:
            errorText = u"The specified X chromatisety value \"{}\" for the \"{}\" device is outside the acceptable range of 0.0 to 1.0.".format(colorX, device.name)
            self.errorLog(errorText)
            # Remember the error.
            self.lastErrorMessage = errorText
            return
        if colorY < 0.0 or colorY > 1.0:
            errorText = u"The specified Y chromatisety value \"{}\" for the \"{}\" device is outside the acceptable range of 0.0 to 1.0.".format(colorX, device.name)
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
            # Exclude transition time if needed.
            if device.pluginProps.get("noOnRampRate", False) and currentBrightness == 0:
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
        self.debugLog(u"Request is {}".format(r.content) )
        try:
            r = requests.put(command, data=requestData, timeout=kTimeout)
        except requests.exceptions.Timeout:
            errorText = u"Failed to connect to the Hue bridge at {} after {} seconds. - Check that the bridge is connected and turned on.".format(ipAddress, kTimeout)
            # Don't display the error if it's been displayed already.
            if errorText != self.lastErrorMessage:
                self.errorLog(errorText)
                # Remember the error.
                self.lastErrorMessage = errorText
            return
        except requests.exceptions.ConnectionError:
            errorText = u"Failed to connect to the Hue bridge at {}. - Check that the bridge is connected and turned on.".format(ipAddress)
            # Don't display the error if it's been displayed already.
            if errorText != self.lastErrorMessage:
                self.errorLog(errorText)
                # Remember the error.
                self.lastErrorMessage = errorText
            return
        self.debugLog(u"Got response - {}".format(r.content) )

        # Update on Indigo
        if int(round(brightness/255.0*100.0)) > 0:
            # Log the change (if enabled).
            if showLog:
                # Exclude mention of ramp rate if none was used.
                if device.pluginProps.get("noOnRampRate", False) and currentBrightness == 0:
                    indigo.server.log(u"\"{}\" on to {} with x/y chromatisety values of {}/{}.".format( device.name,int(round(brightness / 255.0 * 100.0)), round(colorX, 4), round(colorY, 4)  ), 'Sent Hue Lights')
                else:
                    indigo.server.log(u"\"{}\" on to {} with x/y chromatisety values of {}/{}.  at ramp rate  {} sec.".format( device.name, int(round(brightness / 255.0 * 100.0)), round(colorX, 4), round(colorY, 4), rampRate / 10.0 ), 'Sent Hue Lights')
            # Change the Indigo device.
            self.updateDeviceState(device, 'brightnessLevel', int(round(brightness / 255.0 * 100.0)))
        else:
            # Log the change.
            if showLog:
                # Exclude mention of ramp rate if none was used.
                if device.pluginProps.get("noOffRampRate", False):
                    indigo.server.log(u"\"{}\" off,".format( device.name ), 'Sent Hue Lights')
                else:
                    indigo.server.log(u"\"{}\" off, at ramp rate:{} sec".format( device.name, rampRate / 10.0 ), 'Sent Hue Lights')
            # Change the Indigo device.
            self.updateDeviceState(device, 'brightnessLevel', 0)
        # Update the other device states.
        self.updateDeviceState(device, 'colorMode', "xy")
        self.updateDeviceState(device, 'colorX', round(colorX, 4))
        self.updateDeviceState(device, 'colorY', round(colorY, 4))

    # Set Color Temperature
    ########################################
    def doColorTemperature(self, device, temperature, brightness, rampRate=-1, showLog=True):
        self.debugLog(u"Starting doColorTemperature. temperature: {}, brightness: {}. Device: {}".format(temperature, brightness, device))
        # temperature:	Integer from 2000 to 6500.
        # brightness:	Integer from 0 to 255.
        # rampRate:		Optional float from 0 to 540.0 (higher values will probably work too).
        hubNumber, ipAddress, hostId, paired = self.getIdsFromDevice(device)

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
                errorText = u"Default ramp rate could not be obtained: {}".format(e)
                self.errorLog(errorText)
                # Remember the error.
                self.lastErrorMessage = errorText
                rampRate = 5
        else:
            rampRate = int(round(float(rampRate) * 10))

        # Make sure the color temperature value is sane.
        if temperature < 2000 or temperature > 6500:
            errorText = u"Invalid color temperature value of {}. Color temperatures must be between 2000 and 6500 K.".format(temperature)
            self.errorLog(errorText)
            # Remember the error.
            self.lastErrorMessage = errorText
            return

        # Get the current brightness level.
        currentBrightness = device.states.get('brightnessLevel', 100)

        # Save the submitted color temperature into another variable.
        colorTemp = temperature

        # Convert temperature from K to mireds.
        #   Use the ceil and add 3 to help compensate for Hue behavior that "rounds up" to
        #   the next highest compatible mired value for the device.
        temperature = int(3 + ceil(1000000.0 / temperature))

        # Sanity check for an IP address
        if ipAddress is None:
            errorText = u"No IP address set for the Hue bridge. You can get this information from the My Settings page at http://www.meethue.com"
            self.errorLog(errorText)
            # Remember the error.
            self.lastErrorMessage = errorText
            return

        # Act based on device type.
        if device.deviceTypeId == "hueGroup":
            # Sanity check on group ID
            groupId = device.pluginProps.get('groupId', None)
            if groupId is None or groupId == 0:
                errorText = u"No group ID selected for device \"{}\". Check settings for this device and select a Hue Group to control.".format(device.name)
                self.errorLog(errorText)
                # Remember the error.
                self.lastErrorMessage = errorText
                return
        else:
            # Sanity check on bulb ID
            bulbId = device.pluginProps.get('bulbId', None)
            if bulbId is None or bulbId == 0:
                errorText = u"No bulb ID selected for device \"{}\". Check settings for this device and select a Hue Device to control.".format(device.name)
                self.errorLog(errorText)
                # Remember the error.
                self.lastErrorMessage = errorText
                return

        # Make sure this device supports color.
        modelId = device.pluginProps.get('modelId', "")
        type = device.pluginProps.get('type', "")
        if type == kLivingWhitesDeviceIDType or type[0:len(kOnOffOnlyDeviceIDType)] == kOnOffOnlyDeviceIDType:
            errorText = u"Cannot set Color Temperature values. The \"{}\" device does not support variable color temperature.".format(device.name)
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
            # Exclude transition time if needed.
            if device.pluginProps.get("noOnRampRate", False) and currentBrightness == 0:
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
            if device.pluginProps.get("noOffRampRate", False):
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
        self.debugLog(u"Request is {}".format(requestData) )
        try:
            r = requests.put(command, data=requestData, timeout=kTimeout)
        except requests.exceptions.Timeout:
            errorText = u"Failed to connect to the Hue bridge at {} after {} seconds. - Check that the bridge is connected and turned on.".format(ipAddress, kTimeout)
            # Don't display the error if it's been displayed already.
            if errorText != self.lastErrorMessage:
                self.errorLog(errorText)
                # Remember the error.
                self.lastErrorMessage = errorText
            return
        except requests.exceptions.ConnectionError:
            errorText = u"Failed to connect to the Hue bridge at {}. - Check that the bridge is connected and turned on.".format(ipAddress)
            # Don't display the error if it's been displayed already.
            if errorText != self.lastErrorMessage:
                self.errorLog(errorText)
                # Remember the error.
                self.lastErrorMessage = errorText
            return
        self.debugLog(u"Got response - {}".format(r.content) )

        # Update on Indigo
        if brightness > 0:
            # Log the change.
            tempBrightness = int(round(brightness / 255.0 * 100.0))
            # Compensate for rounding errors where it rounds down even though brightness is > 0.
            if tempBrightness == 0 and brightness > 0:
                tempBrightness = 1
            # Use originally submitted color temperature in the log version (if logging is enabled).
            if showLog:
                # Exclude mention of ramp rate if none was used.
                if device.pluginProps.get("noOnRampRate", False) and currentBrightness == 0:
                    indigo.server.log(u"\"{}\" on to {} using color temperature  {}K".format( device.name, tempBrightness, colorTemp, rampRate / 10.0 ), 'Sent Hue Lights')
                else:
                    indigo.server.log(u"\"{}\" on to {} using color temperature  {}K.  at ramp rate  {} sec.".format( device.name, tempBrightness, colorTemp, rampRate / 10.0 ), 'Sent Hue Lights')
            self.updateDeviceState(device, 'brightnessLevel', int(round(brightness / 255.0 * 100.0)))
        else:
            # Log the change.
            if showLog:
                # Exclude mention of ramp rate if nnone was used.
                if device.pluginProps.get("noOffRampRate", False):
                    indigo.server.log(u"\"{}\" off".format( device.name), 'Sent Hue Lights')
                else:
                    indigo.server.log(u"\"{}\" off, at ramp rate:{} sec".format( device.name,  rampRate / 10.0 ), 'Sent Hue Lights')
            self.updateDeviceState(device, 'brightnessLevel', 0)
        # Update the color mode state.
        self.updateDeviceState(device, 'colorMode', "ct")
        # Update the color temperature state (it's in mireds now, convert to Kelvin).
        self.updateDeviceState(device, 'colorTemp', colorTemp)

    # Start Alert (Blinking)
    ########################################
    def doAlert(self, device, alertType="lselect", showLog=True):
        self.debugLog(u"Starting doAlert. alert: {}. Device: {}".format(alertType, device))
        # alertType:	Optional string.  String options are:
        #					lselect		: Long alert (default if nothing specified)
        #					select		: Short alert
        #					none		: Stop any running alerts
        hubNumber, ipAddress, hostId, paired = self.getIdsFromDevice(device)

        # Sanity check for an IP address
        if ipAddress is None:
            errorText = u"No IP address set for the Hue bridge. You can get this information from the My Settings page at http://www.meethue.com"
            self.errorLog(errorText)
            # Remember the error.
            self.lastErrorMessage = errorText
            return

        # Act based on device type.
        if device.deviceTypeId == "hueGroup":
            # Sanity check on group ID
            groupId = device.pluginProps.get('groupId', None)
            if groupId is None or groupId == 0:
                errorText = u"No group ID selected for device \"{}\". Check settings for this device and select a Hue Group to control.".format(device.name)
                self.errorLog(errorText)
                # Remember the error.
                self.lastErrorMessage = errorText
                return
        elif device.deviceTypeId == 'hueAttributeController' or device.deviceTypeId in kMotionSensorTypeIDs or device.deviceTypeId in kTemperatureSensorTypeIDs or device.deviceTypeId in kLightSensorTypeIDs or device.deviceTypeId in kSwitchTypeIDs:
            # Attribute controllers and sensor devices don't support alert actions. Print the error in the Indigo log.
            errorText = u"The \"{}\" device does not support Alert actions. Select a different Hue device.".format(device.name)
            self.errorLog(errorText)
            # Remember the error.
            self.lastErrorMessage = errorText
            return
        else:
            # Sanity check on bulb ID
            bulbId = device.pluginProps.get('bulbId', None)
            if bulbId is None or bulbId == 0:
                errorText = u"No bulb ID selected for device \"{}\". Check settings for this device and select a Hue Device to control.".format(device.name)
                self.errorLog(errorText)
                # Remember the error.
                self.lastErrorMessage = errorText
                return

        requestData = json.dumps({"alert": alertType})
        # Create the command based on whether this is a light or group device.
        if device.deviceTypeId == "hueGroup":
            command = "http://{}/api/{}/groups/{}/action".format(ipAddress, self.hostIds[hubNumber], groupId)
        else:
            command = "http://{}/api/{}/lights/{}/state".format(ipAddress, self.hostIds[hubNumber], bulbId)
        try:
            r = requests.put(command, data=requestData, timeout=kTimeout)
        except requests.exceptions.Timeout:
            errorText = u"Failed to connect to the Hue bridge at {} after {} seconds. - Check that the bridge is connected and turned on.".format(ipAddress, kTimeout)
            # Don't display the error if it's been displayed already.
            if errorText != self.lastErrorMessage:
                self.errorLog(errorText)
                # Remember the error.
                self.lastErrorMessage = errorText
            return
        except requests.exceptions.ConnectionError:
            errorText = u"Failed to connect to the Hue bridge at {}. - Check that the bridge is connected and turned on.".format(ipAddress)
            # Don't display the error if it's been displayed already.
            if errorText != self.lastErrorMessage:
                self.errorLog(errorText)
                # Remember the error.
                self.lastErrorMessage = errorText
            return
        self.debugLog(u"Got response - {}".format(r.content) )

        # Log the change (if enabled).
        if showLog:
            if alertType == "select":
                indigo.server.log(u"\"{}\" start short alert blink.".format(device.name), 'Sent Hue Lights')
            elif alertType == "lselect":
                indigo.server.log(u"\"{}\" start long alert blink.".format(device.name), 'Sent Hue Lights')
            elif alertType == "none":
                indigo.server.log(u"\"{}\" stop alert blink.", 'Sent Hue Lights')
        # Update the device state.
        self.updateDeviceState(device, 'alertMode', alertType)

    # Set Effect Status
    ########################################
    def doEffect(self, device, effect, showLog=True):
        self.debugLog(u"Starting doEffect. effect: {}. Device: {}".format(effect, device))
        # effect:		String specifying the effect to use.  Hue supported effects are:
        #					none		: Stop any current effect
        #					colorloop	: Cycle through all hues at current brightness/saturation.
        #				Other effects may be supported by Hue with future firmware updates.
        hubNumber, ipAddress, hostId, paired = self.getIdsFromDevice(device)

        # Sanity check for an IP address
        if ipAddress is None:
            errorText = u"No IP address set for the Hue bridge. You can get this information from the My Settings page at http://www.meethue.com"
            self.errorLog(errorText)
            # Remember the error.
            self.lastErrorMessage = errorText
            return False

        # Act based on device type.
        if device.deviceTypeId == "hueGroup":
            # Sanity check on group ID
            groupId = device.pluginProps.get('groupId', None)
            if groupId is None or groupId == 0:
                errorText = u"No group ID selected for device \"{}\". Check settings for this device and select a Hue Group to control.".format(device.name)
                self.errorLog(errorText)
                # Remember the error.
                self.lastErrorMessage = errorText
                return
        else:
            # Sanity check on bulb ID
            bulbId = device.pluginProps.get('bulbId', None)
            if bulbId is None or bulbId == 0:
                errorText = u"No bulb ID selected for device \"{}\". Check settings for this device and select a Hue Device to control.".format(device.name)
                self.errorLog(errorText)
                # Remember the error.
                self.lastErrorMessage = errorText
                return

        # Submit to Hue
        requestData = json.dumps({"effect": effect})
        self.debugLog(u"Request is {}".format(r.requestData) )
        # Create the command based on whether this is a light or group device.
        if device.deviceTypeId == "hueGroup":
            command = "http://{}/api/{}/groups/{}/action".format(ipAddress, self.hostIds[hubNumber], groupId)
        else:
            command = "http://{}/api/{}/lights/{}/state".format(ipAddress, self.hostIds[hubNumber], bulbId)
        self.debugLog(u"URL: " + command)
        try:
            r = requests.put(command, data=requestData, timeout=kTimeout)
        except requests.exceptions.Timeout:
            errorText = u"Failed to connect to the Hue bridge at {} after {} seconds. - Check that the bridge is connected and turned on." .format(ipAddress, kTimeout)
            # Don't display the error if it's been displayed already.
            if errorText != self.lastErrorMessage:
                self.errorLog(errorText)
                # Remember the error.
                self.lastErrorMessage = errorText
            return
        except requests.exceptions.ConnectionError:
            errorText = u"Failed to connect to the Hue bridge at {}. - Check that the bridge is connected and turned on.".format(ipAddress)
            # Don't display the error if it's been displayed already.
            if errorText != self.lastErrorMessage:
                self.errorLog(errorText)
                # Remember the error.
                self.lastErrorMessage = errorText
            return
        self.debugLog(u"Got response - {}".format(r.content) )

        # Log the change (if enabled).
        if showLog:
            indigo.server.log(u"\"" + device.name + u"\" set effect to \"" + effect + u"\"", 'Sent Hue Lights')
        # Update the device state.
        self.updateDeviceState(device, 'effect', effect)

    # Recall a Hue Scene
    ########################################
    def doScene(self, groupId="0", sceneId="", hubNumber = "0", showLog=True):
        self.debugLog(u"Starting doScene. groupId: {}, sceneId: {}.".format(groupId, sceneId))
        # groupId:		String. Group ID (numeral) on Hue bridge on which to apply the scene.
        # sceneId:		String. Scene ID on Hue bridge of scene to be applied to the group.

        # The Hue bridge behavior is to apply the scene to all members of the group that are
        #   also members of the scene.  If a group is selected that has no lights that are
        #   also part of the scene, nothing will happen when the scene is activated.  The
        #   build-in Hue group 0 is the set of all Hue lights, so if the scene is applied
        #   to group 0, all lights that are part of the scene will be affected.

        # Sanity check for an IP address
        ipAddress = self.ipAddresses[hubNumber]
        if ipAddress is None:
            errorText = u"No IP address set for the Hue bridge. You can get this information from the My Settings page at http://www.meethue.com"
            self.errorLog(errorText)
            # Remember the error.
            self.lastErrorMessage = errorText
            return

        # Make sure a scene ID was sent.
        if sceneId == "":
            errorText = u"No scene selected. Check settings for this action and select a scene to recall."
            self.errorLog(errorText)
            # Remember the error.
            self.lastErrorMessage = errorText
            return
        else:
            # Let's get more scene information.
            sceneName = self.scenesDict[hubNumber][sceneId]['name']
            sceneOwner = self.scenesDict[hubNumber][sceneId]['owner']
            if sceneOwner in self.usersDict[hubNumber]:
                userName = self.usersDict[hubNumber][sceneOwner]['name'].replace("#", " app on ")
            else:
                userName = u" (a removed scene creator)"

        # If the group isn't the default group ID 0, get more group info.
        if groupId != "0":
            groupName = self.groupsDict[hubNumber][groupId]['name']
        else:
            groupName = "all hue lights"

        # Create the JSON object and send the command to the bridge.
        requestData = json.dumps({"scene": sceneId})
        # Create the command.
        command = "http://{}/api/{}/groups/{}/action".format(ipAddress, self.hostIds[hubNumber], groupId)
        self.debugLog("Sending URL request: {}".format(command) )

        try:
            r = requests.put(command, data=requestData, timeout=kTimeout)

        except requests.exceptions.Timeout:
            errorText = u"Failed to connect to the Hue bridge at {} after {} seconds. - Check that the bridge is connected and turned on.".format(ipAddress, kTimeout)
            # Don't display the error if it's been displayed already.
            if errorText != self.lastErrorMessage:
                self.errorLog(errorText)
                # Remember the error.
                self.lastErrorMessage = errorText
            return

        except requests.exceptions.ConnectionError:
            errorText = u"Failed to connect to the Hue bridge at {}. - Check that the bridge is connected and turned on.".format(ipAddress)
            # Don't display the error if it's been displayed already.
            if errorText != self.lastErrorMessage:
                self.errorLog(errorText)
                # Remember the error.
                self.lastErrorMessage = errorText
            return

        self.debugLog("Got response - {}".format(r.content) )
        # Show the log (if enabled).
        if showLog:
            indigo.server.log(u"\"" + sceneName + u"\" scene from \"" + userName + u"\" recalled for \"" + groupName + u"\"", 'Hue Lights')



    # Update Light, Group, Scene and Sensor Lists
    ########################################
    def updateAllHueLists(self):
        # This function is generally only used as a callback method for the
        #    Plugins -> Hue Lights -> Reload Hue bridge Config menu item, but can
        #    be used to force a reload of everything from the Hue bridge.

       # Do we have a unique Hue username (a.k.a. key or host ID)?
        if self.hostIds == {"0":""}:
            self.hostIds = {"0": self.hostId}
        indigo.server.log(u"hostIds read:  {}".format(self.hostIds))

        for hubNumber in  self.hostIds:
            hueUsername = self.hostIds[hubNumber]
            if hueUsername is None:
                self.debugLog(u"Hue Lights doesn't appear to be paired with the Hue bridge.")
            else:
                self.debugLog(u"The username Hue Lights uses to connect to the Hue bridge is {}" .format(hueUsername) )

        # Get the entire Hue bridge configuration and report the results.


        # Sanity check for an IP address
        ## old if only one hub, expaned to option of having multiple hubs
        ipAddress = self.pluginPrefs.get('address', None)
        tempIP= json.loads(self.pluginPrefs.get('addresses', '{"0":""}'))
        if tempIP == {"0":""}:
            tempIP['0'] = ipAddress

        for hubNumber in tempIP:
            if hubNumber not in khubNumbersAvailable: continue
            if tempIP[hubNumber] is None:
                errorText = u"No IP address set for the Hue bridge. You can get this information from the My Settings page at http://www.meethue.com."
                self.errorLog(errorText)
                # Remember the error.
                self.lastErrorMessage = errorText
                return
            self.ipAddresses[hubNumber] = tempIP[hubNumber]
        indigo.server.log(u"ipAddresses loaded:{} ".format(self.ipAddresses))
        self.pluginPrefs['addresses'] = json.dumps(self.ipAddresses)

        # Get the entire configuration from the Hue bridge.
        self.getHueConfig()
        indigo.server.log(u"hubs paired read:  {}".format(self.paired))

        for hubNumber in self.ipAddresses:
            # Now report the results.
            #
            # Lights list...
            if hubNumber in  self.lightsDict: indigo.server.log(u"hub:{} Loaded {} light(s).".format(hubNumber, len(self.lightsDict[hubNumber])))

            # Groups list...
            if hubNumber in  self.groupsDict: indigo.server.log(u"hub:{} Loaded {} group(s).".format(hubNumber, len(self.groupsDict[hubNumber])))

            # User devices list...
            #indigo.server.log(u"Loaded %i user device." % len(self.usersDict[hubNumber]))

            # Scenes list...
            if hubNumber in  self.scenesDict: indigo.server.log(u"hub:{} Loaded {} scene(s).".format(hubNumber, len(self.scenesDict[hubNumber])))

            # Resource links list...
            #indigo.server.log(u"Loaded %i resource link(s)." % len(self.resourcesDict))

            # Trigger rules list...
            #if hubNumber in  self.lightsDict: indigo.server.log(u"Loaded %i trigger rule(s)." % len(self.rulesDict))

            # Schedules list...
            #if hubNumber in  self.lightsDict: indigo.server.log(u"Loaded %i schedule(s)." % len(self.schedulesDict))

            # Sensors list...
            if hubNumber in  self.sensorsDict: indigo.server.log(u"hub:{} Loaded {} sensor(s).".format(hubNumber, len(self.sensorsDict[hubNumber])))
        return



    ########################################
    # Hue bridge Pairing Methods
    ########################################

    # Start/Restart Pairing with Hue bridge
    ########################################
    def restartPairing(self, valuesDict):
        # This method should only be used as a callback method from the
        #   plugin configuration dialog's "Pair Now" button.
        self.debugLog(u"Starting restartPairing.")
        isError = False
        errorsDict = indigo.Dict()
        errorsDict['showAlertText'] = ""
        hubNumber = valuesDict['hubNumber']
        if hubNumber not in khubNumbersAvailable: 
            self.debugLog(u"Starting restartPairing. bad hubNumber given {}".format(hubNumber))
            return 
        self.hubNumberSelected = valuesDict['hubNumber']

        # Validate the IP Address field.
        if valuesDict.get('address', "") == "":
            # The field was left blank.
            self.debugLog(u"IP address \"{}\" is blank.".format(valuesDict['address']))
            isError = True
            errorsDict['address'] = u"The IP Address field is blank. Please enter an IP Address for the Hue bridge."
            errorsDict['showAlertText'] += errorsDict['address'] + u"\n\n"

        else:
            # The field wasn't blank. Check to see if the format is valid.
            try:
                # Try to format the IP Address as a 32-bit binary value. If this fails, the format was invalid.
                self.debugLog(u"Validating IP address \"{}\".".format(valuesDict['address']))
                socket.inet_aton(valuesDict['address'])

            except socket.error:
                # IP Address format was invalid.
                self.debugLog(u"IP address format is invalid.")
                isError = True
                errorsDict['address'] = u"The IP Address is not valid. Please enter a valid IP address."
                errorsDict['showAlertText'] += errorsDict['address'] + u"\n\n"

        # If there haven't been any errors so far, try to connect to the Hue bridge to see
        #   if it's actually a Hue bridge.
        if not isError:
            try:
                self.debugLog(u"Verifying that a Hue bridge exists at IP address \"{}\".".format(valuesDict['address']))
                command = "http://{}/description.xml".format(valuesDict['address'])
                self.debugLog(u"Accessing URL: {}".format(command))
                r = requests.get(command, timeout=kTimeout)
                self.debugLog(u"Got response:\n{}".format(r.content))

                # Quick and dirty check to see if this is a Philips Hue bridge.
                if "Philips hue bridge" not in r.content:
                    # If "Philips hue bridge" doesn't exist in the response, it's not a Hue bridge.
                    self.debugLog(u"No \"Philips hue bridge\" string found in response. This isn't a Hue bridge.")
                    isError = True
                    errorsDict['address'] = u"This doesn't appear to be a Philips Hue bridge.  Please verify the IP address."
                    errorsDict['showAlertText'] += errorsDict['address'] + u"\n\n"

                else:
                    # This is likely a Hue bridge.
                    self.debugLog(u"Verified that this is a Hue bridge.")

            except requests.exceptions.Timeout:
                errorText = u"Connection to {} timed out after {} seconds.".format(valuesDict['address'], kTimeout)
                self.errorLog(errorText)
                isError = True
                errorsDict['address'] = u"Unable to reach the bridge. Please check the IP address and ensure that the Indigo server and Hue bridge are connected to the network."
                errorsDict['showAlertText'] += errorsDict['address'] + u"\n\n"

            except requests.exceptions.ConnectionError:
                errorText = u"Connection to {} failed. There was a connection error.".format(valuesDict['address'])
                self.errorLog(errorText)
                isError = True
                errorsDict['address'] = u"Connection error. Please check the IP address and ensure that the Indigo server and Hue bridge are connected to the network."
                errorsDict['showAlertText'] += errorsDict['address'] + u"\n\n"

            except Exception, e:
                errorText = u"Connection error. {}".format(e)
                self.errorLog(errorText)
                isError = True
                errorsDict['address'] = u"Connection error. Please check the IP address and ensure that the Indigo server and Hue bridge are connected to the network."
                errorsDict['showAlertText'] += errorsDict['address'] + u"\n\n"

        # Check for errors and act accordingly.
        if isError:
            # There was at least 1 error.
            errorsDict['showAlertText'] = errorsDict['showAlertText'].strip()
            return (valuesDict, errorsDict)
        else:
            # There weren't any errors, so...
            # Try pairing with the bridge.

            # Configure timeout
            socket.setdefaulttimeout(kTimeout)

            # Request a username/key.
            try:
                self.ipAddresses[hubNumber] = valuesDict['address']
                indigo.server.log(u"Attempting to pair with the Hue bridge at \"{}\".".format(valuesDict['address']))
                requestData = json.dumps({"devicetype": "Indigo Hue Lights"})
                self.debugLog(u"Request is {}".format(requestData) )
                command = "http://{}/api".format(valuesDict['address'])
                self.debugLog(u"Sending request to {} (via HTTP POST).".format(command))
                r = requests.post(command, data=requestData, timeout=kTimeout)
                responseData = json.loads(r.content)
                self.debugLog(u"Got response {}".format(responseData))

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
                            errorText = u"Unable to pair with the Hue bridge. Press the center button on the Hue bridge, then click the \"Pair Now\" button."
                            self.errorLog(errorText)
                            isError = True
                            errorsDict['startPairingButton'] = errorText
                            errorsDict['showAlertText'] += errorsDict['startPairingButton'] + u"\n\n"

                        else:
                            errorText = u"Error #{} from the Hue bridge. Description: \"{}\".".format(errorCode, errorDict.get('description', u"(No Description)"))
                            self.errorLog(errorText)
                            isError = True
                            errorsDict['startPairingButton'] = errorText
                            errorsDict['showAlertText'] += errorsDict['startPairingButton'] + u"\n\n"

                    # See if we got a success response.
                    successDict = firstResponseItem.get('success', None)
                    if successDict is not None:
                        # Pairing was successful.
                        indigo.server.log(u"Paired with Hue bridge successfully.")
                        # The plugin was paired with the Hue bridge.
                        self.paired[hubNumber] = True
                        # Get the username provided by the bridge.
                        hueUsername = successDict['username']
                        self.debugLog(u"Username (a.k.a. key) assigned by Hue bridge to Hue Lights plugin: {}".format(hueUsername))
                        # Set the plugin's hostId to the new username.
                        self.hostIds[hubNumber] = hueUsername
                        # Make sure the new username is returned to the config dialog.
                        valuesDict['hostId'] = hueUsername
                        valuesDict['hostIds'] = json.dumps(self.hostIds)

                else:
                    # The Hue bridge is acting weird.  There should have been only 1 response.
                    errorText = u"Invalid response from Hue bridge. Check the IP address and try again."
                    self.errorLog(errorText)
                    self.debugLog(u"Response from Hue bridge contained {} items.".format(len(responseData)))
                    isError = True
                    errorsDict['startPairingButton'] = errorText
                    errorsDict['showAlertText'] += errorsDict['startPairingButton'] + u"\n\n"

            except requests.exceptions.Timeout:
                errorText = u"Connection to {} timed out after {} seconds.".format(valuesDict['address'], kTimeout)
                self.errorLog(errorText)
                isError = True
                errorsDict['startPairingButton'] = u"Unable to reach the bridge. Please check the IP address and ensure that the Indigo server and Hue bridge are connected to the network."
                errorsDict['showAlertText'] += errorsDict['startPairingButton'] + u"\n\n"

            except requests.exceptions.ConnectionError:
                errorText = u"Connection to {} failed. There was a connection error.".format(valuesDict['address'])
                self.errorLog(errorText)
                isError = True
                errorsDict['startPairingButton'] = u"Connection error. Please check the IP address and ensure that the Indigo server and Hue bridge are connected to the network."
                errorsDict['showAlertText'] += errorsDict['startPairingButton'] + u"\n\n"

            except Exception, e:
                errorText = u"Connection error. {}".format(e)
                self.errorLog(errorText)
                isError = True
                errorsDict['startPairingButton'] = u"Connection error. Please check the IP address and ensure that the Indigo server and Hue bridge are connected to the network."
                errorsDict['showAlertText'] += errorsDict['startPairingButton'] + u"\n\n"

            # Check again for errors.
            if isError:
                # There was at least 1 error.
                errorsDict['showAlertText'] = errorsDict['showAlertText'].strip()
                return (valuesDict, errorsDict)

            valuesDict['addresses'] = json.dumps(self.ipAddresses)
            return valuesDict




    ########################################
    # Action Handling Methods
    ########################################

    # Start (or Stop if already) Brightening
    ########################################
    def startStopBrightening(self, action, device):
        # Catch if no device was passed in the action call.
        if device == None:
            errorText = u"No device was selected for the \"" + action.name + u"\" action. Please edit the action and select a Hue Light device."
            self.errorLog(errorText)
            # Remember the error.
            self.lastErrorMessage = errorText
            return
        # Catch if the device is an on/off only device.
        if device.deviceTypeId == "hueOnOffDevice":
            errorText = u"The " + device.name + u" device doesn't support dimming. Please edit the action and select a device that supports dimming."
            self.errorLog(errorText)
            # Remember the error.
            self.lastErrorMessage = errorText
            return

        self.debugLog(u"startStopBrightening: device: {}, action:\n{}".format(device.name, action))
        # Make sure the device is in the deviceList.
        if device.id in self.deviceList:

            # First, remove from the dimmingList if it's there.
            if device.id in self.dimmingList:
                # Log the event to Indigo log.
                indigo.server.log(u"\"{}\" stop dimming".format(device.name), 'Sent Hue Lights')
                # Remove from list.
                self.dimmingList.remove(device.id)

            # Now remove from brighteningList if it's in the list and add if not.
            if device.id in self.brighteningList:
                # Log the event to Indigo log.
                indigo.server.log(u"\"{}\" stop brightening".format(device.name), 'Sent Hue Lights')
                # Remove from list.
                self.brighteningList.remove(device.id)
                # Get the bulb status
                self.getBulbStatus(device.id)
                # Log the new brightnss.
                indigo.server.log(u"\"{}\" status request (received: {})".format( device.name, device.states['brightnessLevel']), 'Sent Hue Lights')
            else:
                # Only begin brightening if current brightness is less than 100%.
                if device.states['brightnessLevel'] < 100:
                    # Log the event in Indigo log.
                    indigo.server.log(u"\"{}\" start brightening".format(device.name), 'Sent Hue Lights')
                    # Add to list.
                    self.brighteningList.append(device.id)

        return

    # Start (or Stop if already) Dimming
    ########################################
    def startStopDimming(self, action, device):
        # Catch if no device was passed in the action call.
        if device == None:
            errorText = u"No device was selected for the \"" + action.name + "\" action. Please edit the action and select a Hue Light device."
            self.errorLog(errorText)
            # Remember the error.
            self.lastErrorMessage = errorText
            return
        # Catch if the device is an on/off only device.
        if device.deviceTypeId == "hueOnOffDevice":
            errorText = u"The {} device doesn't support dimming. Please edit the action and select a device that supports dimming.".format(device.name)
            self.errorLog(errorText)
            # Remember the error.
            self.lastErrorMessage = errorText
            return

        self.debugLog(u"startStopDimming: device: {}, action:\n{}".format(device.name, action))
        # Make sure the device is in the deviceList.
        if device.id in self.deviceList:
            # First, remove from brighteningList if it's there.
            if device.id in self.brighteningList:
                # Log the event to Indigo log.
                indigo.server.log(u"\"{}\" stop brightening".format(device.name), 'Sent Hue Lights')
                # Remove from list.
                self.brighteningList.remove(device.id)

            # Now remove from dimmingList if it's in the list and add if not.
            if device.id in self.dimmingList:
                # Log the event to Indigo log.
                indigo.server.log(u"\"{}\" stop dimming".format(device.name), 'Sent Hue Lights')
                # Remove from list.
                self.dimmingList.remove(device.id)
                # Get the bulb status
                self.getBulbStatus(device.id)
                # Log the new brightnss.
                indigo.server.log(u"\"{}\" status request (received: {})".format(device.name, device.states['brightnessLevel']), 'Sent Hue Lights')
            else:
                # Only begin dimming if current brightness is greater than 0%.
                if device.states['brightnessLevel'] > 0:
                    # Log the event in Indigo log.
                    indigo.server.log(u"\"{}\" start dimming".format(device.name), 'Sent Hue Lights')
                    # Add to list.
                    self.dimmingList.append(device.id)

        return

    # Stop Brightening and Dimming
    ########################################
    def stopBrighteningAndDimming(self, action, device):
        # Catch if no device was passed in the action call.
        if device == None:
            errorText = u"No device was selected for the \"{}\" action. Please edit the action and select a Hue Light device.".format(action)
            self.errorLog(errorText)
            # Remember the error.
            self.lastErrorMessage = errorText
            return
        # Catch if the device is an on/off only device.
        if device.deviceTypeId == "hueOnOffDevice":
            errorText = u"The {} device doesn't support dimming. Please edit the action and select a device that supports dimming.".format(device.name)
            self.errorLog(errorText)
            # Remember the error.
            self.lastErrorMessage = errorText
            return

        self.debugLog(u"stopBrighteningAndDimming: device: {}, action:\n{}".format(device.name, action))
        # Make sure the device is in the deviceList.
        if device.id in self.deviceList:
            # First, remove from brighteningList if it's there.
            if device.id in self.brighteningList:
                # Log the event to Indigo log.
                indigo.server.log(u"\"{}\" stop brightening".format(device.name), 'Sent Hue Lights')
                # Remove from list.
                self.brighteningList.remove(device.id)

            # Now remove from dimmingList if it's in the list.
            if device.id in self.dimmingList:
                # Log the event to Indigo log.
                indigo.server.log(u"\"{}\" stop dimming".format(device.name), 'Sent Hue Lights')
                # Remove from list.
                self.dimmingList.remove(device.id)
                # Get the bulb status
                self.getBulbStatus(device.id)
                # Log the new brightnss.
                indigo.server.log(u"\"{}\" status request (received: {})".format(device.name, device.states['brightnessLevel']), 'Sent Hue Lights')

        return

    # Set Brightness
    ########################################
    def setBrightness(self, action, device):
        self.debugLog(u"setBrightness: device:{}, action:\n{}".format(device.name, action))

        brightnessSource = action.props.get('brightnessSource', False)
        brightness = action.props.get('brightness', False)
        brightnessVarId = action.props.get('brightnessVariable', False)
        brightnessDevId = action.props.get('brightnessDevice', False)
        useRateVariable = action.props.get('useRateVariable', False)
        rate = action.props.get('rate', False)
        rateVarId = action.props.get('rateVariable', False)

        # Act based on device type.
        if device.deviceTypeId == "hueGroup":
            # Sanity check on group ID
            groupId = device.pluginProps.get('groupId', None)
            if groupId is None or groupId == 0:
                errorText = u"No group ID selected for device \"{}\". Check settings for this device and select a Hue Group to control.".format(device.name)
                self.errorLog(errorText)
                # Remember the error.
                self.lastErrorMessage = errorText
                return
        else:
            # Sanity check on bulb ID
            bulbId = device.pluginProps.get('bulbId', None)
            if bulbId is None or bulbId == 0:
                errorText = u"No bulb ID selected for device \"{}\". Check settings for this device and select a Hue Device to control.".format(device.name)
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
                        errorText = u"Brightness level {} is outside the acceptable range of 0 to 100.".format(brightness)
                        self.errorLog(errorText)
                        # Remember the error.
                        self.lastErrorMessage = errorText
                        return None
                except ValueError:
                    errorText = u"Brightness level \"{}\" is invalid. Brightness values can only contain numbers.".format(brightness)
                    self.errorLog(errorText)
                    # Remember the error.
                    self.lastErrorMessage = errorText
                    return None
            self.debugLog(u"Brightness (source: custom): {}, class: {}".format(brightness, brightness.__class__))

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
                        errorText = u"Brightness level {} found in variable \"{}\" is outside the acceptable range of 0 to 100.".format(brightness, brightnessVar.name) 
                        self.errorLog(errorText)
                        # Remember the error.
                        self.lastErrorMessage = errorText
                        return None
                except ValueError:
                    errorText = u"Brightness level \"{}\" found in variable \"{}\" is invalid. Brightness values can only contain numbers.".format(brightnessVar.value, brightnessVar.name) 
                    self.errorLog(errorText)
                    # Remember the error.
                    self.lastErrorMessage = errorText
                    return None
                except IndexError:
                    errorText = u"The specified variable (ID:{}) does not exist in the Indigo database.".format(brightnessVarId)
                    self.errorLog(errorText)
                    # Remember the error.
                    self.lastErrorMessage = errorText
                    return None
            self.debugLog(u"Brightness (source: variable):{} , class:{} ".format(brightnessVarId, brightness.__class__))

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
                        errorText = u"No device with the name \"{}\" could be found in the Indigo database.".format(brightnessDevId)
                        self.errorLog(errorText)
                        # Remember the error.
                        self.lastErrorMessage = errorText
                        return None
                try:
                    brightnessDev = indigo.devices[brightnessDevId]
                    brightness = int(brightnessDev.states.get('brightnessLevel', None))
                    if brightness == None:
                        # Looks like this isn't a dimmer after all.
                        errorText = u"Device \"{}\" does not appear to be a dimmer. Only dimmers can be used as brightness sources.".format(brightnessDev.name)
                        self.errorLog(errorText)
                        # Remember the error.
                        self.lastErrorMessage = errorText
                        return None
                    elif brightness < 0 or brightness > 100:
                        errorText = u"Brightness level {} of device \"{}\" is outside the acceptable range of 0 to 100.".format(brightness, brightnessDev.name)
                        self.errorLog(errorText)
                        # Remember the error.
                        self.lastErrorMessage = errorText
                        return None
                except ValueError:
                    errorText = u"The device \"{}\" does not have a brightness level. Please ensure that the device is a dimmer.".format(brightnessDev.name)
                    self.errorLog(errorText)
                    # Remember the error.
                    self.lastErrorMessage = errorText
                    return None
                except KeyError:
                    errorText = u"The specified device (ID:{}) does not exist in the Indigo database.".format(brightnessDevId)
                    self.errorLog(errorText)
                    # Remember the error.
                    self.lastErrorMessage = errorText
                    return None
            self.debugLog(u"Brightness (source: other dimmer): {}, class: {}".format(brightness, brightness.__class__))

        else:
            errorText = u"Unrecognized brightness source \"{}\". Valid brightness sources are \"custom\", \"variable\", and \"dimmer\".".format(brightnessSource)
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
                        errorText = u"Ramp rate value {} is outside the acceptible range of 0 to 540.".format(rate)
                        self.errorLog(errorText)
                        # Remember the error.
                        self.lastErrorMessage = errorText
                        return None
                except ValueError:
                    errorText = u"Ramp rate value \"{} is an invalid value. Ramp rate values can only contain numbers.".format(rate)
                    self.errorLog(errorText)
                    # Remember the error.
                    self.lastErrorMessage = errorText
                    return None
            self.debugLog(u"Rate: {}" .format(rate))

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
                        errorText = u"Ramp rate value \"{}\" found in variable \"{}\" is outside the acceptible range of 0 to 540.".format(rate, rateVar.name)
                        self.errorLog(errorText)
                        # Remember the error.
                        self.lastErrorMessage = errorText
                        return None
                except ValueError:
                    errorText = u"Ramp rate value \"{}\" found in variable \"{}\" is an invalid value. Ramp rate values can only contain numbers.".format(rate, rateVar.name)
                    self.errorLog(errorText)
                    # Remember the error.
                    self.lastErrorMessage = errorText
                    return None
                except IndexError:
                    errorText = u"The specified variable (ID:{}) does not exist in the Indigo database.".format(brightnessVarId)
                    self.errorLog(errorText)
                    # Remember the error.
                    self.lastErrorMessage = errorText
            self.debugLog(u"Rate: {}".format(rate))

        # Save the new brightness level into the device properties.
        if brightness > 0:
            # On/Off devices have no savedBrightness, so don't try to change it.
            if device.deviceTypeId != "hueOnOffDevice":
                tempProps = device.pluginProps
                tempProps['savedBrightness'] = brightness
                self.updateDeviceProps(device, tempProps)

        # Send the command.
        self.doBrightness(device, int(round(brightness / 100.0 * 255.0)), rate)

    # Set RGB Level Action
    ########################################
    def setRGB(self, action, device):
        self.debugLog(u"setRGB: device:{}, action:\n{}".format(device.name, action))

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
                errorText = u"No group ID selected for device \"{}\". Check settings for this device and select a Hue Group to control.".format(device.name)
                self.errorLog(errorText)
                # Remember the error.
                self.lastErrorMessage = errorText
                return
        else:
            # Sanity check on bulb ID
            bulbId = device.pluginProps.get('bulbId', None)
            if bulbId is None or bulbId == 0:
                errorText = u"No bulb ID selected for device \"{}\". Check settings for this device and select a Hue Device to control.".format(device.name)
                self.errorLog(errorText)
                # Remember the error.
                self.lastErrorMessage = errorText
                return

        try:
            red = int(red)
        except ValueError:
            errorText = u"Red color value specified for \"{}\" is invalid.".format(device.name)
            self.errorLog(errorText)
            # Remember the error.
            self.lastErrorMessage = errorText
            return

        try:
            green = int(green)
        except ValueError:
            errorText = u"Green color value specified for \"{}\" is invalid.".format(device.name)
            self.errorLog(errorText)
            # Remember the error.
            self.lastErrorMessage = errorText
            return

        try:
            blue = int(blue)
        except ValueError:
            errorText = u"Blue color value specified for \"{}\" is invalid.".format(device.name)
            self.errorLog(errorText)
            # Remember the error.
            self.lastErrorMessage = errorText
            return

        if not useRateVariable:
            # Not using varible, so they've specificed a ramp rate.
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
                    errorText = u"Ramp rate value {}\" is outside the acceptible range of 0 to 540.".format(rampRate)
                    self.errorLog(errorText)
                    # Remember the error.
                    self.lastErrorMessage = errorText
                    return None
            except ValueError:
                errorText = u"Ramp rate value \"{}\" is an invalid value. Ramp rate values can only contain numbers.".format(rampRate)
                self.errorLog(errorText)
                # Remember the error.
                self.lastErrorMessage = errorText
                return None
            self.debugLog(u"Rate: {}".format(rampRate))

        else:
            # We're using a ramp rate variable.
            if not rateVarId:
                # No ramp rate variable was specified.
                errorText = u"No variable containing the ramp rate time was specified."
                self.errorLog(errorText)
                # Remember the error.
                self.lastErrorMessage = errorText
                return
            else:
                # A ramp rate variable was specified.
                try:
                    rateVar = indigo.variables[int(rateVarId)]
                    rampRate = rateVar.value
                    rampRate = float(rampRate)
                    if rampRate < 0 or rampRate > 540:
                        errorText = u"Ramp rate value \"{}\" found in variable \"{}\" is outside the acceptible range of 0 to 540.".format(rampRate, rateVar.name )
                        self.errorLog(errorText)
                        # Remember the error.
                        self.lastErrorMessage = errorText
                        return
                except ValueError:
                    errorText = u"Ramp rate value \"{}\" found in variable \"{}\" is an invalid value. Ramp rate values can only contain numbers.".format(rampRate, rateVar.name )
                    self.errorLog(errorText)
                    # Remember the error.
                    self.lastErrorMessage = errorText
                    return
                except IndexError:
                    errorText = u"The specified variable (ID:{}) does not exist in the Indigo database.".format(brightnessVarId )
                    self.errorLog(errorText)
                    # Remember the error.
                    self.lastErrorMessage = errorText
                    return
            self.debugLog(u"Rate: {}".format(rampRate))

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

    # Set HSB Action
    ########################################
    def setHSB(self, action, device):
        self.debugLog(u"setHSB: device:{}, action:\n{}".format(device.name, action))

        hue = action.props.get('hue', 0)
        saturation = action.props.get('saturation', 0)
        brightnessSource = action.props.get('brightnessSource', "custom")
        brightness = action.props.get('brightness', False)
        brightnessVariable = action.props.get('brightnessVariable', False)
        brightnessDevice = action.props.get('brightnessDevice', False)
        useRateVariable = action.props.get('useRateVariable', False)
        rampRate = action.props.get('rate', -1)
        rateVarId = action.props.get('rateVariable', False)

        # Act based on device type.
        if device.deviceTypeId == "hueGroup":
            # Sanity check on group ID
            groupId = device.pluginProps.get('groupId', None)
            if groupId is None or groupId == 0:
                errorText = u"No group ID selected for device \"{}\". Check settings for this device and select a Hue Group to control.".format(device.name)
                self.errorLog(errorText)
                # Remember the error.
                self.lastErrorMessage = errorText
                return
        else:
            # Sanity check on bulb ID
            bulbId = device.pluginProps.get('bulbId', None)
            if bulbId is None or bulbId == 0:
                errorText = u"No bulb ID selected for device \"{}\". Check settings for this device and select a Hue Device to control.".format(device.name)
                self.errorLog(errorText)
                # Remember the error.
                self.lastErrorMessage = errorText
                return

        try:
            hue = float(hue)
        except ValueError:
            # The float() cast above might fail if the user didn't enter a number:
            errorText = u"Set Hue, Saturation, Brightness for device \"{}\" -- invalid hue value (must range 0-360)".format(device.name)
            self.errorLog(errorText)
            # Remember the error.
            self.lastErrorMessage = errorText
            return

        try:
            saturation = int(saturation)
        except ValueError:
            # The int() cast above might fail if the user didn't enter a number:
            errorText = u"Set Hue, Saturation, Brightness for device \"{}\" -- invalid saturation value (must range 0-100)".format(device.name)
            self.errorLog(errorText)
            # Remember the error.
            self.lastErrorMessage = errorText
            return

        if brightnessSource == "custom":
            # Using an entered brightness value.
            if brightness:
                try:
                    brightness = int(brightness)
                except ValueError:
                    errorText = u"Invalid brightness value \"{}\" specified for device \"{}\". Value must be in the range 0-100.".format(brightness, device.name)
                    self.errorLog(errorText)
                    # Remember the error.
                    self.lastErrorMessage = errorText
                    return

                # Make sure the brightness specified in the variable is sane.
                if brightness < 0 or brightness > 100:
                    errorText = u"Brightness value \"{}\" for device \"{}\" is outside the acceptible range of 0 to 100.".format(brightness, device.name)
                    self.errorLog(errorText)
                    # Remember the error.
                    self.lastErrorMessage = errorText
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
                    errorText = u"Brightness value \"{}\" specified in variable \"{}\" for device \"{}\" is invalid.".format(indigo.variables[brightnessVariable].value , indigo.variables[brightnessVariable].name, device.name)
                    self.errorLog(errorText)
                    # Remember the error.
                    self.lastErrorMessage = errorText
                    return
                except IndexError:
                    errorText = u"The brightness source variable (ID:{}) does not exist in the Indigo database.".format(brightnessVariable)
                    self.errorLog(errorText)
                    # Remember the error.
                    self.lastErrorMessage = errorText
                    return

                # Make sure the brightness specified in the variable is sane.
                if brightness < 0 or brightness > 100:
                    errorText = u"Brightness value \"{}\" specified in variable \"{}\" is outside the acceptible range of 0 to 100.".format(brightness , indigo.variables[brightnessVariable].name)
                    self.errorLog(errorText)
                    # Remember the error.
                    self.lastErrorMessage = errorText
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
                    errorText = u"The brightness \"{}\" of the selected source device \"{}\" is invalid.".format(indigo.devices[brightnessDevice].states['brightnessLevel']  , indigo.devices[brightnessDevice].name )
                    self.errorLog(errorText)
                    # Remember the error.
                    self.lastErrorMessage = errorText
                    return
                except IndexError:
                    errorText = u"The brightness source device (ID:{}) does not exist in the Indigo database.".format(brightnessDevice)
                    self.errorLog(errorText)
                    # Remember the error.
                    self.lastErrorMessage = errorText
                    return
            else:
                brightness = device.states['brightnessLevel']

        if not useRateVariable:
            # Not using varible, so they've specificed a ramp rate.
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
                    errorText = u"Ramp rate value {}\" is outside the acceptible range of 0 to 540.".format(rampRate)
                    self.errorLog(errorText)
                    # Remember the error.
                    self.lastErrorMessage = errorText
                    return None
            except ValueError:
                errorText = u"Ramp rate value \"{}\" is an invalid value. Ramp rate values can only contain numbers.".format(rampRate)
                self.errorLog(errorText)
                # Remember the error.
                self.lastErrorMessage = errorText
                return None
            self.debugLog(u"Rate: {}".format(rampRate))

        else:
            # We're using a ramp rate variable.
            if not rateVarId:
                # No ramp rate variable was specified.
                errorText = u"No variable containing the ramp rate time was specified."
                self.errorLog(errorText)
                # Remember the error.
                self.lastErrorMessage = errorText
                return
            else:
                # A ramp rate variable was specified.
                try:
                    rateVar = indigo.variables[int(rateVarId)]
                    rampRate = rateVar.value
                    rampRate = float(rampRate)
                    if rampRate < 0 or rampRate > 540:
                        errorText = u"Ramp rate value \"{}\" found in variable \"{}\" is outside the acceptible range of 0 to 540.".format(rampRate, rateVar.name )
                        self.errorLog(errorText)
                        # Remember the error.
                        self.lastErrorMessage = errorText
                        return
                except ValueError:
                    errorText = u"Ramp rate value \"{}\" found in variable \"{}\" is an invalid value. Ramp rate values can only contain numbers.".format(rampRate, rateVar.name )
                    self.errorLog(errorText)
                    # Remember the error.
                    self.lastErrorMessage = errorText
                    return
                except IndexError:
                    errorText = u"The specified variable (ID:{}) does not exist in the Indigo database.".format(brightnessVarId)
                    self.errorLog(errorText)
                    # Remember the error.
                    self.lastErrorMessage = errorText
                    return
            self.debugLog(u"Rate: {}".format(rampRate))

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
        self.debugLog(u"setXYY calld. device:{}, action:\n{}".format(device.name, action))

        colorX = action.props.get('xyy_x', 0.0)
        colorY = action.props.get('xyy_y', 0.0)
        brightness = action.props.get('xyy_Y', 0)
        useRateVariable = action.props.get('useRateVariable', False)
        rampRate = action.props.get('rate', -1)
        rateVarId = action.props.get('rateVariable', False)

        # Act based on device type.
        if device.deviceTypeId == "hueGroup":
            # Sanity check on group ID
            groupId = device.pluginProps.get('groupId', None)
            if groupId is None or groupId == 0:
                errorText = u"No group ID selected for device \"{}\". Check settings for this device and select a Hue Group to control.".format(device.name)
                self.errorLog(errorText)
                # Remember the error.
                self.lastErrorMessage = errorText
                return
        else:
            # Sanity check on bulb ID
            bulbId = device.pluginProps.get('bulbId', None)
            if bulbId is None or bulbId == 0:
                errorText = u"No bulb ID selected for device \"{}\". Check settings for this device and select a Hue Device to control.".format(device.name)
                self.errorLog(errorText)
                # Remember the error.
                self.lastErrorMessage = errorText
                return

        try:
            colorX = float(colorX)
        except ValueError:
            # The float() cast above might fail if the user didn't enter a number:
            errorText = u"Set chromatisety x, y, and Y values for the device \"{}\" -- invalid x value (must be in the range of 0.0-1.0)".format(device.name)
            self.errorLog(errorText)
            # Remember the error.
            self.lastErrorMessage = errorText
            return

        try:
            colorY = float(colorY)
        except ValueError:
            # The float() cast above might fail if the user didn't enter a number:
            errorText = u"Set chromatisety x, y, and Y values for the device \"{}\" -- invalid y value (must be in the range of 0.0-1.0)".format(device.name)
            self.errorLog(errorText)
            # Remember the error.
            self.lastErrorMessage = errorText
            return

        try:
            brightness = float(brightness)
        except ValueError:
            # The float() cast above might fail if the user didn't enter a number:
            errorText = u"Set chromatisety x, y, and Y values for the device \"{}\" -- invalid Y value of \"{}\" (must be in the range of 0.0-1.0)".format(device.name, brightness)
            self.errorLog(errorText)
            # Remember the error.
            self.lastErrorMessage = errorText
            return

        if not useRateVariable:
            # Not using varible, so they've specificed a ramp rate.
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
                    errorText = u"Ramp rate value {}\" is outside the acceptible range of 0 to 540.".format(rampRate)
                    self.errorLog(errorText)
                    # Remember the error.
                    self.lastErrorMessage = errorText
                    return None
            except ValueError:
                errorText = u"Ramp rate value \"{}\" is an invalid value. Ramp rate values can only contain numbers.".format(rampRate)
                self.errorLog(errorText)
                # Remember the error.
                self.lastErrorMessage = errorText
                return None
            self.debugLog(u"Rate: {}".format(rampRate))

        else:
            # We're using a ramp rate variable.
            if not rateVarId:
                # No ramp rate variable was specified.
                errorText = u"No variable containing the ramp rate time was specified."
                self.errorLog(errorText)
                # Remember the error.
                self.lastErrorMessage = errorText
                return
            else:
                # A ramp rate variable was specified.
                try:
                    rateVar = indigo.variables[int(rateVarId)]
                    rampRate = rateVar.value
                    rampRate = float(rampRate)
                    if rampRate < 0 or rampRate > 540:
                        errorText = u"Ramp rate value \"{}\" found in variable \"{}\" is outside the acceptible range of 0 to 540.".format(rampRate, rateVar.name )
                        self.errorLog(errorText)
                        # Remember the error.
                        self.lastErrorMessage = errorText
                        return
                except ValueError:
                    errorText = u"Ramp rate value \"{}\" found in variable \"{}\" is an invalid value. Ramp rate values can only contain numbers.".format(rampRate, rateVar.name )
                    self.errorLog(errorText)
                    # Remember the error.
                    self.lastErrorMessage = errorText
                    return
                except IndexError:
                    errorText = u"The specified variable (ID:{}) does not exist in the Indigo database.".format(brightnessVarId)
                    self.errorLog(errorText)
                    # Remember the error.
                    self.lastErrorMessage = errorText
                    return
            self.debugLog(u"Rate: {}".format(rampRate))

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
        self.debugLog(u"setColorTemperature: device:{}, action:\n{}".format(device.name, action))

        bulbId = device.pluginProps.get('bulbId', None)
        groupId = device.pluginProps.get('groupId', None)

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

        # Act based on device type.
        if device.deviceTypeId == "hueGroup":
            # Sanity check on group ID
            if groupId is None or groupId == 0:
                errorText = u"No group ID selected for device \"{}\". Check settings for this device and select a Hue Group to control.".format(device.name)
                self.errorLog(errorText)
                # Remember the error.
                self.lastErrorMessage = errorText
                return
        else:
            # Sanity check on bulb ID
            if bulbId is None or bulbId == 0:
                errorText = u"No bulb ID selected for device \"{}\". Check settings for this device and select a Hue Device to control.".format(device.name)
                self.errorLog(errorText)
                # Remember the error.
                self.lastErrorMessage = errorText
                return

        if preset == "custom":
            # Using a custom color recipe (temperature/brightness combination).
            if temperatureSource == "custom":
                try:
                    temperature = int(temperature)
                except ValueError:
                    # The int() cast above might fail if the user didn't enter a number:
                    errorText = u"Invalid color temperature specified for device \"{}\".  Value must be in the range 2000 to 6500.".format(device.name)
                    self.errorLog(errorText)
                    # Remember the error.
                    self.lastErrorMessage = errorText
                    return
            elif temperatureSource == "variable":
                if temperatureVariable:
                    # Action properties are passed as strings. Variable and device IDs are integers
                    # so we need to convert the variable ID passed in brightnessVariable to an integer.
                    temperatureVariable = int(temperatureVariable)
                    try:
                        temperature = int(indigo.variables[temperatureVariable].value)
                    except ValueError:
                        errorText = u"Invalid color temperature value \{}\" found in source variable \"{}\" for device \"{}\".".format(indigo.variables[temperatureVariable].value, indigo.variables[temperatureVariable].name , device.name)
                        self.errorLog(errorText)
                        # Remember the error.
                        self.lastErrorMessage = errorText
                        return

                    # Make sure the color temperature specified in the variable is sane.
                    if temperature < 2000 or temperature > 6500:
                        errorText = u"Color temperature value \"{}\" found in source variable \"{}\" for device \"{}\" is outside the acceptible range of 2000 to 6500." .format(temperature, indigo.variables[temperatureVariable].name , device.name)
                        self.errorLog(errorText)
                        # Remember the error.
                        self.lastErrorMessage = errorText
                        return
                else:
                    temperature = device.states['colorTemp']

            if brightnessSource == "custom":
                # Using an entered brightness value.
                if brightness:
                    try:
                        brightness = int(brightness)
                    except ValueError:
                        errorText = u"Invalid brightness value \"{}\" specified for device \"{}\". Value must be in the range 0-100.".format(brightness, device.name)
                        self.errorLog(errorText)
                        # Remember the error.
                        self.lastErrorMessage = errorText
                        return

                    # Make sure the brightness specified in the variable is sane.
                    if brightness < 0 or brightness > 100:
                        errorText = u"Brightness value \"{}\" for device \"{}\" is outside the acceptible range of 0 to 100.".format(brightness, device.name)
                        self.errorLog(errorText)
                        # Remember the error.
                        self.lastErrorMessage = errorText
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
                        errorText = u"Brightness value \"{}\" specified in variable \"{}\" for device \"{}\" is invalid.".format(indigo.variables[brightnessVariable].value, indigo.variables[tempebrightnessVariableratureVariable].name , device.name)
                        self.errorLog(errorText)
                        # Remember the error.
                        self.lastErrorMessage = errorText
                        return
                    except IndexError:
                        errorText = u"The brightness source variable (ID{}) does not exist in the Indigo database.".format(brightnessVariable)
                        self.errorLog(errorText)
                        # Remember the error.
                        self.lastErrorMessage = errorText
                        return

                    # Make sure the brightness specified in the variable is sane.
                    if brightness < 0 or brightness > 100:
                        errorText = u"Brightness value \"{}\" specified in variable \"{}\" is outside the acceptible range of 0 to 100.".format(brightnessVariable, indigo.variables[brightnessVariable].name)
                        self.errorLog(errorText)
                        # Remember the error.
                        self.lastErrorMessage = errorText
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
                        errorText = u"The brightness \"{}\" of the selected source device \"{}\" is invalid.".format(indigo.devices[brightnessDevice].states['brightnessLevel'], indigo.devices[brightnessDevice].name )
                        self.errorLog(errorText)
                        # Remember the error.
                        self.lastErrorMessage = errorText
                        return
                    except IndexError:
                        errorText = u"The brightness source device (ID:{}) does not exist in the Indigo database.".format(brightnessDevice)
                        self.errorLog(errorText)
                        # Remember the error.
                        self.lastErrorMessage = errorText
                        return
                else:
                    brightness = device.states['brightnessLevel']

            # Scale the brightness value for use with Hue.
            brightness = int(round(brightness / 100.0 * 255.0))

        if not useRateVariable:
            # Not using varible, so they've specificed a ramp rate.
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
                    errorText = u"Ramp rate value {}\" is outside the acceptible range of 0 to 540.".format(rampRate)
                    self.errorLog(errorText)
                    # Remember the error.
                    self.lastErrorMessage = errorText
                    return None
            except ValueError:
                errorText = u"Ramp rate value \"{}\" is an invalid value. Ramp rate values can only contain numbers.".format(rampRate)
                self.errorLog(errorText)
                # Remember the error.
                self.lastErrorMessage = errorText
                return None
            self.debugLog(u"Rate: {}".format(rampRate))

        else:
            # We're using a ramp rate variable.
            if not rateVarId:
                # No ramp rate variable was specified.
                errorText = u"No variable containing the ramp rate time was specified."
                self.errorLog(errorText)
                # Remember the error.
                self.lastErrorMessage = errorText
                return
            else:
                # A ramp rate variable was specified.
                try:
                    rateVar = indigo.variables[int(rateVarId)]
                    rampRate = rateVar.value
                    rampRate = float(rampRate)
                    if rampRate < 0 or rampRate > 540:
                        errorText = u"Ramp rate value \"{}\" found in variable \"{}\" is outside the acceptible range of 0 to 540.".format(rampRate, rateVar.name )
                        self.errorLog(errorText)
                        # Remember the error.
                        self.lastErrorMessage = errorText
                        return
                except ValueError:
                    errorText = u"Ramp rate value \"{}\" found in variable \"{}\" is an invalid value. Ramp rate values can only contain numbers.".format(rampRate, rateVar.name )
                    self.errorLog(errorText)
                    # Remember the error.
                    self.lastErrorMessage = errorText
                    return
                except IndexError:
                    errorText = u"The specified variable (ID:{}) does not exist in the Indigo database.".format(brightnessVarId)
                    self.errorLog(errorText)
                    # Remember the error.
                    self.lastErrorMessage = errorText
                    return
            self.debugLog(u"Rate: {}".formate(rampRate))

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
        self.debugLog(u"alertOnce: device:{}, action:\n{}".format(device.name, action))

        # Act based on device type.
        if device.deviceTypeId == "hueGroup":
            # Sanity check on group ID
            groupId = device.pluginProps.get('groupId', None)
            if groupId is None or groupId == 0:
                errorText = u"No group ID selected for device \"{}\". Check settings for this device and select a Hue Group to control.".format(device.name)
                self.errorLog(errorText)
                # Remember the error.
                self.lastErrorMessage = errorText
                return
        elif device.deviceTypeId == 'hueAttributeController' or device.deviceTypeId in kMotionSensorTypeIDs or device.deviceTypeId in kTemperatureSensorTypeIDs or device.deviceTypeId in kLightSensorTypeIDs or device.deviceTypeId in kSwitchTypeIDs:
            # Attribute controllers and sensor devices don't support alert actions. Print the error in the Indigo log.
            errorText = u"The \"{}\" device does not support Alert actions. Select a different Hue device.".format(device.name)
            self.errorLog(errorText)
            # Remember the error.
            self.lastErrorMessage = errorText
            return
        else:
            # Sanity check on bulb ID
            bulbId = device.pluginProps.get('bulbId', None)
            if bulbId is None or bulbId == 0:
                errorText = u"No bulb ID selected for device \"{}\". Check settings for this device and select a Hue Device to control.".format(device.name)
                self.errorLog(errorText)
                # Remember the error.
                self.lastErrorMessage = errorText
                return

        self.doAlert(device, "select")

    # Set Long Alert Action
    ########################################
    def longAlert(self, action, device):
        self.debugLog(u"longAlert: device:{}, action:\n{}".format(device.name, action))

        # Act based on device type.
        if device.deviceTypeId == "hueGroup":
            # Sanity check on group ID
            groupId = device.pluginProps.get('groupId', None)
            if groupId is None or groupId == 0:
                errorText = u"No group ID selected for device \"{}\". Check settings for this device and select a Hue Group to control.".format(device.name)
                self.errorLog(errorText)
                # Remember the error.
                self.lastErrorMessage = errorText
                return
        elif device.deviceTypeId == 'hueAttributeController' or device.deviceTypeId in kMotionSensorTypeIDs or device.deviceTypeId in kTemperatureSensorTypeIDs or device.deviceTypeId in kLightSensorTypeIDs or device.deviceTypeId in kSwitchTypeIDs:
            # Attribute controllers and sensor devices don't support alert actions. Print the error in the Indigo log.
            errorText = u"The \"{}\" device does not support Alert actions. Select a different Hue device.".format(device.name)
            self.errorLog(errorText)
            # Remember the error.
            self.lastErrorMessage = errorText
            return
        else:
            # Sanity check on bulb ID
            bulbId = device.pluginProps.get('bulbId', None)
            if bulbId is None or bulbId == 0:
                errorText = u"No bulb ID selected for device \"{}\". Check settings for this device and select a Hue Device to control.".format(device.name)
                self.errorLog(errorText)
                # Remember the error.
                self.lastErrorMessage = errorText
                return

        self.doAlert(device, "lselect")

    # Stop Alert Action
    ########################################
    def stopAlert(self, action, device):
        self.debugLog(u"stopAlert: device:{}, action:\n{}".format(device.name, action))

        # Act based on device type.
        if device.deviceTypeId == "hueGroup":
            # Sanity check on group ID
            groupId = device.pluginProps.get('groupId', None)
            if groupId is None or groupId == 0:
                errorText = u"No group ID selected for device \"{}\". Check settings for this device and select a Hue Group to control.".format(device.name)
                self.errorLog(errorText)
                # Remember the error.
                self.lastErrorMessage = errorText
                return
        elif device.deviceTypeId == 'hueAttributeController' or device.deviceTypeId in kMotionSensorTypeIDs or device.deviceTypeId in kTemperatureSensorTypeIDs or device.deviceTypeId in kLightSensorTypeIDs or device.deviceTypeId in kSwitchTypeIDs:
            # Attribute controllers and sensor devices don't support alert actions. Print the error in the Indigo log.
            errorText = u"The \"{}\" device does not support Alert actions so there is no alert to cancel.  Select a different Hue device.".format(device.name)
            self.errorLog(errorText)
            # Remember the error.
            self.lastErrorMessage = errorText
            return
        else:
            # Sanity check on bulb ID
            bulbId = device.pluginProps.get('bulbId', None)
            if bulbId is None or bulbId == 0:
                errorText = u"No bulb ID selected for device \"{}\". Check settings for this device and select a Hue Device to control.".format(device.name)
                self.errorLog(errorText)
                # Remember the error.
                self.lastErrorMessage = errorText
                return

        self.doAlert(device, "none")

    # Set Effect Action
    ########################################
    def effect(self, action, device):
        self.debugLog(u"effect: device:{}, action:\n{}".format(device.name, action))

        # Act based on device type.
        if device.deviceTypeId == "hueGroup":
            # Sanity check on group ID
            groupId = device.pluginProps.get('groupId', None)
            if groupId is None or groupId == 0:
                errorText = u"No group ID selected for device \"{}\". Check settings for this device and select a Hue Group to control.".format(device.name)
                self.errorLog(errorText)
                # Remember the error.
                self.lastErrorMessage = errorText
                return
        elif device.deviceTypeId == 'hueAttributeController' or device.deviceTypeId in kMotionSensorTypeIDs or device.deviceTypeId in kTemperatureSensorTypeIDs or device.deviceTypeId in kLightSensorTypeIDs or device.deviceTypeId in kSwitchTypeIDs:
            # Attribute controllers and sensor devices don't support effects actions. Print the error in the Indigo log.
            errorText = u"The \"{}\" device does not support Effects actions. Select a different Hue device.".format(device.name)
            self.errorLog(errorText)
            # Remember the error.
            self.lastErrorMessage = errorText
            return
        else:
            # Sanity check on bulb ID
            bulbId = device.pluginProps.get('bulbId', None)
            if bulbId is None or bulbId == 0:
                errorText = u"No bulb ID selected for device \"{}\". Check settings for this device and select a Hue Device to control.".format(device.name)
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
        self.debugLog(u"Starting savePreset. action values:\n{}\nDevice/Type ID:\n{}".format(action, device) + "\n")
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

        # Check if the target is a light or group.
        if device.deviceTypeId in kGroupDeviceTypeIDs:
            bulbId = device.pluginProps.get('groupId', "")
        elif device.deviceTypeId in kLightDeviceTypeIDs:
            bulbId = device.pluginProps.get('bulbId', "")
        else:
            bulbId = ""

        # Sanity check on bulb ID
        if bulbId == "":
            errorText = u"No compatible Hue device selected for \"{}\". Check settings and select a Hue light or group to control.".format(device.name)
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
                    errorsDict['rate'] = u"Invalid Ramp Rate value: {}".format(e)
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
            presetName = u""

        # If the submitted name is not blank, change the name in the prefs.
        if presetName != u"":
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
                    errorText = u"Ramp Rate must be a number between 0 and 540 seconds and can be in increments of 0.1 seconds. Value \"{}\" ignored.".format(rampRate)
                    self.errorLog(errorText)
                    # Remember the error.
                    self.lastErrorMessage = errorText
                    rampRate = -1
            except ValueError:
                errorText = u"Ramp Rate must be a number between 0 and 540 seconds and can be in increments of 0.1 seconds. Value \"{}\" ignored.".format(rampRate)
                self.errorLog(errorText)
                # Remember the error.
                self.lastErrorMessage = errorText
                rampRate = -1
            except Exception, e:
                errorText = u"Invalid Ramp Rate value \"{}\". Error was: {}".format(rampRate, e)
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
            indigo.server.log(u"\"{}\" states saved to Preset {} ({})".format(device.name , presetId + 1, presetName))
        else:
            indigo.server.log(u"\"{}\" states saved to Preset {} ({}) with ramp rate {} sec.".format(device.name , presetId + 1, presetName, rampRate))

        # Return a tuple if this is a menu item action.
        if actionType == "menu":
            return (True, action)

    # Recall Preset Action
    ########################################
    def recallPreset(self, action, device):
        self.debugLog(u"Starting recallPreset. action values:\n{}\nDevice/Type ID:\n{}\n".format(action, device))
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

        # Check if the target is a light or group.
        if device.deviceTypeId in kGroupDeviceTypeIDs:
            bulbId = device.pluginProps.get('groupId', "")
        elif device.deviceTypeId in kLightDeviceTypeIDs:
            bulbId = device.pluginProps.get('bulbId', "")
        else:
            bulbId = ""

        # Sanity check on bulb ID
        if bulbId == "":
            errorText = u"No compatible Hue device selected for \"{}\". Check settings and select a Hue light or group to control.".format(device.name)
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
                    errorsDict['rate'] = u"Invalid Ramp Rate value: {}".format(e)
                    errorsDict['showAlertText'] += errorsDict['rate']
                    return (False, action, errorsDict)
        else:
            rampRate = action.props.get('rate', "")

        # If there is no Ramp Rate specified, use -1.
        if rampRate == "":
            rampRate = -1

        type = device.pluginProps.get('type', False)
        if device.deviceTypeId in kLightDeviceTypeIDs:
            # Get the modelId from the device.
            if not type:
                errorText = u"The \"{}\" device is not a Hue device. Please select a Hue device for this action.".format(device.name)
                self.errorLog(errorText)
                # Remember the error.
                self.lastErrorMessage = errorText
                return

            elif type not in kCompatibleDeviceIDType:
                errorText = u"The \"{}\" device is not a compatible Hue device. Please select a compatible Hue device.".format(device.name)
                self.errorLog(errorText)
                # Remember the error.
                self.lastErrorMessage = errorText
                return

        elif device.deviceTypeId not in kLightDeviceTypeIDs and device.deviceTypeId not in kGroupDeviceTypeIDs:
            errorText = u"The \"{}\" device is not a compatible Hue device. Please select a compatible Hue device.".format(device.name)
            self.errorLog(errorText)
            # Remember the error.
            self.lastErrorMessage = errorText
            return

        # Sanity check on preset ID.
        try:
            preset = self.pluginPrefs['presets'][presetId]
        except IndexError:
            errorText = u"Preset number {} does not exist. Please select a Preset that exists.".format(presetId + 1)
            self.errorLog(errorText)
            # Remember the error.
            self.lastErrorMessage = errorText
            return
        except Exception, e:
            errorText = u"Preset number {} couldn't be recalled. The error was \"{}\"".format(presetId + 1)
            self.errorLog(errorText)
            # Remember the error.
            self.lastErrorMessage = errorText
            return

        # Get the data from the preset in the plugin prefs.
        presetName = preset[0]
        presetData = preset[1]
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
                errorText = u"Preset  ({}) is empty. The \"{}\" device was not changed.".format(presetId + 1, device.name )
                self.errorLog(errorText)
                # Remember the error.
                self.lastErrorMessage = errorText
                return

        # Get the brightness level (which is common to all devices).
        brightnessLevel = presetData.get('brightnessLevel', 100)
        # Convert the brightnessLevel to 0-255 range for use in the light
        #   changing method calls.
        brightness = int(round(brightnessLevel / 100.0 * 255.0))

        # Act based on the capabilities of the target device.
        if device.supportsColor:
            if device.supportsWhiteTemperature and device.supportsRGB:
                # This device supports both color temperature and full color.
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
            indigo.server.log(u"\"{}\" compatible states set to Preset {} ({})".format(device.name, presetId + 1, presetName) )
        else:
            indigo.server.log(u"\"{}\" compatible states set to Preset {} ({}) at ramp rate {} sec.".format(device.name, presetId + 1, presetName, rampRate) )

        # Return a tuple if this is a menu item action.
        if actionType == "menu":
            return (True, action)

    # Display Preset Menu Action
    ########################################
    def displayPreset(self, valuesDict, typeId):
        self.debugLog(u"Starting displayPreset. action values:\n{}\nType ID:{}\n".format(valuesDict, typeId) )
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
        logRampRate = u"{} sec".format(presetRate)
        if presetRate == -1:
            logRampRate = u"(none specified)"
        indigo.server.log(u"Displaying Preset {} ({}) stored data:\nRamp Rate: {} {}\n".format(presetId + 1, presetName, logRampRate, presetData))

        # Return a tuple to dismiss the menu item dialog.
        return (True, valuesDict)

    # Recall Hue Scene Action
    ########################################
    def recallScene(self, action, device):
        errorsDict = indigo.Dict()
        errorsDict['showAlertText'] = u""
        # Work with both Menu and Action actions.
        try:
            actionDict = action.props
            # If this succeeds, no need to do anything.
        except AttributeError:
            # If there is an attribute error, this is a Plugins menu call.
            actionDict = action
        self.debugLog(u"Starting recallScene. action values:\n{}\nDevice/Type ID:\n{}\n".format(actionDict, device))

        # Get the sceneId.
        sceneId = actionDict.get('sceneId', False)
        hubNumber = actionDict.get('hubNumber', False)

        if not sceneId:
            errorText = u"No Scene specified."
            self.errorLog(errorText)
            # Remember the error.
            self.lastErrorMessage = errorText
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
        self.debugLog(u"Starting printsListGenerator.\n  filter: {}\n  valuesDict: {}\n  typeId: {}\n  targetId: {}".format(filter, valuesDict, typeId, targetId))
        xList = list()
        if filter == "lights":  
            theDict = self.lightsDict
        elif filter == "sensors":
            theDict = self.sensorsDict
        elif filter == "groups":
            theDict = self.groupsDict
        for hubNumber in sorted(self.ipAddresses, key=self.ipAddresses.get):
            for ID in theDict[hubNumber]:
                xList.append([ID+"-"+hubNumber, hubNumber+"-"+ID+"-"+theDict[hubNumber][ID]['name']])
        return sorted(xList, key=lambda tup: tup[1])
 
    # print lights
    ########################################
    def printHueData(self, valuesDict, menuItem):
        self.debugLog(u"Starting printHueData. ")
 
        indigoList = {}
        if valuesDict['whatToPrint'] == "lights":
            indigoList = self.getIndigoDevDict("bulbId")

            outs = [u"  "]
            for hubNumber in sorted(self.ipAddresses):
                outs.append(u" hubNumber:{}, ipNumber:{}, hostId:{}, paired:{}".format(hubNumber, self.ipAddresses[hubNumber],self.hostIds[hubNumber], self.paired[hubNumber]))
                             #123 12345678901 12345678901234567890123456 12345678901234567890123456789 12345678901234567890123456789 1234567890123456789012345 12345678901234567890123456789 12345678901 1234567890123456789012345 123456789 12345 
                outs.append(u" ID modelId--------- type--------------------- uniqueid------------------ Name---------------------------- ProductId-------------------- manufacturername------------- ProductName------------------ indigoDevName-----")
                theDict = self.lightsDict[hubNumber]
                IDlist = sorted(theDict, key=lambda key: int(key))
                for IDi in IDlist:
                    ID = str(IDi)
                    temp = theDict[ID]
                    if True:                                            out  = u"{:>3} ".format(ID)
                    if 'modelid' in temp:                               out += u"{:17s}".format(temp['modelid'])
                    else:                                               out += u"{:17}".format(" ")
                    if 'type' in temp:                                  out += u"{:26s}".format(temp['type'])
                    else:                                               out += u"{:26s}".format(" ")
                    if 'uniqueid' in temp:                              out += u"{:27s}".format(temp['uniqueid'])
                    else:                                               out += u"{:27s}".format(" ")
                    if 'name' in temp:                                  out += u"{:33s}".format(temp['name'])
                    else:                                               out += u"{:33s}".format(" ")
                    if 'productid' in temp:                             out += u"{:30s}".format(temp['productid'])
                    else:                                               out += u"{:30s}".format(" ")
                    if 'manufacturername' in temp:                      out += u"{:30s}".format(temp['manufacturername'])
                    else:                                               out += u"{:30s}".format(" ")
                    if 'productname' in temp:                           out += u"{:30s}".format(temp['productname'])
                    else:                                               out += u"{:30s}".format(" ")
                    if ID in indigoList:                                out += u"{:<20}".format(indigoList[ID])
                    else:                                               out += u"{:20s}".format(" ")
                    outs.append(out)
            indigo.server.log(u"\n======================= print Hue Lights ====================="+"\n".join(outs))

        elif valuesDict['whatToPrint'] == "sensors":
            indigoList = self.getIndigoDevDict("sensorId")

            outs = [u"  "]
            for hubNumber in sorted(self.ipAddresses):
                outs.append( u"  hubNumber:{}, ipNumber:{}, hostId:{}, paired:{}".format(hubNumber, self.ipAddresses[hubNumber],self.hostIds[hubNumber], self.paired[hubNumber]))
                        #1234 12345678901     12345678901234567890123456789 12345678901234567890123456789 12345678901234567890123456789 1234567890123456789 123456 123456 123456 1234567890123456789 
                outs.append(u" ID modelid-------- type--------------- Name------------------------- productname------------------ manufacturername------------- ON/off reachb Status lastupdated-------- Indigo Device")
                theDict = self.sensorsDict[hubNumber]
                IDlist = sorted(theDict, key=lambda key: int(key))
                for IDi in IDlist:
                    ID = str(IDi)
                    temp = theDict[ID]
                    if True:                                            out  = u"{:>3} ".format(ID)
                    if "modelid" in temp:                               out += u"{:16s}".format(temp['modelid'])
                    else:                                               out += u"{:16s}".format(" ")
                    if "type" in temp:                                  out += u"{:20s}".format(temp['type'])
                    else:                                               out += u"{:20s}".format(" ")
                    if "name" in temp:                                  out += u"{:30s}".format(temp['name'])
                    else:                                               out += u"{:30s}".format(" ")
                    if "productname" in temp:                           out += u"{:30s}".format(temp['productname'])
                    else:                                               out += u"{:30s}".format(" ")
                    if "manufacturername" in temp:                      out += u"{:30s}".format(temp['manufacturername'])
                    else:                                               out += u"{:30s}".format(" ")
                    if "config" in temp: 
                        conf = temp['config']
                        if "on" in conf:                                out += u"{:7s}".format(str(conf['on']))
                        else:                                           out += u"{:7s}".format(" ")
                        if "reachable" in conf:                         out += u"{:7s}".format(str(conf['reachable']))
                        else:                                           out += u"{:7s}".format(" ")
                    else:                                               out += u"{:14s}".format(" ")
                    if "state" in temp: 
                        st = temp['state']
                        if "status" in st:                              out += u"{:7s}".format(str(st['status']))
                        else:                                           out += u"{:7s}".format(" ")
                    else:                                               out += u"{:7s}".format(" ")
                    if "lastupdated" in st:                             out += u"{:20s}".format(st['lastupdated'])
                    else:                                               out += u"{:20s}".format(" ")
                    if ID in indigoList:                                out += u"{:<20}".format(indigoList[ID])
                    else:                                               out += u"{:20s}".format(" ")
                    outs.append(out)
            indigo.server.log("\n======================= print Hue Sensors ====================="+"\n".join(outs)+"\n")

 
        elif valuesDict['whatToPrint'] == "groups":
            indigoList = self.getIndigoDevDict("groupId")
            outs = [u"  "]
            for hubNumber in sorted(self.ipAddresses):
                outs.append(u" hubNumber:{}, ipNumber:{}, hostId:{}, paired:{}".format(hubNumber, self.ipAddresses[hubNumber],self.hostIds[hubNumber], self.paired[hubNumber]))
                             #123 123456789 123456789 123456789 123456789 123456789 12345678901234567890123456789 12345678901234567890123456789 1234567890123456789012345
                outs.append(u" ID Name------------------------- IndigoDevName------ Lights------------------")
                theDict = self.groupsDict[hubNumber]
                IDlist = sorted(theDict, key=lambda key: int(key))
                for IDi in IDlist:
                    ID = str(IDi)
                    temp = theDict[ID]
                    if True:                                            out  = u"{:>3} ".format(ID)
                    if "name" in temp:                                  out += u"{:30s}".format(temp['name'])
                    if ID in indigoList:                                out += u"{:<20}".format(indigoList[ID])
                    else:                                               out += u"{:20s}".format(" ")
                    lights = ""
                    if "lights" in temp:
                        for ll in sorted(temp['lights']):
                            lights += str(ll)+", "
                        out += u"{}".format(lights[:-2])
                    else: pass
                    outs.append(out)
            indigo.server.log("\n======================= print Hue Groups ====================="+"\n".join(outs)+"\n")
 
        elif valuesDict['whatToPrint'] == "scenes":
            outs = [u"  "]
            for hubNumber in sorted(self.ipAddresses):
                outs.append(u" hubNumber:{}, ipNumber:{}, hostId:{}, paired:{}".format(hubNumber, self.ipAddresses[hubNumber],self.hostIds[hubNumber], self.paired[hubNumber]))
                              #123456789 1234 123456789 123456789 123456789 12345 123456789 1234 1234567890123456789 123456789 
                outs.append(u"ID------------- Name------------------------- Group Type---------- Lights------------------")
                theDict = self.scenesDict[hubNumber]
                for ID in theDict:
                    temp = theDict[ID]
                    if True:                                            out  = u"{:15} ".format(ID)
                    if "name" in temp:                                  out += u"{:30s}".format(temp['name'])
                    else:                                               out += u"{:30s}".format(" ")
                    if "group" in temp:                                 out += u"{:6s}".format(temp['group'])
                    else:                                               out += u"{:6s}".format(" ")
                    if "type" in temp:                                  out += u"{:15s}".format(temp['type'])
                    else:                                               out += u"{:15s}".format(" ")
                    lights = ""
                    if "lights" in temp:
                        for ll in sorted(temp['lights']):
                            lights += str(ll)+", "
                        out += u"{}".format(lights[:-2])
                    else: pass
                    outs.append(out)
            indigo.server.log("\n======================= print Hue Secenes ====================="+"\n".join(outs)+"\n")

        elif valuesDict['whatToPrint'].find("specific") >-1:
            if valuesDict['whatToPrint'] == "specificLight":
                idType = "bulbId"
                theDict = self.lightsDict
            elif valuesDict['whatToPrint'] == "specificGroup":
                idType = "groupId"
                theDict = self.groupsDict
            elif valuesDict['whatToPrint'] == "specificSensor":
                idType = "sensorId"
                theDict = self.sensorsDict
            else:
                idType ="error"
                indigo.server.log("ERROR printHueData --- bad input ".format(valuesDict))

            if idType != "error":
                ID, hubNumber = valuesDict[idType].split("-")
                idList = {}
                for dev in indigo.devices.iter(self.pluginId):
                    if idType in dev.pluginProps:
                        idList[dev.pluginProps[idType]] = dev.id

                found = False
                if ID in theDict[hubNumber]:
                    if ID in idList:
                        indigoID = "{:<12}  ".format(idList[ID])
                    else:
                        indigoID = "{:12s}".format(" ")
                    indigo.server.log("printHueData:{};  hubNumber:{}, indigoId:{}  {}:{}  data:\n{}".format(valuesDict['whatToPrint'], hubNumber, indigoID, idType, ID, json.dumps(theDict[hubNumber][ID], indent=2, sort_keys=True)  ))
                    found = True
                if not found:
                   indigo.server.log("ERROR printHueData --- {}:{}- not in list".format(idType, valuesDict[idType]))

        return valuesDict

    # nake a dict of hue indigo devices {id:indigoName}
    ########################################
    def getIndigoDevDict(self, idName):
        indigoList = {}
        for dev in indigo.devices.iter(self.pluginId):
            if idName in dev.pluginProps:
                indigoList[dev.pluginProps[idName]] = dev.name
        return indigoList

    # Toggle Debug Logging Menu Action
    ########################################
    def toggleDebugging(self):
        if self.debug:
            indigo.server.log("Turning off debug logging")
            self.debugLog(u"Turning off debug logging (Toggle Debugging menu item chosen).")
            self.pluginPrefs['showDebugInfo'] = False
            self.plugin_file_handler.setLevel(logging.INFO) # Turn off for the plugin-specific log file.
        else:
            indigo.server.log("Turning on debug logging")
            self.pluginPrefs['showDebugInfo'] = True
            self.plugin_file_handler.setLevel(logging.DEBUG) # Turn on for the plugin-specific log file
            self.debugLog(u"Turning on debug logging (Toggle Debugging menu item chosen).")
        # Turn on/off for the Indigo log level.
        self.debug = not self.debug


