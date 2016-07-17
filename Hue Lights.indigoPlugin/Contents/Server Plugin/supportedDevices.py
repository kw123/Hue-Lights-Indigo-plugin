#! /usr/bin/env python
# -*- coding: utf-8 -*-
####################
# Hue Lights Indigo Plugin
#	This file is imported into the main plugin.py file.


# List of compatible device IDs that may be associated with a Hue hub.
#
# LCT001	=	Hue bulb
# LCT002	=	Hue Downlight BR30 bulb
# LCT003	=	Hue Spot Light GU10 bulb
# LCT007	=	Hue bulb (800 lumen version)
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
# LTW004	=	Hue White Ambiance bulb (color temperature only bulb).
# LWB001	=	LivingWhites bulb
# LWB003	=	" " "
# LWB004	=	Hue A19 Lux
# LWB006	=	Hue White A19 extension bulb
# LWL001	=	LivingWhites light socket
# HML004	=	Phoenix wall lights
# HML006	=	Phoenix white LED lights
# ZLL Light	=	Generic ZigBee Light (e.g. GE Link LEDs)
# FLS-PP3	=	Dresden Elektronik FLS-PP lp LED light strip, color LED segment
# FLS-PP3 White = Dresden Elektronik FLS-PP lp LED light strip, white light segment
# Classic A60 TW = Osram Lightify CLA60 Tunable White bulb (color temp. only)


#   (compatible Hue bulb devices)
kHueBulbDeviceIDs = ['LCT001', 'LCT002', 'LCT003', 'LCT007', 'LLM001', 'LLM010', 'LLM011', 'LLM012', 'LTW004', 'LST002', 'FLS-PP3']
#   (compatible LivingColors devices)
kLivingColorsDeviceIDs = ['LLC001', 'LLC006', 'LLC007', 'LLC010', 'LLC011', 'LLC012', 'LLC013', 'LLC014', 'LLC020']
#   (compatible LightStrips devices)
kLightStripsDeviceIDs = ['LST001']
#   (compatible LivingWhites devices)
kLivingWhitesDeviceIDs = ['LWB001', 'LWB003', 'LWB004', 'LWB006', 'LWL001', 'ZLL Light', 'FLS-PP3 White', 'HML004', 'HML006', 'Classic A60 TW']
#   (all compatible devices)
kCompatibleDeviceIDs = kHueBulbDeviceIDs + kLivingColorsDeviceIDs + kLightStripsDeviceIDs + kLivingWhitesDeviceIDs
