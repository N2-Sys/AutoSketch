p4_template = '''#include <core.p4>
#include <tna.p4>

#include "../common/headers.p4"
#include "../common/util.p4"

struct my_hdr_t {
  ethernet_h ethernet;
  ipv4_h     ipv4;
  udp_h      udp;
  tcp_h      tcp;
}

header eg_mirror_h {
}

struct ig_md_t {
  bit<32> fingerprint;
}

struct eg_md_t {
}

<{ struct definition }>

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

<{ SwitchEgress }>
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

  apply {
  }
}

control SwitchEgressDeparser(
    packet_out pkt,
    inout my_hdr_t hdr,
    in eg_md_t eg_md,
    in egress_intrinsic_metadata_for_deparser_t eg_dprsr_md) {

  apply {
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
'''

unit_indent = '  '
