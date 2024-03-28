cmake_minimum_required(VERSION 3.14)
project(Parser C)

add_definitions("-Wall -g")
include_directories(/usr/local/include)
include_directories(./)
link_directories(/usr/local/lib)

add_executable(preprocess
pcap_preprocess.c
packet.c
)
target_link_libraries(preprocess pcap)
