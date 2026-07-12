#ifndef WRAITH_SCHEDULER_H
#define WRAITH_SCHEDULER_H

#include "task.h"
#include <thread>
#include <vector>
#include <functional>
#include <map>

namespace wraith {

/**
 * @brief Manages worker threads and task distribution.
 *
 * The Scheduler owns a pool of worker threads that pick up tasks
 * from the queue and execute them via registered modules.
 */
class Scheduler {
public:
    using ModuleHandler = std::function<TaskResult(const TaskConfig&)>;

    explicit Scheduler(int num_workers = 2);
    ~Scheduler();

    void start(TaskQueue& queue);
    void stop();

    void register_module(const std::string& name, ModuleHandler handler);

    [[nodiscard]] bool is_running() const;
    [[nodiscard]] int active_workers() const;
    [[nodiscard]] int queued_count() const;

private:
    void worker_loop(int worker_id, TaskQueue& queue);

    std::vector<std::thread> workers_;
    std::atomic<bool> running_{false};
    std::map<std::string, ModuleHandler> modules_;
};

} // namespace wraith

#endif // WRAITH_SCHEDULER_H