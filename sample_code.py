import time

from kaspy.kaspa_clients import RPCClient
    
#Initialize a client instance
client = RPCClient() 
    
#Connect to a predefined host

'''client.connect(host='<ip>', port='<port>')'''
    
    #OR
    
#Connect to a a publicaly broadcasted node from the dns_seed_servers.
client.auto_connect(utxoindex=True, min_kaspad_version='0.12.2')
#define the command you want to send
command = 'getCoinSupplyRequest'
payload = {} #in our case we don't need to send additional information 

#send the request to the server and retrive the response
resp  = client.request(command=command, payload=payload, timeout=20)

print(resp) # print response

command = 'notifyVirtualSelectedParentBlueScoreChangedRequest'

payload = {}

def callback_func(notification : dict): # create a callback function to process the notifications
    print(notification)

#send the request to the server and retrive the response
resp  = client.subscribe(command=command, payload=payload, callback=callback_func)

time.sleep(7) # do stuff i.e. allow some time to gather notifications

client.unsubscribe(command) #unsubscribe to the stream

client.disconnect() # finishes sending all requests and responses in Que, halts all operations, but keeps the channel open.

client.close() # closes the channel completely