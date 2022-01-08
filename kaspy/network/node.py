from logging import getLogger, basicConfig, INFO
import socket
import time

from ..defines import log_messages as lm, RPC_DEF_PORT

basicConfig(level=INFO)
LOG = getLogger('[KASPA_NOD]')


class query_node:
    '''some socket things to navigate and check connectivity'''
    
    @classmethod
    def port_open(cls, ip, port, timeout):
        sock = socket.socket(socket.AF_INET, socket. SOCK_STREAM)
        sock.settimeout(timeout)
        try:
            if sock.connect_ex((ip, int(port))) == 0:
                LOG.info(lm.PORT_OPEN(f'{ip}:{port}'))
                port_open = True
            else:
                LOG.info(lm.PORT_CLOSED(f'{ip}:{port}'))
                port_open = False
        except Exception as e:
            LOG.debug(e)
            LOG.info(lm.PORT_CLOSED(f'{ip}:{port}'))
            port_open = False
        finally: sock.close()
        return port_open
    
    @classmethod
    def latency(cls, ip, port, timeout):
        sock = socket.socket(socket.AF_INET, socket. SOCK_STREAM)
        sock.settimeout(timeout)
        try:
            start = time.perf_counter()
            sock.connect((ip, int(port)))
            latency = time.perf_counter() - start
            LOG.info(lm.LATENCY(f'{ip}:{port}', latency))
        except Exception as e:
            LOG.debug(e)
            latency= None
        finally: sock.close()
        return latency            
    
    @classmethod
    def connected_peers(cls, ip, port):
        try:
            return set([f'{addr[-1][0]}:{port}' for addr in socket.getaddrinfo(host=ip, port=port)])
        except Exception as e:
            LOG.debug(e)
            return None

class Node:
    
    def __init__(self, addr: str) -> None:
        self.ip, self.port = addr.rsplit(':', 1)
        self.addr = addr
    
    def rp2_enabled(self):
        raise NotImplementedError
    
    def p2p_enabled(self):
        raise NotImplementedError
    
    def port_open(self, timeout, service=NotImplemented):
        return query_node.port_open(self.ip, self.port, timeout)
    
    def latency(self, timeout, service=NotImplemented):
        return query_node.latency(self.ip, self.port, timeout)
    
    def __str__(self):
        return self.addr
    
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
    def yield_open_nodes(cls, max_latency, timeout, service = NotImplemented) -> Node:
        LOG.info(lm.SCANNING_FOR_NODES)
        while True:
            scanned = set()
            for dns_server in cls.dns_seed_servers:
                addresses = query_node.connected_peers(ip=dns_server, port=RPC_DEF_PORT) - scanned
                if not addresses: continue
                for addr in addresses:
                    node = Node(addr)
                    LOG.info(lm.RETRIVED_NODE(node.ip, node.port))
                    LOG.info(lm.CHECK_NODE(node))
                    scanned.add(node.addr)
                    latency, port_open = node.latency(timeout), node.port_open(timeout)
                    if latency and port_open and latency <= max_latency:
                        yield node