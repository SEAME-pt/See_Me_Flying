# make            builds everything (face_detection, enroll, recognize)
# make models     downloads the YuNet and SFace models
# make clean      deletes the executables
CXX      := g++
# -isystem: warnings from OpenCV's own headers are hidden, only ours are shown
CXXFLAGS := -O2 -Wall -Wextra -std=c++17 $(patsubst -I%,-isystem %,$(shell pkg-config --cflags opencv4))
LDLIBS   := $(shell pkg-config --libs opencv4)

PROGRAMS := face_detection enroll recognize

all: $(PROGRAMS)

face_detection: main.cpp
	$(CXX) $(CXXFLAGS) $< -o $@ $(LDLIBS)

enroll: enroll.cpp face_common.hpp
	$(CXX) $(CXXFLAGS) $< -o $@ $(LDLIBS)

recognize: recognize.cpp face_common.hpp
	$(CXX) $(CXXFLAGS) $< -o $@ $(LDLIBS)

models:
	./download_models.sh

clean:
	rm -f $(PROGRAMS)

.PHONY: all models clean
