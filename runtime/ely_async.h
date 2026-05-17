#ifndef ELY_ASYNC_H
#define ELY_ASYNC_H

#include <future>
#include <thread>
#include <queue>
#include <mutex>
#include <condition_variable>
#include <functional>
#include <vector>

template <typename T>
class Task {
public:
    Task(std::future<T>&& fut) : future(std::move(fut)) {}
    Task() = default;
    Task(const Task&) = delete;
    Task& operator=(const Task&) = delete;
    Task(Task&& other) noexcept : future(std::move(other.future)) {}
    Task& operator=(Task&& other) noexcept {
        future = std::move(other.future);
        return *this;
    }

    T get() {
        if (!future.valid()) {
            return T{};
        }
        return future.get();
    }

    bool valid() const { return future.valid(); }

private:
    std::future<T> future;
};

class ThreadPool {
public:
    ThreadPool(size_t num_threads = std::thread::hardware_concurrency()) {
        for (size_t i = 0; i < num_threads; ++i) {
            workers.emplace_back([this] { worker(); });
        }
    }
    ~ThreadPool() {
        {
            std::unique_lock<std::mutex> lock(queue_mutex);
            stop = true;
        }
        condition.notify_all();
        for (auto& t : workers) t.join();
    }

    template <typename F, typename... Args>
    auto enqueue(F&& f, Args&&... args) -> std::future<decltype(f(args...))> {
        using return_type = decltype(f(args...));
        auto task = std::make_shared<std::packaged_task<return_type()>>(
            std::bind(std::forward<F>(f), std::forward<Args>(args)...)
        );
        std::future<return_type> res = task->get_future();
        {
            std::unique_lock<std::mutex> lock(queue_mutex);
            tasks.emplace([task]() { (*task)(); });
        }
        condition.notify_one();
        return res;
    }

private:
    void worker() {
        while (true) {
            std::function<void()> task;
            {
                std::unique_lock<std::mutex> lock(queue_mutex);
                condition.wait(lock, [this] { return stop || !tasks.empty(); });
                if (stop && tasks.empty()) return;
                task = std::move(tasks.front());
                tasks.pop();
            }
            task();
        }
    }

    std::vector<std::thread> workers;
    std::queue<std::function<void()>> tasks;
    std::mutex queue_mutex;
    std::condition_variable condition;
    bool stop = false;
};

class ElyEventLoop {
public:
    static ElyEventLoop& instance() {
        static ElyEventLoop loop;
        return loop;
    }

    template <typename F, typename... Args>
    auto run(F&& f, Args&&... args) -> Task<decltype(f(args...))> {
        auto fut = pool.enqueue(std::forward<F>(f), std::forward<Args>(args)...);
        return Task<decltype(f(args...))>(std::move(fut));
    }

private:
    ElyEventLoop() : pool(std::thread::hardware_concurrency()) {}
    ThreadPool pool;
};

#endif