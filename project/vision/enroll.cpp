// Enrolment: takes photos of one person and stores their SFace vectors in gallery.yml
//
// Usage: ./enroll <name> [camera]
// Keys:  SPACE captures | ESC finishes and saves
#include "face_common.hpp"

int main(int argc, char** argv)
{
    if (argc < 2)
    {
        std::cerr << "Usage: ./enroll <name> [camera]" << std::endl;
        return 1;
    }
    const std::string name = argv[1];
    const int camera_index = argc > 2 ? std::stoi(argv[2]) : 0;

    cv::Ptr<cv::FaceDetectorYN> detector;
    cv::Ptr<cv::FaceRecognizerSF> recognizer;
    if (!load_models(detector, recognizer))
        return 1;

    cv::VideoCapture camera;
    if (!open_camera(camera, camera_index))
        return 1;

    // If the person is already in the gallery, the new photos are added to the old ones
    std::vector<Person> people = load_gallery();
    Person* person = nullptr;
    for (auto& p : people)
        if (p.name == name)
            person = &p;
    if (person == nullptr)
    {
        people.push_back(Person{name, {}});
        person = &people.back();
    }
    const size_t before = person->features.size();

    std::cout << "Enrolling '" << name << "' (" << before << " photos already saved).\n"
              << "SPACE captures, ESC finishes. Vary the angle, expression and light.\n";

    cv::Mat frame;
    while (true)
    {
        camera >> frame;
        if (frame.empty())
            continue;

        cv::Mat faces = detect_faces(detector, frame);
        cv::Mat shown = frame.clone();

        // Only captures with exactly 1 face, so the wrong person is never enrolled
        const bool ok = faces.rows == 1;
        const cv::Scalar color = ok ? cv::Scalar(0, 255, 0) : cv::Scalar(0, 0, 255);
        for (int i = 0; i < faces.rows; i++)
        {
            cv::rectangle(shown, face_box(faces.row(i)), color, 2);
            draw_landmarks(shown, faces.row(i), cv::Scalar(0, 255, 255));
        }

        std::string status = ok ? "SPACE to capture"
                                : (faces.rows == 0 ? "No face" : "More than 1 face");
        std::string count = name + ": " + std::to_string(person->features.size()) + " photos";
        cv::putText(shown, count, cv::Point(10, 25), cv::FONT_HERSHEY_SIMPLEX, 0.7, cv::Scalar(255, 255, 255), 2);
        cv::putText(shown, status, cv::Point(10, 55), cv::FONT_HERSHEY_SIMPLEX, 0.7, color, 2);
        cv::imshow("Enrol - " + name, shown);

        int key = cv::waitKey(1);
        if (key == 27)   // ESC
            break;
        if (key == ' ' && ok)
        {
            person->features.push_back(extract_feature(recognizer, frame, faces.row(0)));
            std::cout << "Photo " << person->features.size() << " captured." << std::endl;
        }
    }

    camera.release();
    cv::destroyAllWindows();

    if (person->features.size() == before)
    {
        std::cout << "No new photos: gallery unchanged." << std::endl;
        return 0;
    }
    save_gallery(people);
    std::cout << "Saved to " << GALLERY_FILE << ": '" << name << "' with "
              << person->features.size() << " photos." << std::endl;
    return 0;
}
