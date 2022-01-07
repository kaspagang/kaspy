from logging import DEBUG, getLogger, basicConfig, INFO

from kaspy.exceptions.exceptions import ResponseAsNoneType


from ..protos.messages_pb2 import KaspadMessage
from ..protos.messages_pb2_grpc import RPCStub

from ..defines import log_messages as lm
from ..utils.version_control import version as ver

import grpc
import socket
import json
import time

from google.protobuf import json_format


basicConfig(level=DEBUG)
basicConfig(level=INFO)
LOG = getLogger('[KASPA_NET]')
            
class Node():
    
    def __init__(self, addr: str) -> None:
        self.ip, self.port = addr.rsplit(':', 1)
        self.addr = addr
    
    def __str__(self):
        return self.addr
