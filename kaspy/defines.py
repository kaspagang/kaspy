from .utils.version_comparer import version as ver



#### KASPAD defines #####

# Available services:
RPC_SERVICE = 'RPC' # use _SERVICE suffix, RPC is defined in kaspy.proros.messages_pb_grpc.py
P2P_SERVICE = 'P2P' # use _SERVICE suffix, P2P is defined in kaspy.proros.messages_pb_grpc.py


# Subnetworks:

## Subnetwork names:
MAINNET = 'mainnet'
TESTNET = 'testnet'
DEVNET = NotImplemented # need to find default ports
SIMNET = NotImplemented # need to find default ports

## Default ports for services:
RPC_DEF_PORTS = {
     MAINNET : 16110,
     TESTNET : 16210, 
 #    DEVNET : NotImplemented,
  #   SIMNET : NotImplemented
}

P2P_DEF_PORTS = {
     MAINNET : 16111,
     TESTNET : 16211, 
     DEVNET : NotImplemented,
     SIMNET : NotImplemented
}


## Available subnetworks:
SUBNETWORKS = (MAINNET, TESTNET, DEVNET, SIMNET) #Devnet and Simnet are NotImplmented

# Kaspad, latest version:
LATEST_KASPAD_VERSION = ver(0, 11, 9)

#### PORT defines #####

# PORT defines:
OPEN = 'open'
CLOSED = 'closed'