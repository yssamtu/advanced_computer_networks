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

from ryu.base import app_manager
from ryu.controller import mac_to_port
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.mac import haddr_to_bin
from ryu.lib.packet import packet
from ryu.lib.packet import ipv4
from ryu.lib.packet import arp
from ryu.lib.packet import ether_types
from ryu.lib.packet import ethernet
from ryu.topology import event, switches
from ryu.topology.api import get_switch, get_link
from ryu.app.wsgi import ControllerBase

import topo


class FTRouter(app_manager.RyuApp):

    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(FTRouter, self).__init__(*args, **kwargs)
        self.topo_net = topo.Fattree(4)
        self.mac_to_port = mac_to_port.MacToPortTable()
        self.dpid_to_node = {}
        self.ip_to_dpid = {}
        self.outport_to_ip = {}

    # Topology discovery
    @set_ev_cls(event.EventSwitchEnter)
    def get_topology_data(self, ev):
        # Switches and links in the network
        self.switches = get_switch(self, None)
        # self.links = get_link(self, None)
        # setup dpid_to_node and ip_to_dpid
        for switch in self.switches:
            switch_info = switch.to_dict()
            dpid = int(switch_info["dpid"], base=16)
            # just choose the first one
            switch_name = switch_info["ports"][0]["name"]
            for topo_switch in self.topo_net.switches:
                if switch_name.startswith(topo_switch.id):
                    self.dpid_to_node[dpid] = topo_switch
                    self.ip_to_dpid[topo_switch.ip_addr] = dpid
                    break
        # print(self.dpid_to_node)
        # setup outport to ip
        try:
            for switch in self.switches:
                switch_info = switch.to_dict()
                dpid = int(switch_info["dpid"], base=16)
                self.outport_to_ip[dpid] = {}
                links = get_link(self, dpid)
                for link in links:
                    self.outport_to_ip[dpid][link.src.port_no] = self.dpid_to_node[
                        link.dst.dpid
                    ].ip_addr
            self.setup_two_level_routing()
        except:
            pass

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # Install entry-miss flow entry
        match = parser.OFPMatch()
        actions = [
            parser.OFPActionOutput(ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER)
        ]
        self.add_flow(datapath, 0, match, actions)

    def setup_two_level_routing(self):
        # setup edge switch rule (lower port rule already setup during arp)
        for switch in self.topo_net.edge_switches:
            dpid = self.ip_to_dpid[switch.ip_addr]
            datapath = get_switch(self, dpid)[0].dp
            parser = datapath.ofproto_parser
            for cnt, outport in enumerate(self._get_upper_ports(dpid)):
                # it dosen't matter which outport it match
                host_id = 2 + cnt
                match = parser.OFPMatch(
                    eth_type=ether_types.ETH_TYPE_IP,
                    ipv4_dst=(f"0.0.0.{host_id}", "0.0.0.255"),
                )
                actions = [parser.OFPActionOutput(outport)]
                self.add_flow(datapath, 1, match, actions)
        # setup aggregate switch rule
        for switch in self.topo_net.aggr_switches:
            # need to get lower node port and IP
            dpid = self.ip_to_dpid[switch.ip_addr]
            datapath = get_switch(self, dpid)[0].dp
            parser = datapath.ofproto_parser
            for outport in self._get_lower_ports(dpid):
                next_hop_ip = self.outport_to_ip[dpid][outport]
                match = parser.OFPMatch(
                    eth_type=ether_types.ETH_TYPE_IP,
                    ipv4_dst=(next_hop_ip, "255.255.255.0"),
                )
                actions = [parser.OFPActionOutput(outport)]
                self.add_flow(datapath, 2, match, actions)
            for cnt, outport in enumerate(self._get_upper_ports(dpid)):
                # it dosen't matter which outport it match
                host_id = 2 + cnt
                match = parser.OFPMatch(
                    eth_type=ether_types.ETH_TYPE_IP,
                    ipv4_dst=(f"0.0.0.{host_id}", "0.0.0.255"),
                )
                actions = [parser.OFPActionOutput(outport)]
                self.add_flow(datapath, 1, match, actions)
        # setup core switch rule
        for switch in self.topo_net.core_switches:
            dpid = self.ip_to_dpid[switch.ip_addr]
            datapath = get_switch(self, dpid)[0].dp
            parser = datapath.ofproto_parser
            for outport in self._get_lower_ports(dpid):
                next_hop_ip = self.outport_to_ip[dpid][outport]
                match = parser.OFPMatch(
                    eth_type=ether_types.ETH_TYPE_IP,
                    ipv4_dst=(next_hop_ip, "255.255.0.0"),
                )
                actions = [parser.OFPActionOutput(outport)]
                self.add_flow(datapath, 1, match, actions)

    # Add a flow entry to the flow-table
    def add_flow(self, datapath, priority, match, actions):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # Construct flow_mod message and send it
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        mod = parser.OFPFlowMod(
            datapath=datapath, priority=priority, match=match, instructions=inst
        )
        datapath.send_msg(mod)

    def _is_from_upper_port(self, dpid, in_port):

        if in_port in self._get_upper_ports(dpid):
            return True
        else:
            return False

    def _get_upper_ports(self, dpid):
        ports = []
        links = get_link(self, dpid)
        receiver_type = self.dpid_to_node[dpid].type
        for link in links:
            sender_dpid = link.dst.dpid
            sender_type = self.dpid_to_node[sender_dpid].type
            if receiver_type == "es":
                if sender_type == "as" or sender_type == "cs":
                    ports.append(link.src.port_no)
            elif receiver_type == "as":
                if sender_type == "cs":
                    ports.append(link.src.port_no)
        return ports

    def _get_lower_ports(self, dpid):
        # lower port might connect to host, so cannot use get_link to get
        # because get_link would not show the connection with host
        ports = []
        switch = get_switch(self, dpid)
        upper_port = self._get_upper_ports(dpid)
        for port in switch[0].ports:
            if port.port_no not in upper_port:
                ports.append(port.port_no)

        return ports

    def _get_flood_ports(self, dpid, in_port):
        switch_type = self.dpid_to_node[dpid].type
        ports = []
        if switch_type == "cs":
            ports.extend(self._get_lower_ports(dpid))
            ports.remove(in_port)
            # print("flood to lower: ", ports)
        else:
            if self._is_from_upper_port(dpid, in_port):
                ports = self._get_lower_ports(dpid)
            else:
                ports.extend(self._get_lower_ports(dpid))
                ports.remove(in_port)
                # choose first upper link to flood (maybe random would be better)
                ports.append(self._get_upper_ports(dpid)[0])

        return ports

    def _is_es(self, dpid):
        return self.dpid_to_node[dpid].type == "es"

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        dpid = datapath.id
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match["in_port"]
        pkt = packet.Packet(msg.data)

        arp_pkt = pkt.get_protocol(arp.arp)
        if arp_pkt:
            # add ip rule if it is edge switch and from lower
            if self._is_es(dpid) and not self._is_from_upper_port(dpid, in_port):
                # # by arp pkt, we can know which port connect to which host
                # # 0x0800 means ipv4, 0x0806 means arp package
                match = parser.OFPMatch(
                    eth_type=ether_types.ETH_TYPE_IP, ipv4_dst=arp_pkt.src_ip
                )
                actions = [parser.OFPActionOutput(in_port)]
                self.add_flow(datapath, 2, match, actions)

            # add mac address to port to table
            actions = []
            eth = pkt.get_protocol(ethernet.ethernet)
            mac_src = eth.src
            mac_dst = eth.dst
            self.mac_to_port.dpid_add(dpid)
            self.mac_to_port.port_add(dpid, in_port, haddr_to_bin(mac_src))

            # if found the out_port
            out_port = self.mac_to_port.port_get(dpid, haddr_to_bin(mac_dst))
            if out_port:
                actions.append(parser.OFPActionOutput(out_port))
            else:
                flood_ports = self._get_flood_ports(dpid, in_port)
                # flood out the arp request
                for out_port in flood_ports:
                    actions.append(parser.OFPActionOutput(out_port))

            out = parser.OFPPacketOut(
                datapath=datapath,
                in_port=in_port,
                actions=actions,
                buffer_id=datapath.ofproto.OFP_NO_BUFFER,
                data=msg.data,
            )
            datapath.send_msg(out)
