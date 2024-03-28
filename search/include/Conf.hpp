#pragma once

#include "Search.hpp"
#include "Query.hpp"

#include <jsoncpp/json/json.h>

template <typename T>
T fromJson(const Json::Value &v);

Json::Value jNonNull(Json::Value v) {
  if (v.isNull())
    throw std::invalid_argument("null value in json");
  return v;
}

template <>
SearchConf fromJson(const Json::Value &v) {
  return {
    .nThreads = jNonNull(v["nThreads"]).asUInt(),
    .aluMax = jNonNull(v["aluMax"]).asUInt(),
    .pageMax = jNonNull(v["pageMax"]).asUInt(),
    .maxStagePerOp = jNonNull(v["maxStagePerOp"]).asUInt(),
    .alpha = jNonNull(v["alpha"]).asDouble(),
    .beta = jNonNull(v["beta"]).asDouble()
  };
}

template <>
TraceConf fromJson(const Json::Value &v) {
  return {
    .trace = std::make_shared<Trace>(readTrace(jNonNull(v["path"]).asCString())),
    .nEpoch = jNonNull(v["nEpoch"]).asUInt(),
    .interval = jNonNull(v["interval"]).asDouble()
  };
}

template <>
RecallPrecisionConf fromJson(const Json::Value &v) {
  return {
    .precisionMin = jNonNull(v["precisionMin"]).asDouble(),
    .recallMin = jNonNull(v["recallMin"]).asDouble(),
    .confidence = jNonNull(v["confidence"]).asDouble()
  };
}

template <>
AREConf fromJson(const Json::Value &v) {
  return {
    .areMax = jNonNull(v["areMax"]).asDouble(),
    .precisionMin = jNonNull(v["precisionMin"]).asDouble(),
    .recallMin = jNonNull(v["recallMin"]).asDouble(),
    .confidence = jNonNull(v["confidence"]).asDouble()
  };
}

template <>
RegConf fromJson(const Json::Value &v) {
  return {
    .d = jNonNull(v["d"]).asUInt(),
    .w = jNonNull(v["w"]).asUInt()
  };
}

Json::Value toJson(RegConf c) {
  Json::Value res;
  res["d"] = Json::Value::UInt(c.d);
  res["w"] = Json::Value::UInt(c.w);
  return res;
}
