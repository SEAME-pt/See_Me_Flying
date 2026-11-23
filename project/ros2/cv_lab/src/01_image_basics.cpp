// 01 - Image basics: read, inspect, convert, resize, crop, draw, save.
// Run: ./build/01_image_basics data/lena.jpg
#include "common.hpp"

int main(int argc, char** argv) {
    cv::Mat img = cv::imread(argc > 1 ? argv[1] : "data/lena.jpg");  // BGR, 8 bits per channel
    if (img.empty()) { std::cerr << "Could not read the image\n"; return 1; }

    std::cout << "size " << img.size() << ", channels " << img.channels()
              << ", depth CV_8U? " << (img.depth() == CV_8U) << "\n";

    // A pixel is a cv::Vec3b in B, G, R order.
    cv::Vec3b px = img.at<cv::Vec3b>(100, 200);  // row (y) first, then column (x)!
    std::cout << "pixel (x=200,y=100) BGR = " << px << "\n";

    cv::Mat gray;
    cv::cvtColor(img, gray, cv::COLOR_BGR2GRAY);

    cv::Mat small;
    cv::resize(img, small, cv::Size(), 0.5, 0.5, cv::INTER_AREA);

    // A crop (ROI) shares memory with the original: changing it changes img too.
    cv::Rect roi(200, 200, 150, 150);
    cv::Mat crop = img(roi).clone();  // .clone() makes an independent copy

    cv::Mat drawing = img.clone();
    cv::rectangle(drawing, roi, {0, 255, 0}, 2);
    cv::circle(drawing, {256, 256}, 40, {0, 0, 255}, 3);
    cv::line(drawing, {0, 0}, {drawing.cols - 1, drawing.rows - 1}, {255, 0, 0}, 2);
    cv::putText(drawing, "OpenCV C++", {10, 30}, cv::FONT_HERSHEY_SIMPLEX, 1.0, {255, 255, 255}, 2);

    show("01_gray", gray);
    show("01_small", small);
    show("01_crop", crop);
    show("01_drawing", drawing);
    std::cout << "Saved to out/01_*.jpg\n";
    wait();
    return 0;
}
