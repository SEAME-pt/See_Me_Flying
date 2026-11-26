// Shared by enroll and recognize: camera, models and gallery.
#pragma once

#include <opencv2/opencv.hpp>
#include <opencv2/objdetect.hpp>

#include <iostream>
#include <string>
#include <vector>

// Files used (relative paths: run the programs from this folder)
const std::string YUNET_MODEL = "models/face_detection_yunet_2023mar.onnx";
const std::string SFACE_MODEL = "models/face_recognition_sface_2021dec.onnx";
const std::string GALLERY_FILE = "gallery.yml";

// Cosine similarity threshold OpenCV recommends for SFace:
// cosine >= 0.363 -> same person
const double COSINE_THRESHOLD = 0.363;

// One enrolled person: the name and one 128-number vector per photo
struct Person
{
    std::string name;
    std::vector<cv::Mat> features;
};

// Opens the camera like main.cpp does (V4L2 + MJPG), but at 640x480:
// with more pixels the face is bigger and YuNet finds it from further away.
inline bool open_camera(cv::VideoCapture& camera, int index = 0)
{
    camera.open(index, cv::CAP_V4L2);
    if (!camera.isOpened())
    {
        std::cerr << "Could not open camera " << index << "." << std::endl;
        return false;
    }
    camera.set(cv::CAP_PROP_FOURCC, cv::VideoWriter::fourcc('M', 'J', 'P', 'G'));
    camera.set(cv::CAP_PROP_FRAME_WIDTH, 640);
    camera.set(cv::CAP_PROP_FRAME_HEIGHT, 480);
    camera.set(cv::CAP_PROP_FPS, 30);
    return true;
}

// Loads both networks. Returns false (with a message) if a model is missing.
inline bool load_models(cv::Ptr<cv::FaceDetectorYN>& detector,
                        cv::Ptr<cv::FaceRecognizerSF>& recognizer)
{
    try
    {
        // score 0.9: only faces with 90% confidence
        // nms 0.3: merges repeated boxes of the same face
        detector = cv::FaceDetectorYN::create(YUNET_MODEL, "", cv::Size(640, 480), 0.9f, 0.3f);
        recognizer = cv::FaceRecognizerSF::create(SFACE_MODEL, "");
    }
    catch (const cv::Exception& e)
    {
        std::cerr << "Could not load the models. Run ./download_models.sh first.\n"
                  << e.what() << std::endl;
        return false;
    }
    return true;
}

// Detects the faces in the frame. Each row of 'faces' has 15 numbers:
// x, y, w, h | right eye (x,y) | left eye (x,y) | nose tip (x,y) |
// right mouth corner (x,y) | left mouth corner (x,y) | score
inline cv::Mat detect_faces(cv::Ptr<cv::FaceDetectorYN>& detector, const cv::Mat& frame)
{
    cv::Mat faces;
    detector->setInputSize(frame.size());
    detector->detect(frame, faces);
    return faces;
}

// Aligns one face (112x112, eyes in the standard position) and extracts its 128-number vector
inline cv::Mat extract_feature(cv::Ptr<cv::FaceRecognizerSF>& recognizer,
                               const cv::Mat& frame, const cv::Mat& face_row)
{
    cv::Mat aligned, feature;
    recognizer->alignCrop(frame, face_row, aligned);
    recognizer->feature(aligned, feature);
    return feature.clone();   // clone: the network may reuse 'feature'
}

inline cv::Rect face_box(const cv::Mat& face_row)
{
    return cv::Rect(int(face_row.at<float>(0, 0)), int(face_row.at<float>(0, 1)),
                    int(face_row.at<float>(0, 2)), int(face_row.at<float>(0, 3)));
}

// Draws the 5 points YuNet found (the ones the alignment uses)
inline void draw_landmarks(cv::Mat& frame, const cv::Mat& face_row, const cv::Scalar& color)
{
    for (int p = 0; p < 5; p++)
    {
        cv::Point pt(int(face_row.at<float>(0, 4 + 2 * p)), int(face_row.at<float>(0, 5 + 2 * p)));
        cv::circle(frame, pt, 2, color, cv::FILLED);
    }
}

// Gallery in YAML:
// people:
//   - name: "Matheus"
//     features: <N x 128 matrix, one row per photo>
inline std::vector<Person> load_gallery(const std::string& path = GALLERY_FILE)
{
    std::vector<Person> people;
    cv::FileStorage fs(path, cv::FileStorage::READ);
    if (!fs.isOpened())
        return people;   // does not exist yet: empty gallery

    for (const auto& node : fs["people"])
    {
        Person person;
        cv::Mat all;
        node["name"] >> person.name;
        node["features"] >> all;
        for (int r = 0; r < all.rows; r++)
            person.features.push_back(all.row(r).clone());
        people.push_back(person);
    }
    return people;
}

inline void save_gallery(const std::vector<Person>& people, const std::string& path = GALLERY_FILE)
{
    cv::FileStorage fs(path, cv::FileStorage::WRITE);
    fs << "people" << "[";
    for (const auto& person : people)
    {
        cv::Mat all;
        cv::vconcat(person.features, all);   // stacks the vectors: N rows x 128
        fs << "{" << "name" << person.name << "features" << all << "}";
    }
    fs << "]";
}
