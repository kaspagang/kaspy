from kaspy.client import kaspa_client

'''If you run this a thousand times it will eventually work... I promise'''

command = 'getPeerAddressesRequest'
payload = {}

client = kaspa_client()
client.auto_connect()
resp = client.request(command=command, payload=payload)
print(resp)