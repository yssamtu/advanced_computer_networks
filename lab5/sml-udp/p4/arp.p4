#ifndef _ARP_H
#define _ARP_H

#include "headers.p4"

control ARP(inout headers hdr, inout standard_metadata_t standard_metadata) {
  action arp_reply(mac_addr_t sw_mac_addr){
    ipv4_addr_t ipv4_addr_tmp;
    /* 1 is request, 2 is reply */
    hdr.arp.oper = 2;
    /* mac address */
    hdr.arp_ipv4.tha = hdr.arp_ipv4.sha;
    hdr.arp_ipv4.sha = sw_mac_addr;
    /* layer 2 */
    hdr.eth.dstAddr = hdr.arp_ipv4.tha;
    hdr.eth.srcAddr = hdr.arp_ipv4.sha;
    /* ip address */
    ipv4_addr_tmp = hdr.arp_ipv4.tpa;
    hdr.arp_ipv4.tpa = hdr.arp_ipv4.spa;
    hdr.arp_ipv4.spa = ipv4_addr_tmp;
    //is egress_port is read only?
    standard_metadata.egress_spec = standard_metadata.ingress_port;
  }
  table tbl_arp {
    key = {
      standard_metadata.ingress_port: exact;
    }
    actions = {
      arp_reply;
      NoAction;
    }
    size = 8;
    default_action = NoAction();
  }
  apply {
    tbl_arp.apply();
  }
}


#endif