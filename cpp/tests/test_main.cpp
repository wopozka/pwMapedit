#include <cstdio>
#include <cstring>

#include "test_framework.hpp"

int main(int argc, char** argv) {
    const char* filter = argc > 1 ? argv[1] : nullptr;
    int run = 0, failed_tests = 0;
    for (const auto& t : tf::registry()) {
        if (filter && !std::strstr(t.name, filter)) continue;
        int before = tf::failures();
        try {
            t.fn();
        } catch (const std::exception& e) {
            tf::fail(t.name, 0, std::string("nieoczekiwany wyjatek: ") + e.what());
        }
        ++run;
        bool ok = tf::failures() == before;
        if (!ok) ++failed_tests;
        std::printf("%s %s\n", ok ? "[ OK ]" : "[BLAD]", t.name);
    }
    std::printf("\n%d testow, %d nieudanych\n", run, failed_tests);
    return failed_tests ? 1 : 0;
}
