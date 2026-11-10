// Minimalny framework testowy (bez zewnetrznych zaleznosci).
#pragma once

#include <cstdio>
#include <functional>
#include <optional>
#include <sstream>
#include <string>
#include <vector>

namespace tf {

struct TestCase {
    const char* name;
    std::function<void()> fn;
};

inline std::vector<TestCase>& registry() {
    static std::vector<TestCase> r;
    return r;
}

inline int& failures() {
    static int f = 0;
    return f;
}

struct Registrar {
    Registrar(const char* name, std::function<void()> fn) { registry().push_back({name, std::move(fn)}); }
};

template <typename T>
std::string show(const T& v) {
    std::ostringstream ss;
    ss << v;
    return ss.str();
}
inline std::string show(const std::string& v) { return "\"" + v + "\""; }
template <typename T>
std::string show(const std::optional<T>& v);
inline std::string show(const char* v) { return show(std::string(v)); }
template <typename T>
std::string show(const std::vector<T>& v) {
    std::string s = "[";
    for (size_t i = 0; i < v.size(); ++i) {
        if (i) s += ", ";
        s += show(v[i]);
    }
    return s + "]";
}
template <typename T>
std::string show(const std::optional<T>& v) {
    return v ? show(*v) : std::string("None");
}

inline void fail(const char* file, int line, const std::string& msg) {
    ++failures();
    std::printf("    BLAD %s:%d: %s\n", file, line, msg.c_str());
}

}  // namespace tf

#define TF_CAT2(a, b) a##b
#define TF_CAT(a, b) TF_CAT2(a, b)
#define TEST(name)                                                              \
    static void TF_CAT(test_fn_, name)();                                       \
    static tf::Registrar TF_CAT(test_reg_, name)(#name, TF_CAT(test_fn_, name)); \
    static void TF_CAT(test_fn_, name)()

#define CHECK(cond)                                         \
    do {                                                    \
        if (!(cond)) tf::fail(__FILE__, __LINE__, #cond);   \
    } while (0)

#define CHECK_EQ(a, b)                                                                                   \
    do {                                                                                                 \
        auto _va = (a);                                                                                  \
        auto _vb = (b);                                                                                  \
        if (!(_va == _vb))                                                                               \
            tf::fail(__FILE__, __LINE__, std::string(#a " == " #b "\n      jest:    ") + tf::show(_va) + \
                                             "\n      oczek.:  " + tf::show(_vb));                       \
    } while (0)

#define CHECK_NEAR(a, b, eps)                                                                              \
    do {                                                                                                   \
        double _va = (a), _vb = (b);                                                                       \
        if (!(std::fabs(_va - _vb) <= (eps)))                                                              \
            tf::fail(__FILE__, __LINE__, std::string(#a " ~= " #b ": ") + tf::show(_va) + " vs " + tf::show(_vb)); \
    } while (0)

#define CHECK_THROWS(expr)                                            \
    do {                                                              \
        bool _thrown = false;                                         \
        try {                                                         \
            (void)(expr);                                             \
        } catch (...) {                                               \
            _thrown = true;                                           \
        }                                                             \
        if (!_thrown) tf::fail(__FILE__, __LINE__, "brak wyjatku: " #expr); \
    } while (0)
