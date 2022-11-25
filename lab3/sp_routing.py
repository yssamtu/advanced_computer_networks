# This code is part of the Advanced Computer Networks (2020) course at Vrije 
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

#!/usr/bin/env python3

from ryu.base.app_manager import RyuApp
from ryu.controller.ofp_event import EventOFPSwitchFeatures, EventOFPPacketIn
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, set_ev_cls
from ryu.ofproto.ofproto_v1_3 import OFP_VERSION
from ryu.lib.packet.packet import Packet
from ryu.lib.packet.arp import arp
from ryu.lib.packet.ether_types import ETH_TYPE_IP

from ryu.topology.event import EventSwitchEnter
from ryu.topology.api import get_switch, get_link

from topo import Fattree
from dijkstra import Dijkstra

class SPRouter(RyuApp):

    OFP_VERSIONS = [OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(SPRouter, self).__init__(*args, **kwargs)
        self.topo_net = Fattree(4)
        self.ip_to_port = {}
        self.ip_to_dpid = {}
        self.dpid_to_node = {}
        self.dijkstra_fattree = Dijkstra(self.topo_net.switches, self.topo_net.edge_switches)

    # Topology discovery
    @set_ev_cls(EventSwitchEnter)
    def get_topology_data(self, ev):
        # Switches and links in the network
        switches = get_switch(self, None)
        for switch in switches:
            dpid = switch.dp.id
            # just choose the first one
            switch_name = switch.ports[0].name.decode("utf-8")
            for topo_switch in self.topo_net.switches:
                if switch_name.startswith(topo_switch.id):
                    self.dpid_to_node[dpid] = topo_switch

    @set_ev_cls(EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        # Install entry-miss flow entry
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                          ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(datapath, 0, match, actions)

    # Add a flow entry to the flow-table
    def add_flow(self, datapath, priority, match, actions):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        # Construct flow_mod message and send it
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
                                match=match, instructions=inst)
        datapath.send_msg(mod)
    
    def _get_upper_ports(self, dpid):
        links = get_link(self, dpid)
        receiver_type = self.dpid_to_node[dpid].type
        if receiver_type == "es":
            return {link.src.port_no for link in links if self.dpid_to_node[link.dst.dpid].type != "h"}
        elif receiver_type == "as":
            return {link.src.port_no for link in links if self.dpid_to_node[link.dst.dpid].type == "cs"}
        else:
            return set()

    def _get_lower_ports(self, dpid):
        # lower port might connect to host, so cannot use get_link to get
        # because get_link would not show the connection with host
        switch = get_switch(self, dpid)[0]
        upper_port = self._get_upper_ports(dpid)
        return {port.port_no for port in switch.ports if port.port_no not in upper_port}

    def _is_from_upper_port(self, dpid, in_port):
        return in_port in self._get_upper_ports(dpid)

    def _get_all_ports(self, dpid):
        switch = get_switch(self, dpid)[0]
        return {port.port_no for port in switch.ports}

    def _get_paths(self, src_dpid):
        start_node = self.dpid_to_node[src_dpid]
        return [self.dijkstra_fattree.get_path(start_node, node) 
                for node in self.topo_net.edge_switches
                if node is not start_node]

    def _get_next_nodes(self, dpid, src_ip):
        start_node = self.dpid_to_node[dpid]
        paths = self._get_paths(self.ip_to_dpid[src_ip])
        next_nodes = set()
        for path in paths:
            if start_node in path:
                index = path.index(start_node) + 1
                if index < len(path):
                    next_nodes.add(path[index])
        return next_nodes

    def _get_next_ports(self, dpid, src_ip, is_from_upper_port):
        dpids = tuple(self.dpid_to_node.keys())
        nodes = tuple(self.dpid_to_node.values())
        next_nodes = self._get_next_nodes(dpid, src_ip)
        next_dpids = {dpids[nodes.index(next_node)] for next_node in next_nodes}
        links = get_link(self, dpid)
        next_ports = {link.src.port_no for link in links if link.dst.dpid in next_dpids}
        if is_from_upper_port:
            next_ports.intersection_update(self._get_lower_ports(dpid))
        return next_ports

    def _get_flood_ports(self, dpid, in_port, src_ip):
        is_from_upper_port = self._is_from_upper_port(dpid, in_port)
        next_ports = self._get_next_ports(dpid, src_ip, is_from_upper_port)
        if self.dpid_to_node[dpid].type == "es":
            next_ports.update(self._get_lower_ports(dpid))
            if not self._is_from_upper_port(dpid, in_port):
                next_ports.remove(in_port)
        return next_ports
    
    def _is_es(self, dpid):
        return self.dpid_to_node[dpid].type == "es"
    
    @set_ev_cls(EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        dpid = datapath.id
        buffer_id = datapath.ofproto.OFP_NO_BUFFER
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']
        pkt = Packet(msg.data)
        arp_pkt = pkt.get_protocol(arp)
        if arp_pkt:
            self.ip_to_dpid.setdefault(arp_pkt.src_ip, dpid)
            # by arp pkt, we can know which port connect to which host
            actions = []
            self.ip_to_port.setdefault(dpid, {})
            match = parser.OFPMatch(eth_type=ETH_TYPE_IP, ipv4_dst=arp_pkt.src_ip)
            actions = [parser.OFPActionOutput(in_port)]
            self.add_flow(datapath, 1, match, actions)
            self.ip_to_port[dpid].setdefault(arp_pkt.src_ip, in_port)
            out_port = self.ip_to_port[dpid].get(arp_pkt.dst_ip)
            if out_port:
                actions.append(parser.OFPActionOutput(out_port))
            else:
                flood_ports = self._get_flood_ports(dpid, in_port, arp_pkt.src_ip)
                for out_port in flood_ports:
                    actions.append(parser.OFPActionOutput(out_port))
            out = parser.OFPPacketOut(
                datapath=datapath,
                in_port=in_port,
                actions=actions,
                buffer_id=buffer_id,
                data=msg.data
            )
            datapath.send_msg(out)
