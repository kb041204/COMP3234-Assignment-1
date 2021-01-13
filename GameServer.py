#!/usr/bin/python3
import socket
import threading
import sys
import time
import random

num_player_lock = threading.Lock() #mutex lock for modifying number_of_player_in_room array
number_of_room = 10
number_of_player_in_room = [] #Global variable: array[number_of_room] containing the number of players in room

response_lock = threading.Lock() #mutex lock for modifying responses 2D array
responses = [] #Global variable: 2D array[number_of_room][2] containing the response from client
result = [] #Global variable: array[number_of_room] containing the random result generated

judging_lock = threading.Lock() #mutex lock for judging who is the winner

for i in range(0, number_of_room): #initialize all the arrays
	number_of_player_in_room.append(0)
	responses.append(["waiting","waiting"])
	result.append("null")

class ServerThread(threading.Thread):
	def __init__(self, client, pathToUserInfo):
		threading.Thread.__init__(self)
		self.client = client
		self.pathToUserInfo = pathToUserInfo
		self.connSocket, self.connAddr = self.client
	
	def msg_send(self, msg): #for receiving message and handle exception
		try:
			self.connSocket.send(msg.encode('ascii'))
		except socket.error as emsg:
			print("Thread: User \"" + self.username + "\" with IP \"" + self.connAddr[0] + "\" has disconnected unexpectedly")
			self.connSocket.close()
			sys.exit(1)
	
	def msg_send_after_judge(self, msg, room_number, player, first_thread): #send message and in case player disconnected unexpectedly, clear part of the room first
		self.acquire_lock("RES")
		result[room_number-1] = "null"
		responses[room_number-1][player] = "waiting" #cleanup itself
		if first_thread == False: #In case first thread disconnected unexpectedly during judging
			responses[room_number-1][(player-1)*-1] = "waiting" #cleanup the first thread as well
		self.release_lock("RES")
		self.acquire_lock("NUM")
		number_of_player_in_room[room_number-1] = 0
		self.release_lock("NUM")
		
		try: #first thread has disconnected unexpectedly
			self.connSocket.send(msg.encode('ascii'))
		except socket.error as emsg:
			self.acquire_lock("RES")
			if first_thread == True:
				responses[room_number-1][player] = "withdrawal"
			self.release_lock("RES")
			self.release_lock("JUD")
			print("Thread: User \"" + self.username + "\" with IP \"" + self.connAddr[0] + "\" has disconnected unexpectedly during judging")
			self.connSocket.close()
			sys.exit(1)
	
	def msg_receive(self): #for sending message and handle exception
		try:
			msg = self.connSocket.recv(10000).decode('ascii') #receive client message
			return msg
		except socket.error as emsg:
			print("Thread: User \"" + self.username + "\" with IP \"" + self.connAddr[0] + "\" has disconnected unexpectedly")
			self.connSocket.close()
			sys.exit(1)
	
	def acquire_lock(self, type): #for acquiring the mutex lock, and displaying log in server
		if type == "NUM":
			num_player_lock.acquire()
			print("Thread: User \"" + self.username + "\" with IP \"" + self.connAddr[0] + "\" has acquired NUM lock")
		elif type == "RES":
			response_lock.acquire()
			print("Thread: User \"" + self.username + "\" with IP \"" + self.connAddr[0] + "\" has acquired RES lock")
		elif type == "JUD":
			judging_lock.acquire()
			print("Thread: User \"" + self.username + "\" with IP \"" + self.connAddr[0] + "\" has acquired JUD lock")
	
	def release_lock(self, type): #for acquiring the mutex lock, and displaying log in server
		if type == "NUM":
			num_player_lock.release()
			print("Thread: User \"" + self.username + "\" with IP \"" + self.connAddr[0] + "\" has released NUM lock")
		elif type == "RES":
			response_lock.release()
			print("Thread: User \"" + self.username + "\" with IP \"" + self.connAddr[0] + "\" has released RES lock")
		elif type == "JUD":
			judging_lock.release()
			print("Thread: User \"" + self.username + "\" with IP \"" + self.connAddr[0] + "\" has released JUD lock")
	
	def clear_room(self, room_number): #for reseting both arrays for use of next clients, only applicable when both threads has disconnected unexpectedly
		print("Thread: Room " + str(room_number-1) + " begin clean up")
		self.acquire_lock("NUM")
		number_of_player_in_room[room_number-1] = 0
		self.release_lock("NUM")
		
		self.acquire_lock("RES")
		responses[room_number-1][0] = "waiting"
		responses[room_number-1][1] = "waiting"
		result[room_number-1] = "null"
		self.release_lock("RES")
		print("Thread: Room " + str(room_number-1) + " finish clean up")
	
	def run(self):
		pathToUserInfo = self.pathToUserInfo
		
		#======Part 1 - User Authentication
		authenticated = False
		self.username = "NOT AUTHENTICATED"
		while not authenticated:
			auth_message = self.msg_receive()
			
			try:
				userInfoFile = open(pathToUserInfo, "r")
			except OSError as emsg:
				print("Thread: OSError: " + str(emsg))
				userInfoFile.close()
				sys.exit(1)
			
			#client disconnected unexpectedly when login
			try:
				login_command, username, password = auth_message.split(' ')
			except ValueError: #less than 3 input
				print("Thread: User \"" + self.username + "\" with IP \"" + self.connAddr[0] + "\" has failed to authenticate")
				self.msg_send("1002 Authentication failed")
				continue;
			
			user_auth_to_compare = username + ':' + password
			user_auth_list = userInfoFile.readlines() #put all info into a list
			
			for line in user_auth_list:
				if user_auth_to_compare == line.strip(): #Matching line
					authenticated = True
					break
					
			userInfoFile.close() #close the file for next thread
			
			if authenticated:
				self.msg_send("1001 Authentication successful")
			else:
				self.msg_send("1002 Authentication failed")
				print("Thread: User \"" + self.username + "\" with IP \"" + self.connAddr[0] + "\" has failed to authenticate")
		
		self.username = username
		print("Thread: User \"" + username + "\" with IP \"" + self.connAddr[0] + "\" has been authenticated successfully")
		client_state = 1001
		
		#======Part 2 - In the Game Hall
		while client_state != 4001:
			client_command = self.msg_receive()
			if client_command == "/list":
				self.acquire_lock("NUM")
				#Assemble the message
				message = "3001 " + str(number_of_room)
				for i in number_of_player_in_room:
					message = message + " " + str(i)
					
				self.msg_send(message)
				self.release_lock("NUM")

			elif client_command[0:6] == "/enter":
				try:
					command, room_number = client_command.split(" ")
					room_number = int(room_number)
				except ValueError: #Room number is not an integer OR command is "/enter(any spaces)" only
					self.msg_send("4002 Unrecognized message")
					continue;
					
				if(room_number < 1 or room_number > number_of_room): #Room number out of range
					self.msg_send("4002 Unrecognized message")
					continue;
					
				#Entering room
				first_player = True
				self.acquire_lock("NUM")
				if number_of_player_in_room[room_number-1] == 2:
					print("Thread: User \"" + self.username + "\" with IP \"" + self.connAddr[0] + "\" failed to enter room " + str(room_number-1) + " because it is full")
					client_state = 3013
					self.msg_send("3013 The room is full")
					self.release_lock("NUM")
					continue
				number_of_player_in_room[room_number-1] = number_of_player_in_room[room_number-1] + 1
				self.release_lock("NUM")
				print("Thread: User \"" + self.username + "\" with IP \"" + self.connAddr[0] + "\" has enter room " + str(room_number-1))
				
				if number_of_player_in_room[room_number-1] == 2:
					first_player = False
					client_state = 3012
					self.msg_send("3012 Game started. Please guess true or false")
				elif number_of_player_in_room[room_number-1] == 1:
					client_state = 3011
					self.msg_send("3011 Wait")
				
				if first_player == True: #Send 3012 to first player that enter the room
					while number_of_player_in_room[room_number-1] != 2: #keep checking if another player has entered the room for every 0.1s
						try: 
							self.connSocket.send(b"") #keep sending data every 0.1s to socket to check if it is still online
							time.sleep(0.1)
						except ConnectionResetError: #player himself has disconnected
							print("Thread: User \"" + self.username + "\" with IP \"" + self.connAddr[0] + "\" has disconnected unexpectedly while waiting for another player to enter")
							self.connSocket.close()
							self.clear_room(room_number) #one player only, safe to run
							sys.exit(1)
					self.msg_send("3012 Game started. Please guess true or false")
					client_state = 3012
				
				#======Part 3a - Playing a Game
				while True:
					if first_player == True: #for recognizing which slot in array
						player = 0
						opponent = 1
					else:
						player = 1
						opponent = 0
				
					#Handle unexpected disconnection before entering true/false
					try: 
						client_command = self.connSocket.recv(10000).decode('ascii') #receive client message
					except socket.error as emsg:
						print("Thread: User \"" + self.username + "\" with IP \"" + self.connAddr[0] + "\" has disconnected unexpectedly before entering true/false")
						self.connSocket.close()
						self.acquire_lock("RES")
						responses[room_number-1][player] = "withdrawal"
						self.release_lock("RES")
						if responses[room_number-1][player] == "withdrawal" and responses[room_number-1][opponent] == "withdrawal":
							print("Thread: Both users has disconnected unexpectedly before entering true/false")
							self.clear_room(room_number)
						sys.exit(1)
					
					#Handle command incorrect syntax
					try:
						command, guess = client_command.split(" ")
					except ValueError: #command is "/guess(any spaces)" only
						self.msg_send("4002 Unrecognized message")
						continue;
						
					if command != "/guess" or guess not in ("true", "false"):
						self.msg_send("4002 Unrecognized message")
						continue;
					
					#correct command syntax
					self.acquire_lock("RES")
					result[room_number-1] = bool(random.getrandbits(1)) #generate result
					responses[room_number-1][player] = guess #store player's guess into array
					self.release_lock("RES")

					#Handle player unexpected disconnection after entering true/false and opponents still guessing
					while True:
						if responses[room_number-1][opponent] != "waiting":
							break
						try: 
							self.connSocket.send(b"") #keep sending data every 0.1s to socket to check if it is still online
							time.sleep(0.1)
						except ConnectionResetError: #player himself has disconnected
							print("Thread: User \"" + self.username + "\" with IP \"" + self.connAddr[0] + "\" has disconnected unexpectedly after entering true/false")
							self.connSocket.close()
							self.acquire_lock("RES")
							responses[room_number-1][player] = "withdrawal"
							self.release_lock("RES")
							if responses[room_number-1][player] == "withdrawal" and responses[room_number-1][opponent] == "withdrawal":
								print("Thread: Both users has disconnected unexpectedly after entering true/false")
								self.clear_room(room_number)
							sys.exit(1)
							
					break #all guesses are recorded and ready to judge
					
				time.sleep(0.25) #Wait 0.25s for the first player to exit out from while loop
				
				#======Part 3b - Judging time --- At this point, there should be at least one thread that runs this part of the code
				#First thread to acquire the lock is responsible for judging
				self.acquire_lock("JUD")
				print("Thread: Judging start: Room " + str(room_number-1) + " response: " + str(responses[room_number-1]) + ", result: " + str(result[room_number-1]) + ", by user \"" + self.username + "\"")
				if responses[room_number-1][opponent] == "withdrawal": #Check withdrawal, if yes, then player is the winner
					print("Thread: Judging: Room " + str(room_number-1) + ", user \"" + self.username + "\" win by opponent disconnecting")
					self.clear_room(room_number) #safe to run coz one thread only
					self.msg_send("3021 You are the winner")
				
				elif responses[room_number-1][player] not in ("win", "lose", "tie"): #result not judged (first thread that acquire the lock)
					if responses[room_number-1][player] == responses[room_number-1][opponent]: #tie
						responses[room_number-1][opponent] = "tie"
						self.msg_send_after_judge("3023 The result is a tie", room_number, player, True)
					elif responses[room_number-1][player] == str(result[room_number-1]).lower(): #same guess as result, player is the winner
						responses[room_number-1][opponent] = "lose"
						self.msg_send_after_judge("3021 You are the winner", room_number, player, True)
					else: #different guess as result, opponent is the winner
						responses[room_number-1][opponent] = "win"
						self.msg_send_after_judge("3022 You lost this game", room_number, player, True)
							
				else: #result is judged (second thread that acquire the lock will run this part)
						if responses[room_number-1][opponent] == "withdrawal" or responses[room_number-1][player] == "win": #first thread disconnected unexpectedly during judging / second thread wins
							self.msg_send_after_judge("3021 You are the winner", room_number, player, False)
						elif responses[room_number-1][player] == "lose":
							self.msg_send_after_judge("3022 You lost this game", room_number, player, False)
						else:
							self.msg_send_after_judge("3023 The result is a tie", room_number, player, False)
				self.release_lock("JUD")
				
				#At this point, both arrays entry for the room should be cleaned up
				print("Thread: Judging successful: Room " + str(room_number-1) +", all data reset")
				print("Thread: Judging successful: Room " + str(room_number-1) + " response: " + str(responses[room_number-1]) + ", result: " + str(result[room_number-1]))
					
			#======Part 4 - Exit from the System
			elif client_command == "/exit":
				client_state = 4001
				self.msg_send("4001 Bye bye")
				print("Thread: User \"" + self.username + "\" with IP \"" + self.connAddr[0] + "\" has disconnected")
				self.connSocket.close()
				
			#======Part 5 - Dealing with incorrect message format
			else: #other command
				self.msg_send("4002 Unrecognized message")

def main(argv):
	#server port not an integer
	try:
		serverPort = int(argv[1])
	except ValueError:
		print("Error: The server port number is not an integer")
		sys.exit(1)
	
	#server port out-of-range
	if (serverPort < 0 or serverPort > 65535):
		print("Error: The server port number is not within 0 and 65535")
		sys.exit(1)
	
	#try if UserInfo.txt exists
	try:
		userInfoFile = open(argv[2], "r")
	except OSError as emsg:
		print("Error: \"" + argv[2] + "\" does not exist")
		sys.exit(1)
	userInfoFile.close()
	
	serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	serverSocket.bind( ("", serverPort) )
	serverSocket.listen(5)
	print("Main: The server is ready")
	
	#accept client and create a thread for that socket
	while True:
		client = serverSocket.accept()
		t = ServerThread(client, argv[2])
		t.start() 
	
if __name__ == '__main__':
	if len(sys.argv) != 3:
		print("Usage: python GameServer.py <listening port> <path to UserInfo.txt>")
		sys.exit(1)
	main(sys.argv)