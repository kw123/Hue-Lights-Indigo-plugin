#! /usr/bin/env python
# -*- coding: utf-8 -*-
####################
# statsSqlIgnore.py: the same file in shellyDirect, homematic, piBeacon, uniFiAP, Hue Lights and utilities
# option "statistics states into the SQL logger": plugin config default (checkbox) + device edit menu (default / not written / written)
# statistics states = min / max / ave today / yesterday (+ At), measurements today / yesterday, today, yesterday, day-2 .. day-9,
#                     this / last week, month, year, switchpoints (At0), today date
# indigo's SQL logger skips the states listed in the shared device property "sqlLoggerIgnoreStates" (comma separated).
# only the statistics states are added / removed there, entries the plugin sets for other reasons stay.

import re, threading, logging
import indigo

PREF	= "sqlNoStatsDefault"	# plugin config checkbox: true = statistics states are not written into the SQL logger
FIELD	= "sqlNoStats"			# device edit menu: "default" (plugin config) / "no" (not written) / "yes" (written)
_regex	= re.compile(r"((Min|Max|Ave)(Today|Yesterday)(At)?|Measurements(Today|Yesterday)|Today|Yesterday|Day_[2-9]|Day-[2-9]|ThisWeek|LastWeek|ThisMonth|LastMonth|ThisYear|LastYear|_?At0|TodayDate)$")
_log	= logging.getLogger("Plugin")


def statsStates(dev):
	# the statistics states this device has
	return sorted(state for state in dev.states if not state.endswith(".ui") and _regex.search(state))


def prefDefault(prefs=None):
	# plugin config: true = not written into SQL
	try:
		if prefs is None: prefs = indigo.activePlugin.pluginPrefs
		return "{}".format(prefs.get(PREF, False)).lower() in ["true", "1", "yes", "on"]
	except Exception:
		return False


def notWritten(dev, default):
	choice = "{}".format(dev.pluginProps.get(FIELD, "default")).lower()
	if choice == "no":	return True
	if choice == "yes":	return False
	return default


def mergeIgnore(dev, add=(), remove=()):
	# add / remove entries of sqlLoggerIgnoreStates, keeps the others. returns True if changed
	sp = dev.sharedProps
	cur = [xx.strip() for xx in "{}".format(sp.get("sqlLoggerIgnoreStates", "") or "").split(",") if xx.strip() != ""]
	rem = set(xx.strip() for xx in remove)
	new = [xx for xx in cur if xx not in rem]
	for xx in add:
		xx = xx.strip()
		if xx != "" and xx not in new: new.append(xx)
	if new == cur: return False
	sp["sqlLoggerIgnoreStates"] = ", ".join(new)
	dev.replaceSharedPropsOnServer(sp)
	return True


def apply(devId, default=None):
	try:
		if devId not in indigo.devices: return
		dev = indigo.devices[devId]
		if default is None: default = prefDefault()
		states = statsStates(dev)
		if notWritten(dev, default):	changed = mergeIgnore(dev, add=states)
		else:							changed = mergeIgnore(dev, remove=states)
		if changed: _log.log(10, "SQL logger: statistics states of {} {}: {}".format(dev.name, "not written" if notWritten(dev, default) else "written again", ", ".join(states)))
	except Exception:
		_log.log(30, "", exc_info=True)
	return


def applyLater(devId, secs=5):
	# after the device start: the plugin may still add states (statistics options)
	timer = threading.Timer(secs, apply, args=(devId,))
	timer.daemon = True
	timer.start()
	return


def applyAll(default=None):
	try:
		for dev in indigo.devices.iter("self"):
			apply(dev.id, default)
	except Exception:
		_log.log(30, "", exc_info=True)
	return


def prefsChanged(valuesDict):
	# called from validatePrefsConfigUi: the plugin config default changed --> all devices of the plugin
	try:
		new = prefDefault(valuesDict)
		if new == prefDefault(): return
		timer = threading.Timer(2, applyAll, args=(new,))
		timer.daemon = True
		timer.start()
	except Exception:
		_log.log(30, "", exc_info=True)
	return
