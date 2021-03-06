import time
import sys

class pubTopic:
  #-----topics
  
  SUB_TOPIC = "NWS/ALL/ALL/COOP/ALL/COMMAND"
  COMMAND_TOPIC = "NWS/CRH/MPX/COOP/ZBRM5/COMMAND"
  TEMP_PUB_TOPIC = "NWS/CRH/MPX/COOP/ZBRM5/TEMP"
  PRECIP_PUB_TOPIC = "NWS/CRH/MPX/COOP/ZBRM5/PRECIP"
  DAILY_PUB_TOPIC = "NWS/CRH/MPX/COOP/ZBRM5/DAILY"
  MESSAGE_TOPIC = "NWS/CRH/MPX/COOP/ZBRM5/MSG"
  UPDATE_TOPIC = "NWS/CRH/MPX/COOP/ZBRM5/UPDATE"
  ALERT_TOPIC = "NWS/CRH/MPX/COOP/ZBRM5/ALERT"
  clientID = "ZBRM5"
  clientTZ = "-6"
  server_Address = "sftp.crh.noaa.gov"
