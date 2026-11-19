// Small helpers shared by the exercises.
#pragma once
#include <opencv2/opencv.hpp>
#include <cstdlib>
#include <filesystem>
#include <iostream>

// True when there is a screen to open windows on (DISPLAY set and not empty).
inline bool has_gui() {
    const char* d = std::getenv("DISPLAY");
    return d && *d;
}

// Shows the image in a window if there is a screen; always saves it to out/<name>.jpg.
inline void show(const std::string& name, const cv::Mat& img) {
    std::filesystem::create_directories("out");
    cv::imwrite("out/" + name + ".jpg", img);
    if (has_gui()) cv::imshow(name, img);
}

// Waits for a key if there is a screen (0 = forever). Returns the key, or -1.
inline int wait(int ms = 0) {
    return has_gui() ? cv::waitKey(ms) : -1;
}
