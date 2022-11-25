# This code is part of the Advanced Computer Networks course at Vrije
# Universiteit Amsterdam.

# Licensed under the Apache License, Version 2.0 (the "License"); you may not
# use this file except in compliance with the License. You may obtain a copy
# of the License at

#   http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import sys
import random
import queue

# Class for an edge in the graph
class Edge:
    def __init__(self, lnode=None, rnode=None):
        self.lnode = lnode
        self.rnode = rnode

    def remove(self):
        self.lnode.edges.remove(self)
        self.rnode.edges.remove(self)
        self.lnode = None
        self.rnode = None


# Class for a node in the graph
class Node:
    def __init__(self, id, type, ip_addr):
        self.edges = []
        self.id = id
        self.type = type
        self.ip_addr = ip_addr

    # Add an edge connected to another node
    def add_edge(self, node):
        edge = Edge()
        edge.lnode = self
        edge.rnode = node
        self.edges.append(edge)
        node.edges.append(edge)
        return edge

    # Remove an edge from the node
    def remove_edge(self, edge):
        self.edges.remove(edge)

    # Decide if another node is a neighbor
    def is_neighbor(self, node):
        for edge in self.edges:
            if edge.lnode == node or edge.rnode == node:
                return True
        return False


class Fattree:
    def __init__(self, num_ports):
        # k pod
        self.k = num_ports
        self.servers = []
        self.switches = []
        self.edge_switches = []
        self.aggr_switches = []
        self.core_switches = []
        self.generate(num_ports)

    def generate(self, num_ports):
        # add core_switch to switches
        core_switches = self._generate_core_switch()
        for cs_row in core_switches:
            self.switches.extend(cs_row)
            self.core_switches.extend(cs_row)

        # create pod and link host and core switch
        for pod_id in range(self.k):
            # create pod switch
            upper_layer, lower_layer = self._generate_pod(pod_id)
            # create host
            host = self._generate_host(pod_id)

            # link upper pod switch and core switch
            for cs_row_id, cs_row in enumerate(core_switches):
                for cs in cs_row:
                    cs.add_edge(upper_layer[cs_row_id])
            # link lower pod switch and host
            for host_group_id, ps in enumerate(lower_layer):
                for h in host[host_group_id]:
                    ps.add_edge(h)

            # add pod_switch to switches
            self.switches.extend(upper_layer)
            self.switches.extend(lower_layer)
            # add host to servers
            for host_group in host:
                self.servers.extend(host_group)
            # add edge_switch to edge_switches
            self.edge_switches.extend(lower_layer)
            self.aggr_switches.extend(upper_layer)

    def _generate_core_switch(self):
        # (k/2)*(k/2) core nodes matrix
        core_switch = []
        for j in range(1, self.k // 2 + 1):
            cs_row = []
            for i in range(1, self.k // 2 + 1):
                cs_row.append(
                    Node(
                        # 10.k.j.i
                        id=f"cs{self.k}{j}{i}",
                        type="cs",
                        ip_addr=f"10.{self.k}.{j}.{i}"
                    )
                )
            core_switch.append(cs_row)
        return core_switch

    def _generate_pod(self, pod_id):
        upper_layer = []
        lower_layer = []
        for s in range(self.k):
            if s < self.k // 2:
                switch = Node(
                    # 10.pod.switch.1
                    id=f"es{pod_id}{s}",
                    type="es",
                    ip_addr=f"10.{pod_id}.{s}.1"
                )
                lower_layer.append(switch)
            else:
                switch = Node(
                    # 10.pod.switch.1
                    id=f"as{pod_id}{s}",
                    type="as",
                    ip_addr=f"10.{pod_id}.{s}.1"
                )
                upper_layer.append(switch)

        # link upper and lower layer
        for i in range(self.k // 2):
            for j in range(self.k // 2):
                upper_layer[i].add_edge(lower_layer[j])

        return upper_layer, lower_layer

    def _generate_host(self, pod_id):
        host = []
        for s in range(self.k // 2):
            host_group = []
            for id in range(2, self.k // 2 + 2):
                host_group.append(
                    Node(
                        # 10.pod.switch.ID
                        id=f"h{pod_id}{s}{id}",
                        type="h",
                        ip_addr=f"10.{pod_id}.{s}.{id}"
                    )
                )
            host.append(host_group)

        return host
