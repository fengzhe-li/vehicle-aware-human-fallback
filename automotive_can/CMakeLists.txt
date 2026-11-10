cmake_minimum_required(VERSION 3.16)
project(automotive_can LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

add_library(automotive_can src/can_dbc.cpp)
target_include_directories(automotive_can PUBLIC include)
target_compile_options(automotive_can PRIVATE -Wall -Wextra -Wpedantic)

add_executable(automotive_can_tests tests/test_can_dbc.cpp)
target_link_libraries(automotive_can_tests PRIVATE automotive_can)
enable_testing()
add_test(NAME automotive_can_tests COMMAND automotive_can_tests)
