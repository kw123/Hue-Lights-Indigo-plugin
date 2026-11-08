# Hue Lights - "Local Network access" test, standalone (no plugin required)
# =========================================================================
# WHY run it inside Indigo:
#   macOS gates "Local Network" access per PROCESS. IndigoServer has its own grant; Terminal has a
#   different one. A Terminal "python3 thisfile.py" therefore CANNOT see a block that affects Indigo.
#   Run this where it shares IndigoServer's process/identity, e.g.:
#     - Indigo menu:  Plugins/Scripting shell, or paste into an Action "Execute Script" (Embedded Python),
#     - or drop it in Indigo's "Scripts" folder and run it from the Scripting menu.
#   Output goes to the Indigo Event Log via indigo.server.log().
#
# Set BRIDGE_IPS to the bridge IP(s) you want to test (same ones configured in the plugin).

import socket

BRIDGE_IPS = ["192.168.1.15"]          # <-- EDIT: your Hue bridge IP address(es)
MCAST      = "224.0.0.251"             # mDNS multicast group (bridge discovery)
MPORT      = 5353


def multicast_ok():
	"""Try a multicast send - the operation macOS blocks first when Local Network is denied (errno 65)."""
	s = None
	try:
		s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
		try:	s.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
		except Exception:	pass
		s.sendto(b"\x00", (MCAST, MPORT))      # any datagram proves multicast egress is allowed
		return True, None
	except Exception as e:
		return False, getattr(e, "errno", None)
	finally:
		if s is not None:
			try:	s.close()
			except Exception:	pass


def tcp_ok(host, port, timeout=1.5):
	"""TCP-connect 'ping' (pure Python, no /sbin/ping). True if the host answers on that port."""
	s = None
	try:
		s = socket.create_connection((host, port), timeout=timeout)
		return True
	except Exception:
		return False
	finally:
		if s is not None:
			try:	s.close()
			except Exception:	pass


mok, merr = multicast_ok()
bridge    = next((ip for ip in BRIDGE_IPS if tcp_ok(ip, 443)), None)     # LAN check
internet  = tcp_ok("www.google.com", 443) or tcp_ok("1.1.1.1", 443)     # WAN check (1.1.1.1 = DNS-free fallback)
errnoStr  = " (errno %s)" % merr if merr else ""
triedStr  = ", ".join(BRIDGE_IPS) if BRIDGE_IPS else "none configured"

# A successful multicast send is itself proof that Local Network access is granted, so key off mok
# first; only if multicast FAILED can this be a permission block.
if mok:
	if bridge:
		verdict = "OK: multicast works and bridge %s is reachable - Local Network access is granted." % bridge
	else:
		verdict = ("Local Network access is OK (the multicast send succeeded), but no configured bridge "
				   "answered on port 443 (tried: %s). That points to a wrong/missing bridge IP in "
				   "BRIDGE_IPS, the bridge being off, or a different subnet - NOT a macOS permission "
				   "problem." % triedStr)
else:
	if bridge:
		verdict = ("PARTIAL: direct connect to bridge %s works, but the multicast send failed%s. "
				   "Existing devices keep working; only auto-discovery of NEW bridges is affected "
				   "(multicast-only restriction)." % (bridge, errnoStr))
	elif internet:
		verdict = ("BLOCKED: the public internet is reachable but the LAN is NOT (multicast failed%s, no "
				   "configured bridge reachable, tried: %s). macOS is blocking Indigo's Local Network "
				   "access. Fix: System Settings > Privacy & Security > Local Network, enable Indigo, then "
				   "REBOOT. If the Indigo server runs as a boot/root service it cannot receive the "
				   "per-user grant - run it in your logged-in session." % (errnoStr, triedStr))
	else:
		verdict = ("NETWORK DOWN: neither the LAN nor the public internet is reachable from Indigo. This is "
				   "a general network / DNS / VPN / firewall problem, not a Local Network permission issue - "
				   "check the Mac's network connection first.")

try:
	indigo.server.log("Hue network test: multicastOk=%s, bridgeReachable=%s, internetOk=%s  =>  %s"
					  % (mok, bridge or False, internet, verdict))
except NameError:
	# not running inside Indigo (e.g. launched from Terminal) - fall back to print, and warn about context
	print("WARNING: not running inside Indigo - this reflects Terminal's Local Network grant, NOT Indigo's.")
	print("Hue network test: multicastOk=%s, bridgeReachable=%s, internetOk=%s\n%s"
		  % (mok, bridge or False, internet, verdict))
