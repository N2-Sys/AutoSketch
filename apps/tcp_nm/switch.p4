#include <core.p4>
#include <tna.p4>

#include "../common/headers.p4"
#include "../common/util.p4"

//#include "../common/data-col.p4"
#include "../common/count-min.p4"
#include "../common/bloom-filter.p4"

// #if !TUMBLING && !SLIDING
// #warning "unspecified window type, using tumbling"
// #define TUMBLING
// #endif

// #define SLIDING
// #define PROC_OVERLAP
#define EPOCH_DATA_SIZE (1 << 19)

#define NDATA 65536
#define NKEYS 16384

#define MSG_LEN 8
#define MSG_BUF_SIZE (1 << 24)
#define MSG_BATCH_SIZE (1 << 14)

#define RWR_LEN 4

#define IP_HDR_LEN 20
#define UDP_HDR_LEN 8
#define RWR_HDR_LEN (12 + 16)
#define IMMDT_LEN 4
#define ICRC_LEN 4


typedef bit<32> key_type_t;

struct my_hdr_t {
  // eg_op_h    eg_op;

  ethernet_h ethernet;
  ipv4_h     ipv4;
  udp_h      udp;
  tcp_h      tcp;

}


header eg_mirror_h {
}

struct ig_md_t {
}

struct eg_md_t {
  bit<32> fingerprint;

}

struct nm_pair {
  bit<32> tcpseq;
  bit<32> cnt;
}


parser SwitchIngressParser(
    packet_in pkt,
    out my_hdr_t hdr,
    out ig_md_t ig_md,
    out ingress_intrinsic_metadata_t ig_intr_md
  ) {

  TofinoIngressParser() tofino_parser;

  state start {
    tofino_parser.apply(pkt, ig_intr_md);
    transition parse_ethernet;
  }

  state parse_ethernet {
    pkt.extract(hdr.ethernet);
    transition select (hdr.ethernet.ether_type) {
      ETHERTYPE_IPV4: parse_ipv4;
      default:        accept;
    }
  }

  state parse_ipv4 {
    pkt.extract(hdr.ipv4);
    transition select (hdr.ipv4.ihl, hdr.ipv4.protocol) {
      (5, IP_PROTOCOLS_UDP): parse_udp;
      (5, IP_PROTOCOLS_TCP): parse_tcp;
      default:               accept;
    }
  }

  state parse_udp {
    pkt.extract(hdr.udp);
    transition accept;
    // transition select (hdr.udp.dst_port, hdr.udp.src_port) {
      // (UDP_PORT_DC, UDP_PORT_DC): parse_eg_op;
      // default:                    accept;
    // }
  }

  state parse_tcp {
    pkt.extract(hdr.tcp);
    transition accept;
  }

}


control SwitchIngress(
    inout my_hdr_t hdr,
    inout ig_md_t ig_md,
    in ingress_intrinsic_metadata_t ig_intr_md,
    in ingress_intrinsic_metadata_from_parser_t ig_prsr_md,
    inout ingress_intrinsic_metadata_for_deparser_t ig_dprsr_md,
    inout ingress_intrinsic_metadata_for_tm_t ig_tm_md) {

  action send(PortId_t egress_port) {
    ig_tm_md.ucast_egress_port = egress_port;
  }

  action drop() {
    ig_dprsr_md.drop_ctl = 0x1;
  }

  table tab_forward {
    key = {
      ig_intr_md.ingress_port : exact;
    }

    actions = {
      send;
      @defaultonly drop;
    }

    const default_action = drop();
    size = 512;
  }

  apply {
    tab_forward.apply();
  }
}


control SwitchIngressDeparser(
    packet_out pkt,
    inout my_hdr_t hdr,
    in ig_md_t ig_md,
    in ingress_intrinsic_metadata_for_deparser_t ig_dprsr_md) {

  apply {
    pkt.emit(hdr);
  }
}


parser SwitchEgressParser(
    packet_in pkt,
    out my_hdr_t hdr,
    out eg_md_t eg_md,
    out egress_intrinsic_metadata_t eg_intr_md) {

  TofinoEgressParser() tofino_parser;

  state start {
    tofino_parser.apply(pkt, eg_intr_md);
    // transition accept;
    transition parse_ethernet;
  }

  state parse_ethernet {
    pkt.extract(hdr.ethernet);
    transition select (hdr.ethernet.ether_type) {
      ETHERTYPE_IPV4: parse_ipv4;
      default:        accept;
    }
  }

  state parse_ipv4 {
    pkt.extract(hdr.ipv4);

    transition select (hdr.ipv4.ihl, hdr.ipv4.protocol) {
      (5, IP_PROTOCOLS_UDP): parse_udp;
      (5, IP_PROTOCOLS_TCP): parse_tcp;
      default:               accept;
    }
  }

  state parse_udp {
    pkt.extract(hdr.udp);
    // transition select (hdr.udp.dst_port, hdr.udp.src_port) {
    //   (UDP_PORT_ROCE, UDP_PORT_ROCE): parse_roce;
    //   default:                        accept;
    // }
    transition accept;
  }

  state parse_tcp {
    pkt.extract(hdr.tcp);
    transition accept;
  }

}


control SwitchEgress(
    inout my_hdr_t hdr,
    inout eg_md_t eg_md,
    in egress_intrinsic_metadata_t                 eg_intr_md,
    in egress_intrinsic_metadata_from_parser_t     eg_prsr_md,
    inout egress_intrinsic_metadata_for_deparser_t    eg_dprsr_md,
    inout egress_intrinsic_metadata_for_output_port_t eg_oport_md) {

  CRCPolynomial<bit<16>>(0x3D65, true, false, false, 0, 0) poly1;
  Hash<bit<16>>(HashAlgorithm_t.CRC16, poly1) hash1;

  CRCPolynomial<bit<16>>(0x8BB7, true, false, false, 0, 0) poly2;
  Hash<bit<16>>(HashAlgorithm_t.CRC16, poly2) hash2; 

  Hash<bit<32>>(HashAlgorithm_t.CRC32) crc32;

  const key_type_t EmptyKey = 32w0;

  Register<bit<32>, bit<16>>(size=65536, initial_value=0) reg_fingerprint_1;
  RegisterAction<bit<32>, bit<16>, bit<1>>(reg_fingerprint_1) reg_fingerprint_1_action = {
    void apply(inout bit<32> fp, out bit<1> hit_flag) {
      if (fp == EmptyKey || fp == eg_md.fingerprint) {
        hit_flag = 1;
        fp = eg_md.fingerprint;
      } else {
        hit_flag = 0;
      }  
    }
  };

  Register<nm_pair, bit<16>>(size=65536, initial_value={0, 0}) reg_nm_1;
  RegisterAction<nm_pair, bit<16>, bit<32>>(reg_nm_1) reg_nm_1_action = {
    void apply(inout nm_pair p, out bit<32> res) {
      if (p.tcpseq < hdr.tcp.seq_no) {
        p.tcpseq = hdr.tcp.seq_no;
      } else {
        p.cnt = p.cnt + 1;
      }
      res = p.cnt;
    }
  };
  
  
  Register<bit<32>, bit<16>>(size=65536, initial_value=0) reg_fingerprint_2;
  RegisterAction<bit<32>, bit<16>, bit<1>>(reg_fingerprint_2) reg_fingerprint_2_action = {
    void apply(inout bit<32> fp, out bit<1> hit_flag) {
      if (fp == EmptyKey || fp == eg_md.fingerprint) {
        hit_flag = 1;
        fp = eg_md.fingerprint;
      } else {
        hit_flag = 0;
      }
    }
  };

  Register<nm_pair, bit<16>>(size=65536, initial_value={0, 0}) reg_nm_2;
  RegisterAction<nm_pair, bit<16>, bit<32>>(reg_nm_2) reg_nm_2_action = {
    void apply(inout nm_pair p, out bit<32> res) {
      if (p.tcpseq < hdr.tcp.seq_no) {
        p.tcpseq = hdr.tcp.seq_no;
      } else {
        p.cnt = p.cnt + 1;
      }
      res = p.cnt;
    }
  };


  apply {
    if (hdr.tcp.isValid()) {
      bit<16> idx;
      bit<1> fp_hit;
      idx = hash1.get({
        hdr.ipv4.src_addr,
        hdr.ipv4.dst_addr,
        hdr.tcp.src_port,
        hdr.tcp.dst_port});

      eg_md.fingerprint = crc32.get({
        hdr.ipv4.src_addr,
        hdr.ipv4.dst_addr,
        hdr.tcp.src_port,
        hdr.tcp.dst_port});

      fp_hit = reg_fingerprint_1_action.execute(idx);

      if (fp_hit == 1) {
        reg_nm_1_action.execute(idx);
      } 
      else {
        idx = hash2.get({
          hdr.ipv4.src_addr,
          hdr.ipv4.dst_addr,
          hdr.tcp.src_port,
          hdr.tcp.dst_port});
		    fp_hit = reg_fingerprint_2_action.execute(idx);
	    }

	    if (fp_hit == 1) {
		    reg_nm_2_action.execute(idx);
	    }
    }
  }



}

control SwitchEgressDeparser(
    packet_out pkt,
    inout my_hdr_t hdr,
    in eg_md_t eg_md,
    in egress_intrinsic_metadata_for_deparser_t eg_dprsr_md) {

  // Checksum() ipv4_checksum;

  apply {

    // if (eg_md.ipv4_upd) {
    //   hdr.ipv4.hdr_checksum = ipv4_checksum.update({
    //     hdr.ipv4.version,
    //     hdr.ipv4.ihl,
    //     hdr.ipv4.diffserv,
    //     hdr.ipv4.total_len,
    //     hdr.ipv4.identification,
    //     hdr.ipv4.flags,
    //     hdr.ipv4.frag_offset,
    //     hdr.ipv4.ttl,
    //     hdr.ipv4.protocol,
    //     hdr.ipv4.src_addr,
    //     hdr.ipv4.dst_addr
    //   });
    // }


    pkt.emit(hdr);
  }
}


Pipeline(SwitchIngressParser(),
         SwitchIngress(),
         SwitchIngressDeparser(),
         SwitchEgressParser(),
         SwitchEgress(),
         SwitchEgressDeparser()) pipe;

Switch(pipe) main;
