# make            builds everything (face_detection, enroll, recognize, yolo_detect)
# make models     downloads the models and ONNX Runtime (./download_models.sh)
# make clean      deletes the executables
CXX      := g++
# -isystem: warnings from OpenCV's own headers are hidden, only ours are shown
CXXFLAGS := -O2 -Wall -Wextra -std=c++17 $(patsubst -I%,-isystem %,$(shell pkg-config --cflags opencv4))
LDLIBS   := $(shell pkg-config --libs opencv4)

# ONNX Runtime (C++), unpacked by ./download_models.sh; only yolo_detect uses it
ORT_DIR  := third_party/onnxruntime

PROGRAMS := face_detection enroll recognize
ifneq ($(wildcard $(ORT_DIR)/include/onnxruntime_cxx_api.h),)
PROGRAMS += yolo_detect
else
$(info ONNX Runtime not found in $(ORT_DIR): skipping yolo_detect (run ./download_models.sh))
endif

all: $(PROGRAMS)

face_detection: main.cpp
	$(CXX) $(CXXFLAGS) $< -o $@ $(LDLIBS)

enroll: enroll.cpp face_common.hpp
	$(CXX) $(CXXFLAGS) $< -o $@ $(LDLIBS)

recognize: recognize.cpp face_common.hpp
	$(CXX) $(CXXFLAGS) $< -o $@ $(LDLIBS)

# rpath: the program finds libonnxruntime.so in third_party without LD_LIBRARY_PATH
yolo_detect: yolo_detect.cpp
	$(CXX) $(CXXFLAGS) -isystem $(ORT_DIR)/include $< -o $@ $(LDLIBS) \
	    -L$(ORT_DIR)/lib -lonnxruntime -Wl,-rpath,'$$ORIGIN/$(ORT_DIR)/lib'

models:
	./download_models.sh

clean:
	rm -f face_detection enroll recognize yolo_detect

.PHONY: all models clean
