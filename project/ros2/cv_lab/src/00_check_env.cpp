// Confirms OpenCV is installed and reads an image.
// Run: ./build/00_check_env data/lena.jpg
#include <opencv2/opencv.hpp>
#include <iostream>

int main(int argc, char** argv) {
    std::cout << "OpenCV " << CV_VERSION << "\n";
    std::cout << "Threads: " << cv::getNumThreads() << "\n";

    const std::string path = argc > 1 ? argv[1] : "data/lena.jpg";
    cv::Mat img = cv::imread(path);
    if (img.empty()) {
        std::cerr << "Could not read " << path << "\n";
        return 1;
    }
    std::cout << path << ": " << img.cols << "x" << img.rows
              << ", " << img.channels() << " channels, type " << img.type() << "\n";

    // Only open a window if a display is available.
    if (const char* d = std::getenv("DISPLAY"); d && *d) {
        cv::imshow("check_env", img);
        std::cout << "Press any key in the window to exit.\n";
        cv::waitKey(0);
    }
    return 0;
}
