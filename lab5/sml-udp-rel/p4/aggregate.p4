
#ifndef _AGGREGATE_H
#define _AGGREGATE_H

#include "headers.p4"
#include "types.p4"


control Aggregate(in elem_t elem_in,
                  out elem_t elem_out,
                  in bit<8> chunk_id,
                  in bit<8> rank,
                  in bit<8> num_workers,
                  inout metadata meta,
                  inout standard_metadata_t standard_metadata) {

  register<bit<32>>(64) elem_sum_reg;
  action broadcast() {
    standard_metadata.mcast_grp = 1;
  }
  action unicast() {
    standard_metadata.egress_spec = standard_metadata.ingress_port;
  }
  action aggr() {
    bit<32> elem_tmp = 0;
    bit<8> elem_base_idx = 0;
    bit<8> worker_arrive_tmp = 0;
    bit<8> mask = (bit<8>)0xff << num_workers;
    if(chunk_id == 1){
      elem_base_idx = chunk_size;
      worker_arrive_tmp = meta.worker_arrive[15:8];
    }else{
      worker_arrive_tmp = meta.worker_arrive[7:0];
    }
    /* read the data from register */
    elem_sum_reg.read(elem_tmp, meta.elem_idx + (bit<32>)elem_base_idx);
    elem_out = elem_tmp;
    if(meta.opcode == 0){
      if ((worker_arrive_tmp ^ mask ^ ((bit<8>)1<<rank) ) == 0){
        /* this is the first worker */
        elem_tmp = elem_in;
      }else{
        /* aggregate current value and register value */
        elem_tmp = elem_tmp + elem_in;
      }
      /* update new value to header (not nessesary if it is not last worker) */
      elem_out = elem_tmp;
      if (worker_arrive_tmp == 0xff) {
        /* and then broadcast the modified packet to all worker */
        broadcast();
      }
    }else if(meta.opcode == 1){
      unicast();
    }
    /* write new value to register */
    elem_sum_reg.write(meta.elem_idx + (bit<32>)elem_base_idx, elem_tmp);
    /* plus 1 before go to next stage */
    meta.elem_idx = meta.elem_idx + 1;
  }
  table tbl_aggr {
    actions = {
      aggr();
    }
    default_action = aggr();
  }

  apply {
    @atomic {
      tbl_aggr.apply();
    }
  }
}


#endif