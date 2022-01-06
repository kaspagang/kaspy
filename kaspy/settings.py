from .utils.version_control import version as ver
from .defines import *
from requests import get
import os

default_port = 16110
kaspad_version = ver(0, 11, 9)
sub_networks = (MAINNET,)
os.environ['GRPC_DNS_RESOLVER']='ares' #solves some connection issues, see : https://github.com/grpc/grpc/issues/19954