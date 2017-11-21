Hue Lights 1.6.10

(FREE Indigo 7 plugin)


Hue Lights is a plugin for Indigo which allows you to control your Philips Hue lights and Friends of Hue lights through the Indigo system. It allows you to perform basic operations like turning bulbs on and off, setting brightness, and setting the default dimming ramp rate. It also keeps the status of each bulb updated in Indigo so Indigo always knows the condition of each bulb even when the bulbs are controlled by the Hue iOS or Android apps. Additionally, Hue Lights enables advanced control of the Philips Hue devices, allowing you to set custom colors (using RGB, HSB, or color temperature), and the ability to turn on or off alerts (blinking) and effects (color loop).

Hue Lights offers the following features:

•	Full Indigo Integration. Use standard Turn On, Turn Off, Set Brightness, Dim By, Brighten By, and Status Request actions in Indigo Pro to control each Philips Hue lighting device.
•	Start or Stop Brightening and Dimming. Use an Indigo action to start brightening or dimming a Hue device, then another action to stop. This can be useful if you want to press a button on a switch or remote to start dimming, then press another button to stop dimming when the light gets to the level you want. It can be even more useful when using the Dimmer Extender plugin to trigger brightening and dimming from INSTEON start brightening/dimming commands (something that can't currently be done with Indigo without a plugin).
•	Set Ramp Rates. Each Hue Lights action allows you to specify how quickly the light should change from it's current state to the settings you're specifying in the Indigo action using a "Ramp Rate" or transition time.
•	Set Colors. Use Indigo actions to set each Hue device to any color. There are 4 ways to set color. RGB levels (specify red, green, and blue levels similar to graphics editing software), HSB values (specify hue, saturation, and brightness similar to graphics editing software), and Color Temperature (set the white point of a bulb based on a Hue preset or your own color temperature, similar to digital camera white balance settings*). For advanced users, you can also specify the "xyY" chromaticity values. Each action can have a custom ramp rate (transition time) associated with it.
•	Use Virtual Dimmer Devices to Control Hue Device Settings. Use the Hue Device Attribute Controller device included with the Hue Lights plugin to control any aspect** of an existing Hue device, such as color saturation, hue, RGB level, or color temperature. These virtual dimmer devices can be especially useful when accessed from the Indigo Touch iOS app because they appear just like any other dimmer device within Indigo Touch. No need to create a control page or use the Hue app to adjust a device's hue or saturation.
•	Turn On and Off Alerts. You can turn on a short or long alert (1 blink for short, 15 blinks for long) for each device, and turn off the alert, also using Indigo actions.
•	Turn On and Off Effects. You can turn on Hue built-in special effects (currently, Hue only offers 1 effect: "color loop").
•	Save and Recall Your Own Presets. So, you've got your Hue bulb over the table set to just the right color, but now you want your LightStrips and LivingColors Bloom in the room to change to the same color. Either from the Plugins menu, or from within an Indigo action, you can save the current settings of your Hue bulb to one of 10 Presets then (in a separate menu selection/action) apply those settings to any other Hue device. From the Plugins menu, you can also print out the saved settings in each Preset to the Indigo log for reference or verification.
•	Extended Device Status Information. Each Hue device in Indigo also maintains all the status information provided by the Hue hub, including current hue and saturation levels, red, green, and blue levels, CIE 1931 xy chromaticity values, color temperature, color rendering mode, alert mode, effect mode, and whether the device is reachable by the hub. All this information can be viewed in the Mac OS X Indigo client (Indigo 6 beta 9 or newer), or on an Indigo control page you create with standard Indigo device state fields.
•	Hue Scene Recall Support. Hue scenes stored on the Hue hub are accessible from within Indigo and can be recalled using an Indigo action.
•	Motion Sensor Support. The Hue Motion Sensor is fully supported, including support for the motion, temperature and luminance sensors that are part of the Hue Motion Sensor.

Installation

Download the Hue Lights zip file (link above) to the computer running the Indigo server. If the file is not already unzipped, double-click the .zip file to unzip it. Double-click the Hue Lights.indigoPlugin file. The Indigo client will open and prompt to install the plugin. Click the option to install and enable the plugin.

Usage

Pairing the Hue Lights Plugin with Your Hue Hub

After installing the Hue Lights plugin for the first time, or if you open the Configuration dialog by going to the "Plugins" then "Hue Lights" then "Configure..." menu items in the Indigo Pro application, you'll be prompted to configure the plugin.

1	Enter the IP address of your Hue hub. The IP address can be obtained by most consumer routers in their administrative interface. It can also be obtained from the http://www.meethue.com web site if you have registered your hub with that site.
2	Press the center button on your Hue hub.
3	Within 30 seconds of pressing the center button on the Hue hub, click the "Pair Now" button in the configuration window. The Hue Lights plugin will first validate the IP address to make sure it's associated with a Hue hub device, then it will pair with the hub. You can now control all the lights registered with your hub.
4	Click "Save" to start creating devices.

Creating a Hue Bulb Device

There are 5 device types available once the Hue Lights plugin is installed. The first device is the "Hue Bulb" device. This is just what it sounds like, an Indigo device that represents one of your Philips Hue bulbs. There's also a "LightStrips" device, a "LivingColors Bloom" device, and a "LivingWhites (Experimental)" device. Use these to add Philips LED LightStrips, Philips Bloom devices, and Philips LIvingWhites devices, respectively. Other LivingColors devices should also work with the LivingColors Bloom device type. LivingWhites support is experimental for now. You can create an Indigo device for each bulb, LightStrip, LivingColors, and LivingWhites device connected to your Hue hub. The 5th device type is a "Hue Device Attribute Controller". This is a virtual dimmer which can be assigned to control any color attribute of an existing Hue Lights plugin device (as long as that device supports color). Hue Device Attribute Controllers are especially useful for quickly changing color attributes like hue or saturation, especially from Indigo Touch.

NOTE: Use these steps to create LightStrips, LivingColors Bloom, and LivingWhites devices as well.

1	Create a new Indigo device (click "New..." in the Devices window). Select the "Hue LIghts" plugin as the device Type. Select "Hue Color/Ambiance" (or "Ambiance Lights", "Hue LightStrips", "Color Lights", "LivingWhites", or "Hue Group") as the device type.
2	A "Configure Hue Color/Ambiance" (or similar) dialog will appear. Select the Hue Device you want to control. Enter an optional Default Brightness and optional "Ramp Rate" (transition time between brightness changes or color changes for color devices) and click "Save." If you don't see all your Hue devices in the list. Click "Cancel" and go to the "Plugins" menu, select "Hue Lights," then "Rebuild Hue Device List," then click the "Edit Device Settings" button in the "Edit Device" window. Select your device and click "Save." Done!

Use standard Indigo actions and controls to turn on and off the Hue device or to set the brightness. With Indigo 7 or newer, you can also use standard actions to change RGB or color temperature settings for Hue devices that support those features. To change colors using Hue Lights specific actions...

1	Create a new trigger and select the "Actions" tab (or create a new Action Group).
2	With Indigo 7, select "Device Actions" then "Hue Lights Controls" then the action that you'd like to execute from the sub-menu for the action type. In Indigo 6, select "Device Controls" then "Hue Lights Controls," then the action that you'd like to execute from that sub-menu. If you're still on Indigo 5, select "Plugin" for the action type, then select the "Action" from the menu beneath it.
3	Select the existing Hue Lights device from the "Device" menu.
4	If the Configure dialog doesn't automatically appear, click "Edit Action Settings." Each action settings dialog window has basic instructions on the meaning of each filed. Fill out the required information and click the "Save" button. Click "OK" on the trigger or action group to close it.

Creating a Hue Device Attribute Controller

1	Create a new Indigo device (click "New..." in the Devices window). Select the "Hue LIghts" plugin as the device Type. Select "Hue Device Attribute Controller" as the device type.
2	A "Configure Hue Device Attribute Controller" dialog will appear. Select the "Hue Color/Ambiance" Indigo device you want to control.
3	Select the color "Attribute to Control".
4	Optionally enter a default "Ramp Rate" (transition time between color changes).
5	Optionally enter a "Default On Level" between 1 and 100 percent. This can be useful if you want to quickly set a Hue device's color to, say, magenta by simply sending an "on" command to the Hue Bulb Attribute Controller virtual device.
6	Click "Save" then give your device a name before closing the Create New Device window.

You can now adjust the Hue Device Attribute Controller to change the color attributes of your Hue device.

Saving a Preset

1	Click the Plugins menu, go to Hue Lights and select Save Preset.
2	Follow the instructions below the fields in the Save Preset dialog that appears and click the Execute button.

You can also save a preset using an action within a trigger, action group, schedule, or control page.

Recalling a Preset

1	Click the Plugins menu, go to Hue Lights and select Recall Preset.
2	Follow the instructions below the fields in the Recall Preset dialog that appears and click the Execute button.

You can also recall a preset using an action within a trigger, action group, schedule, or control page.

Display a Preset's Data in the Indigo Log

This is useful if you'd like to know what device states are stored in a Hue Lights Preset before applying it to a Hue device or using it in an action.

1	Click the Plugins menu, go to Hue Lights and select Display Preset in Log.
2	Follow the instructions below the fields in the Recall Preset dialog that appears and click the Execute button.

Scripting Examples

Hue Lights (like most Indigo plugins) supports embedded scripts within Indigo actions. In addition to the standard device control methods such as indigo.device.turnOn("Device Name"), turnOff(), and toggle(), Hue Lights also supports Hue-sepcific actions. Below are some examples of how to execute Hue Lights actions from an embedded script within Indigo.

Set brightness of "Master Bed Dresser Lamp" to 50 percent at a ramp rate of 6.5 seconds.
plug = indigo.server.getPlugin("com.nathansheldon.indigoplugin.HueLights")
if plug.isEnabled():
   plug.executeAction("setBrightness", indigo.devices["Master Bed Dresser Lamp"].id, props={"brightness":50, "rate":6.5})

Immediately set the hue to 290 degrees, saturation to 100% and brightness to 75% for the "Dining Room Light".
plug = indigo.server.getPlugin("com.nathansheldon.indigoplugin.HueLights")
if plug.isEnabled():
   plug.executeAction("setHSB", indigo.devices["Dining Room Light"].id, props={"hue":290, "saturation":100, "brightness":76, "rate":0})

Set the "Nightstand Lamp" brightness to 60% and color temperature to 2800K.
plug = indigo.server.getPlugin("com.nathansheldon.indigoplugin.HueLights")
if plug.isEnabled():
   plug.executeAction("setCT", indigo.devices["Nightstand Lamp"].id, props={"brightness":60, "temperature":2800})

Indigo 7 ONLY: Set the "Nightstand Lamp" color temperature to 2800K. Note the 5 values before the color temperature of 2800. These are the Red, Green, Blue, White, and White2 levels which are required by the setColorLevels function even when only changing color temperature. Use 100 for R, G, B and W which lets the Hue Lights plugin know you intend to only change color temperature. The White 2 value (zero) is just there as a place holder. The value is ignored.
ndigo.dimmer.setColorLevels(indigo.devices["Nightstand Lamp"], 100, 100, 100, 100, 0, 2800)

Set the "Nightstand Lamp" color temperature to the "Reading" preset.
plug = indigo.server.getPlugin("com.nathansheldon.indigoplugin.HueLights")
if plug.isEnabled():
   plug.executeAction("setCT", indigo.devices["Nightstand Lamp"].id, props={"preset":"reading"})

Set the red, green, and blue color values of the "Table Lamp" to 245, 18, and 150 (respectively).
plug = indigo.server.getPlugin("com.nathansheldon.indigoplugin.HueLights")
if plug.isEnabled():
   plug.executeAction("setRGB", indigo.devices["Table Lamp"].id, props={"red":245, "green":18, "blue":150})

Indigo 7 ONLY: Set the red, green, and blue color values of the "Table Lamp" to 245, 18, and 150 (respectively).
indigo.dimmer.setColorLevels(indigo.devices["Table Lamp"], 245, 18, 150)

Set the x, y, and Y chromaticity and luminosity values of the "Bar Ambient Lights" to 0.5145, 0.3978, and 0.75 (respectively). (x, y and Y define the color and brightness in the CIE 1931 xyY color space). Note the capitalized "Y" in the 3rd property "xyy_Y". All property names are case sensitive.
plug = indigo.server.getPlugin("com.nathansheldon.indigoplugin.HueLights")
if plug.isEnabled():
   plug.executeAction("setXYY", indigo.devices["Bar Ambient Lights"].id, props={"xyy_x":0.5145, "xyy_y":0.3978, "xyy_Y":0.75})

Enable the long alert for the "Hallway Light".
plug = indigo.server.getPlugin("com.nathansheldon.indigoplugin.HueLights")
if plug.isEnabled():
   plug.executeAction("longAlert", indigo.devices["Hallway Light"].id)

Send a single alert pulse to the "Entryway Light".
plug = indigo.server.getPlugin("com.nathansheldon.indigoplugin.HueLights")
if plug.isEnabled():
   plug.executeAction("alertOnce", indigo.devices["Entryway Light"].id)

Stop all active alerts on the "Hallway Light".
plug = indigo.server.getPlugin("com.nathansheldon.indigoplugin.HueLights")
if plug.isEnabled():
   plug.executeAction("stopAlert", indigo.devices["Hallway Light"].id)

Enable the color loop effect on the "Master Bed Dresser Lamp".
plug = indigo.server.getPlugin("com.nathansheldon.indigoplugin.HueLights")
if plug.isEnabled():
   plug.executeAction("effect", indigo.devices["Master Bed Dresser Lamp"].id, props={"effect":"colorloop"})

Disable the color loop effect on the "Master Bed Dresser Lamp".
plug = indigo.server.getPlugin("com.nathansheldon.indigoplugin.HueLights")
if plug.isEnabled():
   plug.executeAction("effect", indigo.devices["Master Bed Dresser Lamp"].id, props={"effect":"none"})

Start or stop brightening the "Table Lamp".
plug = indigo.server.getPlugin("com.nathansheldon.indigoplugin.HueLights")
if plug.isEnabled():
   plug.executeAction("startStopBrightening", indigo.devices["Table Lamp"].id)

Start or stop dimming the "Table Lamp".
plug = indigo.server.getPlugin("com.nathansheldon.indigoplugin.HueLights")
if plug.isEnabled():
   plug.executeAction("startStopDimming", indigo.devices["Table Lamp"].id)

When executing actions through Python scripts, the "rate" property is always optional. If a rate isn't specified, the device's default ramp rate (transition time) will be used (or 0.5 seconds will be used if no default is set). With the "setCT" color temperature action, if you include the "preset" property, the specified preset will override any temperature and brightness specified. If a "preset" property is not specified, the "temperature" and "brightness" properties are required. Possible preset values are "concentrate", "relax", "energize", and "reading". These presets are based on the default presets included in the Hue app for iOS and control both brightness and color temperature when selected.
