// 05 - Classic (pre-deep-learning) detector: Haar cascade for faces.
// Compare it with YOLO later: speed, accuracy, what it can and cannot find.
// Run: ./build/05_face_haar data/lena.jpg
#include "common.hpp"

int main(int argc, char** argv) {
    cv::Mat img = cv::imread(argc > 1 ? argv[1] : "data/lena.jpg");
    if (img.empty()) { std::cerr << "Could not read the image\n"; return 1; }

    // OpenCV's own copy (opencv-data package) first; setup.sh downloads one to models/ as a fallback.
    cv::CascadeClassifier face;
    for (const char* path : {"/usr/share/opencv4/haarcascades/haarcascade_frontalface_default.xml",
                             "models/haarcascade_frontalface_default.xml"})
        if (face.load(path)) break;
    if (face.empty()) {
        std::cerr << "Could not load the cascade: install opencv-data or run ./setup.sh\n";
        return 1;
    }

    cv::Mat gray;
    cv::cvtColor(img, gray, cv::COLOR_BGR2GRAY);
    cv::equalizeHist(gray, gray);  // more robust to lighting

    std::vector<cv::Rect> faces;
    cv::TickMeter tm; tm.start();
    face.detectMultiScale(gray, faces, /*scaleFactor=*/1.1, /*minNeighbors=*/5, 0, /*minSize=*/{40, 40});
    tm.stop();

    std::cout << faces.size() << " face(s) in " << tm.getTimeMilli() << " ms\n";
    for (const auto& f : faces) cv::rectangle(img, f, {0, 255, 0}, 2);
    show("05_faces", img);
    wait();
    return 0;
}
