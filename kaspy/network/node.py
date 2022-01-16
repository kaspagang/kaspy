from logging import getLogger, basicConfig, INFO
from typing import Set, Union, Iterator
import socket
import time
from kaspy.log_handler.log_messages import network as net_lm
from kaspy.defines import MAINNET, P2P_DEF_PORTS, RPC_DEF_PORTS

#basicConfig(level=INFO)
LOG = getLogger('[KASPA_NOD]')

UNKNOWEN = 'unknown'

class query_node:
    '''some socket things to navigate and check connectivity'''
    
    @classmethod
    def port_open(cls, ip : str, port : Union[int, str], timeout: float) -> Union[float, None]:
        LOG.info(net_lm.LATENCY_QUERY(f'{ip}:{port}'))
        sock = socket.socket(socket.AF_INET, socket. SOCK_STREAM)
        sock.settimeout(timeout)
        try:
            start = time.perf_counter()
            sock.connect((ip, int(port)))
            latency = time.perf_counter() - start
            LOG.info(net_lm.CHECK_LATENCY_STATUS_DELAY(f'{ip}:{port}', latency))
        except Exception as e:
            LOG.debug(e)
            LOG.info(net_lm.CHECK_LATENCY_STAUTS_NONE(f'{ip}:{port}'))
            latency= None
        finally: sock.close()
        return latency            
    
    @classmethod
    def connected_peers(cls, ip : str, port : Union[str, int]) -> Union[Set[str], None]:
        try:
            return set([f'{addr[-1][0]}:{port}' for addr in socket.getaddrinfo(host=ip, port=int(port))])
        except Exception as e:
            LOG.debug(e)
            return None

class Node:
    
    def __init__(self, ip: str, port: Union[str, int]) -> None:
        self.ip = ip 
        self.port = port
        self.network = UNKNOWEN
        self.version = UNKNOWEN
        self.protocol = UNKNOWEN
    
    def port_open(self, timeout :float) -> bool:
        return bool(self.latency(timeout))
    
    def latency(self, timeout :float):
        return query_node.port_open(self.ip, self.port, timeout)
    
    def __hash__(self) -> int:
        return hash(f'{self}')
    
    def __str__(self) -> str:
        return f'{self.ip}:{self.port}' #keep for comaptibility with client class until dual RPC and P2P connections are dealt with
    
class node_acquirer:
    
    dns_seed_servers = [
        f"mainnet-dnsseed.daglabs-dev.com",
        f"mainnet-dnsseed-1.kaspanet.org",
        f"mainnet-dnsseed-2.kaspanet.org",
        f"dnsseed.cbytensky.org",
        f"seeder1.kaspad.net",
        f"seeder2.kaspad.net",
        f"seeder3.kaspad.net",
        f"seeder4.kaspad.net",
        f"kaspadns.kaspacalc.net"
    ]
    
    @classmethod
    def yield_open_nodes(cls, port: Union[str, int]) -> Iterator[Node]:
        LOG.info(net_lm.SCANNING)
        while True:
            scanned = set()
            for dns_server in cls.dns_seed_servers:
                addresses = query_node.connected_peers(ip=dns_server, port=RPC_DEF_PORTS[MAINNET]) - scanned
                LOG.info(net_lm.SCANNING_RETRIVED_NODES_FROM(dns_server, addresses))
                if not addresses: continue
                for addr in addresses:
                    node = Node(*addr.rsplit(':', 1))
                    LOG.info(net_lm.CHECK_NODE(node))
                    if node in scanned: continue
                    scanned.add(node)
                    yield node
