#include "wraith/resource_monitor.h"
#include <spdlog/spdlog.h>
#include <fstream>
#include <chrono>
#include <thread>
#include <sstream>
#include <cstring>
#include <unistd.h>

namespace wraith {

ResourceMonitor::ResourceMonitor(double max_memory_mb)
    : max_memory_mb_(max_memory_mb) {}

ResourceMonitor::~ResourceMonitor() {
    stop();
}

void ResourceMonitor::start() {
    running_ = true;
    monitor_thread_ = std::thread(&ResourceMonitor::monitoring_loop, this);
    spdlog::debug("Resource monitor started (max {} MB)", max_memory_mb_.load());
}

void ResourceMonitor::stop() {
    running_ = false;
    if (monitor_thread_.joinable()) {
        monitor_thread_.join();
    }
}

double ResourceMonitor::current_memory_mb() const {
    return current_memory_mb_.load();
}

double ResourceMonitor::current_cpu_percent() const {
    return current_cpu_percent_.load();
}

bool ResourceMonitor::is_overloaded() const {
    return overloaded_.load();
}

std::string ResourceMonitor::get_snapshot_json() const {
    std::ostringstream oss;
    oss << "{"
        << "\"memory_mb\": " << current_memory_mb_.load() << ", "
        << "\"cpu_percent\": " << current_cpu_percent_.load() << ", "
        << "\"overloaded\": " << (overloaded_.load() ? "true" : "false")
        << "}";
    return oss.str();
}

void ResourceMonitor::monitoring_loop() {
    while (running_.load()) {
        current_memory_mb_ = read_memory_mb();
        current_cpu_percent_ = read_cpu_percent();

        if (current_memory_mb_ > max_memory_mb_.load()) {
            overloaded_ = true;
            spdlog::warn("Memory threshold exceeded: {:.1f} MB / {:.1f} MB",
                         current_memory_mb_.load(), max_memory_mb_.load());
        } else {
            overloaded_ = false;
        }

        std::this_thread::sleep_for(std::chrono::seconds(5));
    }
}

double ResourceMonitor::read_memory_mb() {
    std::ifstream status("/proc/self/status");
    if (!status.is_open()) {
        return 0.0;
    }
    std::string line;
    while (std::getline(status, line)) {
        if (line.substr(0, 6) == "VmRSS:") {
            int kb = 0;
            sscanf(line.c_str(), "VmRSS: %d kB", &kb);
            return static_cast<double>(kb) / 1024.0;
        }
    }
    return 0.0;
}

double ResourceMonitor::read_cpu_percent() {
    // Simple /proc/stat-based CPU usage
    static long prev_total = 0;
    static long prev_idle = 0;

    std::ifstream stat("/proc/stat");
    if (!stat.is_open()) return 0.0;

    std::string line;
    std::getline(stat, line);
    stat.close();

    long user, nice, sys, idle, iowait, irq, softirq, steal;
    sscanf(line.c_str(), "cpu %ld %ld %ld %ld %ld %ld %ld %ld",
           &user, &nice, &sys, &idle, &iowait, &irq, &softirq, &steal);

    long total = user + nice + sys + idle + iowait + irq + softirq + steal;
    long diff_total = total - prev_total;
    long diff_idle = idle - prev_idle;

    prev_total = total;
    prev_idle = idle;

    if (diff_total == 0) return 0.0;
    return 100.0 * (1.0 - static_cast<double>(diff_idle) / diff_total);
}

} // namespace wraith