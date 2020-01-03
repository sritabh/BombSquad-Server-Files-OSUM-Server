#ModBySobyDamn
from bsUI import *
import bsUI
import bsInternal
import ChatFilterConfig as config
from datetime import *
import time
#bs.screenMessage("ChatFilter added")
chatLogDir = "/var/www/html/chats"
def chatLogs(msg, clientID):
	date = str(datetime.date(datetime.now()))
	now = datetime.now()
	time = str(now.hour) + ":" + str(now.minute)
	for i in bsInternal._getGameRoster():
		cid = i['clientID']
		if cid == clientID:
			f = open(chatLogDir + "/Chats " + date + ".html",'a')
			f.write("<meta charset='UTF-8'><ul><li><b>" + i['players'][0]['name'] + "(" + i['displayString'] + ")</b>[" + time + "]: " + msg + "</li></ul>\n")
			lastm = i['displayString'] + ": " + msg
			if '/kick' in msg:
				import chatCmd
				chatCmd.cmd(lastm)
	
	
def _chatFilter(msg, clientID):
	chatLogs(msg, clientID)
	if 'yes' in config.blockChats:
		return None
		
	if any(word in msg for word in config.blacklist):
		for i in bsInternal._getGameRoster():
			cid = i['clientID']
			if cid == clientID:
				name = str(i['players'][0]['name'])
				nameID = str(i['displayString'])
				now = str(datetime.now())
		if not 'yes' in config.kickSpammer:
			f = open(chatLogDir + "/spammerID.html",'a')
			f.write("<meta charset='UTF-8'><ul><li>" + nameID + " Used bad word" + "[" + now + "]: " + msg + "<br>\nName Using:-" + name + "</li></ul>\n")
		if 'yes' in config.kickSpammer:
			bsInternal._chatMessage(nameID + " Kicked for using bad word")
			f = open(chatLogDir + "/spammerID.html",'a')
			f.write("<meta charset='UTF-8'><ul><li>" + nameID + " Kicked for using bad word" + "[" + now + "]: " + msg + "<br>\nName Using:-" + name + "</li></ul>\n")
			bsInternal._disconnectClient(clientID)
			if 'yes' in config.credits:
				bsInternal._chatMessage("ChatFilter Made By SobyDamn")
		else:
			return
		return None
		#print 'ChatFilter Working'
	else:
		return msg

bsUI._filterChatMessage = _chatFilter