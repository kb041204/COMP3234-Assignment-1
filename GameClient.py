#!/usr/bin/python3
import socket
import sys

def msg_send(connSocket, msg):
	try:
		connSocket.send(msg.encode('ascii'))
	except socket.error as emsg:
		print("Server has disconnected unexpectedly")
		connSocket.close()
		sys.exit(1)
	
def msg_receive(connSocket):
	try:
		msg = connSocket.recv(10000).decode('ascii') #receive client authentication info
		return msg
	except socket.error as emsg:
		print("Server has disconnected unexpectedly")
		connSocket.close()
		sys.exit(1)

def main(argv):
	#server port not an integer
	try:
		serverPort = int(argv[2])
	except ValueError:
		print("The port number is not an integer")
		sys.exit(1)

	#Try connecting to the server first
	try:
		my_socket = socket.socket()
		my_socket.connect((argv[1], int(argv[2])))
	except socket.error:
		print("Sever is offline")
		my_socket.close()
		sys.exit(1)
	
	#Part 1 - User Authentication
	while True:
		print("Please input your user name:")
		username = input()
		print("Please input your password:")
		password = input()
		
		auth_msg = "/login " + username + ' ' + password
		msg_send(my_socket, auth_msg) #send username and password to server
		
		auth_rev_msg = msg_receive(my_socket) #receive response from server
		print(auth_rev_msg)
		if auth_rev_msg[0:4] == "1001":
			break #exit while loop and stop asking for username and password
	
	#Part 2,3,4,5
	while True:
		command = input()
		
		if command == "": #Avoid sending empty string to server
			print("Error: Empty string detected. Command is not sent to server")
			continue
			
		msg_send(my_socket, command) #send command to server

		rev_msg = msg_receive(my_socket) #receive response from server
		
		print(rev_msg)

		if rev_msg[0:4] == "4001": #exit from game hall if server responses 4001
			print("Client ends")
			my_socket.close()
			break
		elif rev_msg[0:4] == "3011": #waiting for another player to join the game, i.e.3012
			rev_msg = msg_receive(my_socket)
			print(rev_msg)


if __name__ == '__main__':
	if len(sys.argv) != 3:
		print("Usage: python GameClient.py <hostname/IP adress of the server> <Server port>")
		sys.exit(1)
	main(sys.argv)