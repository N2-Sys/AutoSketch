#pragma once

#include "Search.hpp"
#include "Hash.hpp"

#include <algorithm>

struct RecallPrecisionConf {
  double precisionMin, recallMin, confidence;
};

template <size_t N_REGS, typename ResKey>
class QueryRecallPrecision : public Search<N_REGS>::template Query<HashSet<ResKey>> {
public:
  using Result = HashSet<ResKey>;
  using AppConf = typename Search<N_REGS>::AppConf;
  // using typename Search<N_REGS>::template Query<Result>::AppInstanceBase;

protected:
  using Search<N_REGS>::template Query<Result>::resBaseline_;

private:
  RecallPrecisionConf evalConf_;

public:
  QueryRecallPrecision(RecallPrecisionConf evalConf)
    : evalConf_(evalConf) {
  }

  bool evaluateResult(const std::vector<Result> &res, AppConf c) override {
    size_t nEpoch = resBaseline_.size();
    assert(res.size() == nEpoch);

    std::vector<double> precisions(nEpoch), recalls(nEpoch);
    double totKeys = 0;
    for (size_t i = 0; i < nEpoch; i++) {
      size_t correct = 0;
      for (const auto &v : res[i])
        if (resBaseline_[i].count(v))
          correct++;
      precisions[i] = static_cast<double>(correct) / static_cast<double>(res[i].size());
      recalls[i] = static_cast<double>(correct) / static_cast<double>(resBaseline_[i].size());
      totKeys += resBaseline_[i].size();
    }

    size_t k = static_cast<size_t>(static_cast<double>(nEpoch) * evalConf_.confidence);
    if (k > 0)
      k--;
    std::nth_element(precisions.begin(), precisions.begin() + k, precisions.end(), std::greater<double>());
    std::nth_element(recalls.begin(), recalls.begin() + k, recalls.end(), std::greater<double>());

    bool succ = precisions[k] >= evalConf_.precisionMin && recalls[k] >= evalConf_.recallMin;
    spdlog::info("[{}] {}: precision {}, recall {}, confidence {}, avg. keys {}",
      succ ? "success" : "failure", c.str(), precisions[k], recalls[k], evalConf_.confidence, totKeys / nEpoch);
    return succ;
  }
};

struct AREConf {
  double areMax, precisionMin, recallMin, confidence;
};

template <size_t N_REGS, typename ResKey, typename ResVal>
class QueryARE : public Search<N_REGS>::template Query<HashMap<ResKey, ResVal>> {
public:
  using Result = HashMap<ResKey, ResVal>;
  using AppConf = typename Search<N_REGS>::AppConf;
  // using typename Search<N_REGS>::template Query<Result>::AppInstanceBase;

protected:
  using Search<N_REGS>::template Query<Result>::resBaseline_;

private:
  AREConf evalConf_;

public:
  QueryARE(AREConf evalConf)
    : evalConf_(evalConf) {
  }

  bool evaluateResult(const std::vector<Result> &res, AppConf c) override {
    size_t nEpoch = resBaseline_.size();
    assert(res.size() == nEpoch);

    std::vector<double> precisions(nEpoch), recalls(nEpoch), ares(nEpoch);
    double totKeys = 0, totAvgVal = 0;
    for (size_t i = 0; i < nEpoch; i++) {
      size_t correct = 0;
      double totEpVal = 0, totEpErr = 0;
      for (const auto &v : resBaseline_[i]) {
        totEpVal += v.second;
        if (auto p = res[i].find(v.first); p != res[i].end()) {
          correct++;
          totEpErr += std::abs(static_cast<double>(p->second) - static_cast<double>(v.second)) / static_cast<double>(v.second);
        } else {
          totEpErr += 1.0;
        }
      }
      precisions[i] = static_cast<double>(correct) / static_cast<double>(res[i].size());
      recalls[i] = static_cast<double>(correct) / static_cast<double>(resBaseline_[i].size());
      ares[i] = totEpErr / static_cast<double>(resBaseline_[i].size());

      totKeys += resBaseline_[i].size();
      totAvgVal += totEpVal / static_cast<double>(resBaseline_[i].size());
    }

    size_t k = static_cast<size_t>(static_cast<double>(nEpoch) * evalConf_.confidence);
    if (k > 0)
      k--;
    std::nth_element(precisions.begin(), precisions.begin() + k, precisions.end(), std::greater<double>());
    std::nth_element(recalls.begin(), recalls.begin() + k, recalls.end(), std::greater<double>());
    std::nth_element(ares.begin(), ares.begin() + k, ares.end());

    bool succ = ares[k] <= evalConf_.areMax && precisions[k] >= evalConf_.precisionMin && recalls[k] >= evalConf_.recallMin;
    spdlog::info("[{}] {}: are {}, precision {}, recall {}, confidence {}, avg. keys {}, avg. val {}",
      succ ? "success" : "failure", c.str(), ares[k], precisions[k], recalls[k], evalConf_.confidence, totKeys / nEpoch, totAvgVal / nEpoch);
    return succ;
  }
};
