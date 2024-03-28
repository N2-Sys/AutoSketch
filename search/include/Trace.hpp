#pragma once

#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>

#include <vector>
#include <stdexcept>

constexpr uint8_t IP_PROTOCOL_ICMP = 1;
constexpr uint8_t IP_PROTOCOL_TCP = 6;
constexpr uint8_t IP_PROTOCOL_UDP = 17;

constexpr uint8_t IP_PROTOCOLS_ICMP = 1;
constexpr uint8_t IP_PROTOCOLS_TCP = 6;
constexpr uint8_t IP_PROTOCOLS_UDP = 17;

constexpr uint8_t TCP_FLAG_FIN = 0x01;
constexpr uint8_t TCP_FLAG_SYN = 0x02;
constexpr uint8_t TCP_FLAG_RST = 0x04;
constexpr uint8_t TCP_FLAG_PUSH = 0x08;
constexpr uint8_t TCP_FLAG_ACK = 0x10;
constexpr uint8_t TCP_FLAG_SYN_ACK = TCP_FLAG_SYN | TCP_FLAG_ACK;

struct FlowKey {
  // 8 (4*2) bytes
  uint32_t src_ip;  // source IP address
  uint32_t dst_ip;
  // 4 (2*2) bytes
  uint16_t src_port;
  uint16_t dst_port;
  // 1 bytes
  uint8_t proto;
} __attribute__((packed));

struct PktInfo {
  FlowKey key;

  // 8 bytes
  int32_t size;  // inner IP datagram length (header + data)

  // 9 bytes
  uint32_t tcp_ack;  // user for autosketch syn flood
  uint32_t tcp_seq;  // user for marple query
  uint8_t tcp_flag;

  // 8 bytes
  double pkt_ts;  // timestamp of the packet
  uint8_t ip_hdr_size;
  uint8_t tcp_hdr_size;
} __attribute__((packed));

using Trace = std::vector<PktInfo>;

inline Trace readTrace(const char *path) {
  FILE *fp = fopen(path, "r");
  if (!fp)
    throw std::runtime_error(std::string("fopen: ") + strerror(errno));

  int rc = fseek(fp, 0, SEEK_END);
  if (rc < 0)
    throw std::runtime_error(std::string("fseek: ") + strerror(errno));
  long fsize = ftell(fp);
  if (fsize < 0)
    throw std::runtime_error(std::string("ftell: ") + strerror(errno));
  rewind(fp);

  if (fsize % sizeof(PktInfo) != 0)
    throw std::runtime_error("incorrect trace file length");
  size_t n = fsize / sizeof(PktInfo);

  Trace res(n);
  if (fread(res.data(), sizeof(PktInfo), n, fp) != n)
    throw std::runtime_error(std::string("fread: ") + strerror(errno));

  fclose(fp);
  return res;
}
