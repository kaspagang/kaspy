from logging import getLogger, basicConfig, INFO
import threading

from ..defines import MAINNET, log_messages as lm
from .node import Node, query_node
from ..settings import default_port, sub_networks, kaspad_version
 #import SOCK_STREAM, socket

import random
import time
from threading import Thread, Lock

basicConfig(level=INFO)
LOG = getLogger('[KASPA_NET]')

class kaspa_network:
    
    default_port = default_port
    current_kaspa_version = kaspad_version
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
    
    def __init__(self, sub_networks=sub_networks, min_kaspa_version=current_kaspa_version, scan_interval=60, max_nodes=64):
        
        # ensure we don't put too much stress on the network
        assert scan_interval >= 60
        assert max_nodes < 1024 
        
        self.scan_interval = scan_interval
        self.max_nodes = max_nodes
        
        self.sub_networks = sub_networks
        self.min_kaspa_version = min_kaspa_version
        
        self.addresses = list()
        
        self.lock = Lock()
        
        self.populate_nodes()
        threading.Timer(scan_interval, self._scan).start()

    def _check_validity(self, node : Node):
        if isinstance(node.network, type(None)) or node.network not in self.sub_networks:
            LOG.info(lm.DISSALLOWED_NETWORK_ABORT(node, node.network, self.sub_networks))
            return False
        elif isinstance(node.version, type(None)) or node.version < self.min_kaspa_version:
            LOG.info(lm.OLD_VERSION_ABORT(node, node.version, self.min_kaspa_version))
            return False
        else:
            LOG.info(lm.PASSED_VALIDITY_CHECKS(node, node.version, node.network))
            return True
    
    def retrive_valid_node(self) -> Node:
        self.lock.acquire()
        return next(self._yield_valid_node())

            
    def _yield_valid_node(self) -> Node:
        for addr in self.addresses:
            if query_node.is_port_open(*addr.rsplit(':', 1), 0.5):
                node = Node(addr)
                node.version = query_node.version(node)#, 2)
                node.network = query_node.network(node, 2)
                if self._check_validity(node):
                    LOG.info(lm.RETRIVED_NODE(node.ip, node.port))
                    self.lock.release()
                    yield node
        self._yield_valid_node()
    
    def populate_nodes(self):
        addresses = set()
        LOG.info(lm.SCANNING_FOR_NODES)
        for dns_server in self.dns_seed_servers:
            LOG.info(lm.FINDING_NODES(dns_server))
            peers = query_node.connected_peers(dns_server, default_port)
            if peers:
                LOG.info(lm.FOUND_NODES(dns_server, set(peers) - addresses))
                addresses.update(peers)
        self.lock.acquire()
        self.addresses = random.choices(list(addresses), k=len(addresses))
        self.lock.release()
    
    def _scan(self):
        while True:
            time.sleep(self.scan_interval)
            self.populate_nodes()

KaspaNetwork = kaspa_network()