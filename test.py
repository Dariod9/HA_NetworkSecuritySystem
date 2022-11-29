import os
hostname = "192.168.122.1" #example
response = os.system("ping " + hostname)

#and then check the response...
if response == 0:
  print (hostname + ' is up!')
else:
  print (hostname + ' is down!')