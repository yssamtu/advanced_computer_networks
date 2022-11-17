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
    def __init__(self, id, type):
        self.edges = []
        self.id = id
        self.type = type

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


class Jellyfish:
    def __init__(self, num_servers, num_switches, num_ports):
        # number of port
        self.k = num_ports
        # number of switch
        self.n = num_switches
        # number of port connect to other switch ( n(k-r) >= num_server )
        self.r = int(self.k - num_servers / self.n)

        self.switches = [Node(id=id, type="switch") for id in range(self.n)]
        self.servers = [Node(id=id, type="host") for id in range(self.n, self.n + num_servers)]
        # still have free port to link or not stable
        self.unstable_switches = [s for s in self.switches]
        # no link can be add to this switch
        self.stable_switches = []
        self.generate(num_servers, num_switches, num_ports)

        # for count, sw in enumerate(self.stable_switches):
        #     print(count, sw.id)
        #     for ec, e in enumerate(sw.edges):
        #         print("\t", ec, e.lnode.id, e.rnode.id)

    def generate(self, num_servers, num_switches, num_ports):
        while 1:
            invalid_switch = None
            # no more unstable_switches
            if not self._link_random_pair():
                # check if any switch remains >=2 free port
                for s in self.stable_switches:
                    if self.r - len(s.edges) >= 2:
                        invalid_switch = s
                        self._move_to_unstable_switches(invalid_switch)
                        break
                if invalid_switch is None:
                    break
                # choose random edge to remove
                else:
                    random_sw = self.stable_switches[
                        random.randint(0, len(self.stable_switches) - 1)
                    ]
                    random_edge = random_sw.edges[
                        random.randint(0, len(random_sw.edges) - 1)
                    ]
                    # link invalid switch with two selected node
                    random_edge.lnode.add_edge(invalid_switch)
                    random_edge.rnode.add_edge(invalid_switch)
                    # remove selected node original edge
                    random_sw.remove_edge(random_edge)

        self._link_host_with_switch(num_servers)

    def _link_host_with_switch(self, num_servers):
        host_count = 0
        for _ in range(self.k - self.r):
            for switch in self.switches:
                switch.add_edge(self.servers[host_count])
                host_count += 1
                if host_count == num_servers:
                    return


    def _link_random_pair(self):
        # if only one left need remove and add
        while 1:
            # if no more unstable_switches, return False
            if not self.unstable_switches:
                return False
            s1 = self.unstable_switches[
                random.randint(0, len(self.unstable_switches) - 1)
            ]
            linkable_switches = self._get_linkable_switches(s1)
            # move switch to stable list if cannot link to anyone
            if linkable_switches:
                s2 = linkable_switches[random.randint(0, len(linkable_switches) - 1)]
                # print(s1.id, s2.id)
                s1.add_edge(s2)
                # check if no free port after add edge
                if len(s1.edges) == self.r:
                    self._move_to_stable_switches(s1)
                if len(s2.edges) == self.r:
                    self._move_to_stable_switches(s2)
                break
            else:
                self._move_to_stable_switches(s1)

        return True

    def _move_to_stable_switches(self, switch):
        self.unstable_switches.remove(switch)
        self.stable_switches.append(switch)

    def _move_to_unstable_switches(self, switch):
        self.stable_switches.remove(switch)
        self.unstable_switches.append(switch)

    def _get_linkable_switches(self, node):
        linkable_switches = []
        for s in self.unstable_switches:
            # not neighbor and still have free port
            if not node.is_neighbor(s):
                linkable_switches.append(s)
        return linkable_switches


class Fattree:
    def __init__(self, num_ports):
        # k pod
        self.k = num_ports
        self.servers = []
        self.switches = []
        self.generate(num_ports)

    def generate(self, num_ports):
        # create core switch
        core_switch = self._generate_core_switch()
        # add core_switch to switches
        for cs_row in core_switch:
            self.switches.extend(cs_row)

        # create pod and link host and core switch
        for pod_id in range(self.k):
            # create pod switch
            upper_layer, lower_layer = self._generate_pod(pod_id)
            # create host
            host = self._generate_host(pod_id)

            # link upper pod switch and core switch
            for cs_row_id, cs_row in enumerate(core_switch):
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

    def _generate_core_switch(self):
        # (k/2)*(k/2) core nodes matrix
        core_switch = []
        for j in range(1, self.k // 2 + 1):
            cs_row = []
            for i in range(1, self.k // 2 + 1):
                cs_row.append(
                    Node(
                        # 10.k.j.i
                        id=f"10.{self.k}.{j}.{i}",
                        type="core_switch",
                    )
                )
            core_switch.append(cs_row)
        return core_switch

    def _generate_pod(self, pod_id):
        upper_layer = []
        lower_layer = []
        for s in range(self.k):
            switch = Node(
                # 10.pod.switch.1
                id=f"10.{pod_id}.{s}.1",
                type="pod_switch",
            )
            if s < self.k // 2:
                lower_layer.append(switch)
            else:
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
                        id=f"10.{pod_id}.{s}.{id}",
                        type="host",
                    )
                )
            host.append(host_group)

        return host
