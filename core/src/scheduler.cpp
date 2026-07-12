#include "wraith/scheduler.h"
#include "wraith/modules/modules.h"
#include <spdlog/spdlog.h>
#include <chrono>

namespace wraith {

Scheduler::Scheduler(int num_workers) {
    workers_.reserve(num_workers);
    // Register built-in modules
    register_module("scrape", modules::http_scrape);
    register_module("enrich", modules::data_enrich);
    register_module("rate_limit", modules::rate_limit_check);
}

Scheduler::~Scheduler() {
    stop();
}

void Scheduler::start(TaskQueue& queue) {
    running_ = true;
    for (size_t i = 0; i < workers_.capacity(); ++i) {
        workers_.emplace_back(&Scheduler::worker_loop, this, i, std::ref(queue));
    }
    spdlog::info("Scheduler started with {} workers", workers_.size());
}

void Scheduler::stop() {
    running_ = false;
    for (auto& worker : workers_) {
        if (worker.joinable()) {
            worker.join();
        }
    }
    workers_.clear();
}

void Scheduler::register_module(const std::string& name, ModuleHandler handler) {
    modules_[name] = std::move(handler);
    spdlog::debug("Module '{}' registered", name);
}

bool Scheduler::is_running() const {
    return running_.load();
}

int Scheduler::active_workers() const {
    return static_cast<int>(workers_.size());
}

int Scheduler::queued_count() const {
    return 0; // Queue size is tracked by TaskQueue
}

void Scheduler::worker_loop(int worker_id, TaskQueue& queue) {
    spdlog::debug("Worker {} started", worker_id);

    while (running_.load()) {
        auto task = queue.try_pop();
        if (!task) {
            std::this_thread::sleep_for(std::chrono::milliseconds(10));
            continue;
        }

        if (task->is_cancelled) {
            TaskResult result{};
            result.success = false;
            result.error_message = "Task cancelled";
            task->promise.set_value(std::move(result));
            continue;
        }

        task->started_at = std::chrono::steady_clock::now();
        spdlog::debug("Worker {} executing task {}", worker_id, task->config.id);

        TaskResult result{};
        auto start_time = std::chrono::steady_clock::now();

        // Find the handler for this task type
        auto it = modules_.find(task->config.type);
        if (it != modules_.end()) {
            result = it->second(task->config);
        } else {
            result.success = false;
            result.error_message = "Unknown module type: " + task->config.type;
            result.exit_code = -1;
        }

        auto end_time = std::chrono::steady_clock::now();
        result.execution_time_ms = std::chrono::duration<double, std::milli>(
            end_time - start_time).count();

        task->promise.set_value(std::move(result));
    }

    spdlog::debug("Worker {} stopped", worker_id);
}

} // namespace wraith