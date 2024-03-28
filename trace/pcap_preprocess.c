//
// Created by Kira Sun on 2020-05-09.
//

#include <stdlib.h>
#include <string.h>
#include <pcap.h>
#include <errno.h>
#include "util.h"
#include "packet.h"



/*
 * Main program
 */
int main(int argc, char** argv) {

    if(argc != 4){
        printf("you two three parameters: input file dir, input file name, output file name\n");
        return 0;
    }
    const char* dir = argv[1];
    const char* pcap_file = argv[2];
    char pcap_filename[100];
    sprintf(pcap_filename, "%s%s", dir, pcap_file);
    pcap_t* pcap = NULL;
    char errbuf[PCAP_ERRBUF_SIZE];
    if ((pcap = pcap_open_offline(pcap_filename, errbuf)) == NULL) {
        LOG_ERR("cannot open %s (%s)\n", pcap_filename, errbuf);
    }

    const char* output_name = argv[3];
    char tmp[100];
    sprintf(tmp, "%s%s", dir, output_name);
    FILE* output = fopen(tmp, "wb");
    if (output == NULL) {
        LOG_ERR("cannot open %s: %s\n", output_name, strerror(errno));
    }
//    const char* filename = conf_common_tracefile(conf);
    tuple_t p;
    memset(&p, 0, sizeof(struct Tuple));
    uint64_t start_time = now_us();
    uint64_t valid_cnt = 0;
    while (1) {
        double pkt_ts; // packet timestamp
        int pkt_len; // packet snap length
        const u_char* pkt; // raw packet
        enum PACKET_STATUS status;
        uint8_t pkt_data[MAX_CAPLEN];
        struct pcap_pkthdr hdr;

        pkt = pcap_next(pcap, &hdr);
        if (pkt == NULL) {
            break;
        }
        pkt_ts = (double)hdr.ts.tv_usec / 1000000 + hdr.ts.tv_sec;
        pkt_len = hdr.caplen < MAX_CAPLEN ? hdr.caplen : MAX_CAPLEN;
        memcpy(pkt_data, pkt, pkt_len);

        status = decode(pkt_data, pkt_len, hdr.len, pkt_ts, &p);
        if (status == STATUS_VALID) {
            valid_cnt++;
            fwrite(&p, sizeof(tuple_t), 1, output);
//            uint64_t key = ((uint64_t)p.key.src_ip<<32) | p.key.dst_ip;
        }
    }

    uint64_t cur_ts = now_us();
    packet_stat.used_time = cur_ts - start_time;
    report_final_stat();

    pcap_close(pcap);
    fclose(output);
    return 0;
}
