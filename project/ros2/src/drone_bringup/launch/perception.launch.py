from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import EnvironmentVariable, EqualsSubstitution, LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    detector = LaunchConfiguration('detector')
    return LaunchDescription([
        # The receiver's /dev/videoN differs per machine: export CAMERA_DEVICE to override
        DeclareLaunchArgument('video_device',
                              default_value=EnvironmentVariable('CAMERA_DEVICE',
                                                                default_value='/dev/video2')),
        DeclareLaunchArgument('detector', default_value='aruco'),      # aruco or yolo
        DeclareLaunchArgument('marker_size_m', default_value='0.10'),
        DeclareLaunchArgument('model_path',
                              default_value='/home/dev/ros2_ws/models/yolov8n.onnx'),
        DeclareLaunchArgument('camera_info_url',
                              default_value='file:///home/dev/ros2_ws/config/camera/ratel2.yaml'),

        Node(package='v4l2_camera', executable='v4l2_camera_node', output='screen',
             parameters=[{
                 'video_device': LaunchConfiguration('video_device'),
                 'image_size': [640, 480],
                 'pixel_format': 'YUYV',
                 'camera_info_url': LaunchConfiguration('camera_info_url'),
             }]),

        Node(package='drone_perception', executable='aruco_detector', output='screen',
             condition=IfCondition(EqualsSubstitution(detector, 'aruco')),
             parameters=[{'marker_size_m': LaunchConfiguration('marker_size_m')}]),

        Node(package='drone_perception', executable='yolo_detector', output='screen',
             condition=IfCondition(EqualsSubstitution(detector, 'yolo')),
             parameters=[{'model_path': LaunchConfiguration('model_path')}]),
    ])
