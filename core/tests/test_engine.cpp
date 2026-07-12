#include <gtest/gtest.h>
#include "wraith/engine.h"

using namespace wraith;

TEST(EngineTest, CreateAndDestroy) {
    EngineConfig config;
    config.max_concurrent_tasks = 2;
    config.worker_threads = 1;

    Engine engine(config);
    EXPECT_FALSE(engine.is_running());
}

TEST(EngineTest, StartAndStop) {
    Engine engine;
    engine.start();
    EXPECT_TRUE(engine.is_running());
    engine.stop();
    EXPECT_FALSE(engine.is_running());
}

TEST(EngineTest, SubmitTask) {
    Engine engine;
    engine.start();

    TaskConfig task;
    task.id = "test-1";
    task.type = "scrape";
    task.target = "https://example.com";
    task.priority = 1;

    auto future = engine.submit_task(task);
    auto result = future.get();

    EXPECT_TRUE(result.success);
    engine.stop();
}

TEST(EngineTest, GetStats) {
    Engine engine;
    engine.start();

    auto stats = engine.get_stats_json();
    EXPECT_FALSE(stats.empty());
    EXPECT_NE(stats.find("running"), std::string::npos);

    engine.stop();
}