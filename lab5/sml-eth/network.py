from lib import config
from p4app import P4Mininet
from os import environ
from pathlib import PurePath
from mininet.cli import CLI
from mininet.topo import Topo
from config import NUM_WORKERS


class SMLTopo(Topo):
    def __init__(self, **opts):
        Topo.__init__(self, **opts)
        # add host and add link

    def build(self):
        switch = self.addSwitch("s1")
        for i in range(NUM_WORKERS):
            host = self.addHost(f"w{i}", mac=f"08:00:00:00:0{i+1}:11")
            self.addLink(switch, host)


def RunWorkers(net):
    """
    Starts the workers and waits for their completion.
    Redirects output to logs/<worker_name>.log (see lib/worker.py, Log())
    This function assumes worker i is named 'w<i>'. Feel free to modify it
    if your naming scheme is different
    """
    def worker(rank):
        return f"w{rank}"

    def log_file(rank):
        return PurePath(environ["APP_LOGS"]).joinpath(f"{worker(rank)}.log")

    for i in range(NUM_WORKERS):
        net.get(worker(i)).sendCmd(f"python worker.py {i} > {log_file(i)}")
    for i in range(NUM_WORKERS):
        net.get(worker(i)).waitOutput()


def RunControlPlane(net):
    """
    One-time control plane configuration
    """
    # like insert table entry
    switch = net.switches[0]
    # the ports is {<Intf lo>: 0, <Intf s1-eth1>: 1, <Intf s1-eth2>: 2}
    ports = [value
             for key, value in switch.ports.items()
             if key.name.startswith(switch.name)]
    switch.addMulticastGroup(mgid=1, ports=ports)


topo = SMLTopo()
net = P4Mininet(program="p4/main.p4", topo=topo)
net.run_control_plane = lambda: RunControlPlane(net)
net.run_workers = lambda: RunWorkers(net)
net.start()
net.run_control_plane()
CLI(net)
net.stop()
