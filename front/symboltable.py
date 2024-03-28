def is_const(name):
    # TODO
    const_dist = {"IP_PROTOCOLS_TCP", "TCP_FLAG_SYN", "Thrd_NEW_TCP_CONNECTIONS"
                  ,"TCP_FLAG_FIN", "TCP_FLAG_ACK", "TCP_FLAG_SYN_ACK"
                  ,"Thrd_TCP_INCOMPLET_FLOW"
                  ,"Thrd_SUPERSPREDER"
                  ,"UNUSUAL_EGRESS_PORT"}
    if name in const_dist:
        return True
    if isinstance(name, int):
        return True
    if name.find("TCP_") != -1 or name.find("IP_") != -1 or name.find("Thrd") != -1:
        return True
    return False

def is_default_header(name):
    default_header = {}
    if name in default_header:
        return True
    if name.find("ipv4.") != -1 or name.find("tcp.") != -1 or name.find("hdr.") != -1:
        return True
    return False

def get_width(name):
    # print("get_width:", name)
    if isinstance(name, int):
        return 32
    if name.find("ipv4.") != -1:
        if name.find("addr") != -1:
            return 32
    if name.find("TCP_FLAG_") != -1:
        return 8
    return 32

def get_const(name) -> int:
    if is_const(name) == False:
        raise Exception("This is not a const!")
    # TODO: real const value based on name
    if name == "UNUSUAL_EGRESS_PORT":
        return "UNUSUAL_EGRESS_PORT"
    if isinstance(name, int):
        return name
    if name.find("TCP_") or name.find("IP_"):
        return name
    return 114514