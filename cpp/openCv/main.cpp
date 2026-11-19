#include <opencv2/opencv.hpp>
#include <iostream>

int main()
{
    cv::VideoCapture camera(0, cv::CAP_V4L2);

    if (!camera.isOpened())
    {
        std::cerr << "Erro ao abrir a camera." << std::endl;
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

    if (!face_cascade.load("haarcascade_frontalface_default.xml"))
    {
        std::cerr << "Erro ao carregar o detector de rosto." << std::endl;
        return 1;
    }

    cv::Mat frame;
    cv::Mat gray;

    while (true)
    {
        camera >> frame;

        if (frame.empty())
        {
            std::cerr << "Frame vazio." << std::endl;
            continue;
        }

        // Converte a imagem para tons de cinza
        cv::cvtColor(frame, gray, cv::COLOR_BGR2GRAY);

        std::vector<cv::Rect> faces;

        // Procura rostos na imagem
        face_cascade.detectMultiScale(
            gray,
            faces,
            1.1,
            5
        );

        // Desenha um retângulo em cada rosto encontrado
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

        // ESC para sair
        if (cv::waitKey(1) == 27)
            break;
    }

    camera.release();
    cv::destroyAllWindows();

    return 0;
}