// 04 - Video: read frames, background subtraction (MOG2), boxes around moving things.
// Run: ./build/04_video_motion data/vtest.avi     (Esc to quit, space to pause)
#include "common.hpp"

int main(int argc, char** argv) {
    std::string src = argc > 1 ? argv[1] : "data/vtest.avi";
    cv::VideoCapture cap;
    if (src.size() == 1 && std::isdigit(src[0])) cap.open(src[0] - '0');  // webcam index
    else cap.open(src);
    if (!cap.isOpened()) { std::cerr << "Could not open " << src << "\n"; return 1; }
    std::cout << "FPS " << cap.get(cv::CAP_PROP_FPS) << ", frames " << cap.get(cv::CAP_PROP_FRAME_COUNT) << "\n";

    auto bg = cv::createBackgroundSubtractorMOG2(/*history=*/300, /*varThreshold=*/25, /*shadows=*/true);
    cv::Mat frame, fg;
    int n = 0;
    while (cap.read(frame)) {
        bg->apply(frame, fg);
        cv::threshold(fg, fg, 200, 255, cv::THRESH_BINARY);  // shadows are 127: drop them
        cv::morphologyEx(fg, fg, cv::MORPH_OPEN, cv::getStructuringElement(cv::MORPH_ELLIPSE, {3, 3}));
        cv::dilate(fg, fg, cv::Mat(), {-1, -1}, 2);

        std::vector<std::vector<cv::Point>> contours;
        cv::findContours(fg, contours, cv::RETR_EXTERNAL, cv::CHAIN_APPROX_SIMPLE);
        int movers = 0;
        for (const auto& c : contours)
            if (cv::contourArea(c) > 400) { cv::rectangle(frame, cv::boundingRect(c), {0, 255, 0}, 2); ++movers; }
        cv::putText(frame, cv::format("frame %d  moving: %d", n, movers), {10, 25},
                    cv::FONT_HERSHEY_SIMPLEX, 0.7, {0, 0, 255}, 2);

        if (has_gui()) {
            cv::imshow("04_video", frame);
            cv::imshow("04_foreground", fg);
            int key = cv::waitKey(30);
            if (key == 27) break;
            if (key == ' ') cv::waitKey(0);
        } else if (n == 100) {
            show("04_video", frame);
            show("04_foreground", fg);
            std::cout << "Saved frame 100 to out/04_*.jpg (" << movers << " moving)\n";
            break;
        }
        ++n;
    }
    return 0;
}
