#pragma once

#include <cassert>
#include <cstring>

#include <vector>
#include <unordered_map>
#include <unordered_set>

#include <boost/crc.hpp>

struct Crc32Conf {
  uint32_t truncPoly;
  uint32_t initRem;
  uint32_t finalXor;
  bool reflectIn;
  bool reflectRem;
};

constexpr size_t N_CRCS = 9;
constexpr Crc32Conf CRC_PARAMS[9] = {
  {0x04C11DB7, 0xFFFFFFFF, 0xFFFFFFFF, true, true},
  {0x1EDC6F41, 0xFFFFFFFF, 0xFFFFFFFF, true, true},
  {0xA833982B, 0xFFFFFFFF, 0xFFFFFFFF, true, true},
  {0x814141AB, 0x00000000, 0x00000000, false, false},
  {0x04C11DB7, 0xFFFFFFFF, 0xFFFFFFFF, false, false},
  {0x04C11DB7, 0xFFFFFFFF, 0x00000000, false, false},
  {0x04C11DB7, 0x00000000, 0xFFFFFFFF, false, false},
  {0x000000AF, 0x00000000, 0x00000000, false, false},
  {0x04C11DB7, 0xFFFFFFFF, 0x00000000, true, true},
};

template <size_t HASH_ID>
uint32_t calcCrc(const void *data, size_t size) {
  constexpr Crc32Conf conf = CRC_PARAMS[HASH_ID];
  boost::crc_optimal<32, conf.truncPoly, conf.initRem, conf.finalXor, conf.reflectIn, conf.reflectRem> p;
  p.process_block(data, reinterpret_cast<const char *>(data) + size);
  return p.checksum();
}

inline uint32_t select_crc(size_t hashId, const void *data, size_t size) {
  switch (hashId) {
  case 0: return calcCrc<0>(data, size);
  case 1: return calcCrc<1>(data, size);
  case 2: return calcCrc<2>(data, size);
  case 3: return calcCrc<3>(data, size);
  case 4: return calcCrc<4>(data, size);
  case 5: return calcCrc<5>(data, size);
  case 6: return calcCrc<6>(data, size);
  case 7: return calcCrc<7>(data, size);
  case 8: return calcCrc<8>(data, size);
  default: throw std::out_of_range("unsupported hash id");
  }
}

template <typename Key>
class Hash {
public:
  size_t operator ()(Key k) const {
    if constexpr (std::is_scalar_v<Key>) {
      return std::hash<Key>()(k);
    } else {
      static_assert(std::is_pod_v<Key>);
      return calcCrc<0>(&k, sizeof(Key));
    }
  }
};

template <typename Key>
class MemEqTo {
public:
  bool operator ()(Key x, Key y) const {
    if constexpr (std::is_scalar_v<Key>) {
      return x == y;
    } else {
      static_assert(std::is_pod_v<Key>);
      return memcmp(&x, &y, sizeof(Key)) == 0;
    }
  }
};

template <typename Key>
using HashSet = std::unordered_set<Key, Hash<Key>, MemEqTo<Key>>;

template <typename Key, typename Val>
using HashMap = std::unordered_map<Key, Val, Hash<Key>, MemEqTo<Key>>;
