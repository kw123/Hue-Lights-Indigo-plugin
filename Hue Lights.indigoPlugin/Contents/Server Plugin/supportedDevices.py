#! /usr/bin/env python
# -*- coding: utf-8 -*-
####################
# Hue Lights Indigo Plugin
#	This file is imported into the main plugin.py file.

### CONSTANTS ###

# List of compatible device IDs that may be associated with a Hue hub.
#
# Philips Hue Color and Ambiance Lights
# LCT001	=	Hue bulb (color gamut B)
# LCT002	=	Hue Downlight/Spot BR30 bulb (color gamut B)
# LCT003	=	Hue Spot Light GU10 bulb (color gamut B)
# LCT007	=	Hue bulb (800 lumen version, color gamut B)
# LCT010	=	Hue bulb (A19 version 3, color gamut C)
# LCT011	=	Hue bulb (BR30 version 3, color gamut C)
# LCT012	=	Hue bulb (E14 color candle, color gamut C)
# LCT014	=	Hue bulb (alternate A19 version 3)
#
# Philips LivingColors and Other Color (Non-Color Temperature) Lights
# LLC001	=	LivingColors light (generic)
# LLC006	=	LivingColors Gen3 Iris
# LLC007	=	LivingColors Gen3 Bloom Aura
# LLC010	=	LivingColors Iris (Europe)
# LLC011	=	Bloom (European?)
# LLC012	=	Bloom
# LLC013	=	Disney StoryLight
# LLC014	=	LivingColors Aura
# LLC020	=	Hue Go
#
# Philips Luminaire Light Modules
# LLM001	=	Hue Luminaire Color Light Module (color gamut B)
# LLM010	=	Hue Color Temperature Module (2200K - 6500K)
# LLM011	=	" " "
# LLM012	=	" " "
#
# Philips LightStrips
# LST001	=	LED LightStrip (color gamut A)
# LST002	=	LED LightStrip Plus (color gamut C)
#
# Philips Ambiance Lights (color temperature only)
# LTW001	=	Hue White Ambiance bulb
# LTC001	=	Hue Ambiance bulb
# LTC003	=	Hue Ambiance Ceiling
# LTW004	=	Hue White Ambiance bulb
# LTW011	=	Hue White Ambiance BR13 bulb
# LTW012	=	Hue Ambiance Candle E14 bulb
# LTW013	=	Hue Ambiance Spot GU10 spotlight bulb.
# LTW014	=	" " "
#
# Philips LivingWhites (Dimming Only) Lights
# LWB001	=	LivingWhites bulb
# LWB003	=	" " "
# LWB004	=	Hue A19 Lux
# LWB006	=	Hue White A19 extension bulb
# LWB007	=	Hue Lux (alternate version)
# LWB010	=	Hue White (version 2)
# LWB014	=	Hue White (version 3)
#
# Philips LivingWhites Light Socket
# LWL001	=	LivingWhites light socket
#
# Philips Hue Beyond Multisource Lights (used with LLM001 or individually).
# HBL001	=	Hue Beyond Table
# HBL002	=	Hue Beyond Pendant
# HBL003	=	Hue Beyond Ceiling
# HEL001	=	Hue Entity Table
# HEL002	=	Hue Entity Pendant
# HIL001	=	Hue Impulse Table
# HIL002	=	Hue Impulse Pendant
#
# Philips Hue Phoenix Lights (used with the LLM010, LLM011 and LLM012, or individually).
# HML001	=	Phoenix Centerpiece
# HML002	=	Phoenix Ceiling
# HML003	=	Phoenix Pendant
# HML004	=	Phoenix Wall
# HML005	=	Phoenix Table
# HML006	=	Phoenix Downlight
#
# Philips Hue Motion Sensors
# SML001	=	Hue Motion Sensor (multi-sensor with presense, illumination and temperature)
#
# 3rd Party (Non-Philips) ZigBee Lights
# ZLL Light	=	Generic ZigBee Light (e.g. GE Link LEDs)
# FLS-PP3	=	Dresden Elektronik FLS-PP lp LED light strip, color LED segment
# FLS-PP3 White = Dresden Elektronik FLS-PP lp LED light strip, white light segment
# Classic A60 TW = Osram Lightify CLA60 Tunable White bulb (color temp. only)


### LIGHTS ###
##############
# Compatible Hue bulb devices) Color and Color Temperature
kHueBulbDeviceIDs = ['LCT001', 'LCT002', 'LCT003', 'LCT007', 'LCT010', 'LCT011', 'LCT012', 'LCT014', 'LLM001', 'HBL001', 'HBL002', 'HBL003', 'HEL001', 'HEL002,' 'HIL001', 'HIL002', 'FLS-PP3']
# Compatible LivingColors devices) Color only
kLivingColorsDeviceIDs = ['LLC001', 'LLC006', 'LLC007', 'LLC010', 'LLC011', 'LLC012', 'LLC013', 'LLC014', 'LLC020']
# Compatible Ambiance devices) Color Temperature only
kAmbianceDeviceIDs = ['LLM010', 'LLM011', 'LLM012', 'LTW001', 'LTC001', 'LTC003', 'LTW004', 'LTW011', 'LTW012', 'LTW013', 'LTW014', 'HML001', 'HML002', 'HML003', 'HML004', 'HML005', 'HML006']
# Compatible LightStrips devices. Color only on LST001. Color and Color Temperature on LST002
kLightStripsDeviceIDs = ['LST001', 'LST002']
# Compatible LivingWhites devices. Dimming only (no color change of any kind)
kLivingWhitesDeviceIDs = ['LWB001', 'LWB003', 'LWB004', 'LWB006', 'LWB007', 'LWB010', 'LWB014', 'LWL001', 'ZLL Light', 'FLS-PP3 White', 'Classic A60 TW']
# All compatible light devices
kCompatibleDeviceIDs = kHueBulbDeviceIDs + kAmbianceDeviceIDs + kLivingColorsDeviceIDs + kLightStripsDeviceIDs + kLivingWhitesDeviceIDs


### SENSORS ###
###############
# Supported Sensor Types
kSupportedSensorTypes = ['ZLLPresence', 'ZLLTemperature', 'ZLLLightLevel']
#
# Specific Sensor Models...
# Compatible motion sensors
kMotionSensorDeviceIDs = ['SML001']
# Compatible light sensors
kLightSensorDeviceIDs = ['SML001']
# Compatible temperature sensors
kTemperatureSensorDeviceIDs = ['SML001']


### Other Constants ###
#######################
# All Light Device Type IDs.
kLightDeviceTypeIDs = ['hueBulb', 'hueAmbiance', 'hueLightStrips', 'hueLivingColorsBloom', 'hueLivingWhites']
# All Group Device Type IDs.
kGroupDeviceTypeIDs = ['hueGroup']
# All Motion Sensor Type IDs.
kMotionSensorTypeIDs = ['hueMotionSensor']
# All Temperature Sensor Type IDs.
kTemperatureSensorTypeIDs = ['hueMotionTemperatureSensor']
# All Light Sensor Type IDs.
kLightSensorTypeIDs = ['hueMotionLightSensor']
