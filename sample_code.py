from kaspy.client import kaspa_client

command = 'getInfoRequest'
payload = {}

client = kaspa_client()
client.auto_connect() #may take a while 
resp = client.request(command=command, payload=payload)
print(resp)
