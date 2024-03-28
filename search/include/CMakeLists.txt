cmake_minimum_required(VERSION 3.0.0)
project(search-ddos VERSION 0.1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)

find_package(spdlog REQUIRED)
find_package(Threads REQUIRED)
find_package(jsoncpp REQUIRED)

link_libraries(spdlog::spdlog Threads::Threads jsoncpp)

add_executable(search-ddos search-ddos.cpp)
