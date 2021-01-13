# COMP3234-Assignment-1
A simple client-server online CLI game

Packages used (all included in Python 3.8.0):
Both GameClient.py and GameServer.py:
	socket (for networking)
	threading (multi-threading for multiple clients)
		
GameServer.py only:
	sys (for terminating a thread if necessary)
	time (for waiting)
	random (for drawing random result)

Usage:
GameClient.py:
	python3 GameClient.py <hostname/IP adress of the server> <Server port>

GameServer.py:
	python3 GameServer.py <listening port> <path to UserInfo.txt>