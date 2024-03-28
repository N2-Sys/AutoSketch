#ifndef __TUPLE_H__
#define __TUPLE_H__
#include<stdint.h>

typedef struct __attribute__ ((__packed__)) FlowKey {
	// 8 (4*2) bytes
    uint32_t src_ip;  // source IP address
    uint32_t dst_ip;
	// 4 (2*2) bytes
    uint16_t src_port;
    uint16_t dst_port;
    // 1 bytes
    uint8_t proto;
} flow_key_t;

#define TUPLE_NORMAL 0
#define TUPLE_PUNC   1
#define TUPLE_TERM   2
#define TUPLE_START  3

typedef struct  __attribute__((packed)) Tuple {
    flow_key_t key;
    int32_t size;  // inner IP datagram length (header + data)

    uint32_t tcp_ack;  // user for autosketch syn flood
    uint32_t tcp_seq;  // user for marple query
    uint8_t tcp_flag;

    double pkt_ts;  // timestamp of the packet
    uint8_t ip_hdr_size;
    uint8_t tcp_hdr_size;
} tuple_t;

#endif
