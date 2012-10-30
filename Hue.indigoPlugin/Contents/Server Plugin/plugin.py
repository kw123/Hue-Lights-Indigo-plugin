#! /usr/bin/env python
# -*- coding: utf-8 -*-
####################
# Developed by Alistair Galbraith
# This is UNSUPPORTED, AS-IS, open source code - do with it as you wish. Don't blame me if it breaks! :)

import os
import sys
import uuid
import hashlib
import simplejson as json
import urllib2
import socket
from math import floor
from ColorPy import colormodels

# Note the "indigo" module is automatically imported and made available inside
# our global name space by the host process.

################################################################################
class Plugin(indigo.PluginBase):
    ########################################
    def __init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs):
        indigo.PluginBase.__init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs)
        self.debug = True
        self.paired = False
        self.lightsDict = dict()

    def __del__(self):
        indigo.PluginBase.__del__(self)

    ########################################
    def startup(self):
        self.debugLog(u"Startup called")

        # Do we have a site ID?
        siteId = self.pluginPrefs.get("hostId", None)
        if siteId is None:
            siteId = str(uuid.uuid1())
            siteId = hashlib.md5(siteId).hexdigest().lower()
            self.debugLog("Host ID is %s" % siteId)
            self.pluginPrefs["hostId"] = siteId

        # Load lights list
        self.updateLightsList()

    def shutdown(self):
        self.debugLog(u"Shutdown called")

    def deviceCreated(self, dev):

        # Debug
        self.debugLog(u"Created device of type \"%s\"" % dev.deviceTypeId)

    ########################################
    def validateDeviceConfigUi(self, valuesDict, typeId, devId):
        return (True, valuesDict)

    ########################################
    # API Methods
    ######################
    def setBrightnessAndOnState(self, brightness, onState, indigoDevice):

        # Sanity check for an IP address
        ipAddress = self.pluginPrefs.get("address", None)
        if ipAddress is None:
            indigo.server.log(u"No IP address set for the Hue hub. You can get this information from the My Settings page at http://www.meethue.com", isError=True)
            return

        # Sanity check on bulb ID
        bulbId = indigoDevice.pluginProps.get("bulbId", None)
        if bulbId is None or bulbId == 0:
            indigo.server.log(u"No bulb ID selected for device \"%s\". Check settings for this bulb and select a Hue bulb to control." % (indigoDevice.name), isError=True)
            return

        requestData = json.dumps({"bri": int(brightness), "on": onState})
        self.debugLog(u"Request is %s" % requestData)
        bulbCommandRequest = urllib2.Request("http://%s/api/%s/lights/%s/state" % (ipAddress, self.pluginPrefs["hostId"], bulbId), requestData)
        bulbCommandRequest.get_method = lambda: 'PUT'
        bulbCommandResponse = urllib2.urlopen(bulbCommandRequest)
        bulbCommandResponseData = json.loads(bulbCommandResponse.read())
        self.debugLog(u"Got response %s" % bulbCommandResponseData)
        indigoDevice.updateStateOnServer(key="onOffState", value=True)
        indigoDevice.updateStateOnServer(key="brightnessLevel", value=floor((brightness/255)*100))

    def setRGB(self, indigoDevice, red, green, blue, brightness):

        # Sanity check for an IP address
        ipAddress = self.pluginPrefs.get("address", None)
        if ipAddress is None:
            indigo.server.log(u"No IP address set for the Hue hub. You can get this information from the My Settings page at http://www.meethue.com", isError=True)
            return

        # Sanity check on bulb ID
        bulbId = indigoDevice.pluginProps.get("bulbId", None)
        if bulbId is None or bulbId == 0:
            indigo.server.log(u"No bulb ID selected for device \"%s\". Check settings for this bulb and select a Hue bulb to control." % (indigoDevice.name), isError=True)
            return

        # We need to convert the RGB value to Yxy.
        redScale = float(red) / 255
        greenScale = float(green) / 255
        blueScale = float(blue) / 255
        colormodels.init(phosphor_red=colormodels.xyz_color(0.64843, 0.33086), phosphor_green=colormodels.xyz_color(0.4091,0.518), phosphor_blue=colormodels.xyz_color(0.167, 0.04))
        xyz = colormodels.xyz_from_rgb(colormodels.irgb_color(red, green, blue))
        xyz = colormodels.xyz_normalize(xyz)

        # Submit to Hue
        requestData = json.dumps({"bri":255, "xy": [xyz[0], xyz[1]], "on":True})
        self.debugLog(u"Request is %s" % requestData)
        bulbCommandRequest = urllib2.Request("http://%s/api/%s/lights/%s/state" % (ipAddress, self.pluginPrefs["hostId"], bulbId), requestData)
        bulbCommandRequest.get_method = lambda: 'PUT'
        bulbCommandResponse = urllib2.urlopen(bulbCommandRequest)
        bulbCommandResponseData = json.loads(bulbCommandResponse.read())
        self.debugLog(u"Got response %s" % bulbCommandResponseData)
        indigoDevice.updateStateOnServer(key="onOffState", value=True)
        indigoDevice.updateStateOnServer(key="brightnessLevel", value=100)

    def updateLightsList(self):

        # Sanity check for an IP address
        ipAddress = self.pluginPrefs.get("address", None)
        if ipAddress is None:
            indigo.server.log(u"No IP address set for the Hue hub. You can get this information from the My Settings page at http://www.meethue.com", isError=True)
            pass

        # Parse the response
        lightsListResponse = urllib2.urlopen("http://%s/api/%s/lights" % (ipAddress, self.pluginPrefs.get("hostId", "ERROR")))
        lightsListResponseData = json.loads(lightsListResponse.read())
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
            errorDict = firstResponseItem.get("error", None)
            if errorDict is not None:

                errorCode = errorDict.get("type", None)

                # Is this a link button not pressed error?
                if errorCode == 1:
                    indigo.server.log(u"Not paired with Hue. Press the middle button on the Hue hub, then press the Retry Pairing button in Plugin Settings", isError=True)
                    self.paired = False

                else:
                    indigo.server.log(u"Error #%i from Hue Hub when loading available bulbs. Description is \"%s\"" % (errorCode, errorDict.get("description", "(No Description")), isError=True)
                    self.paired = False

            else:

                indigo.server.log(u"Unexpected response from Hue (%s) when loading available bulbs!" % (lightsListResponseData))

        else:

            indigo.server.log(u"Unexpected response from Hue (%s) when loading available bulbs!" % (lightsListResponseData))

    ########################################
    # Registration Methods
    ######################
    def updateRegistrationState(self):

        # Sanity check for an IP address
        ipAddress = self.pluginPrefs.get("address", None)
        if ipAddress is None:
            indigo.server.log(u"No IP address set for the Hue hub. You can get this information from the My Settings page at http://www.meethue.com", isError=True)
            pass

        # Configure timeout
        socket.setdefaulttimeout(5)

        # Request login state
        try:
            indigo.server.log(u"Checking with the Hue hub at %s for pairing state..." % (ipAddress))
            requestData = json.dumps({"username": self.pluginPrefs.get("hostId", None), "devicetype": "Indigo Hue Plugin"})
            self.debugLog(u"Request is %s" % requestData)
            loginResponse = urllib2.urlopen("http://%s/api" % ipAddress, requestData)
            responseData = json.loads(loginResponse.read())
            self.debugLog(u"Got response %s" % responseData)

            # We should have a single response item
            if len(responseData) == 1:

                # Get the first item
                firstResponseItem = responseData[0]

                # Did we get an error?
                errorDict = firstResponseItem.get("error", None)
                if errorDict is not None:

                    errorCode = errorDict.get("type", None)

                    # Is this a link button not pressed error?
                    if errorCode == 101:
                        indigo.server.log(u"Could not pair with Hue. Press the middle button on the Hue hub, then press the Retry Pairing button in Plugin Settings", isError=True)
                        self.paired = False

                    else:
                        indigo.server.log(u"Error #%i from Hue Hub when checking pairing. Description is \"%s\"" % (errorCode, errorDict.get("description", "(No Description")), isError=True)
                        self.paired = False

                # Were we successful?
                successDict = firstResponseItem.get("success", None)
                if successDict is not None:

                    indigo.server.log(u"Connected to Hue hub successfully.")
                    self.paired = True

            else:

                indigo.server.log(u"Invalid response from Hue. Check the IP address and try again.", isError=True)

        except urllib2.URLError, urlError:

            indigo.server.log(u"Error connecting to Hue hub at %s - check the IP address and try again." % ipAddress, isError=True)


    ########################################
    # Config Callbacks
    ######################
    def restartPairing(self, valuesDict):

        if not self.paired:
            self.updateRegistrationState()
        else:
            indigo.server.log(u"Already paired. No need to update registration", isError=True)

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
    ######################
    def actionControlDimmerRelay(self, action, dev):

        self.debugLog("actionControlDimmerRelay - action is %s, dev is %s" % (action, dev))
        self.debugLog("Command is %s" % action.deviceAction)

        # Get key variables
        command = action.deviceAction
        bulbId = dev.pluginProps.get("bulbId", None)
        hostId = self.pluginPrefs.get("hostId", None)
        ipAddress = self.pluginPrefs.get("address", None)
        self.debugLog("Command is %s, Bulb is %s" % (command, bulbId))

        # TurnOn
        if command == indigo.kDeviceAction.TurnOn:
            self.setBrightnessAndOnState(255, True, dev)

        # TurnOff
        elif command == indigo.kDeviceAction.TurnOff:
            self.setBrightnessAndOnState(0, False, dev)

        # SetBrightness
        elif command == indigo.kDeviceAction.SetBrightness:
            brightnessLevel = floor((float(action.actionValue) / 100.0) * 255.0)
            self.setBrightnessAndOnState(brightnessLevel, True, dev)

        # Catch all
        else:

            indigo.server.log(u"Unhandled Hue bulb command \"%s\"" % (command))

        pass

    ########################################
    # Speed Control Action callback
    ######################
    def actionControlSpeedControl(self, action, dev):
        ###### TURN ON ######
        if action.speedControlAction == indigo.kSpeedControlAction.TurnOn:
            # Command hardware module (dev) to turn ON here:
            # ** IMPLEMENT ME **
            sendSuccess = True        # Set to False if it failed.

            if sendSuccess:
                # If success then log that the command was successfully sent.
                indigo.server.log(u"sent \"%s\" %s" % (dev.name, "on"))

                # And then tell the Indigo Server to update the state.
                dev.updateStateOnServer("onOffState", True)
            else:
                # Else log failure but do NOT update state on Indigo Server.
                indigo.server.log(u"send \"%s\" %s failed" % (dev.name, "on"), isError=True)

        ###### TURN OFF ######
        elif action.speedControlAction == indigo.kSpeedControlAction.TurnOff:
            # Command hardware module (dev) to turn OFF here:
            # ** IMPLEMENT ME **
            sendSuccess = True        # Set to False if it failed.

            if sendSuccess:
                # If success then log that the command was successfully sent.
                indigo.server.log(u"sent \"%s\" %s" % (dev.name, "off"))

                # And then tell the Indigo Server to update the state:
                dev.updateStateOnServer("onOffState", False)
            else:
                # Else log failure but do NOT update state on Indigo Server.
                indigo.server.log(u"send \"%s\" %s failed" % (dev.name, "off"), isError=True)

        ###### TOGGLE ######
        elif action.speedControlAction == indigo.kSpeedControlAction.Toggle:
            # Command hardware module (dev) to toggle here:
            # ** IMPLEMENT ME **
            newOnState = not dev.onState
            sendSuccess = True        # Set to False if it failed.

            if sendSuccess:
                # If success then log that the command was successfully sent.
                indigo.server.log(u"sent \"%s\" %s" % (dev.name, "toggle"))

                # And then tell the Indigo Server to update the state:
                dev.updateStateOnServer("onOffState", newOnState)
            else:
                # Else log failure but do NOT update state on Indigo Server.
                indigo.server.log(u"send \"%s\" %s failed" % (dev.name, "toggle"), isError=True)

        ###### SET SPEED INDEX ######
        elif action.speedControlAction == indigo.kSpeedControlAction.SetSpeedIndex:
            # Command hardware module (dev) to change the speed here to a specific
            # speed index (0=off, 1=low, ..., 3=high):
            # ** IMPLEMENT ME **
            newSpeedIndex = action.actionValue
            sendSuccess = True        # Set to False if it failed.

            if sendSuccess:
                # If success then log that the command was successfully sent.
                indigo.server.log(
                    u"sent \"%s\" %s to %s" % (dev.name, "set motor speed", self.speedLabels[newSpeedIndex]))

                # And then tell the Indigo Server to update the state:
                dev.updateStateOnServer("speedIndex", newSpeedIndex)
            else:
                # Else log failure but do NOT update state on Indigo Server.
                indigo.server.log(
                    u"send \"%s\" %s to %s failed" % (dev.name, "set motor speed", self.speedLabels[newSpeedIndex]),
                    isError=True)

        ###### SET SPEED LEVEL ######
        elif action.speedControlAction == indigo.kSpeedControlAction.SetSpeedLevel:
            # Command hardware module (dev) to change the speed here to an absolute
            # speed level (0 to 100):
            # ** IMPLEMENT ME **
            newSpeedLevel = action.actionValue
            sendSuccess = True        # Set to False if it failed.

            if sendSuccess:
                # If success then log that the command was successfully sent.
                indigo.server.log(u"sent \"%s\" %s to %d" % (dev.name, "set motor speed", newSpeedLevel))

                # And then tell the Indigo Server to update the state:
                dev.updateStateOnServer("speedLevel", newSpeedLevel)
            else:
                # Else log failure but do NOT update state on Indigo Server.
                indigo.server.log(u"send \"%s\" %s to %d failed" % (dev.name, "set motor speed", newSpeedLevel),
                    isError=True)

        ###### INCREASE SPEED INDEX BY ######
        elif action.speedControlAction == indigo.kSpeedControlAction.IncreaseSpeedIndex:
            # Command hardware module (dev) to do a relative speed increase here:
            # ** IMPLEMENT ME **
            newSpeedIndex = dev.speedIndex + action.actionValue
            if newSpeedIndex > 3:
                newSpeedIndex = 3
            sendSuccess = True        # Set to False if it failed.

            if sendSuccess:
                # If success then log that the command was successfully sent.
                indigo.server.log(
                    u"sent \"%s\" %s to %s" % (dev.name, "motor speed increase", self.speedLabels[newSpeedIndex]))

                # And then tell the Indigo Server to update the state:
                dev.updateStateOnServer("speedIndex", newSpeedIndex)
            else:
                # Else log failure but do NOT update state on Indigo Server.
                indigo.server.log(u"send \"%s\" %s to %s failed" % (
                dev.name, "motor speed increase", self.speedLabels[newSpeedIndex]), isError=True)

        ###### DECREASE SPEED INDEX BY ######
        elif action.speedControlAction == indigo.kSpeedControlAction.DecreaseSpeedIndex:
            # Command hardware module (dev) to do a relative speed decrease here:
            # ** IMPLEMENT ME **
            newSpeedIndex = dev.speedIndex - action.actionValue
            if newSpeedIndex < 0:
                newSpeedIndex = 0
            sendSuccess = True        # Set to False if it failed.

            if sendSuccess:
                # If success then log that the command was successfully sent.
                indigo.server.log(
                    u"sent \"%s\" %s to %s" % (dev.name, "motor speed decrease", self.speedLabels[newSpeedIndex]))

                # And then tell the Indigo Server to update the state:
                dev.updateStateOnServer("speedIndex", newSpeedIndex)
            else:
                # Else log failure but do NOT update state on Indigo Server.
                indigo.server.log(u"send \"%s\" %s to %s failed" % (
                dev.name, "motor speed decrease", self.speedLabels[newSpeedIndex]), isError=True)

        ###### STATUS REQUEST ######
        elif action.speedControlAction == indigo.kSpeedControlAction.RequestStatus:
            # Query hardware module (dev) for its current speed/states here:
            # ** IMPLEMENT ME **
            indigo.server.log(u"sent \"%s\" %s" % (dev.name, "status request"))

    ########################################
    # Custom Plugin Action callbacks (defined in Actions.xml)
    ######################
    def setColor(self, pluginAction, dev):

        try:
            red = int(pluginAction.props.get(u"red", None))
            green = int(pluginAction.props.get(u"green", None))
            blue = int(pluginAction.props.get(u"blue", None))
        except ValueError:
            # The int() cast above might fail if the user didn't enter a number:
            indigo.server.log(
                u"Set Color for device \"%s\" -- invalid color values (must range 0-255)" % (dev.name,),
                isError=True)
            return

        self.setRGB(dev, red, green, blue, 255)

    ########################################
    # Device Management Methods
    ######################




