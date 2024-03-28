#pragma once

#include "Trace.hpp"
#include "Hash.hpp"

#include <cstddef>

#include <algorithm>
#include <set>
#include <queue>
#include <array>
#include <memory>
#include <thread>
#include <mutex>
#include <condition_variable>
#include <random>

#include <spdlog/spdlog.h>

constexpr size_t PAGE_SIZE = 16 << 10;
constexpr size_t ALU_PER_STAGE = 4, PAGE_PER_STAGE = 48;
constexpr size_t MAX_PAGE_FOR_ONE_ALU = 32;

struct RegConf {
  size_t d, w;

  std::string str() const {
    return "(" + std::to_string(d) + ", " + std::to_string(w) + ")";
  }
};

inline bool operator ==(RegConf x, RegConf y) {
  return x.d == y.d && x.w == y.w;
}

struct SearchConf {
  size_t nThreads;
  size_t aluMax, pageMax;
  size_t maxStagePerOp;
  double alpha, beta;
};

struct TraceConf {
  std::shared_ptr<const Trace> trace;
  size_t nEpoch;
  double interval;
};

template <size_t N_REGS>
class Search {
public:
  class AppConf : public std::array<RegConf, N_REGS> {
  public:
    using std::array<RegConf, N_REGS>::array;

    std::string str() const {
      std::string s = "[";
      for (size_t i = 0; i < N_REGS; i++) {
        s += (*this)[i].str();
        if (i + 1 < N_REGS)
          s += ", ";
      }
      s += "]";
      return s;
    }
  };

  class QueryBase {
  public:
    virtual ~QueryBase() = default;
    virtual void runBaseline(TraceConf traceConf) = 0;
    virtual bool eval(TraceConf traceConf, AppConf c) = 0;
  };

  template <typename Result>
  class Query : public QueryBase {
  public:
    class AppInstanceBase {
    protected:
      virtual void process(PktInfo pkt) = 0;
      virtual Result switchWin() = 0;

    public:
      virtual ~AppInstanceBase() = default;

      std::vector<Result> run(TraceConf traceConf) {
        spdlog::debug("start running");
        std::vector<Result> res;
        size_t curEpoch = 0;
        double startTime = traceConf.trace->at(0).pkt_ts;
        for (PktInfo pkt : *traceConf.trace) {
          while (pkt.pkt_ts - startTime >= traceConf.interval) {
            res.push_back(switchWin());
            startTime += traceConf.interval;
            // spdlog::debug("passing epoch {}", curEpoch);

            if (++curEpoch == traceConf.nEpoch)
              goto DONE;
          }
          process(pkt);
        }
      DONE:
        spdlog::debug("finished running with {} epoches", curEpoch);
        if (curEpoch < traceConf.nEpoch)
          throw std::runtime_error("finished in epoch " + std::to_string(curEpoch) + "/" + std::to_string(traceConf.nEpoch));
        return res;
      }
    };

  protected:
    std::vector<Result> resBaseline_;

    virtual std::unique_ptr<AppInstanceBase> createInstanceBaseline() = 0;
    virtual std::unique_ptr<AppInstanceBase> createInstance(AppConf c) = 0;
    virtual bool evaluateResult(const std::vector<Result> &res, AppConf c) = 0;

  public:
    void runBaseline(TraceConf traceConf) override {
      resBaseline_ = createInstanceBaseline()->run(std::move(traceConf));
    }
    bool eval(TraceConf traceConf, AppConf c) override {
      std::string strC = "[";
      for (size_t i = 0; i < N_REGS; i++)
        strC += fmt::format("({}, {}), ", c[i].d, c[i].w);
      strC += "]";
      spdlog::debug("evaluating {}", strC);
      return evaluateResult(createInstance(c)->run(std::move(traceConf)), c);
    }
  };

private:
  std::shared_ptr<QueryBase> query_;
  TraceConf traceConf_;
  SearchConf searchConf_;

  mutable std::mutex mtx_;
  mutable std::condition_variable cv_;
  int nActive_ = 0;
  std::vector<std::thread> threads_;

  class Cmp {
    const Search *search_;

  public:
    Cmp(const Search *search) : search_(search) {
    }
    bool operator ()(AppConf x, AppConf y) const {
      return search_->getResourceScore(x) > search_->getResourceScore(y);
    }
  };
  HashSet<AppConf> vis_;
  std::priority_queue<AppConf, std::vector<AppConf>, Cmp> candidates_;
  std::vector<AppConf> answers_, failures_;

  bool checkRegConf(RegConf c) const{
    size_t alu = c.d, mem = c.w;
    if (alu > ALU_PER_STAGE * searchConf_.maxStagePerOp || alu <= 0 || alu > searchConf_.aluMax)
      return false;
    if (mem > PAGE_PER_STAGE || mem <= 0)
      return false;
    if (((alu + searchConf_.maxStagePerOp - 1) / searchConf_.maxStagePerOp) * (mem + 1) > PAGE_PER_STAGE)
      return false;
    return true;
    // return 0 < c.d && c.d <= searchConf_.aluMax && 0 < c.w && c.w <= searchConf_.pageMax;
  }

  double getResourceScore(AppConf c) const {
    double total_alu =
        N_REGS * ALU_PER_STAGE * searchConf_.maxStagePerOp;
    double total_page =
        N_REGS * PAGE_PER_STAGE * searchConf_.maxStagePerOp;
    double mems = 0.0;
    double alus = 0.0;
    double pages = 0.0;
    for (int i = 0; i < N_REGS; i++) {
      alus += c[i].d;
      pages += c[i].d * c[i].w;
      mems += c[i].w;
    }
    pages += alus;  // NDA protect
    mems /= N_REGS;
    // c->resource_score = ALPHA * (alus / total_alu) + BETA * (pages /
    // total_page);
    return searchConf_.alpha * (alus / total_alu) +
                        (searchConf_.beta / 2) * (pages / total_page) +
                        (searchConf_.beta / 2) * (mems / MAX_PAGE_FOR_ONE_ALU);
  }

  void initCandidates() {
    std::mt19937 g;

    std::vector<size_t> alus, pages;
    for (size_t x = 1; x <= searchConf_.aluMax; x++)
      alus.push_back(x);
    for (size_t x = 1; x <= searchConf_.pageMax; x *= 2)
      pages.push_back(x);

    size_t m = std::min(alus.size(), pages.size());
    std::vector<AppConf> cs(m);
    for (size_t i = 0; i < N_REGS; i++) {
      std::shuffle(alus.begin(), alus.end(), g);
      std::shuffle(pages.begin(), pages.end(), g);
      for (size_t j = 0; j < m; j++) {
        cs[j][i] = {alus[j], pages[j]};
      }
    }
    for (AppConf c : cs) {
      bool flag = true;
      for (RegConf rc : c)
        if (!checkRegConf(rc))
          flag = false;
      if (flag) {
        vis_.insert(c);
        candidates_.push(c);
      }
    }
  }

  bool strictExamine(AppConf c) const {
    for (auto c1 : answers_) {
      bool flag = false;
      for (size_t i = 0; i < N_REGS; i++)
        if (c[i].d < c1[i].d || c[i].w < c1[i].w)
          flag = true;
      if (!flag)
        return false;
    }
    for (auto c1 : failures_) {
      bool flag = false;
      for (size_t i = 0; i < N_REGS; i++)
        if (c[i].d > c1[i].d || c[i].w > c1[i].w)
          flag = true;
      if (!flag)
        return false;
    }
    return true;
  }

  bool examineCandidate(AppConf c) const {
    if (vis_.count(c))
      return false;
    return strictExamine(c);
  }

  std::vector<AppConf> calcNeighbors(AppConf c, bool succ) {
    std::vector<AppConf> neighbors;
    for (size_t i = 0; i < N_REGS; i++) {
      if (succ) {
        AppConf c1 = c;
        c1[i].d -= 1;
        if (checkRegConf(c1[i]))
          neighbors.push_back(c1);

        c1 = c;
        c1[i].w /= 2;
        if (checkRegConf(c1[i]))
          neighbors.push_back(c1);
      } else {
        AppConf c1 = c;
        c1[i].d += 1;
        if (checkRegConf(c1[i]))
          neighbors.push_back(c1);

        c1 = c;
        c1[i].w *= 2;
        if (checkRegConf(c1[i]))
          neighbors.push_back(c1);
      }
    }
    return neighbors;
  }

  void searchThread() {
    std::unique_lock<std::mutex> lck{mtx_};

    while (1) {
      while (candidates_.empty() && nActive_ != 0)
        cv_.wait(lck);

      spdlog::debug("{} candidates, {} active threads", candidates_.size(), nActive_);
      if (candidates_.empty())
        break;
      auto c = candidates_.top();
      candidates_.pop();
      nActive_++;

      if (strictExamine(c)) {
        lck.unlock();
        bool succ = query_->eval(traceConf_, c);
        lck.lock();

        if (succ)
          answers_.push_back(c);
        else
          failures_.push_back(c);
        for (AppConf x : calcNeighbors(c, succ))
          if (examineCandidate(x)) {
            vis_.insert(x);
            candidates_.push(x);
          }
      }

      nActive_--;
      spdlog::debug("next job");
      if (!candidates_.empty() || nActive_ == 0)
        cv_.notify_all();
    }
  }

  AppConf pickAnswer() const {
    if (answers_.empty())
      throw std::runtime_error("no satisfied configuration");
    return *std::max_element(answers_.begin(), answers_.end(), Cmp(this));
  }

public:
  Search(std::shared_ptr<QueryBase> query, TraceConf traceConf, SearchConf searchConf)
    : query_(std::move(query))
    , traceConf_(std::move(traceConf))
    , searchConf_(std::move(searchConf))
    , candidates_(Cmp(this)) {
  }

  AppConf run() {
    query_->runBaseline(traceConf_);
    initCandidates();
    for (size_t i = 0; i < searchConf_.nThreads; i++)
      threads_.emplace_back(&Search::searchThread, this);
    for (auto &t : threads_)
      t.join();
    return pickAnswer();
  }
};
