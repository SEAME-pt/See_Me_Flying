// 03 - Blur, Canny edges and contours: find shapes and their bounding boxes.
// Run: ./build/03_edges_contours data/bus.jpg
#include "common.hpp"

int main(int argc, char** argv) {
    cv::Mat img = cv::imread(argc > 1 ? argv[1] : "data/bus.jpg");
    if (img.empty()) { std::cerr << "Could not read the image\n"; return 1; }

    cv::Mat gray, blurred, edges;
    cv::cvtColor(img, gray, cv::COLOR_BGR2GRAY);
    cv::GaussianBlur(gray, blurred, {5, 5}, 1.5);  // less noise -> fewer false edges
    cv::Canny(blurred, edges, 50, 150);            // low/high hysteresis thresholds

    std::vector<std::vector<cv::Point>> contours;
    cv::findContours(edges, contours, cv::RETR_EXTERNAL, cv::CHAIN_APPROX_SIMPLE);

    cv::Mat out = img.clone();
    int kept = 0;
    for (const auto& c : contours) {
        double area = cv::contourArea(c);
        if (area < 500) continue;  // ignore tiny contours
        ++kept;
        cv::drawContours(out, std::vector<std::vector<cv::Point>>{c}, -1, {0, 255, 0}, 2);
        cv::rectangle(out, cv::boundingRect(c), {0, 0, 255}, 1);

        // Approximate the contour by a polygon: 3 vertices = triangle, 4 = rectangle, ...
        std::vector<cv::Point> poly;
        cv::approxPolyDP(c, poly, 0.02 * cv::arcLength(c, true), true);
        cv::putText(out, std::to_string(poly.size()), cv::boundingRect(c).tl(),
                    cv::FONT_HERSHEY_SIMPLEX, 0.5, {255, 0, 0}, 1);
    }
    std::cout << contours.size() << " contours, " << kept << " with area >= 500\n";

    show("03_edges", edges);
    show("03_contours", out);
    wait();
    return 0;
}
