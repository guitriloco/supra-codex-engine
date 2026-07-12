#include "wraith/engine.h"
#include "wraith/scheduler.h"
#include "wraith/resource_monitor.h"
#include "wraith/task.h"
#include <spdlog/spdlog.h>
#include <nlohmann/json.hpp>
#include <chrono>
#include <thread>
#include <sstream>

namespace wraith {

class Engine::Impl {
public:
    explicit Impl(const EngineConfig& config)
        : config_(config)
        , scheduler_(config.worker_threads)
        , task_queue_(config.queue_capacity)
        , resource_monitor_(config.max_memory_usage_mb)
    {}

    void start() {
        spdlog::info("WraithEngine v{} starting...", "0.1.0");
        spdlog::info("Workers: {} | Max concurrent: {} | Queue: {}",
                     config_.worker_threads,
                     config_.max_concurrent_tasks,
                     config_.queue_capacity);

        if (config_.enable_resource_monitoring) {
            resource_monitor_.start();
        }

        scheduler_.start(task_queue_);
        running_ = true;

        spdlog::info("WraithEngine started successfully");
    }

    void stop() {
        spdlog::info("WraithEngine shutting down...");
        running_ = false;

        scheduler_.stop();

        if (config_.enable_resource_monitoring) {
            resource_monitor_.stop();
        }

        task_queue_.clear();
        spdlog::info("WraithEngine stopped");
    }

    std::future<TaskResult> submit_task(const TaskConfig& task) {
        auto internal = std::make_shared<InternalTask>();
        internal->config = task;
        internal->created_at = std::chrono::steady_clock::now();

        auto future = internal->promise.get_future();

        if (!task_queue_.push(std::move(internal))) {
            TaskResult error_result{};
            error_result.success = false;
            error_result.error_message = "Task queue full";
            error_result.exit_code = -1;

            std::promise<TaskResult> error_promise;
            error_promise.set_value(std::move(error_result));
            return error_promise.get_future();
        }

        return future;
    }

    bool is_running() const {
        return running_.load();
    }

    std::string get_stats_json() const {
        nlohmann::json stats;
        stats["running"] = running_.load();
        stats["queue_size"] = task_queue_.size();
        stats["active_workers"] = scheduler_.active_workers();
        stats["memory_mb"] = resource_monitor_.current_memory_mb();
        stats["cpu_percent"] = resource_monitor_.current_cpu_percent();
        stats["overloaded"] = resource_monitor_.is_overloaded();
        return stats.dump(2);
    }

    void register_module(const std::string& name,
                         std::function<TaskResult(const TaskConfig&)> handler) {
        scheduler_.register_module(name, std::move(handler));
    }

private:
    EngineConfig config_;
    TaskQueue task_queue_;
    Scheduler scheduler_;
    ResourceMonitor resource_monitor_;
    std::atomic<bool> running_{false};
};

// ===========================================================================
// Public Engine API
// ===========================================================================

Engine::Engine(const EngineConfig& config)
    : pimpl_(std::make_unique<Impl>(config)) {}

Engine::~Engine() {
    if (is_running()) {
        stop();
    }
}

void Engine::start() { pimpl_->start(); }
void Engine::stop() { pimpl_->stop(); }
std::future<TaskResult> Engine::submit_task(const TaskConfig& task) { return pimpl_->submit_task(task); }
bool Engine::is_running() const { return pimpl_->is_running(); }
std::string Engine::get_stats_json() const { return pimpl_->get_stats_json(); }
void Engine::register_module(const std::string& name,
                              std::function<TaskResult(const TaskConfig&)> handler) {
    pimpl_->register_module(name, std::move(handler));
}

} // namespace wraith