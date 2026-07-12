#ifndef WRAITH_ENGINE_H
#define WRAITH_ENGINE_H

#include <memory>
#include <string>
#include <functional>
#include <future>
#include <vector>

namespace wraith {

/**
 * @brief Represents the result of a task execution.
 */
struct TaskResult {
    bool success;
    std::string data;
    double execution_time_ms;
    std::string error_message;
    int exit_code;
};

/**
 * @brief Configuration for a single task in the engine.
 */
struct TaskConfig {
    std::string id;
    std::string type;           // "scrape", "enrich", "transform", "custom"
    std::string target;         // URL, file path, or target identifier
    std::string payload;        // JSON or raw input data
    int priority;               // Higher = more urgent
    int max_retries;
    int timeout_seconds;
};

/**
 * @brief Engine-level configuration.
 */
struct EngineConfig {
    int max_concurrent_tasks = 4;
    int queue_capacity = 1000;
    int worker_threads = 2;
    bool enable_resource_monitoring = true;
    double max_memory_usage_mb = 512.0;
    std::string log_level = "info";
    std::string temp_directory = "/tmp/wraith";
};

/**
 * @brief Core engine class for executing automation tasks.
 *
 * WraithEngine is the high-performance compute core of Supra-Codex Engine.
 * It manages task scheduling, resource monitoring, and module execution.
 */
class Engine {
public:
    explicit Engine(const EngineConfig& config = {});
    ~Engine();

    // No copy/move
    Engine(const Engine&) = delete;
    Engine& operator=(const Engine&) = delete;

    /**
     * @brief Start the engine and its worker pool.
     */
    void start();

    /**
     * @brief Gracefully stop the engine.
     */
    void stop();

    /**
     * @brief Submit a task for asynchronous execution.
     * @return A future that resolves with the TaskResult.
     */
    std::future<TaskResult> submit_task(const TaskConfig& task);

    /**
     * @brief Check if the engine is currently running.
     */
    [[nodiscard]] bool is_running() const;

    /**
     * @brief Get current engine statistics.
     */
    [[nodiscard]] std::string get_stats_json() const;

    /**
     * @brief Register a custom module by name.
     */
    void register_module(const std::string& name, 
                         std::function<TaskResult(const TaskConfig&)> handler);

private:
    class Impl;
    std::unique_ptr<Impl> pimpl_;
};

} // namespace wraith

#endif // WRAITH_ENGINE_H