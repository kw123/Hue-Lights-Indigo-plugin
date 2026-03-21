#! /usr/bin/env python
# -*- coding: utf-8 -*-
####################
# Developed by Karl Wachs
# karlwachs@me.com

# ===========================================================================
# ch eck for proper plugin name
# ===========================================================================

def checkIndigoPluginName(self, indigo):
	if self.pathToPlugin.find("/"+self.pluginName+".indigoPlugin/") ==-1:
		indigo.server.log("-----------------------------------------------------------------------------------------------------------------------" )
		indigo.server.log("-----------------------------------------------------------------------------------------------------------------------" )
		indigo.server.log("-----------------------------------------------------------------------------------------------------------------------" )
		indigo.server.log("-----------------------------------------------------------------------------------------------------------------------" )
		indigo.server.log("-----------------------------------------------------------------------------------------------------------------------" )
		self.errorLog("The pluginname is not correct, please reinstall or rename")
		self.errorLog("It should be   /Libray/....../Plugins/{}.indigPlugin".format(self.pluginName))
		p=max(0,self.pathToPlugin.find("/Contents/Server"))
		self.errorLog("It is: {}".format(self.pathToPlugin[:p]))
		self.errorLog("please check your download folder, delete old *.indigoPlugin files or this will happen again during next update" )
		self.errorLog("This happens eg when you download a new version and and old with the same name is still in the download folder" )
		self.errorLog(" ")
		self.errorLog("=== and brute force fix method: === ")
		self.errorLog("Shut down the Indigo Server by selecting the Indigo Stop Server menu item in the Mac client " )
		self.errorLog("   (you can leave the client app running).")
		self.errorLog("Open the following folder in the Finder: /Library/Application Support/Perceptive Automation/Indigo x.y/ " )
		self.errorLog("  (you can select the Go→Go to Folder… menu item in the Finder and paste in the path to open a Finder window)." )
		self.errorLog("  In that Finder window you'll see two folders: " )
		self.errorLog("Plugins and Plugins (Disabled). Depending on whether the plugin is enabled or not will determine which folder it's in." )
		self.errorLog("Open the appropriate folder and delete the unwanted plugin." )
		self.errorLog("Switch back to the Indigo Mac client and click on the Start Local Server… button in the Server Connection Status dialog." )
		self.errorLog("Then reinstall the plugin" )
		indigo.server.log("-----------------------------------------------------------------------------------------------------------------------" )
		indigo.server.log("-----------------------------------------------------------------------------------------------------------------------" )
		indigo.server.log("-----------------------------------------------------------------------------------------------------------------------" )
		indigo.server.log("-----------------------------------------------------------------------------------------------------------------------" )
		indigo.server.log("-----------------------------------------------------------------------------------------------------------------------" )
		self.sleep(200000)
		self.quitNOW = "wrong plugin name"
		return False
	return True
