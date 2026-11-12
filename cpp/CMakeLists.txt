# Budowanie pwMapedit w C++.
#   cmake -S . -B build-cmake -G Ninja -DCMAKE_BUILD_TYPE=Release
#   cmake --build build-cmake
#   ctest --test-dir build-cmake          (testy rdzenia)
#
# Rdzen (pwmcore), testy i mptool nie wymagaja Qt. GUI (pwmapedit) budowane jest tylko wtedy,
# gdy znaleziono Qt6 (Widgets). Mozna je wylaczyc: -DPWM_BUILD_GUI=OFF.
cmake_minimum_required(VERSION 3.21)
project(pwMapedit LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

if(NOT CMAKE_BUILD_TYPE AND NOT CMAKE_CONFIGURATION_TYPES)
    set(CMAKE_BUILD_TYPE Release CACHE STRING "" FORCE)
endif()

option(PWM_BUILD_GUI "Buduj GUI w Qt6" ON)

if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
    add_compile_options(-Wall -Wextra -Wpedantic)
endif()

# ---- rdzen ----
file(GLOB PWM_CORE_SOURCES CONFIGURE_DEPENDS core/*.cpp)
add_library(pwmcore STATIC ${PWM_CORE_SOURCES})
target_include_directories(pwmcore PUBLIC core)

add_executable(mptool tools/mptool.cpp)
target_link_libraries(mptool PRIVATE pwmcore)

file(GLOB PWM_TEST_SOURCES CONFIGURE_DEPENDS tests/*.cpp)
add_executable(run_tests ${PWM_TEST_SOURCES})
target_link_libraries(run_tests PRIVATE pwmcore)

enable_testing()
add_test(NAME core_tests COMMAND run_tests)

# ---- GUI ----
if(PWM_BUILD_GUI)
    find_package(Qt6 QUIET COMPONENTS Widgets Concurrent)
    if(Qt6_FOUND)
        set(CMAKE_AUTOMOC ON)
        file(GLOB PWM_GUI_SOURCES CONFIGURE_DEPENDS gui/*.cpp gui/*.hpp)
        add_executable(pwmapedit WIN32 ${PWM_GUI_SOURCES})
        target_link_libraries(pwmapedit PRIVATE pwmcore Qt6::Widgets Qt6::Concurrent)
        # Katalog z ikonami z repozytorium - uzywany, gdy obok programu nie ma katalogu icons/.
        get_filename_component(PWM_REPO_DIR "${CMAKE_CURRENT_SOURCE_DIR}/.." ABSOLUTE)
        target_compile_definitions(pwmapedit PRIVATE PWM_SOURCE_ICONS_DIR="${PWM_REPO_DIR}/icons")
    else()
        message(STATUS "Nie znaleziono Qt6 - GUI (pwmapedit) nie bedzie budowane")
    endif()
endif()
