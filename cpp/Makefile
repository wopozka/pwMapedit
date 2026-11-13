# Budowanie rdzenia C++ pwMapedit (bez zaleznosci od Qt).
#   make            - biblioteka, narzedzie mptool i testy
#   make test       - uruchom testy jednostkowe
#   make compare    - porownaj z wersja Python (wymaga PY=<python z PyQt6> i MP=<plik.mp>)
#   make DEBUG=1    - wersja z sanitizerami (ASan/UBSan)

CXX      ?= g++
CXXFLAGS ?= -std=c++17 -Wall -Wextra -Wpedantic
ifeq ($(DEBUG),1)
  CXXFLAGS += -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer
  LDFLAGS  += -fsanitize=address,undefined
  BUILD    := build-debug
else
  CXXFLAGS += -O2
  BUILD    := build
endif

# Clipper2 (odejmowanie polygonow) - zrodla dolaczone w third_party/clipper2, kompilowane bez naszych ostrzezen
CLIPPER_SRC := $(wildcard third_party/clipper2/src/*.cpp)
CLIPPER_OBJ := $(CLIPPER_SRC:%.cpp=$(BUILD)/%.o)
CPPFLAGS += -isystem third_party/clipper2/include -DPWM_TEST_DATA_DIR='"$(CURDIR)/tests"'

CORE_SRC := $(wildcard core/*.cpp)
CORE_OBJ := $(CORE_SRC:%.cpp=$(BUILD)/%.o) $(CLIPPER_OBJ)
TEST_SRC := $(wildcard tests/*.cpp)
TEST_OBJ := $(TEST_SRC:%.cpp=$(BUILD)/%.o)

all: $(BUILD)/libpwmcore.a $(BUILD)/mptool $(BUILD)/run_tests

$(BUILD)/third_party/%.o: third_party/%.cpp
	@mkdir -p $(dir $@)
	$(CXX) -std=c++17 -O2 -w $(CPPFLAGS) -c $< -o $@

$(BUILD)/%.o: %.cpp $(wildcard core/*.hpp) $(wildcard tests/*.hpp)
	@mkdir -p $(dir $@)
	$(CXX) $(CXXFLAGS) $(CPPFLAGS) -c $< -o $@

$(BUILD)/libpwmcore.a: $(CORE_OBJ)
	ar rcs $@ $^

$(BUILD)/mptool: $(BUILD)/tools/mptool.o $(BUILD)/libpwmcore.a
	$(CXX) $(LDFLAGS) $^ -o $@

$(BUILD)/run_tests: $(TEST_OBJ) $(BUILD)/libpwmcore.a
	$(CXX) $(LDFLAGS) $^ -o $@

test: $(BUILD)/run_tests
	./$(BUILD)/run_tests

PY ?= python3
MP ?= ../tests/wynik.mp
compare: $(BUILD)/mptool
	./tools/compare.sh "$(PY)" "$(MP)" ./$(BUILD)/mptool

clean:
	rm -rf build build-debug

.PHONY: all test compare clean
