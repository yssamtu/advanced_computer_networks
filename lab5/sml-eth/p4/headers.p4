#ifndef _HEADERS_H
#define _HEADERS_H

#include "types.p4"

header ethernet_h {
  mac_addr_t dstAddr;
  mac_addr_t srcAddr;
  eth_type_t etherType;
}

header sml_h {
  bit<8> rank;
  bit<8> num_workers;
}

header elem_h {
  elem_t elem00;
  elem_t elem01;
  elem_t elem02;
  elem_t elem03;
  elem_t elem04;
  elem_t elem05;
  elem_t elem06;
  elem_t elem07;
  elem_t elem08;
  elem_t elem09;
  elem_t elem10;
  elem_t elem11;
  elem_t elem12;
  elem_t elem13;
  elem_t elem14;
  elem_t elem15;
  elem_t elem16;
  elem_t elem17;
  elem_t elem18;
  elem_t elem19;
  elem_t elem20;
  elem_t elem21;
  elem_t elem22;
  elem_t elem23;
  elem_t elem24;
  elem_t elem25;
  elem_t elem26;
  elem_t elem27;
  elem_t elem28;
  elem_t elem29;
  elem_t elem30;
  elem_t elem31;
}

struct headers {
  ethernet_h eth;
  sml_h sml;
  elem_h vector;
}

struct metadata { 
  bit<32> elem_idx;
  bool all_worker_arrive;
}

#endif
