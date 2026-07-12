#include <gtest/gtest.h>
#include "wraith/engine.h"
#include "wraith/modules/modules.h"

using namespace wraith;

TEST(SchedulerTest, ModuleRegistration) {
    EngineConfig config;
    config.worker_threads = 2;

    Engine engine(config);

    bool handler_called = false;
    engine.register_module("custom", [&](const TaskConfig& task) -> TaskResult {
        handler_called = true;
        TaskResult r;
        r.success = true;
        r.data = "handled";
        return r;
    });

    engine.start();

    TaskConfig task;
    task.id = "custom-test";
    task.type = "custom";

    auto future = engine.submit_task(task);
    auto result = future.get();

    EXPECT_TRUE(handler_called);
    EXPECT_TRUE(result.success);
    EXPECT_EQ(result.data, "handled");

    engine.stop();
}

TEST(SchedulerTest, UnknownModule) {
    Engine engine;
    engine.start();

    TaskConfig task;
    task.id = "unknown";
    task.type = "nonexistent";

    auto future = engine.submit_task(task);
    auto result = future.get();

    EXPECT_FALSE(result.success);
    EXPECT_FALSE(result.error_message.empty());

    engine.stop();
}