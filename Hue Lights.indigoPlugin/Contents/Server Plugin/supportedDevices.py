#! /usr/bin/env python
# -*- coding: utf-8 -*-
####################
# Hue Lights Indigo Plugin
#	This file is imported into the main plugin.py file.


# List of compatible device IDs that may be associated with a Hue hub.
#
# LCT001	=	Hue bulb (color gamut B)
# LCT002	=	Hue Downlight/Spot BR30 bulb (color gamut B)
# LCT003	=	Hue Spot Light GU10 bulb (color gamut B)
# LCT007	=	Hue bulb (800 lumen version, color gamut B)
# LCT010	=	Hue bulb (A19 version 3, color gamut C)
# LCT011	=	Hue bulb (BR30 version 3, color gamut C)
# LCT014	=	Hue bulb (alternate A19 version 3)
# LLC001	=	LivingColors light (generic)
# LLC006	=	LivingColors Gen3 Iris
# LLC007	=	LivingColors Gen3 Bloom Aura
# LLC010	=	LivingColors Iris (Europe)
# LLC011	=	Bloom (European?)
# LLC012	=	Bloom
# LLC013	=	Disney StoryLight
# LLC014	=	LivingColors Aura
# LLC020	=	Hue Go
# LLM001	=	Hue Luminaire Color Light Module
# LLM010	=	Hue Color Temperature Module (2200K - 6500K)
# LLM011	=	" " "
# LLM012	=	" " "
# LST001	=	LED LightStrip
# LST002	=	LED LightStrip Plus (RGB + color temperature)
#				The LightStrip Plus is temporarily in the kHueBulbDeviceIDs
#				list because it supports color temperature and more code will
#				need to change before it can be added to the kLightStripsDeviceIDs list.
# LTW001	=	Hue White Ambiance bulb (color temperature only bulb).
# LTW004	=	Another Hue White Ambiance bulb (color temperature only bulb).
# LTW013	=	Hue Ambiance Spot GU10 spotlight bulb.
# LTW014	=	" " "
# LWB001	=	LivingWhites bulb
# LWB003	=	" " "
# LWB004	=	Hue A19 Lux
# LWB006	=	Hue White A19 extension bulb
# LWB007	=	Hue Lux (alternate version)
# LWB010	=	Hue White (version 2)
# LWB014	=	Hue White (version 3)
# LWL001	=	LivingWhites light socket
# HML004	=	Phoenix wall lights
# HML006	=	Phoenix white LED lights
# ZLL Light	=	Generic ZigBee Light (e.g. GE Link LEDs)
# FLS-PP3	=	Dresden Elektronik FLS-PP lp LED light strip, color LED segment
# FLS-PP3 White = Dresden Elektronik FLS-PP lp LED light strip, white light segment
# Classic A60 TW = Osram Lightify CLA60 Tunable White bulb (color temp. only)


#   (compatible Hue bulb devices) Color and Color Temperature
kHueBulbDeviceIDs = ['LCT001', 'LCT002', 'LCT003', 'LCT007', 'LCT010', 'LCT011', 'LCT014', 'LLC010', 'LLM001', 'FLS-PP3']
#	(compatible Ambiance devices) Color Temperature only
kAmbianceDeviceIDs = ['LLM010', 'LLM011', 'LLM012', 'LTW001', 'LTW004', 'LTW013', 'LTW014']
#   (compatible LivingColors devices) Color only
kLivingColorsDeviceIDs = ['LLC001', 'LLC006', 'LLC007', 'LLC011', 'LLC012', 'LLC013', 'LLC014', 'LLC020']
#   (compatible LightStrips devices) Color only on LST001. Color and Color Temperature on LST002.
kLightStripsDeviceIDs = ['LST001', 'LST002']
#   (compatible LivingWhites devices) Dimming only (no color change of any kind)
kLivingWhitesDeviceIDs = ['LWB001', 'LWB003', 'LWB004', 'LWB006', 'LWB007', 'LWB010', 'LWB014', 'LWL001', 'ZLL Light', 'FLS-PP3 White', 'HML004', 'HML006', 'Classic A60 TW']
#   (all compatible devices)
kCompatibleDeviceIDs = kHueBulbDeviceIDs + kAmbianceDeviceIDs + kLivingColorsDeviceIDs + kLightStripsDeviceIDs + kLivingWhitesDeviceIDs

