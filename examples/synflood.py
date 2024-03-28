def remap_key(tcp.flags):
    if tcp.flags == TCP_FLAG_SYN_ACK:
        nkey = ipv4.src_addr
        cnt_flag = 1
    else:
        nkey = ipv4.dst_addr 
        cnt_flag = 0
def sf_seq(tcp.flags, tcp.seq):# nextseq
    if tcp.flags == TCP_FLAG_SYN_ACK:
        nextseq = tcp.seq + 1
def sf_cnt_flag(tcp.ack, nextseq):
    if nextseq == tcp.ack:
        cnt_flag = 2
def sf_cnt(cnt_flag): # cnt
    if cnt_flag == 1:
        cnt += 1
    elif cnt_flag == 2:
        cnt -= 1

syn_flood[precision_min=0.9, recall_min=0.9, confidence=0.9] = PacketStream()
            .filter(left_value="ipv4.protocol", op="eq", right_value="IP_PROTOCOLS_TCP")
            .filter(left_value="tcp.flags", op="bit_and", right_value="TCP_FLAG_ACK")
            .groupby(func_name="remap_key", index=[], args=["tcp.flags"], registers=[], out=["nkey", "cnt_flag"])
            .groupby(func_name="sf_seq", index=["nkey"], args=["tcp.flags", "tcp.seq"], registers=["nextseq"], out=["nextseq"])
            .groupby(func_name="sf_cnt_flag", index=[], args=["tcp.ack", "nextseq"], registers=[], out=["cnt_flag"])
            .groupby(func_name="sf_cnt", index=["nkey"], args=["cnt_flag"], registers=["cnt"], out=["cnt"])
            .filter(left_value="cnt", op="gt", right_value=12)
            .distinct(distinct_keys=["nkey"])

