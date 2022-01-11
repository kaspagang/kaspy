from kaspy.Kaspa_clients import RPCClient

command = 'getPeerAddressesRequest'
payload = {}

client = RPCClient()
client.auto_connect(min_kaspad_version='v.0.11.8') #may take a while 
resp = client.request(command=command, payload=payload)
print(resp)
