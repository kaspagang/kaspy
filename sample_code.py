from kaspy.client import kaspa_client

command = 'getPeerAddressesRequest' 
payload = {}

client = kaspa_client()
client.auto_connect() #may take a while 
resp = client.request(command=command, payload=payload)
client.disconnect()
print(resp)
