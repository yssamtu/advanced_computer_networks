 # This code is part of the Advanced Computer Networks (ACN) course at VU 
# Amsterdam.
#
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


from mininet.topo import Topo
from mininet.link import TCLink
from mininet.node import OVSKernelSwitch


class BridgeTopo(Topo):
    "Creat a bridge-like customized network topology."

    def __init__(self):

        Topo.__init__(self)

        # TODO: add nodes and links to construct the topology
        h1 = self.addHost('h1')
        h2 = self.addHost('h2')
        h3 = self.addHost('h3')
        h4 = self.addHost('h4')
        s1 = self.addSwitch('s1')
        s2 = self.addSwitch('s2')

        self.addLink(h1, s1)
        self.addLink(h2, s1)
        self.addLink(s1, s2)
        self.addLink(s2, h3)
        self.addLink(s2, h4)

topos = {'bridge': (lambda: BridgeTopo())}
