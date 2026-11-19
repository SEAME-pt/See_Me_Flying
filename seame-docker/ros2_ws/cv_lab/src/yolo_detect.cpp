// YOLO11 / YOLOv8 object detection: ONNX Runtime for inference, OpenCV for everything else.
//
// Run (from the cv_lab folder):
//   ./build/yolo_detect data/bus.jpg            # image -> window + out/result.jpg
//   ./build/yolo_detect data/vtest.avi          # video (Esc to quit)
//   ./build/yolo_detect /dev/video2             # camera (V4L2), e.g. the FPV receiver; "2" also works
// Options after the input: --model models/yolo11n.onnx --conf 0.25 --nms 0.45 --nogui
//   camera only: --size 720x576 --fps 25 --fourcc YUYV   (defaults = FPV receiver, PAL)
//   a laptop webcam, compressed: --size 640x480 --fps 30 --fourcc MJPG
// Keys in the window: Esc/q quit, s save a snapshot to out/
#include <onnxruntime_cxx_api.h>
#include <opencv2/opencv.hpp>
#include <opencv2/dnn.hpp>   // only for blobFromImage and NMSBoxes
#include <algorithm>
#include <cstdio>
#include <filesystem>
#include <fstream>
#include <iostream>

struct Detection {
    int class_id;
    float confidence;
    cv::Rect box;
};

class YoloDetector {
public:
    explicit YoloDetector(const std::string& model_path)
        : env_(ORT_LOGGING_LEVEL_WARNING, "yolo") {
        Ort::SessionOptions opts;
        opts.SetIntraOpNumThreads(4);
        opts.SetGraphOptimizationLevel(GraphOptimizationLevel::ORT_ENABLE_ALL);
        session_ = std::make_unique<Ort::Session>(env_, model_path.c_str(), opts);

        Ort::AllocatorWithDefaultOptions alloc;
        input_name_ = session_->GetInputNameAllocated(0, alloc).get();
        output_name_ = session_->GetOutputNameAllocated(0, alloc).get();
        auto shape = session_->GetInputTypeInfo(0).GetTensorTypeAndShapeInfo().GetShape();
        input_size_ = shape.size() == 4 && shape[3] > 0 ? static_cast<int>(shape[3]) : 640;
    }

    std::vector<Detection> detect(const cv::Mat& frame, float conf_thr, float nms_thr) {
        // 1) Pad to a square (keeps the aspect ratio), then resize to 640x640.
        int side = std::max(frame.cols, frame.rows);
        cv::Mat square = cv::Mat::zeros(side, side, CV_8UC3);
        frame.copyTo(square(cv::Rect(0, 0, frame.cols, frame.rows)));
        float scale = static_cast<float>(side) / input_size_;

        // 2) BGR uint8 HWC -> RGB float [0,1] NCHW (1x3x640x640).
        cv::Mat blob = cv::dnn::blobFromImage(square, 1.0 / 255.0, cv::Size(input_size_, input_size_),
                                              cv::Scalar(), /*swapRB=*/true, /*crop=*/false);

        // 3) Run the network.
        std::array<int64_t, 4> in_shape{1, 3, input_size_, input_size_};
        auto mem = Ort::MemoryInfo::CreateCpu(OrtArenaAllocator, OrtMemTypeDefault);
        Ort::Value input = Ort::Value::CreateTensor<float>(mem, blob.ptr<float>(), blob.total(),
                                                           in_shape.data(), in_shape.size());
        const char* in_names[] = {input_name_.c_str()};
        const char* out_names[] = {output_name_.c_str()};
        auto outputs = session_->Run(Ort::RunOptions{nullptr}, in_names, &input, 1, out_names, 1);

        // 4) Output is 1 x (4 + classes) x anchors, e.g. 1x84x8400:
        //    per anchor (column): cx, cy, w, h, then one score per class.
        auto out_shape = outputs[0].GetTensorTypeAndShapeInfo().GetShape();
        const int rows = static_cast<int>(out_shape[1]);
        const int anchors = static_cast<int>(out_shape[2]);
        cv::Mat preds(rows, anchors, CV_32F, outputs[0].GetTensorMutableData<float>());
        preds = preds.t();  // anchors x 84: one row per candidate box

        std::vector<cv::Rect> boxes;
        std::vector<float> scores;
        std::vector<int> ids;
        for (int i = 0; i < preds.rows; ++i) {
            const float* r = preds.ptr<float>(i);
            cv::Mat cls(1, rows - 4, CV_32F, const_cast<float*>(r + 4));
            cv::Point best;
            double score;
            cv::minMaxLoc(cls, nullptr, &score, nullptr, &best);
            if (score < conf_thr) continue;
            float cx = r[0] * scale, cy = r[1] * scale, w = r[2] * scale, h = r[3] * scale;
            boxes.emplace_back(int(cx - w / 2), int(cy - h / 2), int(w), int(h));
            scores.push_back(static_cast<float>(score));
            ids.push_back(best.x);
        }

        // 5) Non-Maximum Suppression: drop overlapping boxes of the same object.
        std::vector<int> keep;
        cv::dnn::NMSBoxes(boxes, scores, conf_thr, nms_thr, keep);
        std::vector<Detection> dets;
        cv::Rect bounds(0, 0, frame.cols, frame.rows);
        for (int k : keep) dets.push_back({ids[k], scores[k], boxes[k] & bounds});
        return dets;
    }

private:
    Ort::Env env_;
    std::unique_ptr<Ort::Session> session_;
    std::string input_name_, output_name_;
    int input_size_ = 640;
};

static std::vector<std::string> load_names(const std::string& path) {
    std::vector<std::string> names;
    std::ifstream f(path);
    for (std::string line; std::getline(f, line);)
        if (!line.empty()) names.push_back(line);
    return names;
}

static void draw(cv::Mat& frame, const std::vector<Detection>& dets,
                 const std::vector<std::string>& names) {
    for (const auto& d : dets) {
        cv::Scalar color((d.class_id * 67 + 80) % 256, (d.class_id * 131 + 160) % 256, (d.class_id * 29 + 60) % 256);
        cv::rectangle(frame, d.box, color, 2);
        std::string label = (d.class_id < (int)names.size() ? names[d.class_id] : std::to_string(d.class_id))
                          + cv::format(" %.2f", d.confidence);
        int base = 0;
        cv::Size ts = cv::getTextSize(label, cv::FONT_HERSHEY_SIMPLEX, 0.5, 1, &base);
        cv::Point org(d.box.x, std::max(d.box.y, ts.height + 4));
        cv::rectangle(frame, org + cv::Point(0, -ts.height - 4), org + cv::Point(ts.width, 2), color, cv::FILLED);
        cv::putText(frame, label, org + cv::Point(0, -2), cv::FONT_HERSHEY_SIMPLEX, 0.5, {255, 255, 255}, 1);
    }
}

int main(int argc, char** argv) {
    std::string input = argc > 1 ? argv[1] : "data/bus.jpg";
    std::string model = "models/yolo11n.onnx";
    float conf = 0.25f, nms = 0.45f;
    int cam_w = 720, cam_h = 576;
    double cam_fps = 25.0;
    std::string cam_fourcc = "YUYV";
    const char* disp = std::getenv("DISPLAY");
    bool gui = disp && *disp;
    for (int i = 2; i < argc; ++i) {
        std::string a = argv[i];
        if (a == "--model" && i + 1 < argc) model = argv[++i];
        else if (a == "--size" && i + 1 < argc) std::sscanf(argv[++i], "%dx%d", &cam_w, &cam_h);
        else if (a == "--fps" && i + 1 < argc) cam_fps = std::stod(argv[++i]);
        else if (a == "--fourcc" && i + 1 < argc) cam_fourcc = argv[++i];
        else if (a == "--conf" && i + 1 < argc) conf = std::stof(argv[++i]);
        else if (a == "--nms" && i + 1 < argc) nms = std::stof(argv[++i]);
        else if (a == "--nogui") gui = false;
    }

    YoloDetector yolo(model);
    auto names = load_names("data/coco.names");
    std::filesystem::create_directories("out");

    std::string ext = std::filesystem::path(input).extension().string();
    bool is_image = ext == ".jpg" || ext == ".jpeg" || ext == ".png" || ext == ".bmp";

    if (is_image) {
        cv::Mat img = cv::imread(input);
        if (img.empty()) { std::cerr << "Could not read " << input << "\n"; return 1; }
        cv::TickMeter tm; tm.start();
        auto dets = yolo.detect(img, conf, nms);
        tm.stop();
        std::cout << dets.size() << " detections in " << tm.getTimeMilli() << " ms\n";
        for (const auto& d : dets)
            std::cout << "  " << names.at(d.class_id) << " " << d.confidence << " " << d.box << "\n";
        draw(img, dets, names);
        cv::imwrite("out/result.jpg", img);
        std::cout << "Saved out/result.jpg\n";
        if (gui) { cv::imshow("yolo", img); cv::waitKey(0); }
        return 0;
    }

    // Camera: "2" or "/dev/video2" (V4L2). Anything else: a video file or a stream URL.
    bool is_camera = std::all_of(input.begin(), input.end(), ::isdigit) || input.rfind("/dev/video", 0) == 0;
    cv::VideoCapture cap;
    if (is_camera) {
        int index = std::stoi(input.substr(input.find_first_of("0123456789")));
        cap.open(index, cv::CAP_V4L2);
        if (cap.isOpened()) {
            // The FPV receiver's native PAL mode (see docs/Doc-ROS2/FPV_Video_Receiver_Setup_UVC_Receiver_to_ROS.md).
            // YUYV = raw (no delay, a lot of USB bandwidth); MJPG = compressed (less bandwidth).
            cam_fourcc.resize(4, ' ');
            cap.set(cv::CAP_PROP_FOURCC, cv::VideoWriter::fourcc(cam_fourcc[0], cam_fourcc[1], cam_fourcc[2], cam_fourcc[3]));
            cap.set(cv::CAP_PROP_FRAME_WIDTH, cam_w);
            cap.set(cv::CAP_PROP_FRAME_HEIGHT, cam_h);
            cap.set(cv::CAP_PROP_FPS, cam_fps);
            // Keep only the newest frame: YOLO is slower than the camera, so a queue would add delay.
            cap.set(cv::CAP_PROP_BUFFERSIZE, 1);
            int f = static_cast<int>(cap.get(cv::CAP_PROP_FOURCC));
            std::cout << "Camera /dev/video" << index << ": " << cap.get(cv::CAP_PROP_FRAME_WIDTH) << "x"
                      << cap.get(cv::CAP_PROP_FRAME_HEIGHT) << " @ " << cap.get(cv::CAP_PROP_FPS) << " fps, "
                      << char(f & 255) << char((f >> 8) & 255) << char((f >> 16) & 255) << char((f >> 24) & 255)
                      << "\n";
        }
    } else {
        cap.open(input);
    }
    if (!cap.isOpened()) {
        std::cerr << "Could not open " << input << "\n";
        if (is_camera)
            std::cerr << "  Is the device in the container (ls /dev/video*)? Is usb_cam already using it?\n";
        return 1;
    }

    cv::Mat frame;
    int n = 0, saved = 0;
    while (cap.read(frame)) {
        cv::TickMeter tm; tm.start();
        auto dets = yolo.detect(frame, conf, nms);
        tm.stop();
        draw(frame, dets, names);
        cv::putText(frame, cv::format("%.1f FPS", 1000.0 / tm.getTimeMilli()), {10, 25},
                    cv::FONT_HERSHEY_SIMPLEX, 0.8, {0, 255, 0}, 2);
        ++n;
        if (gui) {
            cv::imshow("yolo", frame);
            int key = cv::waitKey(1) & 0xFF;
            if (key == 27 || key == 'q') break;  // Esc / q
            if (key == 's') {                    // s: save a snapshot
                std::string path = cv::format("out/snapshot_%03d.jpg", saved++);
                cv::imwrite(path, frame);
                std::cout << "Saved " << path << "\n";
            }
        } else {
            if (n % 20 == 0)
                std::cout << "frame " << n << ": " << dets.size() << " detections, "
                          << tm.getTimeMilli() << " ms\n";
            if (n >= 60) break;  // headless: just a short benchmark
        }
    }
    if (!gui && !frame.empty()) {
        cv::imwrite("out/last_frame.jpg", frame);
        std::cout << "Saved out/last_frame.jpg\n";
    }
    return 0;
}
