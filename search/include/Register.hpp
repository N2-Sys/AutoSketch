#pragma once

#include "Hash.hpp"

#include <cstddef>
#include <cassert>

#include <vector>
#include <tuple>
#include <unordered_map>
#include <numeric>
#include <stdexcept>

// using RegIndex = std::vector<std::byte>;

// template <typename... Ts>
// struct PackedTuple;

// template <typename TFirst>
// struct PackedTuple<TFirst> {
//   TFirst vFirst;
// } __attribute__((packed));

// template <typename TFirst, typename... TOthers>
// struct PackedTuple<TFirst, TOthers...> {
//   TFirst vFirst;
//   PackedTuple<TOthers...> others;
// } __attribute__((packed));

// template <typename... TArgs>
// RegIndex getRegIndex(TArgs... args) {
//   PackedTuple<TArgs...> t{args...};
//   return std::vector<std::byte>(
//     reinterpret_cast<const std::byte *>(&t),
//     reinterpret_cast<const std::byte *>(&t) + sizeof(t)
//   );
// }

// template <>
// class Hash<RegIndex> {
// public:
//   size_t operator ()(RegIndex k) const {
//     return select_crc(0, k.data(), k.size());
//   }
// };

template <typename RegIndex, typename Value>
class Register {
public:
  virtual ~Register() = default;
  virtual void reset() = 0;
  virtual Value get(const RegIndex &idx) = 0;
  virtual void add(const RegIndex &idx, Value v) {
    throw std::logic_error("unsupported operation");
  }
  virtual void minus(const RegIndex &idx, Value v) {
    throw std::logic_error("unsupported operation");
  }
  virtual void assign(const RegIndex &idx, Value v) {
    throw std::logic_error("unsupported operation");
  }
};

template <typename RegIndex, typename Value>
class BaselineRegister : public Register<RegIndex, Value> {
  HashMap<RegIndex, Value> m_;

public:
  void reset() override {
    m_.clear();
  }
  Value get(const RegIndex &idx) override {
    return m_[idx];
  }
  void add(const RegIndex &idx, Value v) override {
    m_[idx] += v;
  }
  void minus(const RegIndex &idx, Value v) override {
    m_[idx] -= v;
  }
  void assign(const RegIndex &idx, Value v) override {
    m_[idx] = v;
  }
};

// inline size_t hRegIdx(size_t hashId, size_t w, const RegIndex &idx) {
//   return select_crc(hashId, idx.data(), idx.size()) & (w - 1);
// }

template <typename RegIndex>
size_t hRegIdx(size_t hashId, size_t w, const RegIndex &idx) {
  static_assert(std::is_pod_v<RegIndex>);
  return select_crc(hashId, &idx, sizeof(idx)) & (w - 1);
}

template <typename RegIndex>
class BloomFilter : public Register<RegIndex, bool> {
  std::vector<std::vector<bool>> m_;

public:
  BloomFilter(size_t d, size_t w)
    : m_(d, std::vector<bool>(w)) {
  }
  void reset() override {
    for (auto &v : m_)
      v.assign(v.size(), false);
  }
  bool get(const RegIndex &idx) override {
    bool res = true;
    for (size_t i = 0; i < m_.size(); i++)
      res = res && m_[i][hRegIdx(i, m_[i].size(), idx)];
    return res;
  }
  void assign(const RegIndex &idx, bool v) override {
    assert(v);
    for (size_t i = 0; i < m_.size(); i++)
      m_[i][hRegIdx(i, m_[i].size(), idx)] = v;
  }
};

template <typename RegIndex, typename Value>
class CountMin : public Register<RegIndex, Value> {
protected:
  std::vector<std::vector<Value>> m_;

public:
  CountMin(size_t d, size_t w)
    : m_(d, std::vector<Value>(w)) {
  }
  void reset() override {
    for (auto &v : m_)
      v.assign(v.size(), 0);
  }
  Value get(const RegIndex &idx) override {
    Value res = std::numeric_limits<Value>::max();
    for (size_t i = 0; i < m_.size(); i++)
      res = std::min(res, m_[i][hRegIdx(i, m_[i].size(), idx)]);
    return res;
  }
  void add(const RegIndex &idx, Value v) override {
    assert(v >= 0);
    for (size_t i = 0; i < m_.size(); i++)
      m_[i][hRegIdx(i, m_[i].size(), idx)] += v;
  }
};

template <typename RegIndex, typename Value>
class GroupByCM : public CountMin<RegIndex, Value> {
  using CountMin<RegIndex, Value>::m_;

public:
  using CountMin<RegIndex, Value>::CountMin;

  void minus(const RegIndex &idx, Value v) override {
    for (size_t i = 0; i < m_.size(); i++)
      m_[i][hRegIdx(i, m_[i].size(), idx)] -= v;
  }
  void assign(const RegIndex &idx, Value v) override {
    for (size_t i = 0; i < m_.size(); i++)
      m_[i][hRegIdx(i, m_[i].size(), idx)] = v;
  }
};
