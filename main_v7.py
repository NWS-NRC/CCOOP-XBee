import micropython
import xbee
import uio
import uos
from umqtt.simple import MQTTClient
from sys import stdin, stdout
import network
import machine
import json
import time
import utime
import sys
from sites.siteFile import pubTopic


SERVER = pubTopic.server_Address
msg_Topic = pubTopic.MESSAGE_TOPIC  
sub_Topic = pubTopic.SUB_TOPIC
temp_Topic = pubTopic.TEMP_PUB_TOPIC
precip_Topic = pubTopic.PRECIP_PUB_TOPIC
daily_Topic = pubTopic.DAILY_PUB_TOPIC
update_Topic = pubTopic.UPDATE_TOPIC
command_Topic = pubTopic.COMMAND_TOPIC
alert_Topic = pubTopic.ALERT_TOPIC
msg_payload = ""
payload_Topic = ""

topic_ToSend = [""] * 100
msg_ToSend = [""] * 100
missed_Obs = 0
topic_File = "topic.log"
msg_File = "msg.log"
files_Exist = False

CLIENT_ID = pubTopic.clientID  # Should be unique for each device connected.

second = 0
minute = 0
hour = 0
dayOfWeek = 0
daymonth = 0
year = 0
dayCheck = 0
dow = 0
TZ = pubTopic.clientTZ

ds = ""
maxTempT = ""
maxTemp = ""
minTempT = ""
minTemp = ""
tempT = ""
temp = ""
pp = ""

timeUpdated = False
tempUpdate = False
temp_Inbound = False
dailyUpdate = False
precipUpdate = False
precip_Inbound = False
alertUpdate = False
alert_Inbound = False

'''
AI_DESC = {
    0x00: 'CONNECTED',
    0x22: 'REGISTERING_TO_NETWORK',
    0x23: 'CONNECTING_TO_INTERNET',
    0x24: 'RECOVERY_NEEDED',
    0x25: 'NETWORK_REG_FAILURE',
    0x2A: 'AIRPLANE_MODE',
    0x2B: 'USB_DIRECT',
    0x2C: 'PSM_DORMANT',
    0x2F: 'BYPASS_MODE_ACTIVE',
    0xFF: 'MODEM_INITIALIZING',
}
'''

def publishBackup(topic = ""):
  global msg_payload
  global payload_Topic
  global msg_ReadyRcv
  global tempUpdate
  global temp_Inbound
  global precipUpdate
  global precip_Inbound
  global alertUpdate
  global alert_Inbound
  global dailyUpdate
  global temp_Topic
  global daily_Topic
  global precip_Topic
  global topic_ToSend
  global msg_ToSend
  global missed_Obs
  global topic_File
  global msg_File

  if (topic == daily_Topic or topic == precip_Topic):    
    topic_ToSend[missed_Obs] = payload_Topic
    log = uio.open(topic_File, mode="a")
    log.write(topic + "\n")
    time.sleep(0.5)
    log.close()
    msg_ToSend[missed_Obs] = msg_payload
    log1 = uio.open(msg_File, mode="a")
    log1.write(msg_payload + "\n")
    time.sleep(0.5)
    log1.close()
    missed_Obs = missed_Obs + 1
  msg_payload = ""
  payload_Topic = ""
  

def publish(client_id=CLIENT_ID, hostname=SERVER, topic = "", keepalive=60):
  global msg_payload
  global payload_Topic
  global tempUpdate
  global temp_Inbound
  global precipUpdate
  global precip_Inbound
  global alertUpdate
  global alert_Inbound
  global dailyUpdate
  global temp_Topic
  global daily_Topic
  global precip_Topic
  global topic_ToSend
  global msg_ToSend
  global missed_Obs
  global topic_File
  global msg_File
  # Connect to the MQTT server.

  #xbee_debug("Publishing", "")
  client = MQTTClient(client_id, hostname)
  #xbee_debug("#X","- Connecting to '%s'... " % hostname)
  brokerConnected = True
  print (brokerConnected)
  brokerConnected = client.connect()
  print (brokerConnected)
  if (brokerConnected == True and (topic == daily_Topic or topic == precip_Topic)):
    publishBackup(topic)
  elif brokerConnected == False:
    #xbee_debug("#X","Client Connected")
    client.publish(topic, msg_payload)
    time.sleep(1)
    if topic == temp_Topic and tempUpdate == True:
        tempUpdate = False  
        temp_Inbound = False
    if topic == daily_Topic and dailyUpdate == True:
        dailyUpdate = False
        temp_Inbound = False
    if topic == precip_Topic and precipUpdate == True:
        precipUpdate = False
        precip_Inbound = False
    if topic == alert_Topic and alertUpdate == True:
        alertUpdate = False
        alert_Inbound = False
    client.disconnect() 
    payload_Topic = ""
    msg_payload = ""
  else:
    pass
  

def publish_missedObs(client_id=CLIENT_ID, hostname=SERVER, keepalive=60):
  global topic_ToSend
  global msg_ToSend
  global missed_Obs
  global wdt

  cnt = 0
  wdt.feed()
  client = MQTTClient(client_id, hostname)
  #xbee_debug("#X","- Connecting to '%s'... " % hostname)
  client.connect()
  #xbee_debug("#X","Client Connected")
  while cnt < missed_Obs:     
    topic = topic_ToSend[cnt]
    msg = msg_ToSend[cnt]
    client.publish(topic, msg)  
    #xbee_debug("#X","Message Published")
    wdt.feed()
    cnt = cnt + 1
    wdt.feed()
  client.disconnect() 
  if cnt == missed_Obs:
    missed_Obs = 0
    topic_ToSend = [""] * 100
    msg_ToSend = [""] * 100
    if files_Exist == True:
      wdt.feed()
      #pending topics have been sent, remove files 
      deleteFiles()
      time.sleep(1)
      #create new files for logging
      createFiles()   
    

def read_teensy():
  global msg_payload
  global payload_Topic
  global temp_Inbound
  global temp_Topic
  global tempUpdate
  global precip_Inbound
  global precip_Topic
  global precipUpdate
  global alert_Inbound
  global alert_Topic
  global alertUpdate
  global dailyUpdate
  global daily_Topic
  global tempUpdate
  global ds
  global maxTempT
  global maxTemp
  global minTempT
  global minTemp
  global tempT
  global temp
  global pp
  
  msg_read = False
  temp_Inbound = False
  precip_Inbound = False
  alert_Inbound = False
  precipUpdate = False
  dailyUpdate = False
  tempUpdate = False
  alertUpdate = False
  teensy_data = [""] * 8
  var = ""
  msg_payload = ""
  empty_Read = False

  time.sleep(3)
  c = stdin.buffer.read() # reads byte and returns first byte in buffer or None
  if c is None: #buffer is empty, move on
    empty_Read = True
  if empty_Read == False:
    final_String = str(c.decode())
    trim_String = final_String[2:len(final_String)-2]
    if (final_String[0] == '#'):
      if (final_String[1] == 'T'):
        temp_Inbound = True      
      elif (final_String[1] == 'F'):
        precip_Inbound = True
      elif (final_String[1] == 'A'):
        alert_Inbound = True
      elif (final_String[1] == '?'):
        return
      else:
        pass
        
      if (temp_Inbound == True) or (precip_Inbound == True) or (alert_Inbound == True):
        msg_payload = trim_String
        msg_read = True
      else:
        pass
            
    else:
      pass           
        
    if msg_read == True:
      if precip_Inbound == True:
        precipUpdate = True
        payload_Topic=precip_Topic
        
      elif temp_Inbound == True:
        if msg_payload.count(",") == 7: # daily has the pp value so there will be 7 "," delimiters
          teensy_data = msg_payload.split(",")
          ds = teensy_data[0]
          maxTempT = teensy_data[1]
          maxTemp = teensy_data[2]
          minTempT = teensy_data[3]
          minTemp = teensy_data[4]
          tempT = teensy_data[5]
          temp = teensy_data[6]
          pp = teensy_data[7]
          dailyUpdate = True
        else:
          teensy_data = msg_payload.split(",")
          ds = teensy_data[0]
          maxTempT = ""
          maxTemp = ""
          minTempT = ""
          minTemp = ""
          tempT = teensy_data[5]
          temp = teensy_data[6]
          pp = ""
          tempUpdate = True

      elif alert_Inbound == True:
        alertUpdate = True
        payload_Topic=alert_Topic
        
      else:
        pass
      
    else:
      pass
  
  if dailyUpdate == True:
    comma = ','
    msg_payload = pubTopic.clientID + comma + ds + comma + maxTempT + comma + maxTemp + comma + minTempT + comma + minTemp + comma + tempT + comma + temp + comma + pp
    payload_Topic=daily_Topic
    ds = ""
    maxTempT = ""
    maxTemp = ""
    minTempT = ""
    minTemp = ""
    tempT = ""
    temp = ""
    pp = ""
  
  if tempUpdate == True:
    comma = ","
    msg_payload = pubTopic.clientID + comma + ds + comma + maxTempT + comma + maxTemp + comma + minTempT + comma + minTemp + comma + tempT + comma + temp
    payload_Topic=temp_Topic
    ds = ""
    maxTempT = ""
    maxTemp = ""
    minTempT = ""
    minTemp = ""
    tempT = ""
    temp = ""    
  

def xbee_debug(desig = "", msgToTeensy = ""):
  if desig == "#T":
    xbee_msg = desig + msgToTeensy + "\r\n"
  else:
    xbee_msg = desig + "\r\n"
  stdout.buffer.write(xbee_msg)
  
def printLocalTime():
  global TZ
  global timeUpdated
  t1 = str(int(utime.localtime()[0]) - 2000) + "," + str(utime.localtime()[1]) + "," + str(utime.localtime()[2]) + "," + str(utime.localtime()[3]) + "," + str(utime.localtime()[4])  + "," + str(utime.localtime()[5])
  timeMsg = t1 + "," + TZ
  xbee_debug("#T",timeMsg + "\r\n")
  timeUpdated = True

def readFiles():
  global missed_Obs
  global topic_ToSend
  global msg_ToSend
  global topic_File
  global msg_File

  obs_ToAdd = 0
  currentNum = missed_Obs
  with uio.open(topic_File, mode="r") as log:
    topics_pending = log.readlines()
    num = len(topics_pending)
    obs_ToAdd = num
    lineCnt = 0
    while lineCnt < num:
      t = topics_pending[lineCnt]
      topic_ToSend[currentNum] = t[:len(t)-1]
      lineCnt = lineCnt + 1
      currentNum = currentNum + 1
    log.close()
  currentNum = missed_Obs
  with uio.open(msg_File, mode="r") as log:
    msg_pending = log.readlines()
    num = len(msg_pending)
    lineCnt = 0
    while lineCnt < num:
      m = msg_pending[lineCnt]
      msg_ToSend[currentNum] = m[:len(m)-1]
      lineCnt = lineCnt + 1
      currentNum = currentNum + 1
    log.close()
  missed_Obs = missed_Obs + obs_ToAdd

def createFiles():
  global topic_File
  global msg_File

  log = uio.open(topic_File, mode="x")
  log.close()
  log1 = uio.open(msg_File, mode="x")
  log1.close()

def deleteFiles():
  global topic_File
  global msg_File

  try:
    log = uio.open(topic_File)
    log.close()
    uos.remove(topic_File)
  except OSError:
    pass

  try:
    log1 = uio.open(msg_File)
    log1.close()
    uos.remove(msg_File)
  except OSError:
    pass
  

topic_ToSend[0] = msg_Topic
topic_ToSend[1] = msg_Topic
msg_ToSend[0] = pubTopic.clientID + " Cellular and MQTT Connected!"
msg_ToSend[1] = pubTopic.clientID + " Time Sync Completed!"
missed_Obs = 2

#Pull pending topic/msg from log files
try:
    log = uio.open(topic_File)
    log.close()
    files_Exist = True
except OSError:
    files_Exist = False
    pass
  
if files_Exist == True:
  readFiles()
else:
  createFiles()
  
fw_version = hex(xbee.atcmd("VR"))
conn = network.Cellular()
while not conn.isconnected():
  read_teensy()
  time.sleep(10)
  print("1")
  if (payload_Topic != ""):
    publishBackup(topic = payload_Topic)
while (utime.localtime()[4]%5) != 0:
  time.sleep(10)
printLocalTime()
wdt = machine.WDT(timeout=60000, response=machine.SOFT_RESET)
xbee_debug("Starting", "")

while True:
  wdt.feed()
  read_teensy()
  if payload_Topic != "":
    if conn.isconnected():
      publish(topic = payload_Topic)
    else:
      publishBackup(topic = payload_Topic)
  if (missed_Obs > 0):
    publish_missedObs()      
  if ((utime.localtime()[4]%15) == 0) and timeUpdated == False:
    printLocalTime()
    timeUpdated = True
  if (timeUpdated == True) and ((utime.localtime()[4]%15) != 0):
    timeUpdated = False    
  time.sleep(0.200)
  
