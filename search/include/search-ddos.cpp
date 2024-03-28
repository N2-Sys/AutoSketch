#include <iostream>
#include <fstream>

#include "Query.hpp"
#include "Register.hpp"
#include "Conf.hpp"

#include <spdlog/cfg/env.h>

struct Idx_var_index_9b50 {
  uint32_t v0;
  uint32_t v1;
} __attribute__((packed));

using Idx_var_index_9fa0 = uint32_t;

class Query_ddos : public QueryRecallPrecision<2, Idx_var_index_9fa0> {
  class AppInstance : public AppInstanceBase {
    friend class Query_ddos;

    std::unique_ptr<Register<Idx_var_index_9b50, bool>> table_distinct_table_9c10;
    std::unique_ptr<Register<Idx_var_index_9fa0, uint32_t>> table_reduce_table_d0a0;
    HashSet<Idx_var_index_9fa0> resKeys_;

  protected:
    void process(PktInfo pkt) override {
      bool var_task_mask_95e0;
      Idx_var_index_9b50 var_index_9b50;
      bool var_distinct_query_9c70;
      Idx_var_index_9fa0 var_index_9fa0;
      uint32_t var_count_d130;
      constexpr uint32_t const_count_9f10 = 1;
      constexpr uint32_t const_Thrd_DDOS_d220 = 174;

      var_index_9b50 = {pkt.key.dst_ip, pkt.key.src_ip};
      var_distinct_query_9c70 = table_distinct_table_9c10->get(var_index_9b50);
      if (var_distinct_query_9c70 == false) {
        table_distinct_table_9c10->assign(var_index_9b50, true);
        var_index_9fa0 = pkt.key.dst_ip;
        table_reduce_table_d0a0->add(var_index_9fa0, const_count_9f10);
        var_count_d130 = table_reduce_table_d0a0->get(var_index_9fa0);
        if (var_count_d130 >= const_Thrd_DDOS_d220) {
          // table_distinct_table_d370[var_index_9fa0].calc(op = assign, key = 1w1);
          resKeys_.insert(var_index_9fa0);
        }
      }
    }

    Result switchWin() override {
      auto r = std::move(resKeys_);
      resKeys_.clear();

      table_distinct_table_9c10->reset();
      table_reduce_table_d0a0->reset();

      return r;
    }
  };

protected:
  std::unique_ptr<AppInstanceBase> createInstanceBaseline() override {
    auto p = std::make_unique<AppInstance>();
    p->table_distinct_table_9c10 = std::make_unique<BaselineRegister<Idx_var_index_9b50, bool>>();
    p->table_reduce_table_d0a0 = std::make_unique<BaselineRegister<Idx_var_index_9fa0, uint32_t>>();
    return p;
  }

  std::unique_ptr<AppInstanceBase> createInstance(AppConf c) override {
    auto p = std::make_unique<AppInstance>();
    p->table_distinct_table_9c10 = std::make_unique<BloomFilter<Idx_var_index_9b50>>(c[0].d, c[0].w * (PAGE_SIZE * 8));
    p->table_reduce_table_d0a0 = std::make_unique<CountMin<Idx_var_index_9fa0, uint32_t>>(c[1].d, c[1].w * (PAGE_SIZE * 8 / 32));
    return p;
  }

public:
  using QueryRecallPrecision<2, Idx_var_index_9fa0>::QueryRecallPrecision;
};

int main(int argc, char **argv) {
  try {
    spdlog::cfg::load_env_levels();

    if (argc < 2) {
      std::cerr << fmt::format("usage: {} <config> [--search | --verify]\n", argv[0]);
      return 1;
    }

    Json::Value jConf;
    {
      std::ifstream fs{argv[1]};
      if (!(fs >> jConf))
        throw std::runtime_error("invalid json format");
    }

    if (argc < 3 || strcmp(argv[2], "--search") == 0) {
      auto sConf = jConf["search"];
      auto traceConf = fromJson<TraceConf>(sConf["trace"]);
      auto evalConf = fromJson<RecallPrecisionConf>(sConf["eval"]);
      auto searchConf = fromJson<SearchConf>(sConf["search"]);

      Search<2> search(std::make_unique<Query_ddos>(evalConf), traceConf, searchConf);
      auto appConf = search.run();

      Json::Value jAppConf{Json::objectValue};
      jAppConf["table_distinct_table_9c10"] = toJson(appConf[0]);
      jAppConf["table_reduce_table_d0a0"] = toJson(appConf[1]);

      Json::StreamWriterBuilder writerBuilder;
      writerBuilder["indentation"] = "  ";
      writerBuilder["enableYAMLCompatibility"] = true;
      std::unique_ptr<Json::StreamWriter> writer(writerBuilder.newStreamWriter());
      writer->write(jAppConf, &std::cout);
      std::cout << '\n';
      return 0;

    } else if (strcmp(argv[2], "--verify") == 0) {
      auto vConf = jConf["verify"];
      auto traceConf = fromJson<TraceConf>(vConf["trace"]);
      auto evalConf = fromJson<RecallPrecisionConf>(jConf["search"]["eval"]);
      auto jAppConf = vConf["conf"];
      Query_ddos::AppConf appConf;

      appConf[0] = fromJson<RegConf>(jAppConf["table_distinct_table_9c10"]);
      appConf[1] = fromJson<RegConf>(jAppConf["table_reduce_table_d0a0"]);

      auto query = std::make_unique<Query_ddos>(evalConf);
      query->runBaseline(traceConf);
      bool succ = query->eval(traceConf, appConf);
      std::cout << (succ ? "success\n" : "failure\n");
      return 0;

    } else {
      std::cerr << fmt::format("invalid option '{}'\n", argv[2]);
      return 1;
    }
  } catch (std::runtime_error &e) {
    spdlog::error(e.what());
  } catch (Json::RuntimeError &e) {
    spdlog::error(e.what());
  }

  return 0;
}
