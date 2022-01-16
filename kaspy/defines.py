from kaspy.utils.version_comparer import version as ver
from . import __version__, __name__

#### KASPAD defines #####

# Available services:
RPC_SERVICE = 'RPC' # use _SERVICE suffix, RPC is defined in kaspy.proros.messages_pb_grpc.py
P2P_SERVICE = 'P2P' # use _SERVICE suffix, P2P is defined in kaspy.proros.messages_pb_grpc.py


# Subnetworks:

## Subnetwork names:
MAINNET = 'mainnet'
TESTNET = 'testnet'
SIMNET = 'simnet'
DEVNET = 'devnet'

## Default ports for services:
RPC_DEF_PORTS = {
    MAINNET: 16110,
    TESTNET: 16210, 
    SIMNET: 16510,
    DEVNET: 16610,
}

P2P_DEF_PORTS = {
    MAINNET : 16111,
    TESTNET : 16211, 
    DEVNET : 16611,
    SIMNET : 16511
}


## Available subnetworks:
SUBNETWORKS = (MAINNET, TESTNET, DEVNET, SIMNET) #Devnet and Simnet are NotImplmented

# Kaspad, latest version:
LATEST_KASPAD_VERSION = ver(0, 11, 9)

LATEST_PROTOCOL_VERSION = ver(3,0,0)

#### For client #####

CONNECTED = 'connected' #connection is open for send / recv
DISCONNECTED = 'disconnected' # disables send / recv, waits for queued send / recv data to pass, keeps spin thread waiting in background for possible reconnection
CLOSED = 'closed' # terminates the connection immediatly, does not wait for queued data, kills spin thread. does not expect a reconnection attempt. 

ClIENT_STATES = (CONNECTED, DISCONNECTED, CLOSED) 

### for p2p usage, I think I need ###
USER_AGENT = f'{__version__} {__name__}'