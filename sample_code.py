from kaspy.Kaspa_clients import RPCClient

command = 'getInfoRequest'
payload = {}

client = RPCClient()
client.auto_connect() #may take a while 
resp = client.request(command=command, payload=payload)
print(resp)
