// Recognition: compares every face on the camera with the people in gallery.yml
//
// Usage: ./recognize [camera] [threshold]
// Key:   ESC quits
#include "face_common.hpp"

int main(int argc, char** argv)
{
    const int camera_index = argc > 1 ? std::stoi(argv[1]) : 0;
    const double threshold = argc > 2 ? std::stod(argv[2]) : COSINE_THRESHOLD;

    cv::Ptr<cv::FaceDetectorYN> detector;
    cv::Ptr<cv::FaceRecognizerSF> recognizer;
    if (!load_models(detector, recognizer))
        return 1;

    std::vector<Person> people = load_gallery();
    if (people.empty())
    {
        std::cerr << "Empty gallery: enrol someone with ./enroll <name>" << std::endl;
        return 1;
    }
    std::cout << "Gallery:";
    for (const auto& p : people)
        std::cout << " " << p.name << " (" << p.features.size() << " photos)";
    std::cout << "\nCosine threshold: " << threshold << ". ESC quits." << std::endl;

    cv::VideoCapture camera;
    if (!open_camera(camera, camera_index))
        return 1;

    cv::TickMeter fps_timer;
    cv::Mat frame;
    while (true)
    {
        fps_timer.start();
        camera >> frame;
        if (frame.empty())
            continue;

        cv::Mat faces = detect_faces(detector, frame);

        for (int i = 0; i < faces.rows; i++)
        {
            cv::Mat feature = extract_feature(recognizer, frame, faces.row(i));

            // Compares with EVERY photo of EVERY person and keeps the highest cosine
            std::string best_name = "Unknown";
            double best_cos = -1.0;
            for (const auto& person : people)
                for (const auto& known : person.features)
                {
                    double cos = recognizer->match(feature, known, cv::FaceRecognizerSF::FR_COSINE);
                    if (cos > best_cos)
                    {
                        best_cos = cos;
                        best_name = person.name;
                    }
                }

            const bool known = best_cos >= threshold;
            const cv::Scalar color = known ? cv::Scalar(0, 255, 0) : cv::Scalar(0, 0, 255);
            const std::string label = (known ? best_name : std::string("Unknown"))
                                    + cv::format(" %.2f", best_cos);

            cv::Rect box = face_box(faces.row(i));
            cv::rectangle(frame, box, color, 2);
            draw_landmarks(frame, faces.row(i), cv::Scalar(0, 255, 255));
            cv::putText(frame, label, cv::Point(box.x, std::max(20, box.y - 8)),
                        cv::FONT_HERSHEY_SIMPLEX, 0.7, color, 2);
        }

        fps_timer.stop();
        cv::putText(frame, cv::format("%.1f FPS", fps_timer.getFPS()), cv::Point(10, 25),
                    cv::FONT_HERSHEY_SIMPLEX, 0.7, cv::Scalar(255, 255, 255), 2);
        cv::imshow("Face recognition", frame);

        if (cv::waitKey(1) == 27)   // ESC
            break;
    }

    camera.release();
    cv::destroyAllWindows();
    return 0;
}
