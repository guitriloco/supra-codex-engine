#ifndef WRAITH_RESOURCE_MONITOR_H
#define WRAITH_RESOURCE_MONITOR_H

#include <atomic>
#include <string>
#include <thread>

namespace wraith {

/**
 * @brief Monitors CPU and memory usage to prevent resource exhaustion.
 *
 * Periodically samples /proc/self/status (Linux) or equivalent and
 * reports metrics. Can pause task submission if thresholds are exceeded.
 */
class ResourceMonitor {
public:
    explicit ResourceMonitor(double max_memory_mb = 512.0);
    ~ResourceMonitor();

    void start();
    void stop();

    [[nodiscard]] double current_memory_mb() const;
    [[nodiscard]] double current_cpu_percent() const;
    [[nodiscard]] bool is_overloaded() const;
    [[nodiscard]] std::string get_snapshot_json() const;

private:
    void monitoring_loop();
    double read_memory_mb();
    double read_cpu_percent();

    std::thread monitor_thread_;
    std::atomic<bool> running_{false};

    std::atomic<double> current_memory_mb_{0.0};
    std::atomic<double> current_cpu_percent_{0.0};
    std::atomic<double> max_memory_mb_;
    std::atomic<bool> overloaded_{false};
};

} // namespace wraith

#endif // WRAITH_RESOURCE_MONITOR_H