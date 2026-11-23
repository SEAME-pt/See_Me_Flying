// 02 - Colour segmentation in HSV, with trackbars to tune the range live.
// Typical use on a drone: find a coloured landing pad or marker.
// Run: ./build/02_color_threshold data/lena.jpg     (keys: q/Esc to quit)
#include "common.hpp"

int main(int argc, char** argv) {
    cv::Mat img = cv::imread(argc > 1 ? argv[1] : "data/lena.jpg");
    if (img.empty()) { std::cerr << "Could not read the image\n"; return 1; }

    cv::Mat hsv;
    cv::cvtColor(img, hsv, cv::COLOR_BGR2HSV);  // H: 0-179, S: 0-255, V: 0-255

    // Default range: reddish/pink tones.
    int h_lo = 160, h_hi = 179, s_lo = 80, s_hi = 255, v_lo = 80, v_hi = 255;
    if (has_gui()) {
        cv::namedWindow("controls", cv::WINDOW_NORMAL);
        cv::createTrackbar("H low", "controls", &h_lo, 179);
        cv::createTrackbar("H high", "controls", &h_hi, 179);
        cv::createTrackbar("S low", "controls", &s_lo, 255);
        cv::createTrackbar("S high", "controls", &s_hi, 255);
        cv::createTrackbar("V low", "controls", &v_lo, 255);
        cv::createTrackbar("V high", "controls", &v_hi, 255);
    }

    while (true) {
        cv::Mat mask;
        cv::inRange(hsv, cv::Scalar(h_lo, s_lo, v_lo), cv::Scalar(h_hi, s_hi, v_hi), mask);

        // Clean the mask: remove specks (open), fill small holes (close).
        cv::Mat k = cv::getStructuringElement(cv::MORPH_ELLIPSE, {5, 5});
        cv::morphologyEx(mask, mask, cv::MORPH_OPEN, k);
        cv::morphologyEx(mask, mask, cv::MORPH_CLOSE, k);

        cv::Mat result;
        img.copyTo(result, mask);  // keep only the pixels inside the mask

        double pct = 100.0 * cv::countNonZero(mask) / mask.total();
        cv::putText(result, cv::format("%.1f%% of pixels", pct), {10, 25},
                    cv::FONT_HERSHEY_SIMPLEX, 0.7, {0, 255, 0}, 2);
        show("02_mask", mask);
        show("02_result", result);

        int key = wait(30);
        if (key == -1 && !has_gui()) { std::cout << "Saved out/02_*.jpg (" << pct << "%)\n"; break; }
        if (key == 'q' || key == 27) break;
    }
    return 0;
}
