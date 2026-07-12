#include <gtest/gtest.h>
#include "wraith/task.h"

using namespace wraith;

TEST(TaskQueueTest, PushAndPop) {
    TaskQueue queue(100);

    auto task = std::make_shared<InternalTask>();
    task->config.id = "test-1";
    task->config.priority = 5;

    EXPECT_TRUE(queue.push(task));
    EXPECT_EQ(queue.size(), 1);
}

TEST(TaskQueueTest, PriorityOrdering) {
    TaskQueue queue(100);

    auto low = std::make_shared<InternalTask>();
    low->config.id = "low";
    low->config.priority = 1;

    auto high = std::make_shared<InternalTask>();
    high->config.id = "high";
    high->config.priority = 10;

    queue.push(low);
    queue.push(high);

    // High priority should come out first
    auto first = queue.try_pop();
    EXPECT_EQ(first->config.id, "high");

    auto second = queue.try_pop();
    EXPECT_EQ(second->config.id, "low");
}

TEST(TaskQueueTest, QueueFull) {
    TaskQueue queue(1);

    auto task1 = std::make_shared<InternalTask>();
    task1->config.id = "first";
    EXPECT_TRUE(queue.push(task1));

    auto task2 = std::make_shared<InternalTask>();
    task2->config.id = "second";
    EXPECT_FALSE(queue.push(task2)); // Should be rejected
}