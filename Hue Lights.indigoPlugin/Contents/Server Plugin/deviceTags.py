#! /usr/bin/env python
# -*- coding: utf-8 -*-
####################
# deviceTags.py: the same file in piBeacon, Hue Lights, uniFiAP, homematic, NetworkScanner, shellyDirect, INDIGOplotD and utilities
# Indigo 2026.1 (API 3.9) device tags: every device of the plugin gets the tag of the plugin, the color of the tag is chosen in the plugin config.
#
# in plugin.py:
#   import deviceTags
#   __init__                  self.tagAvailable = deviceTags.setup("pibeacon", "1E88E5", self)   # tag name, default color, the plugin. True if this Indigo has device tags
#   deviceStartComm(dev)      deviceTags.deviceStart(dev)                                  # the tag is created / colored if needed and added to the device
#   getPrefsConfigUiValues    deviceTags.uiValues(valuesDict)                              # defaults of the config fields (tag name, color)
#   validatePrefsConfigUi     deviceTags.prefsChanged(valuesDict)                          # "add tags" or the color changed: all devices of the plugin
# in PluginConfig.xml: checkbox tagsEnabled, text tagName (the name of the tag, default = the name given to setup()), menu tagColor (shown if tagsEnabled is on)
#
# the Indigo API (3.9, Indigo 2026.1):
#   indigo.server.tags                      the tag library: {name: record}, the record has color (6 hex digits, no #); text_color and border_color are derived, read only
#   indigo.server.create_tag(tag, color)    indigo.server.update_tag(tag, new_tag=None, new_color=None)
#   indigo.device.add_tag(device, tag)      the tag has to exist in the library, nothing happens if the device has it already
#   device.tags                             read only list of the tag names of the device
#   tag names: lower case letters (digits) separated by single dashes, e.g. "network-scanner"
# the plugin only adds its tag and sets its color, it never removes a tag (after a rename the old tag stays on the devices).

import re, threading, logging
import indigo

PREF_ENABLED	= "tagsEnabled"		# plugin config checkbox: add the tag to the devices of this plugin
PREF_NAME		= "tagName"			# plugin config text: the name of the tag, empty = the name the plugin gave to setup()
PREF_COLOR		= "tagColor"		# plugin config menu: the color of the tag, 6 hex digits
MIN_VERSION		= (2026, 1)			# Indigo version with device tags (API 3.9)

# the menu of the plugin config: value (hex) and label
COLORS = [("1E88E5", "blue"), ("039BE5", "light blue"), ("00ACC1", "cyan"), ("00897B", "teal"), ("43A047", "green"),
		  ("9E9D24", "olive"), ("FBC02D", "yellow"), ("FB8C00", "orange"), ("F4511E", "deep orange"), ("E53935", "red"),
		  ("D81B60", "pink"), ("8E24AA", "purple"), ("5E35B1", "deep purple"), ("3949AB", "indigo"), ("6D4C41", "brown"),
		  ("757575", "gray"), ("546E7A", "blue gray"), ("212121", "black")]

_log		= logging.getLogger("Plugin")
_lock		= threading.Lock()
_default_name	= ""		# the tag of this plugin if the plugin config has no name
_default	= "757575"		# its color if the plugin config has none
_available	= False
_problem		= "not checked"
_plugin		= None			# the plugin, its pluginPrefs hold the two config fields
_ensured	= None			# (name, color) of the tag in the library, as far as this plugin knows
_reported	= set()


def tagName(text):
	# "Network Scanner" --> "network-scanner"
	return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", "{}".format(text).lower())).strip("-")


def hexColor(value, default=None):
	# 6 hex digits in upper case, "#" allowed, else the default
	text = "{}".format(value).strip().lstrip("#").upper()
	if re.fullmatch(r"[0-9A-F]{6}", text): return text
	return default


def tagsProblem():
	# "" if this Indigo has device tags (Indigo 2026.1 or newer and the tag commands are there), else why not
	try:
		version = "{}".format(indigo.server.version)
		parts   = [int(re.sub(r"\D.*", "", xx) or 0) for xx in version.split(".")[:2]]
		if tuple(parts) < MIN_VERSION: return "needs Indigo {} or newer, this is {}".format(".".join(str(xx) for xx in MIN_VERSION), version)
		missing = [name for name, ok in (("indigo.server.tags", hasattr(indigo.server, "tags")), ("indigo.server.create_tag", hasattr(indigo.server, "create_tag")),
										 ("indigo.server.update_tag", hasattr(indigo.server, "update_tag")), ("indigo.device.add_tag", hasattr(indigo.device, "add_tag"))) if not ok]
		if missing: return "Indigo {} does not have {}".format(version, ", ".join(missing))
		return ""
	except Exception as e:
		return "the Indigo version could not be checked: {}".format(e)


def setup(name, defaultColor, plugin=None):
	# called once from the plugin __init__, returns True if the tags can be used (plugin attribute tagAvailable)
	global _default_name, _default, _available, _ensured, _plugin, _problem
	_plugin		= plugin
	_default_name = tagName(name)
	_default	= hexColor(defaultColor, "757575")
	_ensured	= None
	_problem	= tagsProblem()
	_available	= _problem == ""
	if not _available:
		# an Indigo that is too old is normal (debug), a new Indigo without the commands is not
		_log.log(10 if _problem.startswith("needs Indigo") else 30, "device tags: not available, {}".format(_problem))
	return _available


def isOn(value):
	return "{}".format(value).lower() in ["true", "1", "yes", "on"]


def pluginPrefs():
	return (_plugin if _plugin is not None else indigo.activePlugin).pluginPrefs


def enabled(prefs=None):
	# plugin config: add the tag to the devices
	try:
		if prefs is None: prefs = pluginPrefs()
		return isOn(prefs.get(PREF_ENABLED, False))
	except Exception as e:
		_report("the plugin config can not be read: {}".format(e))
		return False


def name(prefs=None):
	# plugin config: the name of the tag, empty or only characters that are not allowed --> the default of the plugin
	try:
		if prefs is None: prefs = pluginPrefs()
		return tagName(prefs.get(PREF_NAME, "")) or _default_name
	except Exception as e:
		_report("the plugin config can not be read: {}".format(e))
		return _default_name


def color(prefs=None):
	# plugin config: the color of the tag
	try:
		if prefs is None: prefs = pluginPrefs()
		return hexColor(prefs.get(PREF_COLOR, ""), _default)
	except Exception as e:
		_report("the plugin config can not be read: {}".format(e))
		return _default


def uiValues(valuesDict):
	# from getPrefsConfigUiValues: the defaults of the fields (the tag name is the name of the plugin), "add tags" is off if this Indigo has no tags
	try:
		valuesDict[PREF_NAME] = name(valuesDict)
		if not _available:
			valuesDict[PREF_ENABLED] = "false"
		else:
			if PREF_ENABLED not in valuesDict: valuesDict[PREF_ENABLED] = "false"
			valuesDict[PREF_COLOR] = color(valuesDict)
	except Exception:
		_log.log(30, "", exc_info=True)
	return valuesDict


def _recordColor(record):
	try:
		return hexColor(record["color"])
	except Exception:
		pass
	try:
		return hexColor(record.color)
	except Exception:
		return None


def ensureTag(newName, newColor):
	# the tag is in the library and has the chosen color. True if so
	global _ensured
	with _lock:
		if _ensured == (newName, newColor): return True
		try:
			library = indigo.server.tags
			if newName not in library:
				indigo.server.create_tag(newName, newColor)
				_log.log(20, "device tags: tag '{}' created, color {}".format(newName, newColor))
			elif _recordColor(library[newName]) != newColor:
				indigo.server.update_tag(newName, new_color=newColor)
				_log.log(20, "device tags: color of the tag '{}' set to {}".format(newName, newColor))
			_ensured = (newName, newColor)
			return True
		except Exception as e:
			_report("tag '{}' color {}: {}".format(newName, newColor, e))
			return False


def _report(text):
	# an error is written once, not for every device
	if text in _reported: return
	_reported.add(text)
	_log.log(30, "device tags: {}".format(text))


def tagDevice(dev, tag):
	# nothing happens if the device has the tag
	try:
		if tag in list(getattr(dev, "tags", None) or []): return
		indigo.device.add_tag(dev.id, tag)
	except Exception as e:
		_report("adding the tag '{}' to a device failed: {}".format(tag, e))


def deviceStart(dev):
	# from deviceStartComm: set the tag and its color for this device, if "add tags" is on in the plugin config
	try:
		if not enabled(): return
		if not _available:
			_report("the tags are switched on in the plugin config, but not available: {}".format(_problem))
			return
		newName = name()
		if ensureTag(newName, color()): tagDevice(dev, newName)
	except Exception:
		_log.log(30, "", exc_info=True)
	return


def applyAll(isEnabled, newName, newColor):
	# "add tags", the name or the color changed in the plugin config: the tag in the library and all devices of the plugin
	try:
		if not _available or not isEnabled: return
		if not ensureTag(newName, newColor): return
		for dev in indigo.devices.iter("self"):
			tagDevice(dev, newName)
	except Exception:
		_log.log(30, "", exc_info=True)
	return


def prefsChanged(valuesDict):
	# called from validatePrefsConfigUi, the new values are not saved yet
	try:
		if not _available: return
		newEnabled, newName, newColor = enabled(valuesDict), name(valuesDict), color(valuesDict)
		valuesDict[PREF_NAME] = newName		# saved as the allowed spelling, empty = the default of the plugin
		if (newEnabled, newName, newColor) == (enabled(), name(), color()): return
		timer = threading.Timer(2, applyAll, args=(newEnabled, newName, newColor))
		timer.daemon = True
		timer.start()
	except Exception:
		_log.log(30, "", exc_info=True)
	return
