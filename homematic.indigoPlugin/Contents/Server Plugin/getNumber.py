#!/usr/bin/env python
# -*- coding: utf-8 -*-
# by Karl Wachs
def getNumber(val):
	# test if a val contains a valid number, if not return ""
	# return the number if any meaningful number (with letters before and after return that number)
	# u"a-123.5e" returns -123.5
	# -1.3e5 returns -130000.0
	# -1.3e-5 returns -0.000013
	# u"1.3e-5" returns -0.000013
	# u"1.3e-5x" returns "" ( - sign not first position  ..need to include)
	# True, u"truE" u"on" "ON".. returns 1.0;  False u"faLse" u"off" returns 0.0
	# u"1 2 3" returns ""
	# u"1.2.3" returns ""
	# u"12-5" returns ""
		try:
			return															 float(val)
		except:
			if type(val) is bool										   : return 1.0 if val else 0.0
		if val ==""														   : return "x"
		try:
			xx = ''.join([c for c in val if c in '-1234567890.'])								# remove non numbers 
			lenXX= len(xx)
			if lenXX > 0:																		# found numbers..
				if len( ''.join([c for c in xx if c in '.']) )           >1: return "x"			# remove strings that have 2 or more dots " 5.5 6.6"
				if len( ''.join([c for c in xx if c in '-']) )           >1: return "x"			# remove strings that have 2 or more -    " 5-5 6-6"
				if len( ''.join([c for c in xx if c in '1234567890']) ) ==0: return "x"			# remove strings that just no numbers, just . amd - eg "abc.xyz- hij"
				if lenXX ==1											   : return float(xx)	# just one number
				if xx.find("-") > 0										   : return "x"			# reject if "-" is not in first position
				valList = list(val)																# make it a list
				count = 0																		# count number of numbers
				for i in range(len(val)-1):														# reject -0 1 2.3 4  not consecutive numbers:..
					if (len(''.join([c for c in valList[i] if c in '-1234567890.'])) ==1 ):		# check if this character is a number, if yes:
						count +=1																# 
						if count >= lenXX									: break				# end of # of numbers, end of test: break, it is a number
						if (len(''.join([c for c in valList[i+1] if c in '-1234567890.'])) )== 0: return "x" #  next is not a number and not all numbers accounted for, so it is numberXnumber
				return 														float(xx)			# must be a real number, everything else is excluded
			else:																				# only text left,  no number in this string
				ONE  = [ u"TRUE" , u"T", u"ON",  u"HOME", u"YES", u"JA" , u"SI",  u"IGEN", u"OUI", u"UP",  u"OPEN", u"CLEAR"   ]
				ZERO = [ u"FALSE", u"F", u"OFF", u"AWAY", u"NO",  u"NON", u"NEIN", u"NEM",        u"DOWN", u"CLOSED", u"FAULTED", u"FAULT", u"EXPIRED"]
				val = unicode(val).upper()
				if val in ONE : return 1.0		# true/on   --> 1
				if val in ZERO: return 0.0		# false/off --> 0

# SPECIAL CASES 
				if (val.find(u"LEAV")    == 0 or  # leave 
					  val.find(u"UNK")   == 0 or  
					  val.find(u"LEFT")  == 0  
										   ): return -1. 

				if( val.find(u"ENABL")   == 0 or   # ENABLE ENABLED 
					  val.find(u"ARRIV") == 0 
										   ): return 1.0		# 

				if( val.find(u"STOP")    == 0  # stop stopped
											): return 0.0		# 

				return "x"																		# all tests failed ... nothing there, return "
		except:
			return "x"																			# something failed eg unicode only ==> return ""
		return "x"																				# should not happen just for safety
