#ifndef WRAITH_TASK_H
#define WRAITH_TASK_H

#include "engine.h"
#include <chrono>
#include <queue>
#include <mutex>
#include <condition_variable>
#include <atomic>

namespace wraith {

/**
 * @brief Internal task wrapper with lifecycle tracking.
 */
struct InternalTask {
    TaskConfig config;
    std::promise<TaskResult> promise;
    std::chrono::steady_clock::time_point created_at;
    std::chrono::steady_clock::time_point started_at;
    int retry_count{0};
    bool is_cancelled{false};
};

/**
 * @brief Thread-safe priority queue for tasks.
 */
class TaskQueue {
public:
    explicit TaskQueue(size_t max_size);
    
    bool push(std::shared_ptr<InternalTask> task);
    std::shared_ptr<InternalTask> pop();
    std::shared_ptr<InternalTask> try_pop();
    size_t size() const;
    bool empty() const;
    void clear();

private:
    struct ComparePriority {
        bool operator()(const std::shared_ptr<InternalTask>& a,
                        const std::shared_ptr<InternalTask>& b) const;
    };

    mutable std::mutex mutex_;
    std::condition_variable cv_;
    std::priority_queue<
        std::shared_ptr<InternalTask>,
        std::vector<std::shared_ptr<InternalTask>>,
        ComparePriority
    > queue_;
    size_t max_size_;
};

} // namespace wraith

#endif // WRAITH_TASK_H