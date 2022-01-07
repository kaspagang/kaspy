from logging import getLogger, basicConfig, INFO
import threading

from ..defines import DEFAULT_PORT, log_messages as lm
from .node import Node
import random
import time
import socket
from threading import Lock

basicConfig(level=INFO)
LOG = getLogger('[KASPA_NET]')

class query_node:
    '''some socket things to navigate and check connectivity'''   
    @staticmethod
    def is_port_open(ip, port, timeout):
        sck = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sck.settimeout(5)
        try:
            if sck.connect_ex((ip, int(port))) == 0:
                LOG.info(lm.PORT_OPEN(f'{ip}:{port}'))
                ret = True
            else:
                LOG.info(lm.PORT_CLOSED(f'{ip}:{port}'))
                ret = False
        except Exception as e:
            LOG.debug(e)
            LOG.info(lm.PORT_CLOSED(f'{ip}:{port}'))
            ret = False
        finally: sck.close()
        return ret

    
    @staticmethod
    def connected_peers(ip, port):
        try:
            return [f'{addr[-1][0]}:{port}' for addr in socket.getaddrinfo(host=ip, port=port)]
        except Exception as e:
            LOG.debug(e)
            return None

class kaspa_network(query_node):
    
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
    
    known_addresses = list()
    
    running = False
    scan_interval=60
    max_nodes=64
    
    locker = Lock()
    
    @classmethod
    def run(cls, scan_interval=scan_interval, max_nodes=max_nodes):
        if cls.running:
            raise Exception
        cls.scan_interval = scan_interval
        cls.max_nodes = max_nodes
        cls.running = True
        cls.populate_nodes()
        cls.scanner = threading.Timer(cls.scan_interval, cls.populate_nodes)
    
    @classmethod
    def shut_down(cls):
        cls.running = False
        cls.known_addresses = list()
        cls.scanner.cancel()
    
    @classmethod
    def populate_nodes(cls):
        addresses = set()
        LOG.info(lm.SCANNING_FOR_NODES)
        for dns_server in cls.dns_seed_servers:
            LOG.info(lm.FINDING_NODES(dns_server))
            peers = cls.connected_peers(dns_server, DEFAULT_PORT)
            if peers:
                LOG.info(lm.FOUND_NODES(dns_server, set(peers) - addresses))
                addresses.update(peers)
        cls.locker.acquire()
        cls.known_addresses = random.choices(list(addresses), k=len(addresses))
        cls.locker.release()
        
    @classmethod
    def yield_open_nodes(cls) -> Node:
        cls.locker.acquire()
        if cls.known_addresses:
            for addr in cls.known_addresses:
                if cls.is_port_open(*addr.rsplit(':', 1), 0.5):
                    node = Node(addr)
                    LOG.info(lm.RETRIVED_NODE(node.ip, node.port))
                    cls.locker.release()
                    yield node
                    cls.locker.acquire()
        else: 
            cls.locker.release()
            time.sleep(0.1)
        cls.yield_open_nodes()