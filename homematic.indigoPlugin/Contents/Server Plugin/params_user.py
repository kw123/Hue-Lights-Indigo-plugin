### replace xxx c to define you button device, or delete the entries if not used
### you can define any new device here mapping it to an existing device
###   eg HMIP-PS is a simple relay, a device mapped to that would be:
###   "HMIP-mydev": 	"HMIP-PS",
###  don't forget to add a >>,<<  after each line besides the last one.
k_userDefs = {
	"HMIP-XYZ":		"HMIP-BUTTON",	# any button device  not included in std defs
	"HMIP-mydef1": 	"HMIP-PS",   	# simple relay
	"HMIP-mydef2c": "HMIP-PSM"   	#  simple relay with energy measurement
}
