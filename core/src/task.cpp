#include "wraith/task.h"

namespace wraith {

TaskQueue::TaskQueue(size_t max_size)
    : max_size_(max_size) {}

bool TaskQueue::push(std::shared_ptr<InternalTask> task) {
    std::lock_guard<std::mutex> lock(mutex_);
    if (queue_.size() >= max_size_) {
        return false;
    }
    queue_.push(std::move(task));
    cv_.notify_one();
    return true;
}

std::shared_ptr<InternalTask> TaskQueue::pop() {
    std::unique_lock<std::mutex> lock(mutex_);
    cv_.wait(lock, [this]() { return !queue_.empty(); });
    auto task = std::move(const_cast<std::shared_ptr<InternalTask>&>(queue_.top()));
    queue_.pop();
    return task;
}

std::shared_ptr<InternalTask> TaskQueue::try_pop() {
    std::lock_guard<std::mutex> lock(mutex_);
    if (queue_.empty()) {
        return nullptr;
    }
    auto task = std::move(const_cast<std::shared_ptr<InternalTask>&>(queue_.top()));
    queue_.pop();
    return task;
}

size_t TaskQueue::size() const {
    std::lock_guard<std::mutex> lock(mutex_);
    return queue_.size();
}

bool TaskQueue::empty() const {
    std::lock_guard<std::mutex> lock(mutex_);
    return queue_.empty();
}

void TaskQueue::clear() {
    std::lock_guard<std::mutex> lock(mutex_);
    while (!queue_.empty()) {
        queue_.pop();
    }
}

bool TaskQueue::ComparePriority::operator()(
    const std::shared_ptr<InternalTask>& a,
    const std::shared_ptr<InternalTask>& b) const
{
    // Higher priority value = higher urgency (processed first)
    return a->config.priority < b->config.priority;
}

} // namespace wraith