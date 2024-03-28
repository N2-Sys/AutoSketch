#include "packet.h"

extern struct PacketStat packet_stat;

void report_final_stat_file(const char* filename) {
  FILE* output = fopen(filename, "w");

  if (output == NULL) {
    fprintf(
        stderr,
        "\nRunning Stat\n"
        "===========================================\n"
        "\tUsed time: %.2lf s\n"
        "\tSpeed: %.2lf packets/s (%.2lf Gb/s)\n"
        "\tTrace duration: %.2lf s\n",
        packet_stat.used_time / 1.0e6,
        packet_stat.tot_pkt_cnt * 1.0 / packet_stat.used_time * 1.0e6,
        packet_stat.tot_act_byte_cnt * 8.0 / packet_stat.used_time * 1.0e6 / GB,
        packet_stat.trace_end_ts - packet_stat.trace_start_ts);

    fprintf(stderr,
            "Packet Stat\n"
            "===========================================\n"
            "\tTotal packets observed: %lu\n"
            "\tTotal bytes observed (capture): %lu\n"
            "\tTotal bytes observed (actual): %lu\n"
            "\tValid packet count: %lu\n"
            "\tValid byte count (capture): %lu\n"
            "\tValid byte count (actual): %lu\n"
            "\tNon-IP packet count: %lu\n"
            "\tIP packet with own option count: %lu\n"
            "\tIP-not-full packet count: %lu\n"
            "\tIP-version-failed packet count: %lu\n"
            "\tIP-checksum-failed packet count: %lu\n"
            "\tIP-fragment packet count: %lu\n"
            "\tTCP-not-full packet count: %lu\n"
            "\tUDP-not-full packet count: %lu\n"
            "\tICMP-not-full packet count: %lu\n"
            "\tUndefined packet count: %lu\n"
            "\tNon-GTP packet count: %lu\n"
            "\tNon-GPRS packet count: %lu\n"
            "\tMAX packet size: %lu\n"
            "===========================================\n",
            packet_stat.tot_pkt_cnt, packet_stat.tot_cap_byte_cnt,
            packet_stat.tot_act_byte_cnt, packet_stat.valid_pkt_cnt,
            packet_stat.valid_cap_byte_cnt, packet_stat.valid_act_byte_cnt,
            packet_stat.non_ip_cnt, packet_stat.ip_with_option_cnt,
            packet_stat.ip_not_full_cnt, packet_stat.ip_ver_fail_cnt,
            packet_stat.ip_chksum_fail_cnt++, packet_stat.ip_frag_cnt++,
            packet_stat.tcp_not_full_cnt, packet_stat.udp_not_full_cnt,
            packet_stat.icmp_not_full_cnt, packet_stat.undefined_cnt,
            packet_stat.non_gtp_cnt, packet_stat.non_gprs_cnt,
            packet_stat.max_packet_size);

    //     for (int i = 0; i < 71; i++) {
    //         fprintf(stderr, "packset size_%d # :%lu \t average bytes: %lu\n",
    //         i, packet_stat.cap_packet_size[i]);
    //     }
    //     for (int i = 0; i < 1500; i++){
    //         fprintf(stderr, "size %d num %d\n", i,
    //         packet_stat.packets_totallen_of_version[i]);
    //     }
    //     for (int i = 0; i < 60; i++) {
    //         fprintf(stderr, "verison_%d # of packets :%lu \t average bytes:
    //         %lu\n", i+1, packet_stat.packets_cnt_of_version[i+1],
    //         packet_stat.packets_size_of_version[i+1]/packet_stat.packets_cnt_of_version[i+1]);
    //    }
  } else {
    fprintf(
        output,
        "\nRunning Stat\n"
        "===========================================\n"
        "\tUsed time: %.2lf s\n"
        "\tSpeed: %.2lf packets/s (%.2lf Gb/s)\n"
        "\tTrace duration: %.2lf s\n",
        packet_stat.used_time / 1.0e6,
        packet_stat.tot_pkt_cnt * 1.0 / packet_stat.used_time * 1.0e6,
        packet_stat.tot_act_byte_cnt * 8.0 / packet_stat.used_time * 1.0e6 / GB,
        packet_stat.trace_end_ts - packet_stat.trace_start_ts);

    fprintf(output,
            "Packet Stat\n"
            "===========================================\n"
            "\tTotal packets observed: %lu\n"
            "\tTotal bytes observed (capture): %lu\n"
            "\tTotal bytes observed (actual): %lu\n"
            "\tValid packet count: %lu\n"
            "\tValid byte count (capture): %lu\n"
            "\tValid byte count (actual): %lu\n"
            "\tNon-IP packet count: %lu\n"
            "\tIP packet with own option count: %lu\n"
            "\tIP-not-full packet count: %lu\n"
            "\tIP-version-failed packet count: %lu\n"
            "\tIP-checksum-failed packet count: %lu\n"
            "\tIP-fragment packet count: %lu\n"
            "\tTCP-not-full packet count: %lu\n"
            "\tUDP-not-full packet count: %lu\n"
            "\tICMP-not-full packet count: %lu\n"
            "\tUndefined packet count: %lu\n"
            "\tNon-GTP packet count: %lu\n"
            "\tNon-GPRS packet count: %lu\n"
            "===========================================\n",
            packet_stat.tot_pkt_cnt, packet_stat.tot_cap_byte_cnt,
            packet_stat.tot_act_byte_cnt, packet_stat.valid_pkt_cnt,
            packet_stat.valid_cap_byte_cnt, packet_stat.valid_act_byte_cnt,
            packet_stat.non_ip_cnt, packet_stat.ip_with_option_cnt,
            packet_stat.ip_not_full_cnt, packet_stat.ip_ver_fail_cnt,
            packet_stat.ip_chksum_fail_cnt++, packet_stat.ip_frag_cnt++,
            packet_stat.tcp_not_full_cnt, packet_stat.udp_not_full_cnt,
            packet_stat.icmp_not_full_cnt, packet_stat.undefined_cnt,
            packet_stat.non_gtp_cnt, packet_stat.non_gprs_cnt);
    // for (int i = 0; i < 60; i++) {
    //     fprintf(output, "\nverison_%d # of packets :%lu \t average bytes:
    //     %lu\n", i+1, packet_stat.packets_cnt_of_version[i+1],
    //     packet_stat.packets_size_of_version[i+1]/packet_stat.packets_cnt_of_version[i+1]);
    // }
    fclose(output);
  }
}

void report_final_stat() { report_final_stat_file(NULL); }

/*
 * IP Header checksum - check whether the IP header is valid
 *
 * @param w - short words of IP header
 * @param len - header length (in bytes)
 *
 * @return - 0 if the answer is correct, a non-zero value if there's error
 */
inline static unsigned short in_chksum_ip(unsigned short* w, int len) {
  long sum = 0;

  while (len > 1) {
    sum += *w++;
    if (sum & 0x80000000) /* if high order bit set, fold */
      sum = (sum & 0xFFFF) + (sum >> 16);
    len -= 2;
  }

  if (len) /* take care of left over byte */
    sum += *w;

  while (sum >> 16) sum = (sum & 0xFFFF) + (sum >> 16);

  return ~sum;
}

enum PACKET_STATUS decode(const uint8_t* pkt, uint32_t cap_len,
                          uint32_t act_len, double ts, tuple_t* p) {
  struct ether_header* eth_hdr;
  struct ip* ip_hdr;
  struct tcphdr* tcp_hdr;
  struct udphdr* udp_hdr;
  int eth_len = ETH_LEN;
  enum PACKET_STATUS status;

  //    status = STATUS_VALID;
  status = STATUS_UNDEFINED;
  packet_stat.tot_pkt_cnt++;
  if (packet_stat.tot_pkt_cnt == 1) {
    packet_stat.trace_start_ts = ts;
  }
  if (ts < packet_stat.trace_end_ts) {
    LOG_WARN("Skewed ts: current %lf last %lf\n", ts, packet_stat.trace_end_ts);
  }
  packet_stat.trace_end_ts = ts;
  packet_stat.tot_cap_byte_cnt += cap_len;
  packet_stat.tot_act_byte_cnt += act_len;

  // error checking (Ethernet level)
  if (eth_len == 14) {
    eth_hdr = (struct ether_header*)pkt;
    if (ntohs(eth_hdr->ether_type) == ETHERTYPE_VLAN) {
      eth_len = 18;
    } else if (ntohs(eth_hdr->ether_type) != ETHERTYPE_IP) {
      status = STATUS_NON_IP;
    }
  } else if (eth_len == 4) {
    if (ntohs(*(uint16_t*)(pkt + 2)) != ETHERTYPE_IP) {
      status = STATUS_NON_IP;
    }
  } else if (eth_len != 0) {
    // unkown ethernet header length
    status = STATUS_NON_IP;
  }

  uint32_t len = cap_len - eth_len;

  // error checking (IP level)
  ip_hdr = (struct ip*)(pkt + eth_len);
  // i) IP header length check
  // LOG_MSG("check 1\n");
  if ((int)len < (ip_hdr->ip_hl << 2)) {
    // printf("actual len: %u, header size %u\n", len, (ip_hdr->ip_hl << 2));
    status = STATUS_IP_NOT_FULL;
  }
  if (ip_hdr->ip_hl != 5) {
    status = STATUS_IP_OPTION;
  }
  // ii) IP version check
  // LOG_MSG("check 2\n");
  if (ip_hdr->ip_v != 4) {
    status = STATUS_IP_VER_FAIL;
  }
  // iii) IP checksum check
  // LOG_MSG("check 3\n");
  if (IP_CHECK && in_chksum_ip((unsigned short*)ip_hdr, ip_hdr->ip_hl << 2)) {
    status = STATUS_IP_CHKSUM_FAIL;
  }

  // LOG_MSG("check 4\n");
  //  error checking (TCP/UDP/ICMP layer test)
  if (ip_hdr->ip_p == IPPROTO_TCP) {
    // see if the TCP header is fully captured
    tcp_hdr = (struct tcphdr*)((uint8_t*)ip_hdr + (ip_hdr->ip_hl << 2));
    if ((int)len < (ip_hdr->ip_hl << 2) + (tcp_hdr->th_off << 2)) {
      status = STATUS_TCP_NOT_FULL;
    } else {
      if (status == STATUS_UNDEFINED) status = STATUS_VALID;
    }
  } else if (ip_hdr->ip_p == IPPROTO_UDP) {
    // see if the UDP header is fully captured
    if ((int)len < (ip_hdr->ip_hl << 2) + 8) {
      status = STATUS_UDP_NOT_FULL;
    } else {
      if (status == STATUS_UNDEFINED) status = STATUS_VALID;
    }
  } else if (ip_hdr->ip_p == IPPROTO_ICMP) {
    // see if the ICMP header is fully captured
    if ((int)len < (ip_hdr->ip_hl << 2) + 8) {
      status = STATUS_ICMP_NOT_FULL;
    }
  }

  switch (status) {
    case STATUS_VALID:
      packet_stat.valid_pkt_cnt++;
      packet_stat.valid_cap_byte_cnt += cap_len;
      packet_stat.valid_act_byte_cnt += act_len;
      break;
    case STATUS_NON_IP:
      packet_stat.non_ip_cnt++;
      LOG_DEBUG("non valid status: non ip\n");
      break;
    case STATUS_IP_NOT_FULL:
      packet_stat.ip_not_full_cnt++;
      LOG_DEBUG("non valid status: ip not full\n");
      break;
    case STATUS_IP_OPTION:
      packet_stat.ip_with_option_cnt++;
      LOG_DEBUG("non valid status: ip has own option\n");
      break;
    case STATUS_IP_VER_FAIL:
      packet_stat.ip_ver_fail_cnt++;
      LOG_DEBUG("non valid status: ip ver fail\n");
      break;
    case STATUS_IP_CHKSUM_FAIL:
      packet_stat.ip_chksum_fail_cnt++;
      LOG_DEBUG("non valid status: ip chksum fail\n");
      break;
    case STATUS_IP_FRAG:
      packet_stat.ip_frag_cnt++;
      LOG_DEBUG("non valid status: ip frag\n");
      break;
    case STATUS_TCP_NOT_FULL:
      packet_stat.tcp_not_full_cnt++;
      LOG_DEBUG("non valid status: tcp not full\n");
      break;
    case STATUS_UDP_NOT_FULL:
      packet_stat.udp_not_full_cnt++;
      LOG_DEBUG("non valid status: udp not full\n");
      break;
    case STATUS_ICMP_NOT_FULL:
      packet_stat.icmp_not_full_cnt++;
      LOG_DEBUG("non valid status: icmp not full\n");
      break;
    case STATUS_UNDEFINED:
      packet_stat.undefined_cnt++;
      LOG_DEBUG("non valid status: packet not defined\n");
      break;
    case STATUS_NON_GTP:
      packet_stat.non_gtp_cnt++;
      LOG_DEBUG("non valid status: non gtp\n");
      break;
    case STATUS_NON_GPRS:
      packet_stat.non_gprs_cnt++;
      LOG_DEBUG("non valid status: non gprs\n");
      break;
    default:
      break;
  }

  if (status != STATUS_VALID) return status;

  // assign the fields
  p->key.src_ip = ip_hdr->ip_src.s_addr;
  p->key.dst_ip = ip_hdr->ip_dst.s_addr;
  p->key.proto = ip_hdr->ip_p;
  p->pkt_ts = ts;
  p->size = ntohs(ip_hdr->ip_len);
  p->tcp_seq = 0;
  p->tcp_ack = 0;
  p->tcp_flag = 0;
  p->ip_hdr_size = ip_hdr->ip_hl << 2;
  p->tcp_hdr_size = 0;

  if (ip_hdr->ip_p == IPPROTO_TCP) {
    // TCP
    tcp_hdr = (struct tcphdr*)((uint8_t*)ip_hdr + (ip_hdr->ip_hl << 2));
    p->key.src_port = ntohs(tcp_hdr->th_sport);
    p->key.dst_port = ntohs(tcp_hdr->th_dport);
    p->tcp_flag = tcp_hdr->th_flags;
    p->tcp_seq = tcp_hdr->th_seq;
    p->tcp_ack = tcp_hdr->th_ack;
    p->tcp_hdr_size = tcp_hdr->th_off << 2;
  } else if (ip_hdr->ip_p == IPPROTO_UDP) {
    // UDP
    udp_hdr = (struct udphdr*)((uint8_t*)ip_hdr + (ip_hdr->ip_hl << 2));
    p->key.src_port = ntohs(udp_hdr->uh_sport);
    p->key.dst_port = ntohs(udp_hdr->uh_dport);
  } else {
    // Other L4
    p->key.src_port = 0;
    p->key.dst_port = 0;
  }

#ifdef PREHASH
  for (int i = 0; i < 4; i++) {
    p->sd_hash[i] = select_crc(i, (uint8_t*)p, 8);
    p->s_hash[i] = select_crc(i, (uint8_t*)p, 4);
    p->d_hash[i] = select_crc(i, (uint8_t*)&p->key.dst_ip, 4);
  }
#endif

  return status;
}

void print_tuple(FILE* f, tuple_t* t) {
  char ip1[30], ip2[30];

  fprintf(f, "%s(%u) <-> %s(%u) %u %d\n", ip2a(t->key.src_ip, ip1),
          t->key.src_port, ip2a(t->key.dst_ip, ip2), t->key.dst_port,
          t->key.proto, t->size);
}

void read_tuple(char* line, tuple_t* p) {
  unsigned int ip1, ip2, ip3, ip4, ip5, ip6, ip7, ip8;
  sscanf(line, "%u.%u.%u.%u(%hu) <-> %u.%u.%u.%u(%hu) %hhu %d", &ip1, &ip2,
         &ip3, &ip4, &p->key.src_port, &ip5, &ip6, &ip7, &ip8, &p->key.dst_port,
         &p->key.proto, &p->size);
  p->key.src_ip = (ip4 << 24) | (ip3 << 16) | (ip2 << 8) | ip1;
  p->key.dst_ip = (ip8 << 24) | (ip7 << 16) | (ip6 << 8) | ip5;
}

void reset_stat() { memset(&packet_stat, 0, sizeof(struct PacketStat)); }
