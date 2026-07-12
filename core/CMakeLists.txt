cmake_minimum_required(VERSION 3.20)
project(SupraCodexEngine VERSION 0.1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)

# ============================================================================
# WraithEngine Core Library
# ============================================================================
add_library(wraith_core
    src/engine.cpp
    src/task.cpp
    src/scheduler.cpp
    src/module_loader.cpp
    src/resource_monitor.cpp
)

target_include_directories(wraith_core PUBLIC
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
    $<INSTALL_INTERFACE:include>
)

# WraithEngine modules (optional, can be linked selectively)
add_library(wraith_modules
    src/modules/http_scraper.cpp
    src/modules/data_enricher.cpp
    src/modules/rate_limiter.cpp
)

target_include_directories(wraith_modules PUBLIC
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
    $<INSTALL_INTERFACE:include>
)

target_link_libraries(wraith_modules PUBLIC wraith_core)

# ============================================================================
# Dependencies
# ============================================================================

# libcurl for HTTP operations
find_package(CURL REQUIRED)
target_link_libraries(wraith_core PUBLIC CURL::libcurl)
target_link_libraries(wraith_modules PUBLIC CURL::libcurl)

# nlohmann_json for JSON handling
find_package(nlohmann_json REQUIRED)
target_link_libraries(wraith_core PUBLIC nlohmann_json::nlohmann_json)
target_link_libraries(wraith_modules PUBLIC nlohmann_json::nlohmann_json)

# Threading
find_package(Threads REQUIRED)
target_link_libraries(wraith_core PUBLIC Threads::Threads)

# OpenSSL (for HTTPS, hashing)
find_package(OpenSSL REQUIRED)
target_link_libraries(wraith_core PUBLIC OpenSSL::SSL OpenSSL::Crypto)

# spdlog (structured logging)
find_package(spdlog REQUIRED)
target_link_libraries(wraith_core PUBLIC spdlog::spdlog)
target_link_libraries(wraith_modules PUBLIC spdlog::spdlog)

# ============================================================================
# Testing
# ============================================================================
enable_testing()

find_package(GTest REQUIRED)

add_executable(wraith_tests
    tests/test_engine.cpp
    tests/test_task.cpp
    tests/test_scheduler.cpp
    tests/test_http_scraper.cpp
)

target_link_libraries(wraith_tests PRIVATE
    wraith_core
    wraith_modules
    GTest::gtest
    GTest::gtest_main
)

include(GoogleTest)
gtest_discover_tests(wraith_tests)

# ============================================================================
# Install
# ============================================================================
install(TARGETS wraith_core wraith_modules
    LIBRARY DESTINATION lib
    ARCHIVE DESTINATION lib
    RUNTIME DESTINATION bin
)

install(DIRECTORY include/ DESTINATION include)

# ============================================================================
# Options
# ============================================================================
option(BUILD_PYTHON_BINDINGS "Build Python bindings for WraithEngine" OFF)
option(BUILD_TESTS "Build unit tests" ON)

if(BUILD_PYTHON_BINDINGS)
    find_package(Python COMPONENTS Interpreter Development REQUIRED)
    add_subdirectory(../bindings/python ${CMAKE_BINARY_DIR}/bindings/python)
endif()