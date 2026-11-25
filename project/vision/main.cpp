// Face detection with OpenCV's classic Haar cascade (no deep learning).
// It only finds faces; it does not know whose face it is (see enroll/recognize for that).
//
// Usage: ./face_detection
// Key:   ESC quits
#include <opencv2/opencv.hpp>

#include <iostream>
#include <string>
#include <vector>

// The cascade ships with OpenCV (opencv-data package). If it is not installed,
// ./download_models.sh puts a copy in models/.
const std::vector<std::string> CASCADE_PATHS = {
    "/usr/share/opencv4/haarcascades/haarcascade_frontalface_default.xml",
    "models/haarcascade_frontalface_default.xml",
};

int main()
{
    cv::VideoCapture camera(0, cv::CAP_V4L2);

    if (!camera.isOpened())
    {
        std::cerr << "Could not open the camera." << std::endl;
        return 1;
    }

    camera.set(
        cv::CAP_PROP_FOURCC,
        cv::VideoWriter::fourcc('M', 'J', 'P', 'G')
    );

    camera.set(cv::CAP_PROP_FRAME_WIDTH, 320);
    camera.set(cv::CAP_PROP_FRAME_HEIGHT, 240);
    camera.set(cv::CAP_PROP_FPS, 30);

    cv::CascadeClassifier face_cascade;
    for (const auto& path : CASCADE_PATHS)
        if (face_cascade.load(path))
            break;

    if (face_cascade.empty())
    {
        std::cerr << "Could not load the face cascade. Install opencv-data or run ./download_models.sh."
                  << std::endl;
        return 1;
    }

    cv::Mat frame;
    cv::Mat gray;

    while (true)
    {
        camera >> frame;

        if (frame.empty())
        {
            std::cerr << "Empty frame." << std::endl;
            continue;
        }

        // Converts the image to greyscale
        cv::cvtColor(frame, gray, cv::COLOR_BGR2GRAY);

        std::vector<cv::Rect> faces;

        // Looks for faces in the image
        face_cascade.detectMultiScale(
            gray,
            faces,
            1.1,
            5
        );

        // Draws a rectangle around every face found
        for (size_t i = 0; i < faces.size(); i++)
        {
            cv::rectangle(
                frame,
                faces[i],
                cv::Scalar(0, 255, 0),
                2
            );
        }

        cv::imshow("Camera - Face Detection", frame);

        // ESC quits
        if (cv::waitKey(1) == 27)
            break;
    }

    camera.release();
    cv::destroyAllWindows();

    return 0;
}
