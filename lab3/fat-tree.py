# This code is part of the Advanced Computer Networks (ACN) course at VU 
# Amsterdam.

# Licensed under the Apache License, Version 2.0 (the "License"); you may not
# use this file except in compliance with the License. You may obtain a copy
# of the License at
#   http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

#!/usr/bin/env python3

# A dirty workaround to import topo.py from lab2

import os
import subprocess
import time

import mininet
import mininet.clean
from mininet.net import Mininet
from mininet.cli import CLI
from mininet.log import lg, info
from mininet.link import TCLink
from mininet.node import Node, OVSKernelSwitch, RemoteController
from mininet.topo import Topo
from mininet.util import waitListening, custom

import topo

class FattreeNet(Topo):
	"""
	Create a fat-tree network in Mininet
	"""

	def __init__(self, ft_topo):
		self.ft_topo = ft_topo
		Topo.__init__(self)
		

	def build(self):
		for switch in self.ft_topo.switches:
			self.addSwitch(switch.id)
		for host in self.ft_topo.servers:
			self.addHost(host.id, ip=f"{host.ip_addr}/8")
			
		for switch in self.ft_topo.switches:
			for edge in switch.edges:
				if edge.lnode.id == switch.id:
					s1 = edge.lnode
					s2 = edge.rnode
				else:
					s1 = edge.rnode
					s2 = edge.lnode
				# only add lower link
				if (s1.type == "as") and (s2.type == "cs"):
					continue
				elif (s1.type == "es") and (s2.type == "as"):
					continue

				self.addLink(s1.id, s2.id, bw=15, delay='5ms')

def make_mininet_instance(graph_topo):

	net_topo = FattreeNet(graph_topo)
	net = Mininet(topo=net_topo, controller=None, autoSetMacs=True)
	net.addController('c0', controller=RemoteController, ip="127.0.0.1", port=6653)
	return net

def run(graph_topo):
	
	# Run the Mininet CLI with a given topology
	lg.setLogLevel('info')
	mininet.clean.cleanup()
	net = make_mininet_instance(graph_topo)

	info('*** Starting network ***\n')
	net.start()
	info('*** Running CLI ***\n')
	CLI(net)
	info('*** Stopping network ***\n')
	net.stop()



ft_topo = topo.Fattree(4)
run(ft_topo)
