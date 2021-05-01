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
# LCT014	=	Hue bulb (alternate A19 version 3, color gamut C)
# LCT015	=	Hue bulb (alternate A19 version 3, color gamut C)
# LCT016	=	Hue bulb (alternate A19 version 3, color gamut C)
# LCT024	=	Hue Play light (color gamut C)
# LCS001	=	Hue outdoor Lily spotlight (color gamut C)
# LCF001	=	Hue outdoor calla pathway bollard (color gamut C)
# LCF002	=	Hue outdoor pedestal light (color gamut C)
# LCF003	=	Hue Signe Floor light (color gamut C)
# LCF005    =   Hue Calla outdoor lamp (color gamut C)
# LCG002	=	Hue bulb (GU10, version 2, color gamut C)
# LCA001	=	Hue color lamp (B22, color gamut C)
# LCA002	=	Hue color lamp (A19, color gamut C)
# LCA003    =   Hue color lamp (A19/E26, color gamut C)
# LCB001    =   Hue color downlight (BR30, color gamut C)
# LCG001	=	Hue white and color GU10 400 lumen bulb
# LCW002	=	Hue color wall light (color gamut C, 1200 lumen)
# 1742930P7 =   Hue outdoor wall (color gamut C)
# 1743530P7 =   Hue outdoor floodlight (color gamut C)
# 1746230P7 =   Hue outdoor spot (color gamut C)
# 1746230V7 =   Hue outdoor Lily XL spotlight (color gamut C)
# 1746630P7 =   Hue Amarant Wall Washer (color gamut C)
# 4080148P9 =   Hue color table (color gamut C)
# 4080248P9 =   Hue color floor (color gamut C)
# 5045131P7 =   Hue Centura GU10 color spot (color gamut C)
# 5062148P7 =   Hue Argenta color spot (color gamut C)
# 440400982841  =   Hue Play color light (color gamut C)
#
# Philips LivingColors and Other Color Lights (color gamut A)
# LLC001	=	LivingColors light (generic)
# LLC005	=	LivingColors Gen3 Bloom/Aura
# LLC006	=	LivingColors Gen3 Iris
# LLC007	=	LivingColors Gen3 Bloom/Aura
# LLC010	=	LivingColors Iris (Europe)
# LLC011	=	Bloom (European?)
# LLC012	=	Bloom
# LLC013	=	Disney StoryLight
# LLC014	=	LivingColors Gen3 Aura
# LLC020	=	Hue Go
#
# Philips Luminaire Light Modules
# LLM001	=	Hue Luminaire Color Light Module (color gamut B)
# LLM010	=	Hue Color Temperature Module (2200K - 6500K)
# LLM011	=	Hue Color Temperature Module (2200K - 6500K)
# LLM012	=	Hue Color Temperature Module (2200K - 6500K)
#
# Philips LightStrips
# LST001	=	LED LightStrips (color gamut A)
# LST002	=	LED LightStrips Plus (color gamut C)
# LST003	=	LED LightStrips Outdoor - short (color gamut C)
# LST004	=	LED LightStrips Outdoor - long (color gamut C)
# LCL001    =   LED LightStrips Plus v4 (color gamut C)
# LCL002    =   Hue Lightstrip Outdoor 2m (color gamut C)
# LCL003    =   Hue Lightstrip Outdoor 5m (color gamut C)
# LCX001    =   LED Hue Play Gradient LightStrip (color gamut C)
#
# Philips Ambiance Lights (color temperature only)
# LTW001	=	Hue A19 White Ambiance bulb
# LTC001	=	Hue Ambiance Ceiling
# LTC002	=	Hue Ambiance Ceiling
# LTC003	=	Hue Ambiance Ceiling
# LTC004	=	Hue Ambiance Ceiling
# LTC011    =   Hue Ambiance Ceiling
# LTF001	=	Hue Ambiance Ceiling
# LTF002	=	Hue Ambiance Ceiling
# LTG002    =   Hue Ambiance GU10 bulb
# LTD001	=	Hue Ambiance Ceiling
# LTD002	=	Hue Ambiance Ceiling
# LTW004	=	Hue A19 White Ambiance bulb
# LTW010	=	Hue A19 White Ambiance bulb
# LTW011	=	Hue BR30 White Ambiance bulb
# LTW012	=	Hue Ambiance Candle E14 bulb
# LTW013	=	Hue Ambiance Spot GU10 spotlight bulb
# LTW014	=	Hue Ambiance Spot GU10 spotlight bulb
# LTW015	=	Hue A19 White Ambiance bulb
# LTP001	=	Hue Ambiance Pendant light
# LTP002	=	Hue Ambiance Pendant light
# LTP003	=	Hue Ambiance Pendant light
# LTP004	=	Hue Ambiance Pendant light
# LTP005	=	Hue Ambiance Pendant light
# LTD003	=	Hue Ambiance Pendant light
# LTD009    =   Hue Ambiance downlight
# LTD010    =   Hue Ambiance downlight
# LTD011    =   Hue Ambiance downlight
# LFF001	=	Hue Ambiance Floor light
# LTT001	=	Hue Ambiance Table light
# LDT001	=	Hue Ambiance Downlight
# LTB002	=	Hue White Ambiance BR30
# LTA001	=	Hue White Ambiance A19 806 lumen (European)
# LTA002	=	Hue White Ambiance E26 with Bluetooth
# LTA003    =   Hue White Ambiance A19 bulb
# 3402931P7 =   Hue Adore Ambiance Wall
#
# Philips LivingWhites (Dimming Only) Lights
# LDD001	=	Hue White Table
# LDD002	=	Hue White Floor
# LDF001	=	Hue White Ceiling
# LDF002	=	Hue White Wall Washer
# LWA001	=	Philips dimmable light
# LWA002	=	Philips A19 dimmable light version 5 (800 lm)
# LWA003    =   Philips dimmable light.
# LWA004	=	Philips A60 B22 Hue filament bulb
# LWA005    =   Philips E26 A19 Hue filament bulb
# LWA007    =   Hue White light
# LWA008    =   Philips Hue white lamp
# LWA009    =   Philips Hue white lamp
# LWB001	=	LivingWhites bulb
# LWB003	=	LivingWhites bulb
# LWB004	=	Hue A19 Lux
# LWB006	=	Hue White A19 extension bulb
# LWB007	=	Hue Lux (alternate version)
# LWB010	=	Hue White (version 2)
# LWB014	=	Hue White (version 3)
# LWB015	=	Hue White PAR-38 flood light
# LWB022	=	Hue White BR30 dimmable light
# LWE002    =   Hue White Candle
# LWG001	=	Hue GU10 Dimmable Light (version 1)
# LWG004	=	Hue GU10 Dimmable Light (version 2)
# LWL001	=	Hue LivingWhites light socket
# LWO001	=	Hue LED filament G93 globe bulb (dimming only)
# LWO002	=	Hue LED filament G25 globe bulb (dimming only)
# LWO003    =   Hue LED filament bulb (dimming only)
# LWS001	=	Hue White PAR38 Outdoor
# LWV001	=	Hue LED filament ST64 spiral filament bulb (dimming only)
# LWV002	=	Hue LED filament ST19 Edison bulb (dimming only)
# LWW001	=	Hue Outdoor Lucca (A60 bulb and fixture)
# MWM001	=	Hue White 1-10V
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
# Hue Smart Plug
# LOM001	=	Hue Smart Plug (non-dimmable, on/off only).
# LOM003	=	Hue Smart Plug (non-dimmable, on/off only, UK version).
# LOM004	=	Hue Smart Plug (non-dimmable, on/off only, North American version).
# LOM005    =   Hue Smart Plug (non-dimmable, on/off only, Australia version).
#
# Philips Hue Motion Sensors
# SML001	=	Hue Motion Sensor (multi-sensor with presense, illumination and temperature)
# SML002    =   Hue Outdoor Motion Sensor
#
# Switches
# ZGPSWITCH	=	Hue Tap
# SWT001	=	Hue Tap
# RWL020	=	Hue Dimmer Switch (US)
# RWL021	=	Hue Dimmer Switch (EU)
# RWL022    =   Hue Dimmer Switch (UK)
# ROM001	=	Hue Smart button
# RDM001    =   Hue Wall Switch module
# FOHSWITCH	=	Run Less Wires switch
# PTM215Z   =   Niko (EnOcean) Smart Switch
#
# 3rd Party (Non-Philips) ZigBee Lights
# ZLL Light							=	Generic ZigBee Light (e.g. GE Link LEDs)
# GLEDOPTO							=	GLEDOPTO Generic ZigBee WW/CW light strip (color temp. only)
# GLEDOPTO							=	GLEDOPTO Generic ZigBee color light strip (color and color temp)
# GL-C-006                          =   GLEDOPTO Generic ZigBee color light strip (color and color temp)
# GL-C-007							=	GLEDOPTO Generic ZigBee color light strip (color and color temp)
# GL-C-008                          =   CLEDOPTO Generic ZigBee color light strip (color and color temp)
# GL-C-009                          =   GLEDOPTO Generic ZigBee dimmable LED controller (no color control)
# GL-B-001Z                         =   GLEDOPTO Generic ZigBee color light bulb (color and color temp)
# GL-B-007Z                         =   GLEDOPTO Generic ZigBee color light bulb (color and color temp)
# GL-D-004Z                         =   GLEDOPTO Generic ZigBee color light bulb (color and color temp)
# GL-FL-005P                        =   GLEDOPTO Generic ZigBee color light bulb (color and color temp)
# GL-FL-005TZS                      =   GLEDOPTO Generic ZigBee color light bulb (color and color temp)
# GL-S-007Z                         =   GLEDOPTO Generic ZigBee color light bulb (color and color temp)
# FLS-PP3							=	Dresden Elektronik FLS-PP lp LED light strip, color LED segment
# FLS-PP3 White						=	Dresden Elektronik FLS-PP lp LED light strip, white light segment
# FLS-CT							=	Dredesn Elektronik FLS-CT lp LED color temperature light
# HOMA1001							=	ShenZhen Homa LED light strip controller (extended color light)
# QV-RGBCCT                         =   Quotra-Vision LED RGB and cool/warm white light strip (extended color light)
# Classic A60 TW					=	Osram Lightify A60 Tunable White bulb (color temp. only)
# Classic A60 RGBW					=	Osram Lightify A60 RGBW bulb (extended color bulb)
# Flex RGBW							=	Osram Lightify Flex RGBW light strip (extended color light)
# PAR16 50 TW						=	Osram PAR-16 50W equivalent Tunable White bulb (color temp. only)
# Gardenpole Mini RGBW OSRAM		=	Osram Gardenpole Mini RGBW light (extended color light)
# PAR 16 50 RGBW - LIGHTIFY			=	Osram PAR-16 GU10 Lightify light (extended color light)
# PAR16 RGBW Z3						=	Osram PAR-16 SMART+ Spot GU10 Multicolor 350lm (extended color light)
# Plug 01							=	Osram On/Off Plug
# MR16 TW OSRAM                     =   Osram Smart + LED GU5.3 reflector (color temperature only)
# TRADFRI bulb E26 opal 1000lm		=	IKEA dimmable 1000 lumen E26 light
# TRADFRI bulb E26 WS opal 1000lm	=	IKEA dimmable 1000 lumen E26 color temperature bulb
# TRADFRI bulb E26 WW clear 250lm   =   IKEA dimmable 250 lumen E26 dimmable light.
# TRADFRI bulb E26 WW 806lm         =   IKEA dimmable 806 lumen E26 dimmable light.
# TRADFRI bulb E26 CWS opal 600lm	=	IKEA dimmable 600 lumen E26 color LED bulb (no color temp.)
# TRADFRI bulb E27 CWS opal 600lm	=	IKEA dimmable 600 lumen E27 color LED bulb (no color temp.)
# TRADFRI bulb E27 opal 1000lm		=	IKEA dimmable 1000 lumen E27 light
# TRADFRI bulb E27 WS opal 1000lm	=	IKEA dimmable 1000 lumen E27 color temperature bulb
# TRADFRI bulb E27 WS opal 980lm    =   IKEA dimmable 980 lumen E27 color temperature bulb
# TRADFRI bulb E27 WW 806lm			=	IKEA dimmable 806 lumen E27 light
# TRADFRI bulb E14 W op/ch 400lm	=	IKEA dimmable 400 lumen E14 light
# TRADFRI bulb E14 WS opal 600lm	=	IKEA dimmable 600 lumen E14 color temperature bulb
# TRADFRI bulb E14 CWS opal 600lm	=	IKEA dimmable 600 lumen E14 color bulb
# TRADFRI bulb E12 W op/ch 400lm	=	IKEA dimmable 400 lumen E12 light
# TRADFRI bulb GU10 WW 400lm		=	IKEA dimmable 400 lumen GU10 light
# TRADFRI transformer 10W			=	IKEA dimmable 10 Watt LED transformer.
# TRADFRI transformer 30W			=	IKEA dimmable 30 Watt LED transformer.
# FLOALT panel WS 30x90				=	IKEA color temperature LED panel (30x90)
# FLOALT panel WS 30x30             =   IKEA color temperature LED panel (30x30)
# RS 128 T							=	innr RS-128T GU10 color temperature lights
# AE 280 C                          =   innr AE-280C A19 color and color temperature light
# RB 185 C                          =   innr RB-185C color and color temperature light
# RS 228 T							=	innr RS-228T GU10 color temperature light
# FL 130 C							=	innr Flex Color 4 Meter RGBW LED Strip
# SP 120							=	innr On/Off Plug-in module
# SP 224                            =   innr On/Off Plug-in module
# TS011F                            =   Lidl Silvercrest Smart on/off plug
# TS0502A                           =   Lidl color temperature light
# TZ3000                            =   Lidl Silvercrest on/off plug (another version)
# FB56-ZCW08KU1.1                   =   Feibit Inc. LED strip controller
# FZB56-ZCW27LX1.0					=	Feibit Inc. LED strip controller (3A NUE ZigBee RGBW Light)
# ZBT-ColorTemperature				=	Müller-Licht MLI (Aldi Tint) ZBT color temperature light
# ZB-CL01                           =   eWeLight full color/color temperature A19 bulb


### LIGHTS ###
##############
# Compatible Hue bulb devices (Color and Color Temperature)
kHueBulbDeviceIDs = ['LCT001', 'LCT002', 'LCT003', 'LCT007', 'LCT010', 'LCT011', 'LCT012', 'LCT014', 'LCT015',  'LCT016', 'LCT024', '440400982841', 'LCS001', '1746230V7', 'LCF001', 'LCF002', 'LCF003', 'LCG002', 'LCA001', 'LCA002', 'LCA003', 'LCB001', 'LCG001', 'LCW002', 'LLM001', 'HBL001', 'HBL002', 'HBL003', 'HEL001', 'HEL002', 'HIL001', 'HIL002', 'FLS-PP3', 'GL-B-001Z', 'GL-B-007Z', 'GL-D-004Z', 'GL-FL-005P', 'GL-FL-005TZS', 'GL-S-007Z', 'Classic A60 RGBW', 'Gardenpole Mini RGBW OSRAM', 'PAR 16 50 RGBW - LIGHTIFY', 'RB 185 C', 'AE 280 C', 'PAR16 RGBW Z3', 'LCF005', '1746230P7', '1746630P7', '4080148P9', '4080248P9', '1742930P7', '1743530P7', '5045131P7', '5062148P7', 'ZB-CL01']
# Compatible LivingColors devices (Color only)
kLivingColorsDeviceIDs = ['LLC001', 'LLC005', 'LLC006', 'LLC007', 'LLC010', 'LLC011', 'LLC012', 'LLC013', 'LLC014', 'LLC020', 'TRADFRI bulb E26 CWS opal 600lm', 'TRADFRI bulb E27 CWS opal 600lm', 'TRADFRI bulb E14 CWS opal 600lm']
# Compatible Ambiance devices (Color Temperature only)
kAmbianceDeviceIDs = ['LLM010', 'LLM011', 'LLM012', 'LTW001', 'LTC001', 'LTC003', 'LTC002', 'LTC003', 'LTW004', 'LTC011', 'LTW010', 'LTW011', 'LTW012', 'LTW013', 'LTW014', 'LTW015', 'LTF001', 'LTF002', 'LTG002', 'LTD001', 'LTD002', 'LTP001', 'LTP002', 'LTP003', 'LTP004', 'LTP005', 'LTD003', 'LTD009', 'LTD010', 'LTD011', 'LFF001', 'LTT001', 'LDT001', 'LTB002', 'LTA001', 'LTA002', 'LTA003', 'HML001', 'HML002', 'HML003', 'HML004', 'HML005', 'HML006', '3402931P7', 'Classic A60 TW', 'PAR16 50 TW', 'RS 128 T', 'RS 228 T', 'FLOALT panel WS 30x90', 'FLOALT panel WS 30x30', 'FLS-CT', 'TRADFRI bulb E26 WS opal 1000lm', 'TRADFRI bulb E27 WS opal 1000lm', 'TRADFRI bulb E27 WS opal 980lm', 'TRADFRI bulb E14 WS opal 600lm', 'TRADFRI bulb GU10 WS 400lm', 'ZBT-ColorTemperature', 'TS0502A', 'MR16 TW OSRAM']
# Compatible LightStrips devices. (Color only on LST001. Color and Color Temperature on others)
kLightStripsDeviceIDs = ['LST001', 'LST002', 'LST003', 'LST004', 'LCL001', 'LCL002', 'LCL003', 'LCX001', 'Flex RGBW', 'HOMA1001', 'GL-C-006', 'GL-C-007', 'GL-C-008', 'FB56-ZCW08KU1.1', 'FZB56-ZCW27LX1.0', 'GLEDOPTO', 'TRADFRI transformer 10W', 'TRADFRI transformer 30W', 'FL 130 C', 'QV-RGBCCT']
# Compatible LivingWhites devices. (Dimming only.  No color change of any kind)
kLivingWhitesDeviceIDs = ['LWA001', 'LWA002', 'LWA003', 'LWA004', 'LWA005', 'LWA007', 'LWA008', 'LWA009', 'LWB001', 'LWB003', 'LWB004', 'LWB006', 'LWB007', 'LWB010', 'LWB014', 'LWB015', 'LWB022', 'LWE002', 'LWL001', 'LWW001', 'LDF001', 'LDF002', 'LDD001', 'LDD002', 'MWM001', 'LWS001', 'LWG001', 'LWG004', 'LWO001', 'LWV001', 'LWV002', 'LWO002', 'LWO003', 'ZLL Light', 'FLS-PP3 White', 'TRADFRI bulb E26 WW 806lm', 'TRADFRI bulb E26 opal 1000lm', 'TRADFRI bulb E26 WW clear 250lm', 'TRADFRI bulb E27 opal 1000lm', 'TRADFRI bulb E27 WW 806lm', 'TRADFRI bulb E14 W op/ch 400lm', 'TRADFRI bulb E12 W op/ch 400lm', 'TRADFRI bulb GU10 WW 400lm', 'GL-C-009']
# Compatible on/off devices. (On/Off only.  Not dimmable)
kOnOffOnlyDeviceIDs = ['LOM001', 'LOM003', 'LOM004', 'LOM005', 'SP 120', 'SP 224', 'Plug 01', 'TS011F', 'TZ3000']
# All compatible light devices
kCompatibleDeviceIDs = kHueBulbDeviceIDs + kAmbianceDeviceIDs + kLivingColorsDeviceIDs + kLightStripsDeviceIDs + kLivingWhitesDeviceIDs + kOnOffOnlyDeviceIDs



### SENSORS ###
###############
# Supported Sensor Types
kSupportedSensorTypes = ['ZLLPresence', 'ZLLTemperature', 'ZLLLightLevel', 'ZGPSwitch', 'ZLLSwitch']
#
# Specific Sensor Models...
# Compatible motion sensors
kMotionSensorDeviceIDs = ['SML001', 'SML002']
# Compatible light sensors
kLightSensorDeviceIDs = ['SML001', 'SML002']
# Compatible temperature sensors
kTemperatureSensorDeviceIDs = ['SML001', 'SML002']
# Compatible switches/dimmers
kSwitchDeviceIDs = ['ZGPSWITCH', 'SWT001', 'RWL020', 'RWL021', 'RWL022', 'ROM001', 'RDM001', 'FOHSWITCH', 'PTM215Z']


### Other Constants ###
#######################
# All Light Device Type IDs.
kLightDeviceTypeIDs = ['hueBulb', 'hueAmbiance', 'hueLightStrips', 'hueLivingColorsBloom', 'hueLivingWhites', 'hueOnOffDevice']
# All Group Device Type IDs.
kGroupDeviceTypeIDs = ['hueGroup']
# All Motion Sensor Type IDs.
kMotionSensorTypeIDs = ['hueMotionSensor']
# All Temperature Sensor Type IDs.
kTemperatureSensorTypeIDs = ['hueMotionTemperatureSensor']
# All Light Sensor Type IDs.
kLightSensorTypeIDs = ['hueMotionLightSensor']
# All Switch Type IDs.
kSwitchTypeIDs = ['hueTapSwitch', 'hueDimmerSwitch', 'hueSmartButton', 'runLessWireSwitch']
